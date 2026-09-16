from fastapi import APIRouter, Depends
from .dependencies import get_calculator_service
from .schemas import CostNutritionRequest, CostNutritionResponse
from .service import CostNutritionService

router = APIRouter()


@router.post("/cost-and-nutrition", response_model=CostNutritionResponse)
def calculate_cost_and_nutrition(request: CostNutritionRequest,
                                 service: CostNutritionService = Depends(get_calculator_service)):
    return service.calculate(request)
