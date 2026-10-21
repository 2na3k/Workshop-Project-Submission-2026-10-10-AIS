"""Pure-domain nutrient arithmetic.

Only `test_workflow_arithmetic` needed repair: it used the pre-rename request
code `carbs_g`, whereas the maintained vocabulary is canonical
(`NUTRIENT_FIELDS`, e.g. `carbohydrate_g`).

`domain.nutrients.sum_nutrients` keeps "sum the present values, null only when
every contributor is null" semantics. The stricter R-9 rule (null when ANY
contributor is missing) lives in the calculator's own
`api.features.calculator.domain.nutrition.sum_nutrients`.
"""
from domain.nutrients import (calculate_portion_nutrients, per_serving,
                               scale_nutrients, sum_nutrients, sum_nutrition)
from domain.types import NutrientProfile


def test_profile_arithmetic_preserves_none():
    first = scale_nutrients(NutrientProfile(protein_g=10, fiber_g=None), 200)
    second = scale_nutrients(NutrientProfile(protein_g=None, fiber_g=3), 100)
    total = sum_nutrients([first, second])
    assert total.protein_g == 20
    assert total.fiber_g == 3
    assert per_serving(total, 2).protein_g == 10


def test_workflow_arithmetic():
    portion = calculate_portion_nutrients(
        nutrition_per_100g={"carbohydrate_g": 20}, quantity_g=200, unit="g", servings=2)
    assert portion["carbohydrate_g"] == 20
    assert sum_nutrition([portion, {"carbohydrate_g": 3}])["carbohydrate_g"] == 23
