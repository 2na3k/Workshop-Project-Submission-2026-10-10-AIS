import pytest

from api.features.plan.exceptions import PlanInfeasible
from api.features.plan.models import NamedConstraint, Recipe
from api.features.plan.schemas import NutrientLimit, NutrientRequest, PlanRequest
from api.features.plan.solver_v2 import solve_v2


def _recipe(recipe_id: str, calories: float) -> Recipe:
    return Recipe(recipe_id=recipe_id, title=recipe_id, nutrients={"calories": calories})


def _calorie_request(*, maximum: float, tolerance: int = 0) -> PlanRequest:
    return PlanRequest(
        horizon_days=1,
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


def test_infeasible_names_individually_binding_set():
    with pytest.raises(PlanInfeasible) as caught:
        solve_v2([_recipe("high-calorie", 20)], _calorie_request(maximum=10, tolerance=25))

    assert caught.value.reason == "no-assignment"
    assert caught.value.binding_constraints == [
        NamedConstraint(scope="plan", code="calories", kind="nutrient-bound")
    ]


def test_producible_never_infeasible():
    days, _ = solve_v2([_recipe("fits", 10)], _calorie_request(maximum=10))

    assert [[recipe.recipe_id for recipe in day] for day in days] == [["fits"]]


def test_feasible_returns_plan():
    request = PlanRequest(horizon_days=2, meals_per_day=1)
    days, _ = solve_v2([_recipe("first", 10), _recipe("second", 20)], request)

    assert len(days) == 2
    assert all(len(day) == 1 for day in days)
    assert {day[0].recipe_id for day in days} == {"first", "second"}

