import pytest
from api.features.calculator.resolver import normalize_name, resolve
from api.features.calculator.exceptions import AmbiguousIngredient


def test_normalization_and_alias():
    assert normalize_name("  Crème--Brûlée! ") == "creme brulee"
    with pytest.raises(AmbiguousIngredient):
        resolve("oatmeal", ["rolled oats"])


def test_exact_match_wins():
    assert resolve("Chicken Breast", ["chicken breast", "chicken"])[1] == "exact"
