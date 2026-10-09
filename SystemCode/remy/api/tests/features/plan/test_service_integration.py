from api.features.plan.repository import QUERY_INGREDIENTS, QUERY_RECIPES, PlanRepository
from api.features.plan.service import PlanService
from api.features.plan.schemas import DietaryRequest, NutrientLimit, NutrientRequest, PlanRequest
from api.features.calculator.models import (
    OfferRef,
    RecipeNutritionSignal,
    RequirementOffer,
)


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


class V2Session:
    def __init__(self, skeleton_rows, ingredient_rows, driver):
        self.skeleton_rows = skeleton_rows
        self.ingredient_rows = ingredient_rows
        self.driver = driver

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def run(self, query, **params):
        if query == QUERY_RECIPES:
            self.driver.candidate_limit = params["limit"]
            return self.skeleton_rows
        if query == QUERY_INGREDIENTS:
            self.driver.selected_recipe_ids = list(params["recipe_ids"])
            return [row for row in self.ingredient_rows
                    if row["recipe_id"] in params["recipe_ids"]]
        raise AssertionError("unexpected v2 plan query")


class V2Driver:
    def __init__(self, skeleton_rows, ingredient_rows):
        self.skeleton_rows = skeleton_rows
        self.ingredient_rows = ingredient_rows
        self.candidate_limit = None
        self.selected_recipe_ids = []

    def session(self):
        return V2Session(self.skeleton_rows, self.ingredient_rows, self)


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


def skeleton_row(recipe_id="r-1"):
    return {
        "recipe_id": recipe_id,
        "title": "Recipe",
        "instructions": "Mix.",
        "energy_kcal": 10,
        "protein_g": 1,
        "fat_g": 0,
        "saturated_fat_g": 0,
        "carbohydrate_g": 0,
        "fiber_g": 0,
        "sugars_g": 0,
        "sodium_mg": 1,
        "cholesterol_mg": 0,
        "energy_kcal_missing_count": 0,
        "protein_g_missing_count": 0,
        "fat_g_missing_count": 0,
        "saturated_fat_g_missing_count": 0,
        "carbohydrate_g_missing_count": 0,
        "fiber_g_missing_count": 0,
        "sugars_g_missing_count": 0,
        "sodium_mg_missing_count": 0,
        "cholesterol_mg_missing_count": 0,
        "requirement_count": 1,
        "unmapped_best_fulfillment_count": 0,
        "unmapped_requirements": [],
        "requirements": [{
            "canonical_key": "black_pepper",
            "quantity": 100,
            "unit": "g",
            "occurrence_id": "ingredient-1",
        }],
        "filter_evidence": [{
            "quantity": 100,
            "unit": "g",
            "occurrence_id": "ingredient-1",
            "normalized_name": "black pepper",
            "canonical_key": "black_pepper",
            "concept_name": "Black pepper",
            "best_food_key": "food-1",
            "nutrition_basis": "per 100 g",
            "halal_status": "halal",
            "vegetarian_status": "vegetarian",
            "vegan_status": None,
            "allergen_evidence_kinds": [],
            "potential_allergens": [],
            "may_allergic": False,
            "allergen_screening_status": "screened",
        }],
    }


def test_fetch_candidates_v2_preserves_nutrition_and_unmapped_signals():
    row = skeleton_row()
    row["protein_g_missing_count"] = 1
    row["unmapped_requirements"] = [{
        "occurrence_id": "missing-best",
        "normalized_name": "pepper",
        "raw_text": "pepper",
        "cleaned_text": "pepper",
        "position": 2,
        "reason": "missing-best-fulfillment",
    }]
    row["requirements"].append({
        "canonical_key": "black_pepper",
        "quantity": 1,
        "unit": "g",
        "occurrence_id": "ingredient-2",
    })
    driver = V2Driver([row], [])

    recipe = PlanRepository(driver).fetch_candidates_v2(limit=17)[0]

    assert recipe.ingredients == []
    assert recipe.nutrients["energy_kcal"] == 10
    assert recipe.missing_nutrients == ["protein_g"]
    assert recipe.unmapped_requirements[0].occurrence_id == "missing-best"
    assert recipe.requirements[1].occurrence_id == "ingredient-2"
    assert driver.candidate_limit == 17


