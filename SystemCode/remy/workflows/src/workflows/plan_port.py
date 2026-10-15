"""Dependency-inversion port for the plan feature."""

from __future__ import annotations

from typing import Protocol

from workflows.models import PlanInput, PlanResult, PlanTraceView


class PlanPort(Protocol):
    def generate(self, request: PlanInput) -> tuple[PlanResult, PlanTraceView]:
        """Generate a plan and its complete reasoning trace."""
