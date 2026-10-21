"""Internal audit trace for a cost and nutrition calculation."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NutrientWinnerTrace:
    source_kind: str | None
    food_key: str | None
    nutrition_rank: int | None
    selection_priority: int | None
    value: float


@dataclass(frozen=True)
class PackageTrace:
    food_key: str | None
    listing_name: str | None
    retailer: str | None
    confidence: float | None
    price: float
    package_count: int
    price_basis: str | None
    freshness_status: str | None


@dataclass(frozen=True)
class EdgeEvidenceTrace:
    freshness_status: str | None
    approval_status: str | None


@dataclass(frozen=True)
class WarningTrace:
    code: str
    message: str
    missing_nutrients: list[str] = field(default_factory=list)


@dataclass
class IngredientTrace:
    canonical_key: str
    resolver_match_type: str
    resolver_confidence: float | None
    nutrient_winners: dict[str, NutrientWinnerTrace] = field(default_factory=dict)
    chosen_package: PackageTrace | None = None
    runner_up_package: PackageTrace | None = None
    edge_evidence: list[EdgeEvidenceTrace] = field(default_factory=list)
    warnings: list[WarningTrace] = field(default_factory=list)


@dataclass
class CalculationTrace:
    ingredients: list[IngredientTrace] = field(default_factory=list)
