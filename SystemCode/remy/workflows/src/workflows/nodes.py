"""LangGraph node functions."""

from __future__ import annotations

import json
import re
from typing import Any

from domain.types import REQUEST_TO_CANONICAL

from workflows.models import (
    AllergyConstraint,
    ConstraintSet,
    DietaryConstraint,
    LLMInvocation,
    Outcome,
    NutrientConstraint,
    PlanInput,
)
from workflows.trace import assemble_trace


def _content(response: Any) -> Any:
    value = getattr(response, "content", response)
    if isinstance(value, str):
        return json.loads(value)
    return value


def _constraint_set(value: Any, message: str) -> ConstraintSet:
    if isinstance(value, ConstraintSet):
        return value
    if not isinstance(value, dict):
        raise ValueError("constraint response must be an object")
    if "horizon_days" not in value or "meals_per_day" not in value:
        raise ValueError("horizon_days and meals_per_day are required")
    tolerance = value.get("nutrient_tolerance_pct", 0)
    if not isinstance(tolerance, int) or not 0 <= tolerance <= 25:
        raise ValueError("nutrient_tolerance_pct must be between 0 and 25")
    nutrients = []
    for item in value.get("nutrients", []):
        code = item.get("code")
        if code not in REQUEST_TO_CANONICAL:
            raise ValueError(f"unknown nutrient code: {code}")
        minimum, maximum = item.get("minimum", item.get("min")), item.get("maximum", item.get("max"))
        if minimum is not None and not isinstance(minimum, (int, float)):
            raise ValueError("nutrient minimum must be numeric")
        if maximum is not None and not isinstance(maximum, (int, float)):
            raise ValueError("nutrient maximum must be numeric")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError("nutrient minimum cannot exceed maximum")
        nutrients.append(NutrientConstraint(code, item.get("unit", ""), item.get("goal", "limit"), minimum, maximum))
    allergies = []
    explicit_severity = re.compile(r"\b(mild|severe)\b", re.IGNORECASE)
    for item in value.get("allergies", []):
        severity = item.get("severity")
        match = explicit_severity.search(message)
        allergies.append(AllergyConstraint(item["code"], severity if match else None))
    return ConstraintSet(
        horizon_days=value["horizon_days"],
        meals_per_day=value["meals_per_day"],
        servings=value.get("servings", 1),
        allergies=tuple(allergies),
        dietary=tuple(DietaryConstraint(item["code"]) for item in value.get("dietary", [])),
        nutrients=tuple(nutrients),
        nutrient_tolerance_pct=tolerance if re.search(r"\b(tolerance|relax|within)\b", message, re.I) else 0,
    )


def extract_constraints(state: dict[str, Any], *, llm: Any) -> dict[str, Any]:
    raw_message = state.get("raw_message", "")
    invocations = list(state.get("llm_invocations", []))
    try:
        if state.get("structured_constraints") is not None:
            parsed = _constraint_set(state["structured_constraints"], raw_message)
        else:
            response = llm.invoke(raw_message)
            parsed_response = _content(response)
            invocations.append(LLMInvocation("Extract Constraints", getattr(llm, "provider", "unknown"), getattr(llm, "model", "unknown"), raw_message, response, parsed_response, 0.0))
            parsed = _constraint_set(parsed_response, raw_message)
        unapplied = tuple(state.get("unapplied_constraints", [])) + tuple(parsed_response.get("unapplied", []) if "parsed_response" in locals() and isinstance(parsed_response, dict) else ())
        outcome = Outcome("plan", unapplied_constraints=unapplied)
        updated = {**state, "parsed_constraints": parsed, "unapplied_constraints": list(unapplied), "outcome": outcome, "llm_invocations": invocations}
        updated["trace"] = assemble_trace(raw_message=raw_message, parsed_constraints=parsed, unapplied_constraints=unapplied, outcome=outcome, llm_invocations=tuple(invocations))
        return updated
    except Exception as exc:
        outcome = Outcome("failure", node="Extract Constraints", reason=str(exc), unapplied_constraints=tuple(state.get("unapplied_constraints", [])))
        updated = {**state, "outcome": outcome, "llm_invocations": invocations}
        updated["trace"] = assemble_trace(raw_message=raw_message, parsed_constraints=None, unapplied_constraints=outcome.unapplied_constraints, outcome=outcome, llm_invocations=tuple(invocations))
        return updated


def plan(state: dict[str, Any], *, port: Any) -> dict[str, Any]:
    """Delegate planning to the workflow-owned plan port."""
    raw_message = state.get("raw_message", "")
    constraints = state.get("parsed_constraints")
    try:
        if not isinstance(constraints, ConstraintSet):
            raise ValueError("parsed constraints are required")
        request = PlanInput(
            horizon_days=constraints.horizon_days,
            meals_per_day=constraints.meals_per_day,
            servings=constraints.servings,
            allergies=constraints.allergies,
            dietary=constraints.dietary,
            nutrients=constraints.nutrients,
            nutrient_tolerance_pct=constraints.nutrient_tolerance_pct,
        )
        result, trace_view = port.generate(request)
        kind = "infeasible" if result.feasibility_outcome == "infeasible" else "plan"
        outcome = Outcome(kind, plan=result, reason=trace_view.reason, unapplied_constraints=tuple(state.get("unapplied_constraints", [])))
        updated = {**state, "plan_result": result, "plan_trace": trace_view, "outcome": outcome}
        updated["trace"] = assemble_trace(
            raw_message=raw_message,
            parsed_constraints=constraints,
            unapplied_constraints=outcome.unapplied_constraints,
            outcome=outcome,
            node_runs=tuple(state.get("node_runs", [])),
            llm_invocations=tuple(state.get("llm_invocations", [])),
            plan_trace=trace_view,
        )
        return updated
    except Exception as exc:
        outcome = Outcome("failure", node="Plan", reason=str(exc), unapplied_constraints=tuple(state.get("unapplied_constraints", [])))
        updated = {**state, "plan_result": None, "plan_trace": None, "outcome": outcome}
        updated["trace"] = assemble_trace(
            raw_message=raw_message,
            parsed_constraints=constraints if isinstance(constraints, ConstraintSet) else None,
            unapplied_constraints=outcome.unapplied_constraints,
            outcome=outcome,
            node_runs=tuple(state.get("node_runs", [])),
            llm_invocations=tuple(state.get("llm_invocations", [])),
        )
        return updated
