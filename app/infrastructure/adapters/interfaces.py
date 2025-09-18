import abc
import typing as tp
from collections.abc import Iterable


class IRedisSemaphore(abc.ABC):
    """Глобальный семафор на редисе"""

    @abc.abstractmethod
    async def try_acquire(self, holder: str) -> bool:
        """Попытка захвата семафора"""

    @abc.abstractmethod
    async def heartbeat(self, holder: str) -> None:
        """Обновление времени держателя семафора"""

    @abc.abstractmethod
    async def release(self, holder: str) -> None:
        """Освобождение места семафора"""

    @abc.abstractmethod
    async def acquire(
        self, *, timeout_ms: int | None = None, heartbeat: bool = True
    ) -> tp.AsyncGenerator[tp.Any, None]:
        """Асинхронный контекстный менеджер для захвата семафора"""


class ILLMQueue(abc.ABC):
    """Интерфейс очереди"""

    @abc.abstractmethod
    async def enqueue(self, payload: dict[str, tp.Any]) -> tuple[str, int]:
        """Постановка в очередь задачи"""

    @abc.abstractmethod
    async def set_running(self, ticket_id: str, task_id: str) -> None:
        """Установка задачи в статус running"""

    @abc.abstractmethod
    async def set_done(self, ticket_id: str) -> None:
        """Установка задачи в статус done"""

    @abc.abstractmethod
    async def set_failed(self, ticket_id: str, error: str) -> None:
        """Установка задачи в failed"""

    @abc.abstractmethod
    async def dequeue(self) -> tuple[str, dict[str, tp.Any]] | None:
        """Извлечение из очереди"""

    @abc.abstractmethod
    async def status(self, ticket_id: str) -> dict[str, tp.Any]:
        """Получение статуса задачи"""

    @abc.abstractmethod
    async def dequeue_blocking(self, timeout: int = 0) -> tuple[str, dict[str, tp.Any]] | None:
          """Атомарно: BRPOPLPUSH main -> processing и возврат payload"""

    @ abc.abstractmethod
    async def ack(self, ticket_id: str) -> None:
         """Удалить тикет из processing (LREM)"""