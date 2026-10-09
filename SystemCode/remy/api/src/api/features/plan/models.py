from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from domain.types import Nutrition


@dataclass
class Ingredient:
    quantity: float | None
    unit: str | None
    text: str | None = None
    preparation: str | None = None
    optional: bool = False
    position: int | None = None
    occurrence_id: str | None = None
    raw_text: str | None = None
    cleaned_text: str | None = None
    description: str | None = None
    concept_name: str | None = None
    canonical_key: str | None = None
    ingredients: str | None = None
    allergen_evidence_kinds: list[str] | None = None
    potential_allergens: list[str] | None = None
    may_allergic: bool | None = None
    allergen_screening_status: str | None = None
    halal_status: str | None = None
    halal_evidence_kind: str | None = None
    halal_freshness_status: str | None = None
    vegetarian_status: str | None = None
    vegetarian_evidence_kind: str | None = None
    vegetarian_concerns: list[str] | None = None
    may_non_vegetarian: bool | None = None
    nutrients: Nutrition | None = None
    nutrition_basis: str | None = None
    serving_size: float | None = None
    serving_size_unit: str | None = None
    freshness_status: str | None = None
    offer_observed_at: datetime | None = None
    package_mass_g: float | None = None
    package_unit_basis: str | None = None
    price_status: str | None = None
    price_match_status: str | None = None
    price_basis: str | None = None
    cost_basis_compatible: bool | None = None
    vegan_status: str | None = None


@dataclass(frozen=True)
class IngredientWarning:
    code: str
    ingredient_id: str
    detail: str


@dataclass(frozen=True)
class ConstraintEvaluation:
    constraint: str
    state: str
    detail: str | None = None
    ingredient_id: str | None = None


@dataclass(frozen=True)
class NamedConstraint:
    scope: Literal["plan", "recipe", "requirement"]
    code: str
    kind: Literal[
        "present-evidence-excludes",
        "evidence-absent",
        "unmapped",
        "nutrient-bound",
        "horizon",
    ]


@dataclass(frozen=True)
class RecipeOutcome:
    recipe_id: str
    outcome: Literal["selected", "retained-unselected", "dropped"]
    cause: str | None = None
    causes: tuple[str, ...] = ()


@dataclass(frozen=True)
class RequirementOutcome:
    recipe_id: str
    requirement_id: str | None
    constraint: str
    state: str
    requirement_text: str | None = None
    resolved_concept: str | None = None
    selected_offer: object | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class RequirementRef:
    occurrence_id: str | None
    normalized_name: str | None
    raw_text: str | None
    cleaned_text: str | None
    position: int | None
    reason: Literal["missing-food-concept", "missing-best-fulfillment"]


@dataclass
class CandidateOutcome:
    recipe_id: str
    cause: str | None = None
    evaluations: list[ConstraintEvaluation] = field(default_factory=list)
    warnings: list[IngredientWarning] = field(default_factory=list)
    missing_constraints: list[str] = field(default_factory=list)


class FilterResult(list):
    """Retained recipes plus candidate outcomes for downstream stages."""

    def __init__(self, recipes=None, *, outcomes=None, drop_outcomes=None,
                 unmapped_requirements=0):
        super().__init__(recipes or [])
        self.outcomes = outcomes or {}
        self.drop_outcomes = drop_outcomes or {}
        self.unmapped_requirements = unmapped_requirements


@dataclass
class Recipe:
    recipe_id: str
    title: str
    ingredients: list[Ingredient] = field(default_factory=list)
    nutrients: Nutrition = field(default_factory=Nutrition)
    instructions: str | None = None
    score: float = 0.0
    unmapped_requirements: list[RequirementRef] = field(default_factory=list)
