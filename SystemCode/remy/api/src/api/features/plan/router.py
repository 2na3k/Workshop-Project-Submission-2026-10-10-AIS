from fastapi import APIRouter, Depends
from .dependencies import get_plan_service
from .schemas import PlanRequest, PlanResponse
from .service import PlanService

router = APIRouter()


@router.post("", response_model=PlanResponse)
def create_plan(
        request: PlanRequest,
        service: PlanService = Depends(get_plan_service)
):
    return service.generate(request)

@router.post("/v2", response_model=PlanResponse)
def create_plan_v2(
        request: PlanRequest,
        service: PlanService = Depends(get_plan_service)
):
    return service.generate_v2(request)
