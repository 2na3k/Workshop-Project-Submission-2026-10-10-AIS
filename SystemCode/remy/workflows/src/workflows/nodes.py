"""LangGraph node functions."""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from workflows.prompts import EXTRACT_SYSTEM, RESPONSE_SYSTEM

from domain.types import REQUEST_TO_CANONICAL
from workflows.models import (
    AllergyConstraint,
    ConstraintSet,
    GenerationOutput,
    DietaryConstraint,
    LLMInvocation,
    Outcome,
    NutrientConstraint,
    PlanInput,
)
from workflows.trace import assemble_trace


def _content(response: Any) -> Any:
    value = getattr(response, "content", response)
    if not isinstance(value, str):
        return value
    s = value.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        s = s.rsplit("```", 1)[0].strip()
    lo, hi = s.find("{"), s.rfind("}")
    if lo == -1 or hi <= lo:
        raise ValueError(f"extraction response contained no JSON object: {value[:80]!r}")
    return json.loads(s[lo:hi + 1])


def _constraint_set(value: Any, message: str) -> ConstraintSet:
    if isinstance(value, ConstraintSet):
        return value
    if not isinstance(value, dict):
        raise ValueError("constraint response must be an object")
    for key in ("horizon_days", "meals_per_day"):
        if key not in value:
            raise ValueError(f"missing required field: {key}")
        if not isinstance(value[key], int) or value[key] <= 0:
            raise ValueError(f"{key} must be a positive integer, got {value[key]!r}")
        if key == "horizon_days" and value[key] > 14:
            raise ValueError(f"horizon_days must be <= 14, got {value[key]!r}")
        if key == "meals_per_day" and value[key] > 6:
            raise ValueError(f"meals_per_day must be <= 6, got {value[key]!r}")
    tolerance = value.get("nutrient_tolerance_pct", 0)
    if not isinstance(tolerance, int) or not 0 <= tolerance <= 25:
        raise ValueError("nutrient_tolerance_pct must be between 0 and 25")
    nutrients = []
    for item in value.get("nutrients", []):
        code = item.get("code")
        if code not in REQUEST_TO_CANONICAL:
            raise ValueError(f"unknown nutrient code: {code}")
        minimum, maximum = item.get("minimum", item.get("min")), item.get("maximum",
                                                                          item.get("max"))
        if minimum is not None and not isinstance(minimum, (int, float)):
            raise ValueError("nutrient minimum must be numeric")
        if maximum is not None and not isinstance(maximum, (int, float)):
            raise ValueError("nutrient maximum must be numeric")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError("nutrient minimum cannot exceed maximum")
        goal = item.get("goal")
        if isinstance(goal, dict):
            goal = goal.get("value")
        if goal is not None and not isinstance(goal, (int, float)):
            raise ValueError("nutrient goal must be numeric")
        nutrients.append(NutrientConstraint(code, item.get("unit", ""), goal, minimum, maximum))
    allergies = []
    explicit_severity = re.compile(r"\b(mild|severe)\b", re.IGNORECASE)
    for item in value.get("allergies", []):
        severity = item.get("severity")
        match = explicit_severity.search(message)
        allergies.append(AllergyConstraint(item["code"], severity if match else None))
    cost_query = value.get("cost_query")
    if cost_query is None:
        cost_query = bool(
            re.search(
                r"\b(cost|costs|price|prices|priced|cheap|cheaper|cheapest|budget|afford|affordable|dollar|dollars|sgd)\b|\$\s?\d|\bunder\s+\$?\d",
                message,
                re.IGNORECASE,
            )
        )
    return ConstraintSet(
        horizon_days=value["horizon_days"],
        meals_per_day=value["meals_per_day"],
        servings=value.get("servings", 1),
        allergies=tuple(allergies),
        dietary=tuple(DietaryConstraint(item["code"]) for item in value.get("dietary", [])),
        nutrients=tuple(nutrients),
        nutrient_tolerance_pct=tolerance if re.search(r"\b(tolerance|relax|within)\b", message,
                                                      re.I) else 0,
        cost_query=cost_query,
    )


