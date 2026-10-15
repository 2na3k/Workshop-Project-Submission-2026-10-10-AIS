"""Typed state carried through the recommendation graph."""

from __future__ import annotations

from typing import Any, TypedDict

from workflows.models import ConstraintSet, GenerationOutput, Outcome, PlanResult, PlanTraceView, TraceEnvelope


class WorkflowState(TypedDict, total=False):
    raw_message: str
    structured_constraints: ConstraintSet | None
    parsed_constraints: ConstraintSet | None
    unapplied_constraints: list[str]
    plan_result: PlanResult | None
    plan_trace: PlanTraceView | None
    generation_output: GenerationOutput | None
    generation_text: str | None
    trace: TraceEnvelope | None
    outcome: Outcome | None
    llm_invocations: list[Any]
    node_runs: list[Any]
