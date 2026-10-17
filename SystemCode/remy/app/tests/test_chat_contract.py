import pytest
from pydantic import ValidationError


def test_chat_request_requires_session_and_message():
    from app.chat_contract import ChatRequest

    request = ChatRequest(session_id="session-1", message="Plan meals")
    assert request.model_dump() == {
        "session_id": "session-1",
        "message": "Plan meals",
        "user_context": None,
    }
    assert ChatRequest(session_id="session-1", message="Plan meals", user_context={})

    with pytest.raises(ValidationError):
        ChatRequest(message="Plan meals")
    with pytest.raises(ValidationError):
        ChatRequest(session_id="session-1")


def test_sse_event_type_is_one_of_five():
    from app.chat_contract import DoneEvent, ErrorEvent, MetadataEvent, PlanUpdatedEvent, TokenEvent

    valid_events = (
        MetadataEvent(event="metadata", session_id="s", workflow_node="Plan", trace_id="t"),
        TokenEvent(event="token", delta="hello"),
        PlanUpdatedEvent(
            event="plan_updated",
            delta={"day": 1, "slot": "dinner", "recipe_id": "r1"},
            explanation={"recipe": {"recipe_id": "r1", "outcome": "selected"}, "constraints": []},
        ),
        ErrorEvent(event="error", code="failure", message="Unavailable", trace_id="t"),
        DoneEvent(event="done", status="complete", trace_id="t"),
    )
    assert [item.event for item in valid_events] == ["metadata", "token", "plan_updated", "error", "done"]

    event_types = (MetadataEvent, TokenEvent, PlanUpdatedEvent, ErrorEvent, DoneEvent)
    for event_type in event_types:
        with pytest.raises(ValidationError):
            event_type(event="unknown")
        with pytest.raises(ValidationError):
            event_type(event=valid_events[event_types.index(event_type)].event)


def test_plan_updated_carries_delta_and_scoped_explanation():
    from app.chat_contract import PlanUpdatedEvent

    valid = PlanUpdatedEvent(
        event="plan_updated",
        delta={"day": 1, "slot": "dinner", "recipe_id": "r1"},
        explanation={"recipe": {"recipe_id": "r1", "outcome": "selected"}, "constraints": []},
    )
    assert valid.delta.recipe_id == "r1"
    with pytest.raises(ValidationError):
        PlanUpdatedEvent(event="plan_updated", delta={"day": 1, "slot": "dinner", "recipe_id": "r1"})
    with pytest.raises(ValidationError):
        PlanUpdatedEvent(
            event="plan_updated",
            delta={"day": 1, "slot": "dinner", "recipe_id": "r1"},
            explanation={"plan": {"feasibility_outcome": "feasible"}},
        )


def test_constraint_explanation_fields():
    from app.chat_contract import ConstraintExplanation

    explanation = ConstraintExplanation(
        requirement_id="req-1",
        constraint="vegan",
        state="satisfied",
        resolved_concept="tofu",
        selected_offer=None,
        warnings=["price unavailable"],
    )
    assert explanation.model_dump() == {
        "requirement_id": "req-1",
        "constraint": "vegan",
        "state": "satisfied",
        "resolved_concept": "tofu",
        "selected_offer": None,
        "warnings": ["price unavailable"],
    }


def test_drop_cause_enum_is_closed():
    from app.chat_contract import DropCause

    assert {cause.value for cause in DropCause} == {
        "evidence-absent",
        "present-evidence-excludes",
        "unmapped",
    }
    with pytest.raises(ValueError):
        DropCause("unknown-cause")


def test_r16_floor_is_the_named_field_list():
    from app.chat_contract import CHAT_FORBIDDEN_FIELDS

    assert CHAT_FORBIDDEN_FIELDS == (
        "confidence",
        "normalization_version",
        "source",
        "source_snapshot_id",
        "source_id",
        "mapping_version",
        "food_key",
        "fdc_id",
    )
    assert not any(field.endswith("*_id") for field in CHAT_FORBIDDEN_FIELDS)
    assert not {"recipe_id", "requirement_id", "trace_id", "plan_id", "session_id"}.intersection(
        CHAT_FORBIDDEN_FIELDS
    )