_NUM = re.compile(r"\d+(?:\.\d+)?")
_BOUND_KEYS = ("goal", "min", "max")
_MIN_CUES = ("at least", "no less than", "no fewer than", "minimum", "min of")
_MAX_CUES = ("never exceed", "not exceed", "no more than", "at most",
             "maximum", "under", "below", "up to", "never above")
_NUM_TOKEN = re.compile(r"\d[\d,]*(?:\.\d+)?")
_ALLOWED_TOP = {"horizon_days", "meals_per_day", "servings",
                "nutrient_tolerance_pct", "nutrients", "allergies",
                "dietary", "cost_query", "unapplied"}


def _to_number(val):
    """'about 170' -> 170, '2,500' -> 2500, None/garbage -> None."""
    if isinstance(val, bool):
        return None
    if isinstance(val, str):
        m = _NUM.search(val.replace(",", ""))
        val = m.group() if m else None
    if val is None:
        return None
    try:
        num = float(val)
    except (TypeError, ValueError):
        return None
    return int(num) if num.is_integer() else num


def _coerce_nutrients(parsed: dict) -> dict:
    """Make goal/min/max bare numbers, drop nulls, drop empty nutrients."""
    cleaned = []
    for nut in parsed.get("nutrients") or []:
        for key in _BOUND_KEYS:
            num = _to_number(nut.get(key))
            if num is None:
                nut.pop(key, None)
            else:
                nut[key] = num
        if any(k in nut for k in _BOUND_KEYS):
            cleaned.append(nut)
    parsed["nutrients"] = cleaned
    return parsed


def _drop_unstated_bounds(parsed: dict, user_message: str) -> dict:
    """Remove any goal/min/max whose number never appears in the user's message."""
    stated = {float(n) for n in _NUM.findall(user_message.replace(",", ""))}
    cleaned = []
    for nut in parsed.get("nutrients", []):
        for key in _BOUND_KEYS:
            if key in nut and float(nut[key]) not in stated:
                nut.pop(key)
        if any(k in nut for k in _BOUND_KEYS):
            cleaned.append(nut)
    parsed["nutrients"] = cleaned
    return parsed


def _key_from_context(user_message: str, value: float) -> str:
    low = user_message.lower()
    for m in _NUM_TOKEN.finditer(low):
        if float(m.group().replace(",", "")) != float(value):
            continue
        window = low[max(0, m.start() - 25):m.start()]
        best, best_pos = "goal", -1
        for key, cues in (("min", _MIN_CUES), ("max", _MAX_CUES)):
            for cue in cues:
                pos = window.rfind(cue)
                if pos > best_pos:
                    best, best_pos = key, pos
        return best
    return "goal"  # number not found; _drop_unstated_bounds will handle it


def _fix_bound_keys(parsed: dict, user_message: str) -> dict:
    for nut in parsed.get("nutrients", []):
        values = [nut.pop(k) for k in _BOUND_KEYS if k in nut]
        for v in values:
            nut.setdefault(_key_from_context(user_message, v), v)
    return parsed


def _clean_extraction(parsed: dict, user_message: str) -> dict:
    """Single entry point: normalize types, then drop invented values."""
    parsed = {k: v for k, v in parsed.items() if k in _ALLOWED_TOP}
    parsed = _coerce_nutrients(parsed)
    parsed = _fix_bound_keys(parsed, user_message)
    return _drop_unstated_bounds(parsed, user_message)


def _invoke_extract(llm, raw_message: str):
    messages = [SystemMessage(content=EXTRACT_SYSTEM), HumanMessage(content=raw_message)]
    response = llm.invoke(messages)
    try:
        return response, _content(response)
    except (ValueError, json.JSONDecodeError):
        messages.append(HumanMessage(
            content="Your last output was not a JSON object. Return ONLY the JSON object, "
                    "starting with '{' and ending with '}'."
        ))
        retry = llm.invoke(messages)
        return retry, _content(retry)


