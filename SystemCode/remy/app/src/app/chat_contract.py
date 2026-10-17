"""User-facing chat request, explanation, and stream event contracts."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from workflows.models import NamedConstraintView, TraceEnvelope


# The first four are R-16's named categories. The remaining four
# (source_snapshot_id, source_id, mapping_version, food_key, fdc_id) are
# additional chat payload exclusions; structural identifiers remain allowed.
CHAT_FORBIDDEN_FIELDS: tuple[str, ...] = (
    "confidence",
    "normalization_version",
    "source",
    "source_snapshot_id",
    "source_id",
    "mapping_version",
    "food_key",
    "fdc_id",
)


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


_CAUSE_PRECEDENCE = {
    DropCause.PRESENT_EVIDENCE_EXCLUDES: 0,
    DropCause.EVIDENCE_ABSENT: 1,
    DropCause.UNMAPPED: 2,
}


def _public_offer(value: object) -> OfferView | None:
    if value is None:
        return None
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="python")
    if isinstance(value, dict):
        return OfferView(listing_name=value["listing_name"], retailer=value["retailer"])
    return OfferView(listing_name=value.listing_name, retailer=value.retailer)  # type: ignore[attr-defined]


def _constraint_explanation(value: object) -> ConstraintExplanation:
    return ConstraintExplanation(
        requirement_id=value.requirement_id,  # type: ignore[attr-defined]
        constraint=value.constraint,  # type: ignore[attr-defined]
        state=value.state,  # type: ignore[attr-defined]
        resolved_concept=value.resolved_concept,  # type: ignore[attr-defined]
        selected_offer=_public_offer(value.selected_offer),  # type: ignore[attr-defined]
        warnings=list(value.warnings),  # type: ignore[attr-defined]
    )


def _recipe_explanation(value: object, requirements: list[ConstraintExplanation]) -> RecipeExplanation:
    raw_causes = value.causes or ((value.cause,) if value.cause else ())  # type: ignore[attr-defined]
    causes = sorted((DropCause(cause) for cause in raw_causes), key=_CAUSE_PRECEDENCE.__getitem__)
    return RecipeExplanation(
        recipe_id=value.recipe_id,  # type: ignore[attr-defined]
        outcome=value.outcome,  # type: ignore[attr-defined]
        drop_causes=causes,
        constraints=requirements,
    )


def from_trace_envelope(env: TraceEnvelope, trace_id: str) -> ChatResponseEnvelope:
    """Project a workflow trace into the explainable user response contract."""
    if env.outcome.kind == "failure":
        message = env.outcome.reason or env.outcome.text or "The recommendation workflow failed."
        response = ChatResponseEnvelope(
            trace_id=trace_id,
            plan=None,
            error=ErrorView(code="WORKFLOW_FAILURE", message=message),
        )
        return response

    trace = env.plan_trace
    recipes = trace.recipes if trace is not None else ()
    requirements = trace.requirements if trace is not None else ()
    grouped: dict[str, list[ConstraintExplanation]] = {}
    for requirement in requirements:
        grouped.setdefault(requirement.recipe_id, []).append(_constraint_explanation(requirement))

    trace_bindings = trace.binding_constraints if trace is not None else ()
    plan = env.outcome.plan
    bindings = trace_bindings or (plan.binding_constraints if plan is not None else ())
    feasibility = trace.feasibility_outcome if trace is not None else (
        plan.feasibility_outcome if plan is not None else env.outcome.kind
    )
    tolerance = trace.applied_tolerance_pct if trace is not None else (
        plan.applied_tolerance_pct if plan is not None else 0
    )
    explanation = PlanExplanation(
        feasibility_outcome=feasibility,
        reason=(trace.reason if trace is not None else None) or env.outcome.reason,
        binding_constraints=list(bindings),
        relaxed=bool(plan and plan.relaxed) or feasibility == "relaxed",
        applied_tolerance_pct=tolerance,
        recipes=[_recipe_explanation(recipe, grouped.get(recipe.recipe_id, [])) for recipe in recipes],
    )
    response = ChatResponseEnvelope(trace_id=trace_id, plan=explanation, error=None)
    serialized = response.model_dump(mode="python")

    def assert_public(value: object) -> None:
        if isinstance(value, dict):
            assert not set(value).intersection(CHAT_FORBIDDEN_FIELDS)
            for nested in value.values():
                assert_public(nested)
        elif isinstance(value, (list, tuple)):
            for nested in value:
                assert_public(nested)

    assert_public(serialized)
    return response
