from api.features.calculator.domain.nutrition_select import select_nutrient_value
from api.features.calculator.domain.nutrition import per_serving, scale_nutrients, sum_nutrients
from api.features.calculator.models import FoodFacts, NutrientProfile
from api.features.plan.filtering import filter_candidates
from api.features.plan.models import Ingredient, Recipe
from api.features.plan.schemas import NutrientRequest, NutrientLimit, PlanRequest


def _candidate(*, food_key, value, source_kind="fooddata_central", rank=0,
               priority=0, approval_status="accepted"):
    return FoodFacts(
        canonical_key="ingredient", canonical_name="ingredient", fdc_id=None,
        description=None, nutrients=NutrientProfile(protein_g=value),
        source_kind=source_kind, nutrition_rank=rank,
        selection_priority=priority, food_key=food_key,
        approval_status=approval_status,
    )


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


def test_branded_over_generic():
    branded = _candidate(food_key="brand:1", value=8,
                         source_kind="crawler_fdc_profile", rank=9)
    generic = _candidate(food_key="fdc:1", value=4, rank=0)
    unknown = _candidate(food_key="other:1", value=2, source_kind="other")
    assert select_nutrient_value([generic, branded], "protein_g") == (8, branded)
    assert select_nutrient_value([generic, unknown], "protein_g") == (2, unknown)


def test_same_source_tie_break():
    candidates = [
        _candidate(food_key="fdc:z", value=3, rank=1, priority=1),
        _candidate(food_key="fdc:b", value=2, rank=1, priority=1),
        _candidate(food_key="fdc:a", value=1, rank=1, priority=1),
        _candidate(food_key="fdc:rank", value=0, rank=0, priority=99),
        _candidate(food_key="fdc:null", value=9, rank=None, priority=None),
    ]
    assert select_nutrient_value(candidates, "protein_g") == (0, candidates[3])
    assert select_nutrient_value(candidates[:3], "protein_g") == (1, candidates[2])
