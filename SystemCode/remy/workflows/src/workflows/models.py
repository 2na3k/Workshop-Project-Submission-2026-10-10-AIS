"""Workflow-owned contracts for recommendation orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

OutcomeKind = Literal["plan", "infeasible", "failure"]


@dataclass(frozen=True)
class AllergyConstraint:
    code: str
    severity: str | None = None


@dataclass(frozen=True)
class DietaryConstraint:
    code: str


@dataclass(frozen=True)
class NutrientConstraint:
    code: str
    unit: str
    goal: float | None = None
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True)
class ConstraintSet:
    horizon_days: int
    meals_per_day: int
    servings: int = 1
    allergies: tuple[AllergyConstraint, ...] = ()
    dietary: tuple[DietaryConstraint, ...] = ()
    nutrients: tuple[NutrientConstraint, ...] = ()
    nutrient_tolerance_pct: int = 0


@dataclass(frozen=True)
class PlanInput:
    horizon_days: int
    meals_per_day: int
    servings: int = 1
    allergies: tuple[AllergyConstraint, ...] = ()
    dietary: tuple[DietaryConstraint, ...] = ()
    nutrients: tuple[NutrientConstraint, ...] = ()
    nutrient_tolerance_pct: int = 0


@dataclass(frozen=True)
class NamedConstraintView:
    scope: str
    code: str
    kind: str


@dataclass(frozen=True)
class IngredientWarningView:
    code: str
    ingredient_id: str
    detail: str


@dataclass(frozen=True)
class RecipeOutcomeView:
    recipe_id: str
    outcome: str
    cause: str | None = None
    causes: tuple[str, ...] = ()


@dataclass(frozen=True)
class RequirementOutcomeView:
    recipe_id: str
    requirement_id: str | None
    constraint: str
    state: str
    requirement_text: str | None
    resolved_concept: Any = None
    selected_offer: Any = None
    warnings: tuple[str, ...] = ()
    confidence: float | None = None
    source_snapshot_id: str | None = None
    mapping_version: str | None = None


@dataclass(frozen=True)
class PlanTraceView:
    feasibility_outcome: str
    reason: str | None
    binding_constraints: tuple[NamedConstraintView, ...] = ()
    applied_tolerance_pct: int = 0
    recipes: tuple[RecipeOutcomeView, ...] = ()
    requirements: tuple[RequirementOutcomeView, ...] = ()


@dataclass(frozen=True)
class PlanResult:
    plan_id: str | None
    status: str
    message: str | None
    validation_summary: Any = None
    feasibility_outcome: str = "feasible"
    relaxed: bool = False
    applied_tolerance_pct: int = 0
    binding_constraints: tuple[NamedConstraintView, ...] = ()
    relaxations: tuple[Any, ...] = ()
    horizon_totals: Any = None
    days: tuple[Any, ...] = ()
    recipe_outcomes: tuple[RecipeOutcomeView, ...] = ()
    constraint_outcomes: tuple[RequirementOutcomeView, ...] = ()


@dataclass(frozen=True)
class GenerationOutput:
    recipe_ids: tuple[str, ...] = ()
    requirement_ids: tuple[str, ...] = ()
    drop_causes: tuple[str, ...] = ()
    text: str = ""


@dataclass(frozen=True)
class Outcome:
    kind: OutcomeKind
    plan: PlanResult | None = None
    reason: str | None = None
    node: str | None = None
    unapplied_constraints: tuple[str, ...] = ()
    text: str | None = None


@dataclass(frozen=True)
class NodeRun:
    node: str
    outcome: str


@dataclass(frozen=True)
class LLMInvocation:
    node: str
    provider: str
    model: str
    prompt: str
    raw_response: Any
    parsed_response: Any
    duration_ms: float


@dataclass(frozen=True)
class TraceEnvelope:
    schema_version: str
    outcome: Outcome
    raw_message: str
    parsed_constraints: ConstraintSet | None = None
    unapplied_constraints: tuple[str, ...] = ()
    node_runs: tuple[NodeRun, ...] = ()
    llm_invocations: tuple[LLMInvocation, ...] = ()
    plan_trace: PlanTraceView | None = None
