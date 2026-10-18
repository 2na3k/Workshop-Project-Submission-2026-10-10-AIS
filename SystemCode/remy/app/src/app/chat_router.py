"""Stateless conversational recommendation endpoint."""

from __future__ import annotations

import secrets
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from api.features.calculator.schemas import CostNutritionRequest, IngredientRequest
from workflows.models import TraceEnvelope

from app import composition
from app.chat_contract import (
    ChatRequest,
    DoneEvent,
    ErrorEvent,
    MealDelta,
    MealScopedExplanation,
    MetadataEvent,
    PlanUpdatedEvent,
    TokenEvent,
    from_trace_envelope,
)
from app.sse import serialize_event

router = APIRouter()


def _resolve_services(request: Request) -> tuple[Any, Any]:
    plan_service = getattr(request.app.state, "plan_service", None)
    calculator_service = getattr(request.app.state, "calculator_service", None)
    if plan_service is None or calculator_service is None:
        driver = request.app.state.neo4j_driver
    if plan_service is None:
        plan_service = composition.create_plan_service(driver)
    if calculator_service is None:
        calculator_service = composition.create_calculator_service(driver)
    return plan_service, calculator_service


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


def _scoped_ingredients(envelope: TraceEnvelope, user_context: dict | None) -> list[IngredientRequest]:
    plan_result = envelope.outcome.plan
    days = _member(plan_result, "days", ()) or ()
    if not days and user_context:
        context_plan = user_context.get("plan", user_context)
        days = _member(context_plan, "days", ()) or ()

    requirements: dict[str, list[Any]] = {}
    if envelope.plan_trace is not None:
        for requirement in envelope.plan_trace.requirements:
            requirements.setdefault(requirement.recipe_id, []).append(requirement)

    ingredients: list[IngredientRequest] = []
    for day_value in days:
        for meal in _member(day_value, "meals", ()) or ():
            recipe_id = str(_member(meal, "recipe_id", ""))
            meal_requirements = list(requirements.get(recipe_id, []))
            for ingredient in _member(meal, "ingredients", ()) or ():
                text = _member(ingredient, "text")
                quantity = _member(ingredient, "quantity")
                unit = _member(ingredient, "unit")
                matching = next(
                    (item for item in meal_requirements
                     if item.requirement_text and item.requirement_text == text),
                    None,
                )
                name = (matching.resolved_concept if matching is not None else None) or text
                if name and quantity is not None and unit:
                    ingredients.append(IngredientRequest(
                        name=str(name), quantity=quantity, unit=unit
                    ))
                if matching is not None:
                    meal_requirements.remove(matching)
                if len(ingredients) >= 100:
                    return ingredients
    return ingredients


def _cost_lines(calculation: Any) -> list[str]:
    lines = []
    for item in calculation.itemized:
        warnings = {warning.code for warning in item.warnings}
        if "MISSING_PACKAGE_DATA" in warnings:
            lines.append(
                f"Cost for {item.ingredient}: consumed cost unavailable; "
                "retail package cost unavailable. Warning: MISSING_PACKAGE_DATA."
            )
            continue
        consumed = (
            f"{item.consumed_cost_sgd:.2f}"
            if item.consumed_cost_sgd is not None else "unavailable"
        )
        retail = (
            f"{item.retail_package_cost_sgd:.2f}"
            if item.retail_package_cost_sgd is not None else "unavailable"
        )
        lines.append(
            f"Cost for {item.ingredient}: consumed cost SGD {consumed}; "
            f"retail package cost SGD {retail}."
        )
    return lines


def _explanation_lines(projected: Any) -> list[str]:
    plan = projected.plan
    if plan is None:
        return []
    lines = [f"Plan outcome: {plan.feasibility_outcome}."]
    if plan.reason:
        lines.append(f"Plan reason: {plan.reason}.")
    for binding in plan.binding_constraints:
        lines.append(f"Binding constraint: {binding.scope} {binding.code} ({binding.kind}).")
    for recipe in plan.recipes:
        causes = ", ".join(cause.value for cause in recipe.drop_causes)
        outcome = f"{recipe.outcome} ({causes})" if causes else recipe.outcome
        lines.append(f"Recipe {recipe.recipe_id}: {outcome}.")
        for constraint in recipe.constraints:
            requirement = (
                f" requirement {constraint.requirement_id}"
                if constraint.requirement_id is not None else ""
            )
            resolved = (
                f"; resolved as {constraint.resolved_concept}"
                if constraint.resolved_concept else ""
            )
            offer = ""
            if constraint.selected_offer is not None:
                offer = (
                    f"; offer {constraint.selected_offer.listing_name}"
                    f" from {constraint.selected_offer.retailer}"
                )
            lines.append(
                f"Constraint {constraint.constraint} for recipe {recipe.recipe_id}"
                f"{requirement}: {constraint.state}{resolved}{offer}."
            )
            for warning in constraint.warnings:
                lines.append(f"Warning for recipe {recipe.recipe_id}: {warning}.")
    return lines


def _events(
    payload: ChatRequest,
    envelope: TraceEnvelope,
    projected: Any,
    trace_id: str,
    cost_lines: list[str] | None = None,
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

    text = " ".join(part for part in (
        envelope.outcome.text or "",
        *_explanation_lines(projected),
        *(cost_lines or []),
    ) if part)
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
                delta=MealDelta(day=key[0], slot=key[1], recipe_id=recipe_id),
                explanation=MealScopedExplanation(
                    recipe=recipe,
                    constraints=recipe.constraints,
                ),
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
def chat(payload: ChatRequest, request: Request):
    trace_id = secrets.token_hex(16)
    try:
        plan_service, calculator = _resolve_services(request)
        workflow = composition.create_workflow(plan_service)
        state = workflow.invoke({
            "raw_message": payload.message,
            "user_context": payload.user_context,
        })
        envelope = state if isinstance(state, TraceEnvelope) else state.get("trace")
        if not isinstance(envelope, TraceEnvelope):
            raise TypeError("workflow did not return a TraceEnvelope")
        projected = from_trace_envelope(envelope, trace_id)
        cost_lines = []
        constraints = envelope.parsed_constraints
        if constraints is not None and constraints.cost_query:
            scoped = _scoped_ingredients(envelope, payload.user_context)
            if scoped:
                calculation, _calculation_trace = calculator.calculate(CostNutritionRequest(
                    servings=constraints.servings,
                    ingredients=scoped,
                ))
                cost_lines = _cost_lines(calculation)
        events = _events(payload, envelope, projected, trace_id, cost_lines)
    except Exception:
        events = [ErrorEvent(
            event="error",
            code="WORKFLOW_FAILURE",
            message="The recommendation workflow failed.",
            trace_id=trace_id,
        )]
    return StreamingResponse(_stream(events), media_type="text/event-stream")
