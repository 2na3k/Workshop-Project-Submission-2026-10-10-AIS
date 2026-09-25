import pytest

from domain.exceptions import DomainError, MissingConversionError, UnitConversionError
from domain.units import to_grams


def test_supported_units_and_warning():
    assert to_grams(2, "kg") == (2000.0, [])
    assert to_grams(10, "ml") == (10, ["ML_ASSUMED_GRAMS"])
    assert to_grams(2, "tbsp", grams_per_tbsp=15) == (30, [])


def test_invalid_units_and_conversions():
    with pytest.raises(MissingConversionError):
        to_grams(1, "pc")
    with pytest.raises(UnitConversionError):
        to_grams(1, "unknown")
    with pytest.raises(DomainError):
        to_grams(0, "g")
