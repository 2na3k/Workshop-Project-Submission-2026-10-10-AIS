"""LangGraph assembly for the recommendation workflow."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from workflows.models import NodeRun
from workflows.nodes import extract_constraints, generate_response, plan
from workflows.state import WorkflowState
from workflows.trace import assemble_trace


def _record(state: dict[str, Any], node: str) -> dict[str, Any]:
    outcome = state.get("outcome")
    runs = list(state.get("node_runs", []))
    runs.append(NodeRun(node, outcome.kind if outcome is not None else "unknown"))
    state["node_runs"] = runs
    if state.get("trace") is not None and outcome is not None:
        previous = state["trace"]
        state["trace"] = assemble_trace(
            raw_message=previous.raw_message,
            parsed_constraints=previous.parsed_constraints,
            unapplied_constraints=previous.unapplied_constraints,
            outcome=outcome,
            node_runs=tuple(runs),
            llm_invocations=tuple(state.get("llm_invocations", [])),
            plan_trace=state.get("plan_trace"),
        )
    return state


def build(*, extract_llm: Any, plan_port: Any, response_llm: Any):
    graph = StateGraph(WorkflowState)

    def extract_node(state: WorkflowState) -> dict[str, Any]:
        return _record(extract_constraints(dict(state), llm=extract_llm), "Extract Constraints")

    def plan_node(state: WorkflowState) -> dict[str, Any]:
        return _record(plan(dict(state), port=plan_port), "Plan")

    def response_node(state: WorkflowState) -> dict[str, Any]:
        return _record(generate_response(dict(state), llm=response_llm), "Generate Response")

    graph.add_node("Extract Constraints", extract_node)
    graph.add_node("Plan", plan_node)
    graph.add_node("Generate Response", response_node)
    graph.set_entry_point("Extract Constraints")
    graph.add_conditional_edges(
        "Extract Constraints",
        lambda state: "failure" if state["outcome"].kind == "failure" else "continue",
        {"failure": END, "continue": "Plan"},
    )
    graph.add_conditional_edges(
        "Plan",
        lambda state: "failure" if state["outcome"].kind == "failure" else "continue",
        {"failure": END, "continue": "Generate Response"},
    )
    graph.add_edge("Generate Response", END)
    return graph.compile()
