"""Vocabulary for the p2 reasoning core.

Two vocabularies exist in this system:

- **Request code** — the user-facing API contract for `nutrients[].code`.
  Never appears on internal data structures.
- **Canonical field** — the internal vocabulary. Matches the deployed `Food`
  node's property names (see `SystemCode/docs/neo4j_db_design.md`). Used by
  `NutrientProfile`, `Nutrition`, and every internal dict or dataclass that
  carries a nutrient value.

One boundary translation table (`REQUEST_TO_CANONICAL`) maps between them.
Every module in the p2 reasoning core imports it from here. No module
redeclares its own mapping.
"""
from dataclasses import dataclass
from typing import Literal, TypedDict


# ─── Canonical internal vocabulary (matches the deployed `Food` node) ───

CanonicalField = Literal[
    "energy_kcal",
    "protein_g",
    "fat_g",
    "saturated_fat_g",
    "carbohydrate_g",
    "fiber_g",
    "sugars_g",
    "sodium_mg",
    "cholesterol_mg",
]

NUTRIENT_FIELDS: tuple[CanonicalField, ...] = (
    "energy_kcal",
    "protein_g",
    "fat_g",
    "saturated_fat_g",
    "carbohydrate_g",
    "fiber_g",
    "sugars_g",
    "sodium_mg",
    "cholesterol_mg",
)


@dataclass(frozen=True)
class NutrientProfile:
    """The canonical per-100g nutrient profile for a food."""

    energy_kcal: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    saturated_fat_g: float | None = None
    carbohydrate_g: float | None = None
    fiber_g: float | None = None
    sugars_g: float | None = None
    sodium_mg: float | None = None
    cholesterol_mg: float | None = None


class Nutrition(TypedDict, total=False):
    """Canonical per-ingredient nutrient dict. Field names match
    `NutrientProfile` and the deployed `Food` node."""

    energy_kcal: float | None
    protein_g: float | None
    fat_g: float | None
    saturated_fat_g: float | None
    carbohydrate_g: float | None
    fiber_g: float | None
    sugars_g: float | None
    sodium_mg: float | None
    cholesterol_mg: float | None


# ─── Request vocabulary (user-facing API contract) ───

RequestCode = Literal[
    "calories",
    "protein",
    "carbs",
    "fat",
    "saturated_fat",
    "fiber",
    "sugar",
    "sodium",
    "cholesterol",
]

# The single translation table. Every module imports this; no module redeclares.
REQUEST_TO_CANONICAL: dict[RequestCode, CanonicalField] = {
    "calories": "energy_kcal",
    "protein": "protein_g",
    "carbs": "carbohydrate_g",
    "fat": "fat_g",
    "saturated_fat": "saturated_fat_g",
    "fiber": "fiber_g",
    "sugar": "sugars_g",
    "sodium": "sodium_mg",
    "cholesterol": "cholesterol_mg",
}

# Display units per request code, for response formatting.
REQUEST_UNITS: dict[RequestCode, str] = {
    "calories": "kcal",
    "protein": "g",
    "carbs": "g",
    "fat": "g",
    "saturated_fat": "g",
    "fiber": "g",
    "sugar": "g",
    "sodium": "mg",
    "cholesterol": "mg",
}


def canonical_field(code: RequestCode) -> CanonicalField:
    """Translate a request code to its canonical field name."""
    return REQUEST_TO_CANONICAL[code]


# ─── p2-001 outcome vocabulary ───

CheckState = Literal["pass", "fail", "unknown", "not_requested"]
