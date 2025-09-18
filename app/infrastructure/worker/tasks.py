import json
import asyncio
from celery import shared_task
from dishka import AsyncContainer
from app.common.storages.interfaces import KeyValueStorageProtocol
from app.infrastructure.adapters.interfaces import ILLMQueue, IRedisSemaphore
from app.infrastructure.worker.worker import run_coroutine  # импортируем общий раннер



@shared_task(name="search_task", bind=True, max_retries=3, ignore_result=True)
def process_task(self, ticket_id: str, pack_key: str, result_key: str):
    print("process task")
    async def _run():
        container: AsyncContainer = getattr(self, "container", None)
        if not container:
            raise self.retry(exc=Exception("Dishka container not initialized"), countdown=5)

        storage = await container.get(KeyValueStorageProtocol)
        queue = await container.get(ILLMQueue)
        sem = await container.get(IRedisSemaphore)

        # Отметим в running с id текущей celery-задачи:
        try:
            task_id = getattr(self, "task_id", None) or getattr(self.request, "id", "")
            await queue.set_running(ticket_id, task_id)
        except Exception:
            pass

        raw = await storage.get(pack_key)
        if not raw:
            await queue.set_failed(ticket_id, "missing pack")
            await queue.ack(ticket_id)
            return {"status": "error", "error": "missing pack"}
        try:
            pack = json.loads(raw)
        except json.JSONDecodeError as e:
            await queue.set_failed(ticket_id, f"Invalid pack JSON: {e}")
            await queue.ack(ticket_id)
            return {"status": "error", "error": "invalid pack JSON"}
        query = pack.get("query")
        top_k = pack.get("top_k")
        if not query or not isinstance(top_k, int):
            await queue.set_failed(ticket_id, "Invalid pack: missing query or top_k")
            await queue.ack(ticket_id)
            return {"status": "error", "error": "invalid pack"}
        try:
            async with sem.acquire():
                await asyncio.sleep(5)  # имитация модели
            payload = {"results": [{"id": i, "score": 1.0 - i / top_k} for i in range(top_k)],
                       "answer": query + "_answer"}
            await storage.set(result_key, json.dumps(payload, ensure_ascii=False), ttl=queue.ticket_ttl)
            await queue.set_done(ticket_id)
            return {"status": "ok"}
        except Exception as e:
            await queue.set_failed(ticket_id, str(e))
            raise
        finally:
            try:
                await queue.ack(ticket_id)
            except Exception:
                pass

    return run_coroutine(_run())


@shared_task(name="generate_task", bind=True, max_retries=3, ignore_result=True)
def generate_task(self, ticket_id: str, pack_key: str, result_key: str):
    async def _run():
        container: AsyncContainer = getattr(self, "container", None)
        if not container:
            raise self.retry(exc=Exception("Dishka container not initialized"), countdown=5)

        storage = await container.get(KeyValueStorageProtocol)
        queue = await container.get(ILLMQueue)
        sem = await container.get(IRedisSemaphore)

        # Отметим в running с id текущей celery-задачи:
        try:
            task_id = getattr(self, "task_id", None) or getattr(self.request, "id", "")
            print("set process task runnig for task_id: ", task_id)
            await queue.set_running(ticket_id, task_id)
        except Exception:
            pass

        raw = await storage.get(pack_key)
        print("process task raw")
        if not raw:
            await queue.set_failed(ticket_id, "missing pack")
            await queue.ack(ticket_id)
            return {"status": "error", "error": "missing pack"}
        try:
            pack = json.loads(raw)
        except json.JSONDecodeError as e:
            await queue.set_failed(ticket_id, f"Invalid pack JSON: {e}")
            await queue.ack(ticket_id)
            return {"status": "error", "error": "invalid pack JSON"}
        query = pack.get("query")
        top_k = pack.get("top_k")
        if not query or not isinstance(top_k, int):
            await queue.set_failed(ticket_id, "Invalid pack: missing query or top_k")
            await queue.ack(ticket_id)
            return {"status": "error", "error": "invalid pack"}
        try:
            async with sem.acquire():
                await asyncio.sleep(5)  # имитация модели
            payload = {"results": [{"id": i, "score": 1.0 - i / top_k} for i in range(top_k)],
                       "answer": query + "_answer"}
            await storage.set(result_key, json.dumps(payload, ensure_ascii=False), ttl=queue.ticket_ttl)
            await queue.set_done(ticket_id)
            return {"status": "ok"}
        except Exception as e:
            await queue.set_failed(ticket_id, str(e))
            raise
        finally:
            try:
                await queue.ack(ticket_id)
            except Exception:
                pass

    return run_coroutine(_run())


