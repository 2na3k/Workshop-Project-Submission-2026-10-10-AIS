from dataclasses import dataclass, field
import math

from domain.types import NUTRIENT_FIELDS, NutrientProfile


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

    def __post_init__(self) -> None:
        if self.confidence is not None and (
            not math.isfinite(self.confidence) or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1 inclusive")


@dataclass
class FoodFacts:
    canonical_key: str
    canonical_name: str
    fdc_id: str | None
    description: str | None
    nutrients: NutrientProfile
    source_kind: str | None = None
    candidate_key: str | None = None
    observed_at: str | None = None
    product_id: str | None = None
    packages: list[RetailSKU] = field(default_factory=list)
    grams_per_tbsp: float | None = None
    grams_per_piece: float | None = None


@dataclass(frozen=True)
class ConversionFacts:
    grams_per_tbsp: float | None = None
    grams_per_piece: float | None = None