def test_generate_v2_matches_generate_and_fetches_selected_ingredients_only():
    full_rows = [
        canonical_row(
            recipe_id=recipe_id,
            fat_g=0,
            saturated_fat_g=0,
            carbohydrate_g=0,
            fiber_g=0,
            sugars_g=0,
            cholesterol_mg=0,
        )
        for recipe_id in ("r-1", "r-2")
    ]
    for row in full_rows:
        row["instructions"] = "Mix."
    skeletons = [skeleton_row("r-1"), skeleton_row("r-2")]
    v2_driver = V2Driver(
        skeletons,
        [{"recipe_id": row["recipe_id"], "ingredients": row["ingredients"]}
         for row in full_rows],
    )

    class Inspector:
        def inspect_candidates(self, recipes, servings):
            results = {}
            for recipe in recipes:
                requirements = getattr(recipe, "requirements", [])
                results[recipe.recipe_id] = RecipeNutritionSignal(
                    recipe_id=recipe.recipe_id,
                    missing_nutrients=[],
                    selected_offers=[
                        RequirementOffer(
                            occurrence_id=requirement.occurrence_id,
                            canonical_key=requirement.canonical_key,
                            selected_offer=OfferRef(
                                food_key="offer-food",
                                listing_name="Pepper listing",
                                retailer="Example Market",
                            ),
                        )
                        for requirement in requirements
                    ],
                )
            return results

    request = PlanRequest(horizon_days=1, meals_per_day=1)
    old_response = PlanService(
        PlanRepository(Driver(full_rows)), calculator_service=Inspector()
    ).generate(request)
    v2_response = PlanService(
        PlanRepository(v2_driver), calculator_service=Inspector()
    ).generate_v2(request)

    old_payload = old_response.model_dump(exclude={"plan_id"})
    v2_payload = v2_response.model_dump(exclude={"plan_id"})
    assert old_payload == v2_payload, f"old={old_payload!r}\nv2={v2_payload!r}"
    assert v2_driver.selected_recipe_ids == [v2_response.days[0].meals[0].recipe_id]
    assert len(v2_driver.selected_recipe_ids) == 1


def test_generate_v2_keeps_per_recipe_unmapped_cause():
    valid = skeleton_row("r-valid")
    unmapped = skeleton_row("r-unmapped")
    unmapped["unmapped_requirements"] = [{
        "occurrence_id": "missing-concept",
        "normalized_name": "rare spice",
        "raw_text": "1 tsp rare spice",
        "cleaned_text": "1 tsp rare spice",
        "position": 2,
        "reason": "missing-food-concept",
    }]
    unmapped["unmapped_best_fulfillment_count"] = 1
    full_rows = [
        {"recipe_id": "r-valid", "ingredients": canonical_row()["ingredients"]},
    ]
    driver = V2Driver([valid, unmapped], full_rows)

    class Inspector:
        def inspect_candidates(self, recipes, servings):
            return {
                recipe.recipe_id: RecipeNutritionSignal(recipe.recipe_id, [])
                for recipe in recipes
            }

    response = PlanService(
        PlanRepository(driver), calculator_service=Inspector()
    ).generate_v2(PlanRequest(horizon_days=1, meals_per_day=1))

    outcome = next(item for item in response.recipe_outcomes
                   if item.recipe_id == "r-unmapped")
    assert outcome.outcome == "dropped"
    assert outcome.cause == "unmapped"
    assert any(
        item.recipe_id == "r-unmapped" and item.state == "unmapped"
        and item.requirement_text == "1 tsp rare spice"
        for item in response.constraint_outcomes
    )


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
