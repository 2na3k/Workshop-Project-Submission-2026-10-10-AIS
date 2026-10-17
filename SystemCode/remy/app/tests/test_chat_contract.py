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
