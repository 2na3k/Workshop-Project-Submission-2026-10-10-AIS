from api.features.calculator.domain.nutrition_select import select_nutrient_value
from api.features.calculator.domain.nutrition import (
    missing_nutrients, per_serving, scale_nutrients, sum_nutrients,
)
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


def test_scaling_preserves_nulls_and_only_sums_complete_columns():
    first = scale_nutrients(NutrientProfile(protein_g=10, fiber_g=None), 200)
    second = scale_nutrients(NutrientProfile(protein_g=None, fiber_g=3), 100)
    total = sum_nutrients([first, second])
    assert total.protein_g is None
    assert total.fiber_g is None
    assert per_serving(total, 2).protein_g is None


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
    unknown = _candidate(food_key="other:1", value=2, source_kind="other", rank=-1)
    assert select_nutrient_value([generic, branded], "protein_g") == (8, branded)
    assert select_nutrient_value([unknown, branded], "protein_g") == (8, branded)


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


def test_order_independent_determinism():
    candidates = [
        _candidate(food_key="fdc:z", value=3, rank=1, priority=1),
        _candidate(food_key="fdc:a", value=1, rank=1, priority=1),
        _candidate(food_key="fdc:rank", value=2, rank=0, priority=9),
    ]
    outcomes = []
    for ordered in (candidates, list(reversed(candidates)),
                    [candidates[1], candidates[0], candidates[2]]):
        value, winner = select_nutrient_value(ordered, "protein_g")
        total = sum_nutrients([scale_nutrients(winner.nutrients, 100)])
        outcomes.append((value, winner.food_key, total.protein_g))
    assert outcomes == [(2, "fdc:rank", 2)] * 3


def test_nutrient_null_when_any_missing_and_warning_names():
    complete = NutrientProfile(protein_g=2, sodium_mg=4)
    missing_protein = NutrientProfile(protein_g=None, sodium_mg=5)
    total = sum_nutrients([complete, missing_protein])
    assert total.protein_g is None
    assert per_serving(total, 2).protein_g is None
    assert total.sodium_mg == 9
    assert missing_nutrients(missing_protein) == [
        "calories_kcal", "protein_g", "fat_g", "saturated_fat_g", "carbs_g",
        "fiber_g", "sugar_g", "cholesterol_mg",
    ]


def test_scale_total_per_serving():
    item_one = scale_nutrients(NutrientProfile(protein_g=10, sodium_mg=50), 200)
    item_two = scale_nutrients(NutrientProfile(protein_g=5, sodium_mg=20), 100)
    total = sum_nutrients([item_one, item_two])
    assert item_one.protein_g == 20
    assert total.protein_g == 25
    assert per_serving(total, 5).protein_g == 5