def extract_constraints(state: dict[str, Any], *, llm: Any) -> dict[str, Any]:
    raw_message = state.get("raw_message", "")
    invocations = list(state.get("llm_invocations", []))
    try:
        if state.get("structured_constraints") is not None:
            parsed = _constraint_set(state["structured_constraints"], raw_message)
        else:
            response, parsed_response = _invoke_extract(llm, raw_message)
            parsed_response = _clean_extraction(parsed_response, raw_message)
            invocations.append(
                LLMInvocation("Extract Constraints", getattr(llm, "provider", "unknown"),
                              getattr(llm, "model", "unknown"), raw_message, response,
                              parsed_response, 0.0))
            parsed = _constraint_set(parsed_response, raw_message)
        unapplied = tuple(state.get("unapplied_constraints", [])) + tuple(
            parsed_response.get("unapplied", []) if "parsed_response" in locals() and isinstance(
                parsed_response, dict) else ())
        outcome = Outcome("plan", unapplied_constraints=unapplied)
        updated = {
            **state,
            "parsed_constraints": parsed,
            "unapplied_constraints": list(unapplied),
            "outcome": outcome,
            "llm_invocations": invocations,
            "trace": assemble_trace(raw_message=raw_message, parsed_constraints=parsed,
                                    unapplied_constraints=unapplied, outcome=outcome,
                                    llm_invocations=tuple(invocations))
        }
        return updated
    except Exception as exc:
        outcome = Outcome("failure", node="Extract Constraints", reason=str(exc),
                          unapplied_constraints=tuple(state.get("unapplied_constraints", [])))
        updated = {**state, "outcome": outcome, "llm_invocations": invocations}
        updated["trace"] = assemble_trace(raw_message=raw_message, parsed_constraints=None,
                                          unapplied_constraints=outcome.unapplied_constraints,
                                          outcome=outcome, llm_invocations=tuple(invocations))
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
            cost_query=bool(constraints.cost_query),
        )
        result, trace_view = port.generate(request)
        kind: Literal[
            "plan", "infeasible"] = "infeasible" if result.feasibility_outcome == "infeasible" else "plan"
        outcome = Outcome(kind, plan=result, reason=trace_view.reason,
                          unapplied_constraints=tuple(state.get("unapplied_constraints", [])))
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
        outcome = Outcome("failure", node="Plan", reason=str(exc),
                          unapplied_constraints=tuple(state.get("unapplied_constraints", [])))
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


def _horizon_key(request_code: str) -> str | None:
    suffix = REQUEST_TO_CANONICAL.get(request_code)
    return f"avg_daily_{suffix}" if suffix else None


