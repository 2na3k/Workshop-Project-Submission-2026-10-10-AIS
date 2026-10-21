"""Stateless conversational recommendation endpoint."""

from __future__ import annotations

import asyncio
import logging
import os
import secrets
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from api.features.calculator.schemas import IngredientRequest, CostNutritionRequest
from app import composition
from app.chat_contract import (
    ChatRequest,
    DoneEvent,
    ErrorEvent,
    MealContent,
    MetadataEvent,
    TokenEvent,
    from_trace_envelope, MealDelta, MealScopedExplanation, PlanUpdatedEvent,
)
from app.sse import serialize_event
from workflows.models import TraceEnvelope

router = APIRouter()

logger = logging.getLogger(__name__)


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


def _find_meal(plan: Any, day: int, slot: str, recipe_id: str) -> dict | None:
    """Locate a meal by (day, slot, recipe_id) in the PlanResult days."""
    if plan is None:
        return None
    for day_value in _member(plan, "days", ()) or ():
        if _member(day_value, "day") != day:
            continue
        for meal in _member(day_value, "meals", ()) or ():
            if _member(meal, "slot") == slot and str(_member(meal, "recipe_id")) == recipe_id:
                return {
                    "title": _member(meal, "title", f"Recipe {recipe_id}"),
                    "nutrients": dict(_member(meal, "nutrients", {}) or {}),
                    "ingredients": list(_member(meal, "ingredients", ()) or ()),
                    "instructions": _member(meal, "instructions"),
                }
    return None


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


