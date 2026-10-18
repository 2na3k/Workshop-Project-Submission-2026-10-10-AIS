"""Stateless conversational recommendation endpoint."""

from __future__ import annotations

import secrets
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from workflows.models import TraceEnvelope

from app import composition
from app.chat_contract import (
    ChatRequest,
    DoneEvent,
    ErrorEvent,
    MetadataEvent,
    PlanUpdatedEvent,
    TokenEvent,
    from_trace_envelope,
)
from app.sse import serialize_event

router = APIRouter()


def _plan_service(request: Request) -> Any:
    service = getattr(request.app.state, "plan_service", None)
    if service is not None:
        return service
    return composition.create_plan_service(request.app.state.neo4j_driver)


def _member(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _previous_meals(user_context: dict | None) -> dict[tuple[int, str], str]:
    if not user_context:
        return {}
    plan = user_context.get("plan", user_context)
    previous: dict[tuple[int, str], str] = {}
    for day_value in _member(plan, "days", ()) or ():
        day = _member(day_value, "day")
        for meal in _member(day_value, "meals", ()) or ():
            slot = _member(meal, "slot")
            recipe_id = _member(meal, "recipe_id")
            if day is not None and slot is not None and recipe_id is not None:
                previous[(int(day), str(slot))] = str(recipe_id)
    return previous


def _events(
    payload: ChatRequest,
    envelope: TraceEnvelope,
    projected: Any,
    trace_id: str,
) -> list[Any]:
    if projected.error is not None:
        return [ErrorEvent(
            event="error",
            code=projected.error.code,
            message=projected.error.message,
            trace_id=trace_id,
        )]

    node_runs = envelope.node_runs
    workflow_node = node_runs[-1].node if node_runs else "Workflow"
    events: list[Any] = [MetadataEvent(
        event="metadata",
        session_id=payload.session_id,
        workflow_node=workflow_node,
        trace_id=trace_id,
    )]

    text = envelope.outcome.text or ""
    events.extend(
        TokenEvent(event="token", delta=text[index:index + 40])
        for index in range(0, len(text), 40)
    )

    plan_result = envelope.outcome.plan
    previous = _previous_meals(payload.user_context)
    recipes = {recipe.recipe_id: recipe for recipe in projected.plan.recipes}
    for day_value in _member(plan_result, "days", ()) or ():
        day = _member(day_value, "day")
        for meal in _member(day_value, "meals", ()) or ():
            slot = _member(meal, "slot")
            recipe_id = _member(meal, "recipe_id")
            if day is None or slot is None or recipe_id is None:
                continue
            key = (int(day), str(slot))
            recipe_id = str(recipe_id)
            if previous.get(key) == recipe_id:
                continue
            recipe = recipes.get(recipe_id)
            if recipe is None:
                continue
            events.append(PlanUpdatedEvent(
                event="plan_updated",
                delta={"day": key[0], "slot": key[1], "recipe_id": recipe_id},
                explanation={"recipe": recipe, "constraints": recipe.constraints},
            ))

    events.append(DoneEvent(
        event="done",
        status=projected.plan.feasibility_outcome,
        trace_id=trace_id,
    ))
    return events


def _stream(events: list[Any]) -> Iterator[str]:
    for event in events:
        yield serialize_event(event)


@router.post("/chat")
def chat(payload: ChatRequest, request: Request, plan_service: Any = Depends(_plan_service)):
    trace_id = secrets.token_hex(16)
    try:
        workflow = composition.create_workflow(plan_service)
        state = workflow.invoke({
            "raw_message": payload.message,
            "user_context": payload.user_context,
        })
        envelope = state if isinstance(state, TraceEnvelope) else state.get("trace")
        if not isinstance(envelope, TraceEnvelope):
            raise TypeError("workflow did not return a TraceEnvelope")
        projected = from_trace_envelope(envelope, trace_id)
        events = _events(payload, envelope, projected, trace_id)
    except Exception:
        events = [ErrorEvent(
            event="error",
            code="WORKFLOW_FAILURE",
            message="The recommendation workflow failed.",
            trace_id=trace_id,
        )]
    return StreamingResponse(_stream(events), media_type="text/event-stream")
