import abc
from typing import Optional

from app.api.responses.tasks import TaskQueryResponse, ExampleResponse


class IHybridSearchService(abc.ABC):

    @abc.abstractmethod
    async def enqueue_search(
        self, query: str, top_k: int
    ) -> TaskQueryResponse | list[ExampleResponse]:
        """Семантический поиск"""

    @abc.abstractmethod
    async def enqueue_generate(
            self, query: str, top_k: int, system_prompt: Optional[str]
    ) -> TaskQueryResponse:
        """Постановка задачи генерации в очередь"""
        pass

    @abc.abstractmethod
    async def get_task_status(self, ticket_id: str) -> TaskQueryResponse:
        """Проверяет статус задачи."""
