from api.features.calculator.domain.nutrition import per_serving, scale_nutrients, sum_nutrients
from api.features.calculator.models import NutrientProfile
from api.features.plan.filtering import filter_candidates
from api.features.plan.models import Ingredient, Recipe
from api.features.plan.schemas import NutrientRequest, NutrientLimit, PlanRequest


def _recipe(nutrients=None):
    return Recipe("r-1", "Recipe", [Ingredient(100, "g", nutrients=nutrients,
                                                  nutrition_basis="per 100 g")])


def test_scaling_preserves_nulls_and_sums_values():
    first = scale_nutrients(NutrientProfile(protein_g=10, fiber_g=None), 200)
    second = scale_nutrients(NutrientProfile(protein_g=None, fiber_g=3), 100)
    total = sum_nutrients([first, second])
    assert total.protein_g == 20
    assert total.fiber_g == 3
    assert per_serving(total, 2).protein_g == 10


def test_profileless_candidate_is_not_zero_and_drops_when_required():
    request = PlanRequest(horizon_days=1, meals_per_day=1,
                          nutrients=[NutrientRequest(code="protein", unit="g",
                                                      limit=NutrientLimit(min=1))])
    result = filter_candidates([_recipe(None)], request)
    assert result == []
    assert result.drop_outcomes["r-1"].cause == "evidence-absent"
    assert "protein" in result.drop_outcomes["r-1"].missing_constraints


def test_partial_profile_with_missing_requested_nutrient_is_not_zero():
    request = PlanRequest(horizon_days=1, meals_per_day=1,
                          nutrients=[NutrientRequest(code="fiber", unit="g",
                                                      limit=NutrientLimit(min=1))])
    result = filter_candidates([_recipe({"protein_g": 2})], request)
    assert result == []
    assert result.drop_outcomes["r-1"].cause == "evidence-absent"
