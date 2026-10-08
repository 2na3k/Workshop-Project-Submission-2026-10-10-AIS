import pytest

from api.features.plan.exceptions import PlanInfeasible
from api.features.plan.models import Recipe
from api.features.plan.schemas import NutrientLimit, NutrientRequest, PlanRequest
from api.features.plan.solver_v2 import solve_v2


def _recipe(calories: float) -> Recipe:
    return Recipe(recipe_id="recipe-1", title="Recipe", nutrients={"calories": calories})


def _request(*, tolerance: int, days: int = 1, maximum: float = 9) -> PlanRequest:
    return PlanRequest(
        horizon_days=days,
        meals_per_day=1,
        nutrient_tolerance_pct=tolerance,
        nutrients=[
            NutrientRequest(
                code="calories",
                unit="kcal",
                limit=NutrientLimit(max=maximum),
            )
        ],
    )


def test_relaxed_plan_labeled_and_records_tolerance():
    days, relaxations = solve_v2([_recipe(10)], _request(tolerance=20))

    assert [[recipe.recipe_id for recipe in day] for day in days] == [["recipe-1"]]
    assert relaxations[-1]["kind"] == "widen_nutrient_bounds"
    assert relaxations[-1]["detail"]["applied_tolerance_pct"] == 20


def test_widening_insufficient_hard_infeasible():
    with pytest.raises(PlanInfeasible):
        solve_v2([_recipe(20)], _request(tolerance=25, maximum=10))


def test_structural_relaxations_are_not_applied():
    request = PlanRequest(horizon_days=2, meals_per_day=1, nutrient_tolerance_pct=25)

    with pytest.raises(PlanInfeasible):
        solve_v2([_recipe(10)], request)


def test_tolerance_absent_defaults_zero():
    assert PlanRequest(horizon_days=1, meals_per_day=1).nutrient_tolerance_pct == 0
    assert _request(tolerance=0).nutrient_tolerance_pct == 0

