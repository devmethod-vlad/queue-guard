from __future__ import annotations

import json
import time
import typing as tp
import uuid

from redis.asyncio import Redis

from app.infrastructure.adapters.interfaces import ILLMQueue
from app.settings.config import Settings


class LLMQueue(ILLMQueue):
    """Очередь на Redis:
    - LIST: очередь ticket_id (FIFO)
    - HASH: мета по тикету (state, payload, task_id, error ...)
    """

    def __init__(self, redis: Redis, settings: Settings):
        self.redis = redis
        self.qkey = settings.llm_queue.queue_list_key
        self.tprefix = settings.llm_queue.ticket_hash_prefix
        self.max_size = settings.llm_queue.max_size
        self.ticket_ttl = settings.llm_queue.ticket_ttl

    async def enqueue(self, payload: dict[str, tp.Any]) -> tuple[str, int]:
        """Постановка задачи в очередь"""
        n = await self.redis.llen(self.qkey)

        if n is not None and n >= self.max_size:
            raise OverflowError("LLM queue overflow")

        ticket_id = payload["ticket_id"]
        now = int(time.time())
        hkey = f"{self.tprefix}{ticket_id}"
        data = {
            "state": "queued",
            "created_at": now,
            "updated_at": now,
            "payload": json.dumps(payload, ensure_ascii=False),
            "task_id": "",
            "error": "",
        }
        await self.redis.hset(hkey, mapping=data)


        await self.redis.expire(hkey, self.ticket_ttl)
        await self.redis.rpush(self.qkey, ticket_id)
        pos = (await self.redis.llen(self.qkey)) or 0
        print("Задача в очереди")
        print(pos)
        return ticket_id, pos

    async def set_running(self, ticket_id: str, task_id: str) -> None:
        """Установка задачи в статус running"""
        await self.redis.hset(
            f"{self.tprefix}{ticket_id}",
            mapping={"state": "running", "task_id": task_id, "updated_at": int(time.time())},
        )

    async def set_done(self, ticket_id: str) -> None:
        """Установка задачи в статус done"""
        await self.redis.hset(
            f"{self.tprefix}{ticket_id}", mapping={"state": "done", "updated_at": int(time.time())}
        )

    async def set_failed(self, ticket_id: str, error: str) -> None:
        """Установка задачи в статус failed"""
        await self.redis.hset(
            f"{self.tprefix}{ticket_id}",
            mapping={"state": "failed", "error": error, "updated_at": int(time.time())},
        )

    async def dequeue(self) -> tuple[str, dict[str, tp.Any]] | None:
        """Извлечение задачи из начала очереди"""
        print("Извлекаем задачу")

        ticket_id = await self.redis.lpop(self.qkey)


        if not ticket_id:
            print("None ticket")
            return None
        ticket_id = ticket_id.decode()
        hkey = f"{self.tprefix}{ticket_id}"

        data = await self.redis.hgetall(hkey)

        raw = await self.redis.hget(hkey, "payload")

        if raw is None:
            print("Хэш не найден или поле payload отсутствует:", hkey)
            return ticket_id, {}

        payload = json.loads(raw.decode()) if isinstance(raw, (bytes, bytearray)) else json.loads(raw)
        print(ticket_id, payload)
        return ticket_id, payload

    async def status(self, ticket_id: str) -> dict[str, tp.Any]:
        """Получение статуса задачи"""
        hkey = f"{self.tprefix}{ticket_id}"
        data = await self.redis.hgetall(hkey)
        if not data:
            return {"state": "not_found"}
        data = {
            k.decode(): (v.decode() if isinstance(v, (bytes, bytearray)) else v)
            for k, v in data.items()
        }
        qlen = await self.redis.llen(self.qkey) or 0
        data["approx_position"] = qlen
        return data
