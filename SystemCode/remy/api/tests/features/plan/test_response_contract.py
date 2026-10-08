import pytest

from api.features.plan.exceptions import PlanInfeasible
from api.features.plan.models import NamedConstraint, Recipe
from api.features.plan.schemas import NutrientLimit, NutrientRequest, PlanRequest
from api.features.plan.solver_v2 import solve_v2


def _infeasible(*, recipes, request):
    with pytest.raises(PlanInfeasible) as caught:
        solve_v2(recipes, request)
    return caught.value


def test_infeasibility_reason_discriminator():
    empty = _infeasible(
        recipes=[],
        request=PlanRequest(horizon_days=1, meals_per_day=1),
    )
    assignment = _infeasible(
        recipes=[Recipe(recipe_id="only", title="Only")],
        request=PlanRequest(horizon_days=2, meals_per_day=1),
    )

    assert empty.reason == "no-recipes-survived"
    assert assignment.reason == "no-assignment"


def test_deterministic_across_runs():
    request = PlanRequest(
        horizon_days=1,
        meals_per_day=1,
        nutrient_tolerance_pct=25,
        nutrients=[
            NutrientRequest(
                code="calories",
                unit="kcal",
                limit=NutrientLimit(max=10),
            )
        ],
    )
    recipes = [Recipe(recipe_id="high", title="High", nutrients={"calories": 20})]

    first = _infeasible(recipes=recipes, request=request)
    second = _infeasible(recipes=recipes, request=request)

    assert first.reason == second.reason == "no-assignment"
    assert first.binding_constraints == second.binding_constraints == [
        NamedConstraint(scope="plan", code="calories", kind="nutrient-bound")
    ]
