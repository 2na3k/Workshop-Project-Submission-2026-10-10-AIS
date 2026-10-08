from dataclasses import dataclass, field
# import math

from domain.types import NutrientProfile


@dataclass(frozen=True)
class CandidateRequirement:
    canonical_key: str
    scaled_grams: float
    occurrence_id: str | None = None


@dataclass(frozen=True)
class CandidateRecipe:
    recipe_id: str
    requirements: list[CandidateRequirement]
    nutrient_profiles: list[NutrientProfile]


@dataclass(frozen=True)
class OfferRef:
    food_key: str
    listing_name: str
    retailer: str


@dataclass(frozen=True)
class RequirementOffer:
    occurrence_id: str | None
    canonical_key: str
    selected_offer: OfferRef | None


@dataclass(frozen=True)
class RecipeNutritionSignal:
    recipe_id: str
    missing_nutrients: list[str]
    selected_offers: list[RequirementOffer] = field(default_factory=list)

    @property
    def selected_offer(self) -> OfferRef | None:
        """Return the offer for single-requirement callers; multi-requirement
        callers use ``selected_offers`` to preserve requirement identity.
        """
        if len(self.selected_offers) == 1:
            return self.selected_offers[0].selected_offer
        return None


@dataclass(frozen=True)
class RetailSKU:
    retailer: str | None
    listing_name: str | None
    reference_price_minor: float | None
    currency: str | None
    package_mass_g: float | None
    package_count: int | None
    price_basis: str | None
    cost_basis_compatible: bool | None
    confidence: float | None = None
    fdc_id: str = ""
    price_status: str | None = None
    price_match_status: str | None = None
    freshness_status: str | None = None
    package_volume_ml: float | None = None
    food_key: str | None = None
    nutrition_rank: int | None = None
    selection_priority: int | None = None
    approval_status: str | None = None

    # def __post_init__(self) -> None:
    #     if self.confidence is not None and (
    #         not math.isfinite(self.confidence) or not 0 <= self.confidence <= 1
    #     ):
    #         raise ValueError("confidence must be between 0 and 1 inclusive")


@dataclass
class FoodFacts:
    canonical_key: str
    canonical_name: str
    fdc_id: str | None
    description: str | None
    nutrients: NutrientProfile
    source_kind: str | None = None
    candidate_key: str | None = None
    nutrition_rank: int | None = None
    selection_priority: int | None = None
    food_key: str | None = None
    approval_status: str | None = None
    observed_at: str | None = None
    product_id: str | None = None
    packages: list[RetailSKU] = field(default_factory=list)
    grams_per_tbsp: float | None = None
    grams_per_piece: float | None = None


@dataclass(frozen=True)
class ConversionFacts:
    grams_per_tbsp: float | None = None
    grams_per_piece: float | None = None
