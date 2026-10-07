"""Calculator nutrient operations over the canonical nine nutrient fields."""

from domain.nutrients import per_serving as per_serving, scale_nutrients as scale_nutrients
from domain.types import NUTRIENT_FIELDS, NutrientProfile


def sum_nutrients(items: list[NutrientProfile]) -> NutrientProfile:
    """Sum complete nutrient columns; never expose an undercounted partial sum."""
    return NutrientProfile(**{
        key: (sum(getattr(item, key) for item in items)
              if items and all(getattr(item, key) is not None for item in items) else None)
        for key in NUTRIENT_FIELDS
    })


def missing_nutrients(profile: NutrientProfile) -> list[str]:
    """Return canonical nutrient fields absent from an item profile."""
    return [key for key in NUTRIENT_FIELDS if getattr(profile, key) is None]
