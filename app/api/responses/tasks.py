from pydantic import BaseModel
import typing as tp
class SearchResult(BaseModel):
    """Информация о результате поиска"""

    id: int
    score: float

class HybridSearchResponse(BaseModel):
    """Результаты гибридного поиска"""

    results: list[SearchResult]


class TaskQueryResponse(BaseModel):
    """Информация о задаче"""

    task_id: str
    url: str
    status: tp.Optional[str] = None
    extra: tp.Optional[dict] = None
    answer: tp.Optional[str] = None
    results: tp.Optional[list[SearchResult]] = None


class ExampleResponse(BaseModel):
    """Ответ /example/"""

    id: int
    document: str
    distance: float