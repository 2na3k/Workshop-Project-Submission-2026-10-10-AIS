import pytest
from api.features.calculator.domain.cost import consumed_cost, round_money, select_package
from api.features.calculator.models import RetailSKU
from api.features.plan.filtering import filter_candidates
from api.features.plan.models import Ingredient, Recipe
from api.features.plan.schemas import PlanRequest
from datetime import datetime, timedelta, timezone


def _package(**overrides):
    values = dict(
        retailer="A", listing_name="item", reference_price_minor=100,
        currency="SGD", package_mass_g=100, package_count=1,
        price_basis="package_mass", cost_basis_compatible=True,
        confidence=1.0, fdc_id="1", price_status="estimated",
        price_match_status="accepted", freshness_status="fresh",
        package_volume_ml=None, food_key="fdc:1",
    )
    values.update(overrides)
    return RetailSKU(**values)


def test_selects_lowest_price_per_gram_and_covers_amount():
    packages = [
        RetailSKU("A", "small", 100, "SGD", 100, 1, "package_mass", True, fdc_id="2"),
        RetailSKU("B", "large", 250, "SGD", 500, 1, "package_mass", True, fdc_id="1"),
    ]
    chosen = select_package(packages, 150)
    assert chosen[0].retailer == "B"
    assert chosen[1] == 1
    assert round_money(consumed_cost(chosen[0], 150)) == 0.75


def test_stale_offer_excluded_and_24_hour_boundary_is_fresh():
    now = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
    stale = Ingredient(100, "g", nutrients={"protein_g": 1},
                       nutrition_basis="per 100 g", freshness_status="fresh",
                       offer_observed_at=now - timedelta(hours=24, seconds=1))
    boundary = Ingredient(100, "g", nutrients={"protein_g": 1},
                          nutrition_basis="per 100 g", freshness_status="fresh",
                          offer_observed_at=now - timedelta(hours=24))
    request = PlanRequest(horizon_days=1, meals_per_day=1)
    dropped = filter_candidates([Recipe("stale", "Stale", [stale])], request,
                                now=now, require_fresh=True)
    retained = filter_candidates([Recipe("boundary", "Boundary", [boundary])], request,
                                 now=now, require_fresh=True)
    assert dropped == []
    assert dropped.drop_outcomes["stale"].cause == "evidence-absent"
    assert [r.recipe_id for r in retained] == ["boundary"]


def test_ineligible_excluded_missing_package_warning():
    assert select_package([_package(freshness_status="stale")], 50) is None
    assert select_package([_package(price_status="unavailable")], 50) is None
    assert select_package([_package(price_match_status="estimated")], 50) is None


@pytest.mark.parametrize("changes", [
    {"price_status": "unavailable"},
    {"price_match_status": "estimated"},
    {"freshness_status": "unknown"},
    {"price_basis": "span_reference"},
    {"currency": "USD"},
    {"reference_price_minor": None},
    {"reference_price_minor": 0},
    {"package_mass_g": None},
    {"package_mass_g": 0},
])
def test_each_eligibility_condition_excludes(changes):
    assert select_package([_package(**changes)], 50) is None


def test_package_volume_eligible_and_converted_silently():
    volume = _package(
        retailer="volume", price_basis="package_volume", package_mass_g=None,
        package_volume_ml=100,
    )
    mass = _package(
        retailer="mass", reference_price_minor=200, package_mass_g=150,
    )
    chosen = select_package([mass, volume], 50)
    assert chosen is not None
    assert chosen[0] is volume
    assert round_money(consumed_cost(chosen[0], 50)) == 0.5


def test_consumed_vs_retail_distinct_sub_package():
    package = _package()
    selected = select_package([package], 20)
    assert selected is not None
    consumed = consumed_cost(selected[0], 20)
    retail = selected[1] * selected[2]
    assert round_money(consumed) == 0.2
    assert round_money(retail) == 1.0
    assert consumed != retail


def test_multi_package_ceil():
    package = _package()
    selected = select_package([package], 300.00000001)
    assert selected is not None
    assert selected[1] == 3
    assert round_money(selected[1] * selected[2]) == 3.0
