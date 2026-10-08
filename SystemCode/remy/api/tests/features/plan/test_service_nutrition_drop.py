import pytest

from api.features.calculator.models import RecipeNutritionSignal
from api.features.plan.exceptions import PlanInfeasible
from api.features.plan.models import NamedConstraint
from api.features.plan.repository import PlanRepository
from api.features.plan.schemas import Goal, NutrientLimit, NutrientRequest, PlanRequest
from api.features.plan.service import PlanService


class Session:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def run(self, query, **params):
        return self.rows


class Driver:
    def __init__(self, rows):
        self.rows = rows

    def session(self):
        return Session(self.rows)


class SignalInspector:
    def __init__(self, signals):
        self.signals = signals

    def inspect_candidates(self, recipes, servings):
        return self.signals


def _row(recipe_id):
    return {
        "recipe_id": recipe_id,
        "title": recipe_id,
        "ingredients": [
            {
                "quantity": 100,
                "unit": "g",
                "occurrence_id": f"{recipe_id}-ingredient",
                "normalized_name": "pepper",
                "canonical_key": "black_pepper",
                "concept_name": "Black pepper",
                "best_food_key": f"food:{recipe_id}",
                "energy_kcal": 10,
                "protein_g": 1,
                "sodium_mg": 1,
                "nutrition_basis": "per 100 g",
                "halal_status": "halal",
                "vegetarian_status": "vegetarian",
                "freshness_status": "fresh",
            }
        ],
    }


def _service(signals, *rows):
    service = PlanService(PlanRepository(Driver(list(rows))))
    service.calculator_service = SignalInspector(signals)
    return service


def _sodium_request(*, goal=False):
    target = {"goal": Goal(value=5)} if goal else {"limit": NutrientLimit(max=100)}
    return PlanRequest(
        horizon_days=1,
        meals_per_day=1,
        nutrients=[NutrientRequest(code="sodium", unit="mg", **target)],
    )


def _outcome(response, recipe_id):
    return next(item for item in response.recipe_outcomes if item.recipe_id == recipe_id)


def test_tracked_partial_nutrition_drops():
    service = _service(
        {"partial": RecipeNutritionSignal("partial", ["sodium_mg"]),
         "complete": RecipeNutritionSignal("complete", [])},
        _row("partial"),
        _row("complete"),
    )

    response = service.generate(_sodium_request())

    outcome = _outcome(response, "partial")
    assert outcome.outcome == "dropped"
    assert outcome.cause == "evidence-absent"


def test_drop_categorized_under_nutrient():
    service = _service(
        {"partial": RecipeNutritionSignal("partial", ["sodium_mg"]),
         "complete": RecipeNutritionSignal("complete", [])},
        _row("partial"),
        _row("complete"),
    )

    response = service.generate(_sodium_request())

    assert any(
        item.recipe_id == "partial"
        and item.constraint == "sodium"
        and item.state == "evidence-absent"
        for item in response.constraint_outcomes
    )


def test_goal_on_missing_nutrient_drops():
    service = _service(
        {"partial": RecipeNutritionSignal("partial", ["sodium_mg"]),
         "complete": RecipeNutritionSignal("complete", [])},
        _row("partial"),
        _row("complete"),
    )

    response = service.generate(_sodium_request(goal=True))

    assert _outcome(response, "partial").cause == "evidence-absent"


def test_untracked_partial_nutrition_retained():
    service = _service(
        {"partial": RecipeNutritionSignal("partial", ["sodium_mg"])},
        _row("partial"),
    )
    request = PlanRequest(
        horizon_days=1,
        meals_per_day=1,
        nutrients=[
            NutrientRequest(code="calories", unit="kcal", limit=NutrientLimit(max=100))
        ],
    )

    response = service.generate(request)

    assert _outcome(response, "partial").outcome == "selected"


def test_unmapped_cause_and_binding():
    unmapped = {
        "recipe_id": "unmapped",
        "title": "Unmapped",
        "ingredients": [
            {
                "quantity": 1,
                "unit": "tsp",
                "occurrence_id": "unmapped-ingredient",
                "normalized_name": "rare spice",
                "canonical_key": None,
                "best_food_key": None,
                "raw_text": "rare spice",
            }
        ],
    }
    service = _service(
        {"unmapped": RecipeNutritionSignal("unmapped", [])},
        unmapped,
    )

    with pytest.raises(PlanInfeasible) as caught:
        service.generate(PlanRequest(horizon_days=1, meals_per_day=1))

    assert NamedConstraint(
        scope="requirement", code="rare spice", kind="unmapped"
    ) in caught.value.binding_constraints
