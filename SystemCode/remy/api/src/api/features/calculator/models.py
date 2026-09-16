from dataclasses import dataclass, field


NUTRIENT_FIELDS = ("calories_kcal", "protein_g", "carbs_g", "fat_g", "fiber_g",
                   "sugar_g", "sodium_mg", "calcium_mg", "iron_mg")


@dataclass(frozen=True)
class NutrientProfile:
    calories_kcal: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    fiber_g: float | None = None
    sugar_g: float | None = None
    sodium_mg: float | None = None
    calcium_mg: float | None = None
    iron_mg: float | None = None


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


@dataclass
class FoodFacts:
    canonical_key: str
    canonical_name: str
    fdc_id: str | None
    description: str | None
    nutrients: NutrientProfile
    packages: list[RetailSKU] = field(default_factory=list)
    grams_per_tbsp: float | None = None
    grams_per_piece: float | None = None


@dataclass(frozen=True)
class ConversionFacts:
    grams_per_tbsp: float | None = None
    grams_per_piece: float | None = None
