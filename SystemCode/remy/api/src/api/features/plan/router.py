from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from .dependencies import get_plan_service
from .openapi import PLAN_DESCRIPTION, PLAN_RESPONSES
from .schemas import PlanRequest
from .service import PlanService
from .streaming import SSE_HEADERS, stream_plan

router = APIRouter()


@router.post(
    "",
    response_class=StreamingResponse,
    summary="Generate a meal plan (streamed)",
    description=PLAN_DESCRIPTION,
    responses=PLAN_RESPONSES,
)
async def create_plan(
        request: PlanRequest,
        service: PlanService = Depends(get_plan_service)
):
    service.validate(request)
    return StreamingResponse(
        stream_plan(request, service),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
