"""Pure-domain unit conversion.

Mirrors the maintained fixture
`api/tests/features/calculator/test_domain_conversion.py`.

Stale from the initial scaffold: the warning code is `UNIT_ASSUMED_GRAMS`
(not `ML_ASSUMED_GRAMS`), the ingredient-specific conversion kwargs
(`grams_per_tbsp` / `grams_per_piece`) were removed, and count units such as
`pc` now convert from the fixed table instead of raising.
"""
import pytest

from domain.exceptions import DomainError, UnitConversionError
from domain.units import to_grams


def test_supported_units_and_warning():
    assert to_grams(2, "kg") == (2000.0, [])
    assert to_grams(10, "ml") == (10, ["UNIT_ASSUMED_GRAMS"])
    assert to_grams(2, "tbsp") == (30, ["UNIT_ASSUMED_GRAMS"])


def test_invalid_units_and_conversions():
    assert to_grams(1, "pc") == (50, ["UNIT_ASSUMED_GRAMS"])
    with pytest.raises(UnitConversionError):
        to_grams(1, "unknown")
    with pytest.raises(DomainError):
        to_grams(0, "g")
