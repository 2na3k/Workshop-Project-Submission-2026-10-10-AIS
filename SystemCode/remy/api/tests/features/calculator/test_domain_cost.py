from api.features.calculator.domain.cost import consumed_cost, round_money, select_package
from api.features.calculator.models import RetailSKU
from api.features.plan.filtering import filter_candidates
from api.features.plan.models import Ingredient, Recipe
from api.features.plan.schemas import PlanRequest
from datetime import datetime, timedelta, timezone


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
