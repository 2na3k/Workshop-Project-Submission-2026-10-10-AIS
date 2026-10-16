"""Composition-root wiring for the recommendation workflow."""

from __future__ import annotations

from typing import Any

from workflows.graph import build
from workflows.llm import ChatLLM

from app.plan_adapter import PlanServiceAdapter


def create_workflow(plan_service: Any, *, extract_llm: Any | None = None, response_llm: Any | None = None):
    return build(
        extract_llm=extract_llm or ChatLLM(),
        plan_port=PlanServiceAdapter(plan_service),
        response_llm=response_llm or ChatLLM(),
    )