def test_maps_real_trace_envelope_to_explanation():
    from app.chat_contract import from_trace_envelope
    from workflows.models import (
        NamedConstraintView,
        Outcome,
        PlanResult,
        PlanTraceView,
        RecipeOutcomeView,
        RequirementOutcomeView,
    )
    from workflows.trace import assemble_trace

    def make_envelope(*, kind, feasibility, recipes, requirements=(), bindings=(), plan=None, tolerance=0):
        plan_trace = PlanTraceView(
            feasibility_outcome=feasibility,
            reason="No assignment" if feasibility == "infeasible" else None,
            binding_constraints=bindings,
            applied_tolerance_pct=tolerance,
            recipes=recipes,
            requirements=requirements,
        )
        return assemble_trace(
            raw_message="Plan a meal",
            parsed_constraints=None,
            unapplied_constraints=(),
            outcome=Outcome(kind=kind, plan=plan),
            plan_trace=plan_trace,
        )

    requirements = (
        RequirementOutcomeView(
            recipe_id="r1",
            requirement_id="req-1",
            constraint="vegan",
            state="satisfied",
            requirement_text="tofu",
            resolved_concept="tofu",
            selected_offer={"listing_name": "Firm tofu", "retailer": "Market"},
            warnings=("price unavailable",),
        ),
    )
    feasible_env = make_envelope(
        kind="plan",
        feasibility="feasible",
        recipes=(RecipeOutcomeView("r1", "selected"),),
        requirements=requirements,
        plan=PlanResult(plan_id="p1", status="complete", message=None),
    )
    feasible = from_trace_envelope(feasible_env, trace_id="trace-abc")
    assert feasible.trace_id == "trace-abc"
    assert feasible.plan is not None
    assert feasible.plan.recipes[0].constraints[0].selected_offer.listing_name == "Firm tofu"
    assert feasible.plan.recipes[0].constraints[0].warnings == ["price unavailable"]

    causes = ("present-evidence-excludes", "evidence-absent", "unmapped")
    dropped = RecipeOutcomeView("r2", "dropped", cause=causes[0], causes=causes)
    infeasible_env = make_envelope(
        kind="infeasible",
        feasibility="infeasible",
        recipes=(dropped,),
        bindings=(NamedConstraintView("plan", "nutrition.protein", "minimum"),),
    )
    infeasible = from_trace_envelope(infeasible_env, trace_id="trace-infeasible")
    assert infeasible.plan is not None
    assert infeasible.plan.binding_constraints[0].code == "nutrition.protein"
    assert [cause.value for cause in infeasible.plan.recipes[0].drop_causes] == list(causes)

    relaxed_env = make_envelope(
        kind="plan",
        feasibility="relaxed",
        recipes=(RecipeOutcomeView("r3", "selected"),),
        plan=PlanResult(
            plan_id="p3",
            status="complete",
            message=None,
            feasibility_outcome="relaxed",
            relaxed=True,
            applied_tolerance_pct=15,
        ),
        tolerance=15,
    )
    relaxed = from_trace_envelope(relaxed_env, trace_id="trace-relaxed")
    assert relaxed.plan is not None
    assert relaxed.plan.relaxed is True
    assert relaxed.plan.applied_tolerance_pct == 15


def test_events_serialize_to_wire_payloads():
    from app.chat_contract import (
        CHAT_FORBIDDEN_FIELDS,
        DoneEvent,
        ErrorEvent,
        MetadataEvent,
        PlanUpdatedEvent,
        from_trace_envelope,
    )
    from workflows.models import Outcome, PlanTraceView, RecipeOutcomeView, RequirementOutcomeView
    from workflows.trace import assemble_trace

    trace = assemble_trace(
        raw_message="Plan a meal",
        parsed_constraints=None,
        unapplied_constraints=(),
        outcome=Outcome(kind="plan"),
        plan_trace=PlanTraceView(
            feasibility_outcome="feasible",
            reason=None,
            recipes=(RecipeOutcomeView("r1", "selected"),),
            requirements=(
                RequirementOutcomeView(
                    recipe_id="r1",
                    requirement_id="req-1",
                    constraint="vegan",
                    state="satisfied",
                    requirement_text="tofu",
                    resolved_concept="tofu",
                    selected_offer=None,
                    warnings=(),
                ),
            ),
        ),
    )
    mapped = from_trace_envelope(trace, trace_id="trace-wire")
    recipe = mapped.plan.recipes[0]
    constraint = recipe.constraints[0]
    events = (
        MetadataEvent(event="metadata", session_id="s1", workflow_node="Plan", trace_id=mapped.trace_id),
        PlanUpdatedEvent(
            event="plan_updated",
            delta={"day": 1, "slot": "dinner", "recipe_id": recipe.recipe_id},
            explanation={"recipe": recipe, "constraints": [constraint]},
        ),
        DoneEvent(event="done", status="complete", trace_id=mapped.trace_id),
        ErrorEvent(event="error", code="WORKFLOW_FAILURE", message="failed", trace_id=mapped.trace_id),
    )
    payloads = [event.model_dump() for event in events]
    assert [payload["event"] for payload in payloads] == ["metadata", "plan_updated", "done", "error"]
    assert all("trace" not in payload for payload in payloads)

    def keys(value):
        if isinstance(value, dict):
            for key, nested in value.items():
                yield key
                yield from keys(nested)
        elif isinstance(value, list):
            for nested in value:
                yield from keys(nested)

    assert not set(keys(payloads)).intersection(CHAT_FORBIDDEN_FIELDS)
