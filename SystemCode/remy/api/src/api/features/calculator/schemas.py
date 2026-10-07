import math
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, PositiveFloat, field_validator

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
    calories_kcal: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    saturated_fat_g: float | None = None
    fiber_g: float | None = None
    sugar_g: float | None = None
    sodium_mg: float | None = None
    cholesterol_mg: float | None = None
    calcium_mg: float | None = None
    iron_mg: float | None = None


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
