from dataclasses import asdict
from .domain.conversion import to_grams
from .domain.cost import consumed_cost, round_money, round_nutrient, select_package
from .domain.nutrition import per_serving, scale_nutrients, sum_nutrients
from .exceptions import UnresolvableIngredient
from .models import NutrientProfile
from .resolver import normalize_name, resolve
from .schemas import (CalculationSummary, CostNutritionRequest, CostNutritionResponse,
                      ItemWarning, ItemizedCalculation, MatchedPackage, Nutrients)


def _public_nutrients(profile: NutrientProfile) -> Nutrients:
    return Nutrients(**{key: round_nutrient(key, value) for key, value in asdict(profile).items()})


class CostNutritionService:
    def __init__(self, repository):
        self.repository = repository

    def calculate(self, request: CostNutritionRequest) -> CostNutritionResponse:
        names = [item.name for item in request.ingredients]
        candidates = self.repository.resolve_candidates(names)
        canonical_keys: list[str] = []
        resolved: list[str] = []
        for name in names:
            key_candidates = candidates.get(normalize_name(name), [])
            if not key_candidates:
                raise UnresolvableIngredient(f"Ingredient '{name}' could not be resolved")
            key, _, _ = resolve(name, key_candidates, key_candidates)
            resolved.append(key)
            if key not in canonical_keys:
                canonical_keys.append(key)
        facts = self.repository.fetch_food_facts(canonical_keys)
        items, nutrient_values, consumed_values, retail_values = [], [], [], []
        for ingredient, key in zip(request.ingredients, resolved):
            food = facts.get(key)
            if food is None:
                raise UnresolvableIngredient(f"No facts found for '{ingredient.name}'")
            grams, warning_codes = to_grams(ingredient.quantity, ingredient.unit,
                                             food.grams_per_tbsp, food.grams_per_piece)
            warnings = [ItemWarning(code=code, message="Millilitres are treated as grams") for code in warning_codes]
            scaled = scale_nutrients(food.nutrients, grams)
            nutrient_values.append(scaled)
            selected = select_package(food.packages, grams)
            package_model = None
            item_consumed = consumed_cost(selected[0], grams) if selected else None
            item_retail = selected[2] * selected[1] if selected else None
            if selected:
                package_model = MatchedPackage(retailer=selected[0].retailer,
                    package_title=selected[0].listing_name, package_price_sgd=selected[2],
                    package_amount_g=selected[0].package_mass_g, package_count=selected[1])
            else:
                warnings.append(ItemWarning(code="MISSING_PACKAGE_DATA", message="No usable SGD package was found"))
            if any(getattr(food.nutrients, field) is None for field in food.nutrients.__dict__):
                warnings.append(ItemWarning(code="PARTIAL_NUTRITION_DATA", message="Some nutrient facts are missing"))
            consumed_values.append(item_consumed)
            retail_values.append(item_retail)
            items.append(ItemizedCalculation(ingredient=ingredient.name, canonical_name=food.canonical_name,
                fdc_id=food.fdc_id, consumed_amount_g=grams, consumed_cost_sgd=round_money(item_consumed),
                retail_package_cost_sgd=round_money(item_retail), matched_package=package_model,
                nutrients=_public_nutrients(scaled), warnings=warnings))
        total_nutrients = sum_nutrients(nutrient_values)
        total_consumed = sum(consumed_values) if all(v is not None for v in consumed_values) else None
        total_retail = sum(retail_values) if all(v is not None for v in retail_values) else None
        return CostNutritionResponse(servings=request.servings, summary=CalculationSummary(
            total_consumed_cost_sgd=round_money(total_consumed),
            total_retail_package_cost_sgd=round_money(total_retail),
            nutrients=_public_nutrients(total_nutrients),
            nutrients_per_serving=_public_nutrients(per_serving(total_nutrients, request.servings))), itemized=items)
