from domain.types import NutrientProfile

from api.features.calculator.models import FoodFacts, RetailSKU
from api.features.calculator.service import CostNutritionService
from api.features.plan.repository import PlanRepository
from api.features.plan.schemas import NutrientLimit, NutrientRequest, PlanRequest
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


class CalculatorRepository:
    def __init__(self):
        self.food_facts = {
            "incomplete": FoodFacts(
                canonical_key="incomplete",
                canonical_name="incomplete",
                fdc_id=None,
                description="Incomplete nutrition",
                nutrients=NutrientProfile(sodium_mg=None),
                approval_status="accepted",
                packages=[_package("offered-even-though-incomplete")],
            ),
            "complete-with-offer": FoodFacts(
                canonical_key="complete-with-offer",
                canonical_name="complete with offer",
                fdc_id=None,
                description="Complete nutrition",
                nutrients=NutrientProfile(sodium_mg=1),
                approval_status="accepted",
                packages=[_package("selected-food")],
            ),
            "complete-without-offer": FoodFacts(
                canonical_key="complete-without-offer",
                canonical_name="complete without offer",
                fdc_id=None,
                description="Complete nutrition, no package",
                nutrients=NutrientProfile(sodium_mg=1),
                approval_status="accepted",
            ),
        }

    def fetch_food_facts(self, canonical_keys):
        return {
            key: [self.food_facts[key]] for key in canonical_keys if key in self.food_facts
        }


def _package(food_key):
    return RetailSKU(
        retailer="example-market",
        listing_name="Selected listing",
        reference_price_minor=200,
        currency="SGD",
        package_mass_g=100,
        package_count=1,
        price_basis="package_mass",
        cost_basis_compatible=False,
        confidence=0.9,
        price_status="estimated",
        price_match_status="accepted",
        freshness_status="fresh",
        food_key=food_key,
        approval_status="accepted",
    )


class RecordingCalculatorService(CostNutritionService):
    def __init__(self, repository):
        super().__init__(repository)
        self.last_signals = {}

    def inspect_candidates(self, recipes, servings):
        self.last_signals = super().inspect_candidates(recipes, servings)
        return self.last_signals


def _ingredient(recipe_id, canonical_key, *, sodium=1, occurrence_id="ingredient"):
    return {
        "quantity": 10,
        "unit": "g",
        "occurrence_id": occurrence_id,
        "normalized_name": canonical_key,
        "canonical_key": canonical_key,
        "concept_name": canonical_key.replace("-", " "),
        "best_food_key": f"best:{recipe_id}",
        "cleaned_text": f"10 g {canonical_key}",
        "energy_kcal": 10,
        "protein_g": 1,
        "fat_g": 1,
        "saturated_fat_g": 1,
        "carbohydrate_g": 1,
        "fiber_g": 1,
        "sugars_g": 1,
        "sodium_mg": sodium,
        "cholesterol_mg": 1,
        "nutrition_basis": "per 100 g",
    }


def test_plan_consumes_calculator_partial_nutrition():
    rows = [
        {
            "recipe_id": "a-incomplete",
            "title": "Incomplete recipe",
            "ingredients": [
                _ingredient("a-incomplete", "incomplete", sodium=1, occurrence_id="present"),
                _ingredient("a-incomplete", "incomplete", sodium=None, occurrence_id="missing"),
            ],
        },
        {
            "recipe_id": "b-offer",
            "title": "Recipe with offer",
            "ingredients": [_ingredient("b-offer", "complete-with-offer")],
        },
        {
            "recipe_id": "c-no-offer",
            "title": "Recipe without offer",
            "ingredients": [_ingredient("c-no-offer", "complete-without-offer")],
        },
    ]
    calculator = RecordingCalculatorService(CalculatorRepository())
    service = PlanService(
        PlanRepository(Driver(rows)), calculator_service=calculator
    )
    request = PlanRequest(
        horizon_days=1,
        meals_per_day=1,
        nutrients=[
            NutrientRequest(code="sodium", unit="mg", limit=NutrientLimit(max=100))
        ],
    )

    response = service.generate(request)

    outcomes = {item.recipe_id: item for item in response.recipe_outcomes}
    assert outcomes["a-incomplete"].outcome == "dropped"
    assert outcomes["a-incomplete"].cause == "evidence-absent"
    assert calculator.last_signals["a-incomplete"].missing_nutrients == ["sodium_mg"]
    assert any(
        item.selected_offer is not None
        for item in calculator.last_signals["a-incomplete"].selected_offers
    )
    assert calculator.last_signals["c-no-offer"].selected_offer is None
    assert outcomes["c-no-offer"].outcome == "retained-unselected"

    selected = next(item for item in response.recipe_outcomes if item.outcome == "selected")
    offer_record = next(
        item for item in response.constraint_outcomes
        if item.recipe_id == selected.recipe_id and item.constraint == "requirement"
    )
    assert offer_record.selected_offer is not None
    assert offer_record.selected_offer.listing_name == "Selected listing"
    assert offer_record.selected_offer.retailer == "example-market"
    assert service.last_trace.requirements
    traced_offer = next(
        item for item in service.last_trace.requirements if item.selected_offer is not None
    )
    assert traced_offer.selected_offer.food_key == "selected-food"
    assert "food_key" not in str(response.model_dump())
