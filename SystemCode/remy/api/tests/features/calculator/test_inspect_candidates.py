from domain.types import NUTRIENT_FIELDS, NutrientProfile

from api.features.calculator.models import (
    CandidateRecipe,
    CandidateRequirement,
    FoodFacts,
    OfferRef,
    RetailSKU,
)
from api.features.calculator.service import CostNutritionService


class UnusedRepository:
    def fetch_food_facts(self, keys):
        packages = [
            RetailSKU(
                retailer="retailer-a",
                listing_name="Best value",
                reference_price_minor=100,
                currency="SGD",
                package_mass_g=100,
                package_count=1,
                price_basis="package_mass",
                cost_basis_compatible=False,
                confidence=0.9,
                price_status="estimated",
                price_match_status="accepted",
                freshness_status="fresh",
                food_key="food-best",
                approval_status="accepted",
            ),
            RetailSKU(
                retailer="retailer-b",
                listing_name="Higher price",
                reference_price_minor=250,
                currency="SGD",
                package_mass_g=100,
                package_count=1,
                price_basis="package_mass",
                cost_basis_compatible=True,
                confidence=1.0,
                price_status="estimated",
                price_match_status="accepted",
                freshness_status="fresh",
                food_key="food-expensive",
                approval_status="accepted",
            ),
        ]
        fact = FoodFacts(
            canonical_key="pepper",
            canonical_name="pepper",
            fdc_id=None,
            description=None,
            nutrients=NutrientProfile(),
            approval_status="accepted",
            packages=packages,
        )
        return {"pepper": [fact]} if "pepper" in keys else {}


def _profile(**overrides) -> NutrientProfile:
    values = {field: 1.0 for field in NUTRIENT_FIELDS}
    values.update(overrides)
    return NutrientProfile(**values)


def test_inspect_candidates_returns_missing_nutrients_per_recipe():
    recipes = [
        CandidateRecipe(
            recipe_id="partial",
            requirements=[CandidateRequirement("pepper", 50, "partial-ingredient")],
            nutrient_profiles=[
                _profile(),
                _profile(sodium_mg=None, fiber_g=None),
            ],
        ),
        CandidateRecipe(
            recipe_id="complete",
            requirements=[CandidateRequirement("no-offer", 20, "complete-ingredient")],
            nutrient_profiles=[_profile(), _profile()],
        ),
    ]

    signals = CostNutritionService(UnusedRepository()).inspect_candidates(recipes, servings=3)

    assert signals["partial"].missing_nutrients == ["fiber_g", "sodium_mg"]
    assert signals["partial"].selected_offers[0].selected_offer == OfferRef(
        food_key="food-best",
        listing_name="Best value",
        retailer="retailer-a",
        confidence=0.9,
    )
    assert signals["complete"].missing_nutrients == []
    assert signals["complete"].selected_offers[0].selected_offer is None
