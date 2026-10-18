import pytest

from api.features.calculator.domain.cost import select_package
from api.features.calculator.models import FoodFacts, NutrientProfile, RecipeNutritionSignal, RequirementOffer, RetailSKU
from api.features.calculator.schemas import CostNutritionRequest, IngredientRequest
from api.features.calculator.service import CostNutritionService
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
    def inspect_candidates(self, recipes, servings):
        return {
            recipe.recipe_id: RecipeNutritionSignal(
                recipe_id=recipe.recipe_id,
                missing_nutrients=[],
                selected_offers=[RequirementOffer(
                    occurrence_id="recipe-ingredient",
                    canonical_key="black_pepper",
                    selected_offer=None,
                )],
            )
            for recipe in recipes
        }


class CalculatorRepository:
    def __init__(self, package):
        self.package = package

    def resolve_candidates(self, _names):
        return {"black pepper": ["black_pepper"]}

    def fetch_food_facts(self, _keys):
        return {"black_pepper": [FoodFacts(
            canonical_key="black_pepper",
            canonical_name="Black pepper",
            fdc_id="1",
            description="Black pepper",
            nutrients=NutrientProfile(protein_g=1),
            approval_status="accepted",
            food_key="food:1",
            packages=[self.package],
        )]}


def _package(**overrides):
    values = dict(
        retailer="A", listing_name="pepper", reference_price_minor=100,
        currency="SGD", package_mass_g=100, package_count=1,
        price_basis="package_mass", cost_basis_compatible=True,
        confidence=1.0, fdc_id="1", price_status="estimated",
        price_match_status="accepted", freshness_status="fresh",
        package_volume_ml=None, food_key="food:1", approval_status="accepted",
    )
    values.update(overrides)
    return RetailSKU(**values)


def _row():
    return {
        "recipe_id": "recipe",
        "title": "recipe",
        "ingredients": [{
            "quantity": 50,
            "unit": "g",
            "occurrence_id": "recipe-ingredient",
            "normalized_name": "pepper",
            "canonical_key": "black_pepper",
            "concept_name": "Black pepper",
            "best_food_key": "food:1",
            "energy_kcal": 10,
            "protein_g": 1,
            "sodium_mg": 1,
            "nutrition_basis": "per 100 g",
            "halal_status": "halal",
            "vegetarian_status": "vegetarian",
            "freshness_status": "fresh",
        }],
    }


def _assert_recipe_dropped_and_warning(package):
    assert select_package([package], 50) is None
    calc = CostNutritionService(CalculatorRepository(package))
    response, _trace = calc.calculate(CostNutritionRequest(
        servings=1,
        ingredients=[IngredientRequest(name="black pepper", quantity=50, unit="g")],
    ))
    assert "MISSING_PACKAGE_DATA" in {warning.code for warning in response.itemized[0].warnings}

    service = PlanService(PlanRepository(Driver([_row()])))
    service.calculator_service = SignalInspector()
    plan, _trace = service.generate(
        PlanRequest(horizon_days=1, meals_per_day=1), drop_uncosted=True
    )
    outcome = next(item for item in plan.recipe_outcomes if item.recipe_id == "recipe")
    assert outcome.outcome == "dropped"
    assert outcome.cause == "evidence-absent"


def test_non_fresh_package_drops_recipe():
    _assert_recipe_dropped_and_warning(_package(freshness_status="stale"))


@pytest.mark.parametrize("changes", [
    {"price_status": "unavailable"},
    {"price_match_status": "estimated"},
    {"price_basis": "span_reference"},
])
def test_ineligible_price_basis_drops_recipe(changes):
    _assert_recipe_dropped_and_warning(_package(**changes))
