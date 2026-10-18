from dataclasses import asdict

from .types import NUTRIENT_FIELDS, NutrientProfile, Nutrition
from .units import to_grams


def scale_nutrients(profile: NutrientProfile, grams: float) -> NutrientProfile:
    return NutrientProfile(**{
        key: (value * grams / 100.0 if value is not None else None)
        for key, value in asdict(profile).items()
    })


def sum_nutrients(items: list[NutrientProfile]) -> NutrientProfile:
    return NutrientProfile(**{
        key: (
            sum(v for v in (getattr(item, key) for item in items) if v is not None)
            if any(getattr(item, key) is not None for item in items)
            else None
        )
        for key in NUTRIENT_FIELDS
    })


def per_serving(profile: NutrientProfile, servings: int) -> NutrientProfile:
    return NutrientProfile(**{
        key: (round((value / servings), 2) if value is not None else None)
        for key, value in asdict(profile).items()
    })


def calculate_portion_nutrients(*, nutrition_per_100g: Nutrition | None,
                                quantity_g: float,
                                unit: str,
                                servings: int = 1
                                ) -> Nutrition | None:
    if nutrition_per_100g is None:
        return None
    if unit in {'kcal'}:
        grams = quantity_g
    else:
        try:
            grams, _ = to_grams(quantity_g, unit)
        except Exception:
            return None
    factor = grams / (100.0 * max(servings, 1))

    out: Nutrition = {}
    for key in NUTRIENT_FIELDS:
        value = nutrition_per_100g.get(key)
        if value is not None:
            out[key] = round(value * factor, 4)
    return out


def sum_nutrition(servings: list[Nutrition]) -> Nutrition:
    result: Nutrition = {}
    for key in NUTRIENT_FIELDS:
        total: float | None = 0.0
        missing = False
        for serving in servings:
            value = serving.get(key)
            if value is None:
                missing = True
                break
            total += value
        result[key] = None if missing else total
    return result
