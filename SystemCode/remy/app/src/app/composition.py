"""Composition-root wiring for the recommendation workflow."""

from __future__ import annotations

from typing import Any

from api.features.calculator.repository import CostNutritionRepository
from api.features.calculator.service import CostNutritionService
from api.features.plan.repository import PlanRepository
from api.features.plan.service import PlanService
from app.plan_adapter import PlanServiceAdapter
from workflows.graph import build
from workflows.llm import ChatLLM


def create_plan_service(driver: Any) -> PlanService:
    return PlanService(PlanRepository(driver))


def create_calculator_service(driver: Any) -> CostNutritionService:
    return CostNutritionService(CostNutritionRepository(driver))


def create_workflow(plan_service: Any, *, extract_llm: Any | None = None,
                    response_llm: Any | None = None):
    return build(
        extract_llm=extract_llm or ChatLLM(format="json"),
        plan_port=(
            plan_service
            if isinstance(plan_service, PlanServiceAdapter)
            else PlanServiceAdapter(plan_service)
        ),
        response_llm=response_llm or ChatLLM(),
    )
