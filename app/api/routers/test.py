from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse

from app.api.responses.tasks import TaskQueryResponse
from app.services.infrastructure import IHybridSearchService

router = APIRouter(prefix="/test")

@router.post("/search")
@inject
async def search(service: FromDishka[IHybridSearchService], query: str, top_k: int = 5):
    response = await service.enqueue_search(query=query, top_k=top_k)
    return JSONResponse(content=jsonable_encoder(response), status_code=202)



@router.get("/task/{ticket_id}", response_model=TaskQueryResponse)
@inject
async def get_task_status(
    ticket_id: str,
    service: FromDishka[IHybridSearchService] = None,
) -> JSONResponse:
    """Проверяет статус задачи по ticket_id."""
    response = await service.get_task_status(ticket_id)
    return JSONResponse(content=jsonable_encoder(response, exclude_none=True), status_code=200)
