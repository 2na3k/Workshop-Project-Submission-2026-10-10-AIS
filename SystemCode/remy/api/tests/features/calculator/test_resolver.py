from api.features.calculator.resolver import normalize_name, resolve


def test_normalization_and_alias():
    assert normalize_name("  Crème--Brûlée! ") == "creme brulee"
    assert resolve("oatmeal", ["rolled oats"])[0] == "rolled oats"


def test_exact_match_wins():
    assert resolve("Chicken Breast", ["chicken breast", "chicken"])[1] == "exact"
