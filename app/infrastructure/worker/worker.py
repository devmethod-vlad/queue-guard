from __future__ import annotations
import asyncio
import typing as tp
from threading import Thread
from celery import Celery
from typing import TYPE_CHECKING
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

# --- Celery worker ---
worker = Celery(
    'mock_project',
    broker=str(settings.redis.dsn),
    backend=str(settings.redis.dsn),
    include=['app.infrastructure.worker.tasks'],
)

worker.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    task_queues={
        'default': {'exchange': 'default', 'routing_key': 'default'},
        'queue_processor': {'exchange': 'queue_processor', 'routing_key': 'queue_processor'},
    },
    task_routes={
        'queue_processor': {'queue': 'queue_processor'},
        'process_task': {'queue': 'default'},
    },
    beat_schedule={
        'run-queue-processor': {
            'task': 'queue_processor',
            'schedule': 5.0,
        },
    },
    beat_max_loop_interval=30,
)

worker.autodiscover_tasks(["app.infrastructure.worker.tasks"])

# --- Единый event loop ---
loop = asyncio.new_event_loop()


def _start_loop():
    asyncio.set_event_loop(loop)
    loop.run_forever()


Thread(target=_start_loop, daemon=True).start()


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
    async_redis_storage = AsyncRedis.from_url(str(settings.redis.dsn))


@worker_process_init.connect
def on_worker_process_init(**kwargs: dict[str, tp.Any]) -> None:
    run_coroutine(init_redis())
    init_container()


@task_prerun.connect
def on_task_prerun(task: tp.Callable, task_id: str, **kwargs: dict[str, tp.Any]) -> None:
    task.container = container
    task.task_id = task_id



@task_postrun.connect
def on_task_postrun(task_id: str, **kwargs: dict[str, tp.Any]) -> None:
    async def _run():
        existing_keys = await async_redis_storage.lrange(settings.llm_queue.queue_list_key, 0, -1)
        if existing_keys:
            await async_redis_storage.delete(settings.llm_queue.queue_list_key)
            existing_keys = [key for key in existing_keys if key != task_id.encode()]
            if existing_keys:
                await async_redis_storage.lpush(settings.llm_queue.queue_list_key, *existing_keys)

    run_coroutine(_run())


@worker_process_shutdown.connect
def on_worker_process_shutdown(**kwargs: dict[str, tp.Any]) -> None:
    global container, async_redis_storage

    async def _run():
        if container:
            await container.close()
            container = None
        if async_redis_storage:
            await async_redis_storage.close()

    run_coroutine(_run())


async def clear_cache(*additional_keys: str) -> None:
    await async_redis_storage.delete(
        *additional_keys,
        *[key async for key in async_redis_storage.scan_iter(match="celery-task-meta-*")],
        settings.llm_queue.queue_list_key,
    )