import pytest
from api.features.calculator.domain.conversion import to_grams
from api.features.calculator.exceptions import MissingUnitConversion
from api.features.plan.filtering import filter_candidates
from api.features.plan.models import Ingredient, Recipe
from api.features.plan.schemas import PlanRequest


def test_fixed_units_and_ml_warning():
    assert to_grams(2, "kg") == (2000.0, [])
    assert to_grams(10, "ml") == (10, ["UNIT_ASSUMED_GRAMS"])


def test_component_units_require_positive_facts():
    assert to_grams(2, "tbsp", grams_per_tbsp=15) == (30, [])
    with pytest.raises(MissingUnitConversion):
        to_grams(1, "pc")


def test_incompatible_unit_basis_is_excluded_and_drops_when_only_option():
    ingredient = Ingredient(1, "pc", nutrients={"protein_g": 1},
                            nutrition_basis="per serving",
                            cost_basis_compatible=False,
                            package_unit_basis="mass")
    result = filter_candidates([Recipe("r-1", "Recipe", [ingredient])],
                               PlanRequest(horizon_days=1, meals_per_day=1),
                               require_cost=True)
    assert result == []
    assert result.drop_outcomes["r-1"].cause == "evidence-absent"