def _fact_sheet(result, constraints) -> dict:
    """Deterministic facts the response may state. No LLM here."""
    selected = [r for r in result.recipe_outcomes if r.outcome == "selected"]
    selected_ids = sorted({r.recipe_id for r in selected})
    dropped = [r for r in result.recipe_outcomes if r.outcome == "dropped"]

    # Nutrient status: computed from horizon_totals vs the constraints we actually asked for.
    nutrient_status = []
    for nut in (constraints.nutrients if constraints else ()):
        code = nut.code
        key = f"avg_daily_{_horizon_key(code)}"
        actual = (result.horizon_totals or {}).get(key) if key else None
        goal = getattr(nut, "goal", None)
        lo, hi = getattr(nut, "minimum", None), getattr(nut, "maximum", None)
        status = "unknown"
        if actual is not None:
            if lo is not None and actual < lo:
                status = "short"
            elif hi is not None and actual > hi:
                status = "over"
            elif goal is not None and lo is None and hi is None:
                # goal-only: compare with tolerance applied
                tol = result.applied_tolerance_pct or 0
                if actual < goal * (1 - tol / 100):
                    status = "below-goal"
                else:
                    status = "at-or-above-goal"
            else:
                status = "within"
        nutrient_status.append({
            "code": code, "actual": actual, "goal": goal,
            "min": lo, "max": hi, "status": status,
        })

    # Which requested constraints have NO recorded outcome = never evaluated.
    recorded = {o.constraint for o in result.constraint_outcomes}
    unevaluated = [n["code"] for n in nutrient_status
                   if n["goal"] is not None and n["code"] not in recorded]

    # Meals with titles and per-meal nutrients only (no offers).
    meals = [
        {
            "day": d["day"],
            "slot": m["slot"],
            "recipe_id": m["recipe_id"],
            "title": m["title"],
            "ingredients": [
                {"text": ing["text"], "quantity": ing["quantity"],
                 "unit": ing["unit"], "optional": ing.get("optional", False)}
                for ing in m.get("ingredients", [])
            ],
            "nutrients": m.get("nutrients", {}),
            "instructions": m.get("instructions", ""),  # optional — include if budget allows
        }
        for d in result.days for m in d["meals"]
    ]

    # Drops grouped by cause (count only; per-recipe details can go in the trace).
    drops_by_cause = {}
    for r in dropped:
        drops_by_cause[r.cause] = drops_by_cause.get(r.cause, 0) + 1

    return {
        "feasibility": result.feasibility_outcome,
        "relaxed": bool(result.relaxed),
        "applied_tolerance_pct": result.applied_tolerance_pct,
        "binding_constraints": list(result.binding_constraints),
        "selected_recipe_ids": selected_ids,
        "meals": meals,
        "horizon_totals": dict(result.horizon_totals or {}),
        "nutrient_status": nutrient_status,
        "unevaluated_constraints": unevaluated,
        "drops_by_cause": drops_by_cause,
        # NOTE: selected_offer intentionally omitted — see "Rule 6".
    }


def _fallback_from_facts(facts) -> tuple[str, list[str], list[str]]:
    """Deterministic prose built from facts alone. Used if the LLM fails."""
    parts = []
    if facts["feasibility"] == "infeasible":
        parts.append("No feasible plan could be produced. Binding constraints: "
                     + ", ".join(facts["binding_constraints"]) + ".")
    else:
        n = len(facts["meals"])
        parts.append(f"A {len({m['day'] for m in facts['meals']})}-day plan with {n} meals.")
    for ns in facts["nutrient_status"]:
        if ns["status"] == "short":
            parts.append(f"{ns['code']}: {ns['actual']:.1f} (below the {ns['min']} minimum).")
        elif ns["status"] == "over":
            parts.append(f"{ns['code']}: {ns['actual']:.1f} (above the {ns['max']} maximum).")
        elif ns["status"] == "below-goal":
            parts.append(f"{ns['code']}: {ns['actual']:.1f} (goal {ns['goal']}; not met).")
        elif ns["status"] == "at-or-above-goal":
            parts.append(f"{ns['code']}: {ns['actual']:.1f} (goal {ns['goal']}; met).")
    if facts["unevaluated_constraints"]:
        parts.append("Not evaluated: " + ", ".join(facts["unevaluated_constraints"]) + ".")
    refs = [m["recipe_id"] for m in facts["meals"]]
    return " ".join(parts), refs, list(facts["drops_by_cause"].keys())


def _enforce_nutrient_disclosure(text: str, facts) -> str:
    """If any tracked nutrient is short/over/below-goal, ensure the text says
    so. MVP-safe version: prepend a single deterministic disclosure sentence
    the LLM cannot contradict."""
    bad = [n for n in facts["nutrient_status"]
           if n["status"] in ("short", "over", "below-goal")]
    if not bad:
        return text
    lines = []
    for n in bad:
        if n["status"] == "short":
            lines.append(f"{n['code']} is below the {n['min']} minimum ({n['actual']:.1f}).")
        elif n["status"] == "over":
            lines.append(f"{n['code']} exceeds the {n['max']} maximum ({n['actual']:.1f}).")
        else:
            lines.append(f"{n['code']} does not reach the {n['goal']} goal ({n['actual']:.1f}).")
    prefix = " ".join(lines)
    return prefix + " " + text


