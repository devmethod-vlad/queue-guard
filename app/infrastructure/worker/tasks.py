import json
import asyncio
from celery import shared_task
from dishka import AsyncContainer
from app.common.storages.interfaces import KeyValueStorageProtocol
from app.infrastructure.adapters.interfaces import ILLMQueue, IRedisSemaphore
from app.infrastructure.worker.worker import run_coroutine  # импортируем общий раннер

@shared_task(name="queue_processor", bind=True, max_retries=3)
def queue_processor(self):
    async def _run():
        print("queue_processor: start polling redis")
        # забрать тикет
        container: AsyncContainer = getattr(self, "container", None)
        if not container:
            raise self.retry(exc=Exception("Dishka container not initialized"), countdown=5)

        queue = await container.get(ILLMQueue)
        ticket_data = await queue.dequeue()
        if not ticket_data:
            print("Queue is empty")
            return None

        ticket_id, payload = ticket_data
        if not isinstance(payload, dict) or "pack_key" not in payload or "result_key" not in payload:
            await queue.set_failed(ticket_id, "Invalid payload: missing pack_key or result_key")
            return None

        pack_key = payload["pack_key"]
        print(pack_key)
        result_key = payload["result_key"]

        storage = await container.get(KeyValueStorageProtocol)
        raw = await storage.get(pack_key)
        if not raw:
            await queue.set_failed(ticket_id, "missing pack")
            print("Queue is empty")
            return None


        try:
            pack = json.loads(raw)
        except json.JSONDecodeError as e:
            await queue.set_failed(ticket_id, f"Invalid pack JSON: {e}")
            print("Invalid pack JSON")
            return None
        if pack.get("type") == "search":
            process_task.delay(self.task_id, ticket_id, pack_key, result_key)
        else:
            await queue.set_failed(ticket_id, f"Unknown task type: {pack.get('type')}")
            print("Unknown task type")
        return None

    return run_coroutine(_run())


@shared_task(name="process_task", bind=True, max_retries=3)
def process_task(self, parent_task_id: str, ticket_id: str, pack_key: str, result_key: str):
    async def _run():
        container: AsyncContainer = getattr(self, "container", None)
        if not container:
            raise self.retry(exc=Exception("Dishka container not initialized"), countdown=5)

        storage = await container.get(KeyValueStorageProtocol)
        queue = await container.get(ILLMQueue)
        sem = await container.get(IRedisSemaphore)

        await queue.set_running(ticket_id, parent_task_id)

        raw = await storage.get(pack_key)
        if not raw:
            await queue.set_failed(ticket_id, "missing pack")
            return {"status": "error", "error": "missing pack"}

        try:
            pack = json.loads(raw)
        except json.JSONDecodeError as e:
            await queue.set_failed(ticket_id, f"Invalid pack JSON: {e}")
            return {"status": "error", "error": "invalid pack JSON"}
        print(result_key)
        query = pack.get("query")
        top_k = pack.get("top_k")
        if not query or not isinstance(top_k, int):
            await queue.set_failed(ticket_id, "Invalid pack: missing query or top_k")
            return {"status": "error", "error": "invalid pack"}

        print(f"Processing search for query: {query}, top_k: {top_k}")

        try:
            async with sem.acquire():
                print(f"Starting AI simulation for {ticket_id}")
                await asyncio.sleep(5)
                print(f"Finished AI simulation for {ticket_id}")
            payload = {"results": [{"id": i, "score": 1.0 - i / top_k} for i in range(top_k)], "answer": query + "_answer"}
            await storage.set(result_key, json.dumps(payload, ensure_ascii=False), ttl=queue.ticket_ttl)
            await queue.set_done(ticket_id)
            return {"status": "ok"}
        except Exception as e:
            await queue.set_failed(ticket_id, str(e))
            raise

    return run_coroutine(_run())
