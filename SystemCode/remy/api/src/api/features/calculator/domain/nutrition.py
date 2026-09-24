from dataclasses import asdict
from ..models import NutrientProfile, NUTRIENT_FIELDS


def scale_nutrients(profile: NutrientProfile, grams: float) -> NutrientProfile:
    return NutrientProfile(**{key: (value * grams / 100.0 if value is not None else None)
                              for key, value in asdict(profile).items()})


def sum_nutrients(items: list[NutrientProfile]) -> NutrientProfile:
    return NutrientProfile(**{key: (sum(v for v in (getattr(item, key) for item in items) if v is not None)
                                  if any(getattr(item, key) is not None for item in items) else None)
                              for key in NUTRIENT_FIELDS})


def per_serving(profile: NutrientProfile, servings: int) -> NutrientProfile:
    return NutrientProfile(**{key: (value / servings if value is not None else None)
                              for key, value in profile.__dict__.items()})