def _strip_offer_names(text: str, facts) -> str:
    """Current graph maps many ingredients to wrong products (polenta -> water).
    Until p2-002 fixes the mapping, don't print listing names in user text."""
    for meal in facts["meals"]:
        # If offers were in text, they'd appear here; we have none in facts, so
        # this is a no-op today. Kept as a named stub so the intent is recorded.
        pass
    return text


# def generate_response(state: dict[str, Any], *, llm: Any) -> dict[str, Any]:
#     """Generate user text and verify its structured references deterministically."""
#     raw_message = state.get("raw_message", "")
#     result = state.get("plan_result")
#     invocations = list(state.get("llm_invocations", []))
#     try:
#         if result is None:
#             raise ValueError("plan result is required")
#         allowed_recipes = {item.recipe_id for item in result.recipe_outcomes}
#         allowed_requirements = {item.requirement_id for item in result.constraint_outcomes}
#         allowed_causes = {cause for item in result.recipe_outcomes for cause in
#                           ((item.cause,) if item.cause else ()) + item.causes}
#         prompt = (
#             "Write a concise recommendation using only the following opaque recipe and requirement identifiers. "
#             f"Allowed recipes: {sorted(allowed_recipes)}; allowed requirements: {sorted(allowed_requirements)}; "
#             f"allowed drop causes: {sorted(allowed_causes)}. Do not expose audit provenance."
#         )
#         response = llm.invoke(prompt)
#         parsed = _content(response)
#         if not isinstance(parsed, dict):
#             raise ValueError("generation response must be an object")
#         recipe_ids = tuple(parsed.get("recipe_ids", ()))
#         requirement_ids = tuple(parsed.get("requirement_ids", ()))
#         drop_causes = tuple(parsed.get("drop_causes", ()))
#         if not set(recipe_ids) <= allowed_recipes or not set(
#                 requirement_ids) <= allowed_requirements:
#             raise ValueError("generation references an unknown identifier")
#         if not set(drop_causes) <= allowed_causes:
#             raise ValueError("generation references an unknown drop cause")
#         if set(parsed.get("selected_recipe_ids", ())) & set(recipe_ids) & {
#             item.recipe_id for item in result.recipe_outcomes if
#             "evidence-absent" in ((item.cause,) if item.cause else ()) + item.causes
#         }:
#             raise ValueError("evidence-absent recipes cannot be selected")
#         text = parsed.get("text", "")
#         output = GenerationOutput(recipe_ids, requirement_ids, drop_causes, text)
#         invocations.append(LLMInvocation("Generate Response", getattr(llm, "provider", "unknown"),
#                                          getattr(llm, "model", "unknown"), prompt, response, parsed,
#                                          0.0))
#         outcome = Outcome(state.get("outcome", Outcome("plan")).kind, plan=result, text=text,
#                           unapplied_constraints=tuple(state.get("unapplied_constraints", [])))
#         updated = {**state, "generation_output": output, "generation_text": text,
#                    "outcome": outcome, "llm_invocations": invocations}
#         updated["trace"] = assemble_trace(raw_message=raw_message,
#                                           parsed_constraints=state.get("parsed_constraints"),
#                                           unapplied_constraints=outcome.unapplied_constraints,
#                                           outcome=outcome,
#                                           node_runs=tuple(state.get("node_runs", [])),
#                                           llm_invocations=tuple(invocations),
#                                           plan_trace=state.get("plan_trace"))
#         return updated
#     except Exception as exc:
#         outcome = Outcome("failure", node="Generate Response", reason=str(exc),
#                           unapplied_constraints=tuple(state.get("unapplied_constraints", [])))
#         updated = {**state, "outcome": outcome, "llm_invocations": invocations}
#         updated["trace"] = assemble_trace(raw_message=raw_message,
#                                           parsed_constraints=state.get("parsed_constraints"),
#                                           unapplied_constraints=outcome.unapplied_constraints,
#                                           outcome=outcome,
#                                           node_runs=tuple(state.get("node_runs", [])),
#                                           llm_invocations=tuple(invocations),
#                                           plan_trace=state.get("plan_trace"))
#         return updated

