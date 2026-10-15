from domain.types import NutrientProfile

from api.features.calculator.models import FoodFacts, RetailSKU
from api.features.calculator.service import CostNutritionService
from api.features.plan.repository import QUERY_INGREDIENTS, QUERY_RECIPES, PlanRepository
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


class V2Session(Session):
    def __init__(self, skeleton_rows, ingredient_rows, driver):
        super().__init__(skeleton_rows)
        self.ingredient_rows = ingredient_rows
        self.driver = driver

    def run(self, query, **params):
        if query == QUERY_RECIPES:
            return self.rows
        if query == QUERY_INGREDIENTS:
            self.driver.selected_recipe_ids = list(params["recipe_ids"])
            return [row for row in self.ingredient_rows
                    if row["recipe_id"] in params["recipe_ids"]]
        raise AssertionError("unexpected v2 plan query")


class V2Driver:
    def __init__(self, full_rows):
        self.full_rows = full_rows
        self.selected_recipe_ids = []
        self.skeleton_rows = [_skeleton_row(row) for row in full_rows]

    def session(self):
        return V2Session(self.skeleton_rows, self.full_rows, self)


_NUTRIENT_FIELDS = (
    "energy_kcal", "protein_g", "fat_g", "saturated_fat_g",
    "carbohydrate_g", "fiber_g", "sugars_g", "sodium_mg", "cholesterol_mg",
)


def _skeleton_row(row):
    nutrients = {field: 0.0 for field in _NUTRIENT_FIELDS}
    missing = {field: 0 for field in _NUTRIENT_FIELDS}
    requirements = []
    unmapped = []
    filter_evidence = []
    for ingredient in row["ingredients"]:
        if ingredient.get("canonical_key") is None:
            unmapped.append({
                "occurrence_id": ingredient.get("occurrence_id"),
                "normalized_name": ingredient.get("normalized_name"),
                "raw_text": ingredient.get("raw_text"),
                "cleaned_text": ingredient.get("cleaned_text"),
                "position": ingredient.get("position"),
                "reason": "missing-food-concept",
            })
        elif ingredient.get("best_food_key") is None:
            unmapped.append({
                "occurrence_id": ingredient.get("occurrence_id"),
                "normalized_name": ingredient.get("normalized_name"),
                "raw_text": ingredient.get("raw_text"),
                "cleaned_text": ingredient.get("cleaned_text"),
                "position": ingredient.get("position"),
                "reason": "missing-best-fulfillment",
            })
        else:
            requirements.append({
                "canonical_key": ingredient["canonical_key"],
                "quantity": ingredient.get("quantity"),
                "unit": ingredient.get("unit"),
                "occurrence_id": ingredient.get("occurrence_id"),
            })
        quantity = ingredient.get("quantity") or 0
        for field in _NUTRIENT_FIELDS:
            value = ingredient.get(field)
            if value is None:
                missing[field] += 1
            else:
                nutrients[field] += value * quantity / 100
        filter_evidence.append({
            key: ingredient.get(key) for key in (
                "quantity", "unit", "optional", "preparation", "raw_text",
                "cleaned_text", "occurrence_id", "normalized_name", "position",
                "canonical_key", "concept_name", "best_food_key", "nutrition_basis",
                "serving_size", "serving_size_unit", "allergen_evidence_kinds",
                "potential_allergens", "may_allergic", "allergen_screening_status",
                "halal_status", "halal_evidence_kind", "vegetarian_status",
                "vegetarian_evidence_kind", "vegetarian_concerns", "may_non_vegetarian",
            )
        })
    result = {
        "recipe_id": row["recipe_id"],
        "title": row.get("title"),
        "instructions": row.get("instructions"),
        "requirement_count": len(row["ingredients"]),
        "unmapped_requirements": unmapped,
        "requirements": requirements,
        "filter_evidence": filter_evidence,
    }
    for field in _NUTRIENT_FIELDS:
        result[field] = nutrients[field]
        result[f"{field}_value_count"] = len(row["ingredients"]) - missing[field]
        result[f"{field}_missing_count"] = missing[field]
    return result


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
        self.last_candidates = []

    def inspect_candidates(self, recipes, servings):
        self.last_candidates = recipes
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

    response, _trace = service.generate(request)

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


def test_plan_v2_consumes_query_missing_counts_and_keeps_offer_path():
    full_rows = [
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
    driver = V2Driver(full_rows)
    calculator = RecordingCalculatorService(CalculatorRepository())
    service = PlanService(PlanRepository(driver), calculator_service=calculator)
    request = PlanRequest(
        horizon_days=1,
        meals_per_day=1,
        nutrients=[
            NutrientRequest(code="sodium", unit="mg", limit=NutrientLimit(max=100))
        ],
    )

    response = service.generate_v2(request)

    outcomes = {item.recipe_id: item for item in response.recipe_outcomes}
    assert outcomes["a-incomplete"].outcome == "dropped"
    assert outcomes["a-incomplete"].cause == "evidence-absent"
    assert "sodium_mg" in next(
        recipe.missing_nutrients
        for recipe in service.last_filter_result
        if recipe.recipe_id == "a-incomplete"
    )
    assert calculator.last_signals["b-offer"].selected_offers
    assert all(not candidate.nutrient_profiles for candidate in calculator.last_candidates)
    selected = next(item for item in response.recipe_outcomes if item.outcome == "selected")
    offer = next(
        item for item in response.constraint_outcomes
        if item.recipe_id == selected.recipe_id and item.constraint == "requirement"
    )
    assert offer.selected_offer is not None
    assert driver.selected_recipe_ids == [selected.recipe_id]
    assert "food_key" not in str(response.model_dump())
