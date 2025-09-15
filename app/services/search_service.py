import json
import uuid

from redis.asyncio import Redis

from app.api.responses.tasks import TaskQueryResponse, SearchResult
from app.infrastructure.adapters.interfaces import ILLMQueue
from app.services.infrastructure import IHybridSearchService
from app.settings.config import Settings


class HybridSearchService(IHybridSearchService):
    """Сервис гибридного поиска"""

    def __init__(self, redis: Redis, queue: ILLMQueue, settings: Settings):
        self.redis = redis
        self.queue = queue
        self.llm_queue_settings = settings.llm_queue
        self.sem_settings = settings.llm_global_sem

    async def enqueue_search(self, query: str, top_k: int) -> TaskQueryResponse:
        """Ставит задачу поиска в очередь."""
        ticket_id = str(uuid.uuid4())
        pack_key = f"{self.llm_queue_settings.ticket_hash_prefix}{ticket_id}:pack"
        result_key = f"{self.llm_queue_settings.ticket_hash_prefix}{ticket_id}:result"
        pack = {
            "type": "search",
            "query": query,
            "top_k": top_k,
        }
        await self.redis.set(
            pack_key, json.dumps(pack, ensure_ascii=False), ex=self.llm_queue_settings.ticket_ttl
        )
        try:
            _, pos = await self.queue.enqueue({"pack_key": pack_key, "result_key": result_key, "ticket_id": ticket_id})
        except OverflowError as e:
            raise Exception("LLM queue overflow, try later") from e
        return TaskQueryResponse(
            task_id=ticket_id,
            url=f"/taskmanager/ticket/{ticket_id}",
            status="queued",
            extra={"position": pos},
        )

    async def get_task_status(self, ticket_id: str) -> TaskQueryResponse:
        """Проверяет статус задачи."""
        status = await self.queue.status(ticket_id)
        result_key = f"{self.llm_queue_settings.ticket_hash_prefix}{ticket_id}:result"
        raw = await self.redis.get(result_key)
        results = None
        answer = None
        if raw:
            # Декодируем bytes в строку
            raw_str = raw.decode('utf-8')
            result_data = json.loads(raw_str)

            if "results" in result_data:
                results = [SearchResult(**r) for r in result_data["results"]]
            if "answer" in result_data:
                answer = result_data["answer"]

        return TaskQueryResponse(
            task_id=ticket_id,
            url=f"/taskmanager/ticket/{ticket_id}",
            status=status.get("state"),
            extra={"position": status.get("approx_position")},
            results=results,
            answer=answer,
        )