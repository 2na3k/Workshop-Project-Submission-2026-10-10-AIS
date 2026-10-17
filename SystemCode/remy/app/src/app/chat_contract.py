"""User-facing chat request, explanation, and stream event contracts."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from workflows.models import NamedConstraintView


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChatRequest(_StrictModel):
    session_id: str
    message: str
    user_context: dict | None = None


class DropCause(str, Enum):
    EVIDENCE_ABSENT = "evidence-absent"
    PRESENT_EVIDENCE_EXCLUDES = "present-evidence-excludes"
    UNMAPPED = "unmapped"


class OfferView(_StrictModel):
    listing_name: str
    retailer: str


class ConstraintExplanation(_StrictModel):
    requirement_id: str | None
    constraint: str
    state: str
    resolved_concept: str | None
    selected_offer: OfferView | None
    warnings: list[str]


class RecipeExplanation(_StrictModel):
    recipe_id: str
    outcome: str
    drop_causes: list[DropCause] = Field(default_factory=list)
    constraints: list[ConstraintExplanation] = Field(default_factory=list)


class PlanExplanation(_StrictModel):
    feasibility_outcome: str
    reason: str | None
    binding_constraints: list[NamedConstraintView]
    relaxed: bool
    applied_tolerance_pct: int
    recipes: list[RecipeExplanation]


class MealDelta(_StrictModel):
    day: int
    slot: str
    recipe_id: str


class MealScopedExplanation(_StrictModel):
    recipe: RecipeExplanation
    constraints: list[ConstraintExplanation]


class MetadataEvent(_StrictModel):
    event: Literal["metadata"]
    session_id: str
    workflow_node: str
    trace_id: str


class TokenEvent(_StrictModel):
    event: Literal["token"]
    delta: str


class PlanUpdatedEvent(_StrictModel):
    event: Literal["plan_updated"]
    delta: MealDelta
    explanation: MealScopedExplanation


class ErrorEvent(_StrictModel):
    event: Literal["error"]
    code: str
    message: str
    trace_id: str | None = None


class DoneEvent(_StrictModel):
    event: Literal["done"]
    status: str
    trace_id: str


class ErrorView(_StrictModel):
    code: str
    message: str


class ChatResponseEnvelope(_StrictModel):
    trace_id: str
    plan: PlanExplanation | None
    error: ErrorView | None
