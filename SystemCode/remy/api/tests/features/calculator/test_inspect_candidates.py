from domain.types import NUTRIENT_FIELDS, NutrientProfile

from api.features.calculator.models import CandidateRecipe, RecipeNutritionSignal
from api.features.calculator.service import CostNutritionService


class UnusedRepository:
    pass


def _profile(**overrides) -> NutrientProfile:
    values = {field: 1.0 for field in NUTRIENT_FIELDS}
    values.update(overrides)
    return NutrientProfile(**values)


def test_inspect_candidates_returns_missing_nutrients_per_recipe():
    recipes = [
        CandidateRecipe(
            recipe_id="partial",
            ingredient_nutrients=[
                _profile(),
                _profile(sodium_mg=None, fiber_g=None),
            ],
        ),
        CandidateRecipe(
            recipe_id="complete",
            ingredient_nutrients=[_profile(), _profile()],
        ),
    ]

    signals = CostNutritionService(UnusedRepository()).inspect_candidates(recipes, servings=3)

    assert signals == {
        "partial": RecipeNutritionSignal(
            recipe_id="partial",
            missing_nutrients=["fiber_g", "sodium_mg"],
        ),
        "complete": RecipeNutritionSignal(recipe_id="complete", missing_nutrients=[]),
    }
