from api.features.plan.repository import PlanRepository
from api.features.plan.service import PlanService
from api.features.plan.schemas import DietaryRequest, NutrientLimit, NutrientRequest, PlanRequest
from api.features.calculator.models import RecipeNutritionSignal


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


def canonical_row(**overrides):
    recipe_id = overrides.pop("recipe_id", "r-1")
    ingredient = {
        "quantity": 100, "unit": "g", "occurrence_id": "ingredient-1",
        "canonical_key": "black_pepper", "concept_name": "Black pepper",
        "nutrition_basis": "per 100 g", "energy_kcal": 10,
        "protein_g": 1, "sodium_mg": 1, "halal_status": "halal",
        "best_food_key": "food-1",
        "freshness_status": "fresh", "package_mass_g": 100,
        "price_basis": "package_mass", "cost_basis_compatible": True,
    }
    ingredient.update(overrides)
    return {"recipe_id": recipe_id, "title": "Recipe", "ingredients": [ingredient]}


def test_repository_evidence_reaches_filtering():
    recipe = PlanRepository(Driver([canonical_row(halal_status=None)])).fetch_candidates()[0]
    assert recipe.ingredients[0].halal_status is None


def test_service_propagates_distinct_filter_outcomes():
    class Inspector:
        def inspect_candidates(self, recipes, servings):
            return {
                recipe.recipe_id: RecipeNutritionSignal(recipe.recipe_id, [])
                for recipe in recipes
            }

    service = PlanService(
        PlanRepository(Driver([canonical_row()])), calculator_service=Inspector()
    )
    request = PlanRequest(horizon_days=1, meals_per_day=1,
                          dietary=[DietaryRequest(code="halal")])
    response = service.generate(request)
    assert response.days[0].meals[0].recipe_id == "r-1"
    assert response.recipe_outcomes[0].outcome == "selected"
    assert response.relaxed is False
    assert response.applied_tolerance_pct == 0
    assert any(
        outcome.recipe_id == "r-1" and outcome.constraint == "requirement"
        for outcome in response.constraint_outcomes
    )


def test_canonical_evidence_fields_are_consumed():
    recipe = PlanRepository(Driver([canonical_row(freshness_status="stale",
                                                   cost_basis_compatible=False)])).fetch_candidates()[0]
    ingredient = recipe.ingredients[0]
    assert ingredient.freshness_status == "stale"
    assert ingredient.cost_basis_compatible is False


def test_repository_records_unmapped_requirements_per_recipe():
    row = {
        "recipe_id": "r-unmapped",
        "title": "Partially mapped recipe",
        "ingredients": [
            {
                "quantity": 1,
                "unit": "tsp",
                "occurrence_id": "missing-concept",
                "normalized_name": "rare spice",
                "canonical_key": None,
                "best_food_key": None,
                "raw_text": "1 tsp rare spice",
            },
            {
                "quantity": 2,
                "unit": "g",
                "occurrence_id": "missing-best",
                "normalized_name": "pepper",
                "canonical_key": "black_pepper",
                "best_food_key": None,
                "raw_text": "2 g pepper",
            },
        ],
    }

    recipe = PlanRepository(Driver([row])).fetch_candidates()[0]

    assert [item.occurrence_id for item in recipe.unmapped_requirements] == [
        "missing-concept",
        "missing-best",
    ]
    assert [item.normalized_name for item in recipe.unmapped_requirements] == [
        "rare spice",
        "pepper",
    ]


def test_unmapped_fact_and_relaxed_label_survive_service_path():
    first = canonical_row(recipe_id="r-1", energy_kcal=10, sodium_mg=6)
    second = canonical_row(recipe_id="r-2", energy_kcal=10, sodium_mg=6)
    unmapped = canonical_row(recipe_id="r-unmapped", sodium_mg=1)
    unmapped["ingredients"].append({
        "quantity": 1,
        "unit": "tsp",
        "occurrence_id": "missing-concept",
        "normalized_name": "rare spice",
        "canonical_key": None,
        "best_food_key": None,
        "raw_text": "1 tsp rare spice",
    })

    class Inspector:
        def inspect_candidates(self, recipes, servings):
            from api.features.calculator.models import RecipeNutritionSignal
            return {
                recipe.recipe_id: RecipeNutritionSignal(recipe.recipe_id, [])
                for recipe in recipes
            }

    service = PlanService(
        PlanRepository(Driver([first, second, unmapped])), calculator_service=Inspector()
    )
    request = PlanRequest(
        horizon_days=1,
        meals_per_day=2,
        nutrient_tolerance_pct=20,
        nutrients=[
            NutrientRequest(
                code="sodium",
                unit="mg",
                limit=NutrientLimit(max=10),
            )
        ],
    )

    response = service.generate(request)

    assert response.status == "partial"
    assert response.relaxed is True
    assert response.applied_tolerance_pct == 20
    dropped = next(item for item in response.recipe_outcomes
                   if item.recipe_id == "r-unmapped")
    assert dropped.outcome == "dropped"
    assert dropped.cause == "unmapped"
    assert any(
        item.recipe_id == "r-unmapped"
        and item.constraint == "unmapped"
        and item.requirement_text == "1 tsp rare spice"
        for item in response.constraint_outcomes
    )