def _scoped_ingredients(envelope: TraceEnvelope, user_context: dict | None) -> list[
    IngredientRequest]:
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
        *(cost_lines or []),
    ) if part)
    events.extend(
        TokenEvent(event="token", delta=text[index:index + 40])
        for index in range(0, len(text), 40)
    )

    # plan_result = envelope.outcome.plan
    # previous = _previous_meals(payload.user_context)
    # recipes = {recipe.recipe_id: recipe for recipe in projected.plan.recipes}
    # for day_value in _member(plan_result, "days", ()) or ():
    #     day = _member(day_value, "day")
    #     for meal in _member(day_value, "meals", ()) or ():
    #         slot = _member(meal, "slot")
    #         recipe_id = _member(meal, "recipe_id")
    #         if day is None or slot is None or recipe_id is None:
    #             continue
    #         key = (int(day), str(slot))
    #         recipe_id = str(recipe_id)
    #         if previous.get(key) == recipe_id:
    #             continue
    #         recipe = recipes.get(recipe_id)
    #         if recipe is None:
    #             continue
    #         events.append(PlanUpdatedEvent(
    #             event="plan_updated",
    #             delta=MealDelta(day=key[0], slot=key[1], recipe_id=recipe_id),
    #             explanation=MealScopedExplanation(
    #                 recipe=recipe,
    #                 constraints=recipe.constraints,
    #             ),
    #         ))

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
async def chat(payload: ChatRequest, request: Request):
    return StreamingResponse(
        _stream_chat(payload, request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream_chat(payload: ChatRequest, request: Request):
    trace_id = secrets.token_hex(16)

    # 1. Instant Metadata
    yield serialize_event(MetadataEvent(
        event="metadata",
        session_id=payload.session_id,
        workflow_node="Start",
        trace_id=trace_id,
    ))
    await asyncio.sleep(0)

    yield serialize_event(TokenEvent(event="token", delta="Planning your meals…\n\n"))
    await asyncio.sleep(0)

    # 2. Start blocking workflow in a background thread
    try:
        plan_service, calculator = _resolve_services(request)
        workflow = composition.create_workflow(plan_service)

        # --- ADD LANGFUSE CALLBACK HERE ---
        config = {}
        if os.getenv("LANGFUSE_TRACING_ENABLED", "false").lower() == "true":
            try:
                from langfuse import Langfuse
                from langfuse.langchain import CallbackHandler

                # v3: the client is a singleton that holds credentials; the handler picks it up.
                Langfuse(
                    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
                    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
                    host=os.getenv("LANGFUSE_HOST", "http://localhost:3031"),
                )
                config["callbacks"] = [CallbackHandler()]
            except Exception as e:
                logger.warning(f"Failed to init Langfuse LangGraph callback: {e}")
        # ----------------------------------

        task = asyncio.create_task(asyncio.to_thread(
            workflow.invoke,
            {"raw_message": payload.message, "user_context": payload.user_context},
            config=config,
        ))

        # 3. Heartbeat loop while the solver thinks
        while not task.done():
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=10.0)
            except asyncio.TimeoutError:
                yield ": ping\n\n"  # SSE comment heartbeat

        state = task.result()
        envelope = state.get("trace") if isinstance(state, dict) else None
        if isinstance(envelope, dict):
            envelope = TraceEnvelope(**envelope)
        if not isinstance(envelope, TraceEnvelope):
            raise TypeError("workflow did not return a TraceEnvelope")
    except Exception:
        logger.exception("chat workflow failed trace_id=%s", trace_id)
        yield serialize_event(ErrorEvent(
            event="error",
            code="WORKFLOW_FAILURE",
            message="The recommendation workflow failed.",
            trace_id=trace_id,
        ))
        return

    yield serialize_event(TokenEvent(event="token", delta="Generating your recommendation…\n\n"))
    await asyncio.sleep(0)

    projected = from_trace_envelope(envelope, trace_id)

    # --- RESTORE COST BRANCH (F-1) ---
    cost_lines: list[str] = []
    constraints = envelope.parsed_constraints
    if constraints is not None and getattr(constraints, "cost_query", False):
        scoped = _scoped_ingredients(envelope, payload.user_context)
        if scoped:
            try:
                calculation, _ = calculator.calculate(CostNutritionRequest(
                    servings=constraints.servings,
                    ingredients=scoped,
                ))
                cost_lines = _cost_lines(calculation)
            except Exception:
                logger.exception("cost projection failed trace_id=%s", trace_id)
                cost_lines = []

    # --- RESTORE PLAN UPDATED (F-2, F-5) ---
    previous = _previous_meals(payload.user_context)
    if projected.plan is not None:
        recipes = {recipe.recipe_id: recipe for recipe in projected.plan.recipes}
        for day_value in _member(envelope.outcome.plan, "days", ()) or ():
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

                # Sanitize constraints to hide selected_offer (prevents "water -> sugar" leak)
                sanitized_constraints = [
                    c.model_copy(update={"selected_offer": None}) for c in recipe.constraints
                ]
                sanitized_recipe = recipe.model_copy(update={"constraints": sanitized_constraints})

                # Enrich recipe explanation with meal content
                meal_data = _find_meal(envelope.outcome.plan, key[0], key[1], recipe_id)
                if meal_data is not None:
                    sanitized_recipe = sanitized_recipe.model_copy(update={
                        "meal": MealContent(
                            title=meal_data["title"],
                            nutrients={k: float(v) for k, v in
                                       (meal_data["nutrients"] or {}).items() if v is not None},
                            ingredients=meal_data["ingredients"],
                            instructions=meal_data["instructions"],
                        )
                    })

                yield serialize_event(PlanUpdatedEvent(
                    event="plan_updated",
                    delta=MealDelta(day=key[0], slot=key[1], recipe_id=recipe_id),
                    explanation=MealScopedExplanation(
                        recipe=sanitized_recipe,
                        constraints=sanitized_constraints,
                    ),
                ))
                await asyncio.sleep(0)  # Flush immediately

    # 4. Yield text progressively, line by line
    # (Because the LLM intro and meal list are combined in envelope.outcome.text)
    text = envelope.outcome.text or ""
    if cost_lines:
        text = text + "\n\n" + "\n".join(cost_lines)
    for line in text.split("\n"):
        if line.strip():
            yield serialize_event(TokenEvent(event="token", delta=line + "\n"))
            await asyncio.sleep(0.01)  # Force socket flush

    # 5. Finish
    yield serialize_event(DoneEvent(
        event="done",
        status=(projected.plan.feasibility_outcome if projected.plan else "error"),
        trace_id=trace_id,
    ))
