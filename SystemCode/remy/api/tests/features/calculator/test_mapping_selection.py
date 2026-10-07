"""R-13 fixture: selection uses the best available accepted evidence, with no confidence floor."""

import pytest

from api.features.calculator.exceptions import UnresolvableIngredient
from api.features.calculator.models import FoodFacts, NutrientProfile, RetailSKU
from api.features.calculator.schemas import CostNutritionRequest, IngredientRequest
from api.features.calculator.service import CostNutritionService


def _fact(*, food_key, protein, approval="accepted", confidence=1.0,
          listing="offer", retailer="store", price=100, amount=100):
    package = RetailSKU(
        retailer=retailer, listing_name=listing, reference_price_minor=price,
        currency="SGD", package_mass_g=amount, package_count=1,
        price_basis="package_mass", cost_basis_compatible=False,
        confidence=confidence, fdc_id=food_key,
        price_status="estimated", price_match_status="accepted",
        freshness_status="fresh", food_key=food_key, approval_status=approval,
    )
    return FoodFacts(
        canonical_key="blackberry", canonical_name="blackberry", fdc_id=food_key,
        description=food_key, nutrients=NutrientProfile(protein_g=protein),
        source_kind="fooddata_central", candidate_key=f"candidate:{food_key}",
        nutrition_rank=0, selection_priority=0, food_key=food_key,
        approval_status=approval, packages=[package],
    )


class _Repository:
    def __init__(self, facts):
        self.facts = facts

    def resolve_candidates(self, _names):
        return {"blackberry": ["blackberry"]}

    def fetch_food_facts(self, _keys):
        return {"blackberry": self.facts}


def _request():
    return CostNutritionRequest(
        servings=1,
        ingredients=[IngredientRequest(name="blackberry", quantity=50, unit="g")],
    )


def test_only_accepted_candidates_usable():
    accepted = _fact(food_key="accepted", protein=2, listing="accepted offer", price=300)
    rejected = _fact(food_key="rejected", protein=99, approval="rejected",
                     listing="rejected offer", price=1)
    response, _trace = CostNutritionService(_Repository([rejected, accepted])).calculate(_request())
    item = response.itemized[0]
    assert item.nutrients.protein_g == 1
    assert item.listing_name == "accepted offer"


def test_no_accepted_candidate_is_unresolvable():
    rejected = _fact(food_key="rejected", protein=99, approval="rejected")
    with pytest.raises(UnresolvableIngredient):
        CostNutritionService(_Repository([rejected])).calculate(_request())
