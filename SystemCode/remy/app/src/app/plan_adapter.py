"""Adapter between API plan models and workflow-owned models."""

from __future__ import annotations

from typing import Any

from api.features.plan.schemas import (
    AllergyRequest,
    DietaryRequest,
    Goal,
    NutrientLimit,
    NutrientRequest,
    PlanRequest,
)
from workflows.models import (
    NamedConstraintView,
    NutrientConstraint,
    PlanInput,
    PlanResult,
    PlanTraceView,
    RecipeOutcomeView,
    RequirementOutcomeView,
)
from workflows.plan_port import PlanPort


class PlanServiceAdapter(PlanPort):
    def __init__(self, service: Any) -> None:
        self._service = service

    def generate(self, request: PlanInput) -> tuple[PlanResult, PlanTraceView]:
        api_request = PlanRequest(
            horizon_days=request.horizon_days,
            meals_per_day=request.meals_per_day,
            servings=request.servings,
            nutrient_tolerance_pct=request.nutrient_tolerance_pct,
            allergies=[AllergyRequest(code=item.code, severity=item.severity) for item in request.allergies] or None,
            dietary=[DietaryRequest(code=item.code) for item in request.dietary] or None,
            nutrients=[self._nutrient(item) for item in request.nutrients] or None,
        )
        returned = self._service.generate(
            api_request,
            drop_uncosted=request.cost_query,
        )
        if not isinstance(returned, tuple) or len(returned) != 2:
            raise TypeError("generate did not return a tuple; P-1 prerequisite missing")
        response, trace = returned
        return self._result(response), self._trace(trace)

    @staticmethod
    def _nutrient(item: NutrientConstraint) -> NutrientRequest:
        limit = NutrientLimit(min=item.minimum, max=item.maximum) if item.minimum is not None or item.maximum is not None else None
        goal = Goal(value=item.goal) if item.goal is not None else None
        return NutrientRequest(code=item.code, unit=item.unit, goal=goal, limit=limit)

    @staticmethod
    def _constraint(value: Any) -> NamedConstraintView:
        return NamedConstraintView(value.scope, value.code, value.kind)

    @staticmethod
    def _recipe(value: Any) -> RecipeOutcomeView:
        return RecipeOutcomeView(value.recipe_id, value.outcome, value.cause, tuple(value.causes))

    @staticmethod
    def _offer(value: Any) -> Any:
        offer = value.selected_offer
        if hasattr(offer, "model_dump"):
            offer = offer.model_dump(mode="python")
        return offer

    @staticmethod
    def _requirement(value: Any) -> RequirementOutcomeView:
        """User-facing requirement outcome. R-16: no audit provenance here."""
        return RequirementOutcomeView(
            value.recipe_id,
            value.requirement_id,
            value.constraint,
            value.state,
            value.requirement_text,
            value.resolved_concept,
            PlanServiceAdapter._offer(value),
            tuple(value.warnings),
        )

    @staticmethod
    def _trace_requirement(value: Any) -> RequirementOutcomeView:
        """Trace requirement outcome, retaining R-16 audit provenance (F-P3-1)."""
        return RequirementOutcomeView(
            value.recipe_id,
            value.requirement_id,
            value.constraint,
            value.state,
            value.requirement_text,
            value.resolved_concept,
            PlanServiceAdapter._offer(value),
            tuple(value.warnings),
            getattr(value, "confidence", None),
            getattr(value, "source_snapshot_id", None),
            getattr(value, "mapping_version", None),
        )

    def _result(self, response: Any) -> PlanResult:
        return PlanResult(
            response.plan_id,
            response.status,
            response.message,
            response.validation_summary,
            response.feasibility_outcome,
            response.relaxed,
            response.applied_tolerance_pct,
            tuple(self._constraint(item) for item in response.binding_constraints or []),
            tuple(item.model_dump(mode="python") if hasattr(item, "model_dump") else item for item in response.relaxations),
            response.horizon_totals,
            tuple(item.model_dump(mode="python") if hasattr(item, "model_dump") else item for item in response.days),
            tuple(self._recipe(item) for item in response.recipe_outcomes),
            tuple(self._requirement(item) for item in response.constraint_outcomes),
        )

    def _trace(self, trace: Any) -> PlanTraceView:
        return PlanTraceView(
            trace.feasibility_outcome,
            trace.reason,
            tuple(self._constraint(item) for item in trace.binding_constraints),
            trace.applied_tolerance_pct,
            tuple(self._recipe(item) for item in trace.recipes),
            tuple(self._trace_requirement(item) for item in trace.requirements),
        )
