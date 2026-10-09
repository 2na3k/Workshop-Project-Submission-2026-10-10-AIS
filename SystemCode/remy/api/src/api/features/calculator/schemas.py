import math
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, PositiveFloat, field_validator

from domain import NutrientProfile

MAX_REQUEST_INGREDIENTS = 100


class IngredientRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    quantity: PositiveFloat
    unit: Literal["g", "kg", "ml", "tbsp", "pcs"]

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value

    @field_validator("quantity")
    @classmethod
    def finite_quantity(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("quantity must be finite")
        return value


class CostNutritionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    servings: int = Field(ge=1, le=1000)
    budget: float | None = None
    ingredients: list[IngredientRequest] = Field(
        min_length=1, max_length=MAX_REQUEST_INGREDIENTS
    )


class Nutrients(BaseModel):
    """Public API response DTO. Field names are the API contract; do not
    change them without a spec-level API revision."""

    calories_kcal: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    fiber_g: float | None = None
    sugar_g: float | None = None
    sodium_mg: float | None = None
    calcium_mg: float | None = None
    iron_mg: float | None = None

    @classmethod
    def from_profile(cls, profile: NutrientProfile) -> "Nutrients":
        """Boundary translation: canonical internal names → API contract names."""
        return cls(
            calories_kcal=profile.energy_kcal,
            protein_g=profile.protein_g,
            carbs_g=profile.carbohydrate_g,
            fat_g=profile.fat_g,
            fiber_g=profile.fiber_g,
            sugar_g=profile.sugars_g,
            sodium_mg=profile.sodium_mg,
        )


class ItemWarning(BaseModel):
    code: str
    message: str


class ItemizedCalculation(BaseModel):
    ingredient: str
    canonical_key: str
    listing_name: str | None = None
    retailer: str | None = None
    consumed_amount_g: float | None
    consumed_cost_sgd: float | None
    retail_package_cost_sgd: float | None
    nutrients: Nutrients
    warnings: list[ItemWarning] = Field(default_factory=list)


class CalculationSummary(BaseModel):
    total_consumed_cost_sgd: float | None
    total_retail_package_cost_sgd: float | None
    nutrients: Nutrients
    nutrients_per_serving: Nutrients


class CostNutritionResponse(BaseModel):
    status: Literal["success"] = "success"
    servings: int
    summary: CalculationSummary
    itemized: list[ItemizedCalculation]