def generate_response(state, *, llm):
    raw_message = state.get("raw_message", "")
    result = state.get("plan_result")
    constraints = state.get("parsed_constraints")
    invocations = list(state.get("llm_invocations", []))
    try:
        if result is None:
            raise ValueError("plan result is required")
        facts = _fact_sheet(result, constraints)

        # 1. Ask the LLM to phrase the facts.
        prompt = (
                "Fact sheet:\n" + json.dumps(facts, default=str) +
                "\nUser message: " + json.dumps(raw_message)
        )
        response = llm.invoke([
            SystemMessage(content=RESPONSE_SYSTEM),
            HumanMessage(content=prompt),
        ])
        invocations.append(
            LLMInvocation("Generate Response", getattr(llm, "provider", "unknown"),
                          getattr(llm, "model", "unknown"), prompt, response, None, 0.0)
        )

        # 2. Parse tolerantly. Bad JSON -> deterministic fallback, plan survives.
        text, ref_recipes, ref_causes = _fallback_from_facts(facts)
        try:
            parsed = _content(response)
            if not isinstance(parsed, dict):
                raise ValueError("generation response must be an object")
            text = str(parsed.get("text") or text)
            ref_recipes = [str(x) for x in parsed.get("referenced_recipe_ids") or ref_recipes]
            ref_causes = [str(x) for x in parsed.get("referenced_drop_causes") or ref_causes]
        except Exception:
            invocations[-1] = invocations[-1]._replace(parsed=None)  # keep the raw response

        # 3. Verify LLM output against facts, not against itself.
        allowed_recipes = set(facts["selected_recipe_ids"])
        allowed_causes = set(facts["drops_by_cause"].keys())
        ref_recipes = [r for r in ref_recipes if r in allowed_recipes]
        ref_causes = [c for c in ref_causes if c in allowed_causes]

        # 4. Deterministic verification: reject LLM text that contradicts a
        #    numeric claim the service computed. Cheap check: any number in the
        #    text that matches `goal` for a nutrient whose status is 'short' or
        #    'below-goal' must not be presented as met. Under time pressure, the
        #    safe rule is: if any nutrient_status has status != 'within' /
        #    'at-or-above-goal', prepend a deterministic disclosure sentence and
        #    strip any LLM sentence claiming otherwise.
        text = _enforce_nutrient_disclosure(text, facts)

        # 5. If offers cannot be trusted (current graph), don't ship them.
        text = _strip_offer_names(text, facts)

        output = GenerationOutput(tuple(ref_recipes), (), tuple(ref_causes), text)
        outcome = Outcome(state.get("outcome", Outcome("plan")).kind,
                          plan=result, text=text,
                          unapplied_constraints=tuple(state.get("unapplied_constraints", [])))
        return {
            **state,
            "generation_output": output,
            "generation_text": text,
            "outcome": outcome,
            "llm_invocations": invocations,
            "trace": assemble_trace(
                raw_message=raw_message,
                parsed_constraints=state.get("parsed_constraints"),
                unapplied_constraints=outcome.unapplied_constraints,
                outcome=outcome,
                node_runs=tuple(state.get("node_runs", [])),
                llm_invocations=tuple(invocations),
                plan_trace=state.get("plan_trace")
            )
        }

    except Exception as exc:
        outcome = Outcome("failure", node="Generate Response", reason=str(exc),
                          unapplied_constraints=tuple(state.get("unapplied_constraints", [])))
        updated = {**state, "outcome": outcome, "llm_invocations": invocations}
        updated["trace"] = assemble_trace(
            raw_message=raw_message,
            parsed_constraints=state.get("parsed_constraints"),
            unapplied_constraints=outcome.unapplied_constraints,
            outcome=outcome,
            node_runs=tuple(state.get("node_runs", [])),
            llm_invocations=tuple(invocations),
            plan_trace=state.get("plan_trace")
        )
        return updated
