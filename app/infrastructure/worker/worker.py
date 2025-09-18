from __future__ import annotations
import asyncio
import contextlib
import json
import threading
import typing as tp
from threading import Thread
from celery import Celery
from typing import TYPE_CHECKING

from app.common.storages.interfaces import KeyValueStorageProtocol
from app.infrastructure.adapters.interfaces import ILLMQueue

if TYPE_CHECKING:
    from dishka import AsyncContainer
from celery.signals import task_postrun, task_prerun, worker_process_init, worker_process_shutdown
from redis.asyncio import Redis as AsyncRedis
from dishka import AsyncContainer, make_async_container
from app.settings.config import settings, Settings, AppSettings, RedisSettings
from app.infrastructure.ioc import ApplicationProvider
from app.infrastructure.providers import RedisProvider

# --- Глобальные объекты ---
container: AsyncContainer | None = None
async_redis_storage: AsyncRedis | None = None
drain_task: asyncio.Task | None = None

# --- Celery worker ---
worker = Celery(
    'aisearch',
    broker=str(settings.redis.dsn),
    backend=str(settings.redis.dsn),
    include=['app.infrastructure.worker.tasks'],
)

worker.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    task_queues={'default': {'exchange': 'default', 'routing_key': 'default'}},
    task_routes={'search_task': {'queue': 'default'}, "generate_task": {'queue': 'default'}},
    result_expires=600,
)

worker.autodiscover_tasks(["app.infrastructure.worker.tasks"])

# --- Единый event loop ---
loop = asyncio.new_event_loop()



def run_coroutine(coro):
    """Запуск корутин в общем event loop."""
    return asyncio.run_coroutine_threadsafe(coro, loop).result()


# --- Инициализация контейнера и Redis ---
def init_container() -> AsyncContainer:
    global container

    container = make_async_container(
        ApplicationProvider(),
        RedisProvider(),
        context={Settings: settings, AppSettings: settings.app, RedisSettings: settings.redis},
    )
    return container


async def init_redis():
    global async_redis_storage
    print(settings.redis.dsn)
    async_redis_storage = AsyncRedis.from_url(str(settings.redis.dsn))

async def _queue_drain_loop():
    """Фоновая корутина: ждёт тикеты блокирующе и стартует celery-задачи."""

    assert container is not None
    queue = await container.get(ILLMQueue)
    redis = await container.get(KeyValueStorageProtocol)
    while True:

        try:
            print("Drain loop tick...")
            item = await queue.dequeue_blocking(timeout=5)
            print(item)
            if not item:
                print("Not_ITem")
                await asyncio.sleep(0.1)
                continue


            ticket_id, payload = item
            print("___________PAYLOAD___________________")
            print(payload)
            if not isinstance(payload, dict) or "pack_key" not in payload or "result_key" not in payload:
                await queue.set_failed(ticket_id, "Invalid payload: missing pack_key or result_key")
                await queue.ack(ticket_id)

                continue

            pack_key = payload.get("pack_key")
            print(f"Здесь, {pack_key}")
            raw = await redis.get(pack_key)
            print("Здесь 2", raw)
            pack = json.loads(raw)

            task_type = pack.get("type")

            if task_type == "search":
                worker.send_task("search_task",  args=(ticket_id, payload["pack_key"], payload["result_key"]), queue='default',)
            elif task_type == "generate":
                worker.send_task("generate_task", args=(ticket_id, payload["pack_key"], payload["result_key"]), queue='default',)
        except Exception as e:
            print(f"{e} - ошибка в drain queue loop" )
            await asyncio.sleep(1)







@worker_process_init.connect
def on_worker_process_init(**kwargs):
    global drain_task

    asyncio.set_event_loop(loop)  # ставим loop текущим
    init_container()              # создаём контейнер

    # Запуск drain loop в отдельной задаче
    drain_task = asyncio.ensure_future(_queue_drain_loop(), loop=loop)

    # Запуск loop в отдельном потоке
    def _start_loop():
        loop.run_forever()

    threading.Thread(target=_start_loop, daemon=True).start()

@task_prerun.connect
def on_task_prerun(task: tp.Callable, task_id: str, **kwargs: dict[str, tp.Any]) -> None:
    task.container = container
    task.task_id = task_id



@worker_process_shutdown.connect
def on_worker_process_shutdown(**kwargs: dict[str, tp.Any]) -> None:
    global container, async_redis_storage, drain_task

    async def _stop_drain():
        if drain_task:
            drain_task.cancel()
            with contextlib.suppress(Exception):
                await drain_task
    async def _run():
        await _stop_drain()
        if container:
            await container.close()
        if async_redis_storage:
            await async_redis_storage.close()
    run_coroutine(_run())


async def clear_cache(*additional_keys: str) -> None:
    await async_redis_storage.delete(
        *additional_keys,
        *[key async for key in async_redis_storage.scan_iter(match="celery-task-meta-*")],
        settings.llm_queue.queue_list_key,
    )