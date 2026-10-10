import pytest
from api.features.calculator.domain.conversion import to_grams
from api.features.calculator.exceptions import MissingUnitConversion


def test_fixed_units_and_ml_warning():
    assert to_grams(2, "kg") == (2000.0, [])
    assert to_grams(10, "ml") == (10, ["ML_ASSUMED_GRAMS"])


def test_component_units_require_positive_facts():
    assert to_grams(2, "tbsp", grams_per_tbsp=15) == (30, [])
    with pytest.raises(MissingUnitConversion):
        to_grams(1, "pc")
