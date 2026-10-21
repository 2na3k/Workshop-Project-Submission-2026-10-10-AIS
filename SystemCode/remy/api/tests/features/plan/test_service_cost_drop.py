from api.features.calculator.models import OfferRef, RecipeNutritionSignal, RequirementOffer
from api.features.plan.repository import PlanRepository
from api.features.plan.schemas import PlanRequest
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
        "ingredients": [{
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
        }],
    }


def _service(signals, *rows):
    service = PlanService(PlanRepository(Driver(list(rows))))
    service.calculator_service = SignalInspector(signals)
    return service


def _signal(recipe_id, offer):
    return RecipeNutritionSignal(
        recipe_id=recipe_id,
        missing_nutrients=[],
        selected_offers=[RequirementOffer(
            occurrence_id=f"{recipe_id}-ingredient",
            canonical_key="black_pepper",
            selected_offer=offer,
        )],
    )


def _outcome(response, recipe_id):
    return next(item for item in response.recipe_outcomes if item.recipe_id == recipe_id)


def test_uncosted_recipe_dropped_evidence_absent():
    service = _service(
        {
            "uncosted": _signal("uncosted", None),
            "costed": _signal("costed", OfferRef("food:1", "pepper", "store")),
        },
        _row("uncosted"),
        _row("costed"),
    )

    response, _trace = service.generate(
        PlanRequest(horizon_days=1, meals_per_day=1), drop_uncosted=True
    )

    assert _outcome(response, "uncosted").outcome == "dropped"
    assert _outcome(response, "uncosted").cause == "evidence-absent"
    assert _outcome(response, "costed").outcome in {"selected", "retained-unselected"}
    assert any(
        item.recipe_id == "uncosted"
        and item.requirement_id == "uncosted-ingredient"
        and item.constraint == "budget"
        and item.state == "evidence-absent"
        for item in response.constraint_outcomes
    )


def test_uncosted_recipe_retained_when_cost_not_requested():
    service = _service({"uncosted": _signal("uncosted", None)}, _row("uncosted"))

    response, _trace = service.generate(
        PlanRequest(horizon_days=1, meals_per_day=1), drop_uncosted=False
    )

    assert _outcome(response, "uncosted").outcome in {"selected", "retained-unselected"}
