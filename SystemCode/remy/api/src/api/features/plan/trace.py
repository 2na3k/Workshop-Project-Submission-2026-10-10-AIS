from dataclasses import dataclass, field

from .models import NamedConstraint, RecipeOutcome, RequirementOutcome


@dataclass
class PlanTrace:
    feasibility_outcome: str = "plan-produced"
    reason: str | None = None
    binding_constraints: list[NamedConstraint] = field(default_factory=list)
    applied_tolerance_pct: int = 0
    recipes: list[RecipeOutcome] = field(default_factory=list)
    requirements: list[RequirementOutcome] = field(default_factory=list)
