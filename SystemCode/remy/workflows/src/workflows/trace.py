"""Construction helpers for the versioned workflow trace."""

from __future__ import annotations

from workflows.models import ConstraintSet, LLMInvocation, NodeRun, Outcome, PlanTraceView, TraceEnvelope

TRACE_SCHEMA_VERSION = "p3-001.v1"


def assemble_trace(
    *,
    raw_message: str,
    parsed_constraints: ConstraintSet | None,
    unapplied_constraints: tuple[str, ...],
    outcome: Outcome,
    node_runs: tuple[NodeRun, ...] = (),
    llm_invocations: tuple[LLMInvocation, ...] = (),
    plan_trace: PlanTraceView | None = None,
) -> TraceEnvelope:
    return TraceEnvelope(
        schema_version=TRACE_SCHEMA_VERSION,
        outcome=outcome,
        raw_message=raw_message,
        parsed_constraints=parsed_constraints,
        unapplied_constraints=unapplied_constraints,
        node_runs=node_runs,
        llm_invocations=llm_invocations,
        plan_trace=plan_trace,
    )
