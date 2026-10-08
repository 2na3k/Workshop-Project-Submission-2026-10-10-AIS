from dataclasses import asdict

from domain.exceptions import DomainError
from domain.types import NUTRIENT_FIELDS, NutrientProfile
from domain.units import to_grams

from .domain.cost import consumed_cost, round_money, round_nutrient, select_package
from .domain.nutrition import missing_nutrients, per_serving, scale_nutrients, sum_nutrients
from .domain.nutrition_select import select_nutrient_value
from .exceptions import MissingUnitConversion, UnresolvableIngredient
from .models import CandidateRecipe, OfferRef, RecipeNutritionSignal, RequirementOffer
from .resolver import normalize_name, resolve
from .schemas import (
    CalculationSummary, CostNutritionRequest, CostNutritionResponse, ItemWarning,
    ItemizedCalculation, Nutrients,
)
from .trace import (
    CalculationTrace, EdgeEvidenceTrace, IngredientTrace, NutrientWinnerTrace,
    PackageTrace, WarningTrace,
)


def _public_nutrients(profile: NutrientProfile) -> Nutrients:
    return Nutrients(**{
        key: round_nutrient(key, value) for key, value in asdict(profile).items()
    })


def _package_trace(selected) -> PackageTrace:
    package, count, price = selected
    return PackageTrace(
        food_key=package.food_key,
        listing_name=package.listing_name,
        retailer=package.retailer,
        confidence=package.confidence,
        price=price,
        package_count=count,
        price_basis=package.price_basis,
        freshness_status=package.freshness_status,
    )


class CostNutritionService:
    def __init__(self, repository):
        self.repository = repository

    def inspect_candidates(
        self, recipes: list[CandidateRecipe], servings: int
    ) -> dict[str, RecipeNutritionSignal]:
        """Report nutrients missing from any ingredient in each candidate."""
        del servings  # Missingness is independent of portion scaling.
        signals = {}
        for recipe in recipes:
            absent = set()
            for profile in recipe.nutrient_profiles:
                absent.update(missing_nutrients(profile))
            if not recipe.nutrient_profiles:
                absent.update(NUTRIENT_FIELDS)
            selected_offers = []
            facts_by_key = self.repository.fetch_food_facts(
                [requirement.canonical_key for requirement in recipe.requirements]
            ) if recipe.requirements else {}
            for requirement in recipe.requirements:
                packages = [
                    package
                    for fact in facts_by_key.get(requirement.canonical_key, [])
                    if fact.approval_status == "accepted"
                    for package in fact.packages
                    if package.approval_status == "accepted"
                ]
                selected = select_package(packages, requirement.scaled_grams)
                offer = None
                if selected is not None:
                    package = selected[0]
                    if package.food_key and package.listing_name and package.retailer:
                        offer = OfferRef(
                            food_key=package.food_key,
                            listing_name=package.listing_name,
                            retailer=package.retailer,
                        )
                selected_offers.append(RequirementOffer(
                    occurrence_id=requirement.occurrence_id,
                    canonical_key=requirement.canonical_key,
                    selected_offer=offer,
                ))
            signals[recipe.recipe_id] = RecipeNutritionSignal(
                recipe_id=recipe.recipe_id,
                missing_nutrients=[field for field in NUTRIENT_FIELDS if field in absent],
                selected_offers=selected_offers,
            )
        return signals

    def calculate(self, request: CostNutritionRequest) -> tuple[CostNutritionResponse, CalculationTrace]:
        names = [item.name for item in request.ingredients]
        candidates = self.repository.resolve_candidates(names)
        resolved: list[tuple[str, str, float | None]] = []
        canonical_keys: list[str] = []
        for name in names:
            key_candidates = candidates.get(normalize_name(name), [])
            if not key_candidates:
                raise UnresolvableIngredient(f"Ingredient '{name}' could not be resolved")
            key, match_type, confidence = resolve(name, key_candidates, key_candidates)
            resolved.append((key, match_type, confidence))
            if key not in canonical_keys:
                canonical_keys.append(key)

        facts_by_key = self.repository.fetch_food_facts(canonical_keys)
        items: list[ItemizedCalculation] = []
        nutrient_values: list[NutrientProfile] = []
        consumed_values: list[float | None] = []
        retail_values: list[float | None] = []
        trace = CalculationTrace()

        for ingredient, (key, match_type, resolver_confidence) in zip(request.ingredients, resolved):
            all_facts = facts_by_key.get(key, [])
            accepted = [fact for fact in all_facts if fact.approval_status == "accepted"]
            if not accepted:
                raise UnresolvableIngredient(f"No accepted candidate found for '{ingredient.name}'")

            try:
                grams, unit_warnings = to_grams(ingredient.quantity, ingredient.unit)
            except DomainError as exc:
                raise MissingUnitConversion(str(exc)) from exc

            winners: dict[str, NutrientWinnerTrace] = {}
            selected_nutrients: dict[str, float | None] = {}
            for field in NUTRIENT_FIELDS:
                value, winner = select_nutrient_value(accepted, field)
                selected_nutrients[field] = value
                if winner is not None and value is not None:
                    winners[field] = NutrientWinnerTrace(
                        source_kind=winner.source_kind,
                        food_key=winner.food_key,
                        nutrition_rank=winner.nutrition_rank,
                        selection_priority=winner.selection_priority,
                        value=value,
                    )
            selected_profile = NutrientProfile(**selected_nutrients)
            scaled = scale_nutrients(selected_profile, grams)
            nutrient_values.append(scaled)

            warnings: list[ItemWarning] = []
            warning_traces: list[WarningTrace] = []
            for code in unit_warnings:
                message = "Quantity converted using an assumed gram equivalence"
                warnings.append(ItemWarning(code=code, message=message))
                warning_traces.append(WarningTrace(code=code, message=message))

            absent_nutrients = missing_nutrients(selected_profile)
            if absent_nutrients:
                message = "Missing nutrients: " + ", ".join(absent_nutrients)
                warnings.append(ItemWarning(code="PARTIAL_NUTRITION_DATA", message=message))
                warning_traces.append(WarningTrace(
                    code="PARTIAL_NUTRITION_DATA", message=message,
                    missing_nutrients=absent_nutrients,
                ))

            packages = [
                package for fact in accepted for package in fact.packages
                if package.approval_status == "accepted"
            ]
            selected = select_package(packages, grams)
            runner_up = None
            if selected is not None:
                remaining = [package for package in packages if package is not selected[0]]
                runner_up = select_package(remaining, grams)
                item_consumed = consumed_cost(selected[0], grams)
                item_retail = selected[2] * selected[1]
                listing_name = selected[0].listing_name
                retailer = selected[0].retailer
                chosen_trace = _package_trace(selected)
                runner_trace = _package_trace(runner_up) if runner_up is not None else None
            else:
                item_consumed = None
                item_retail = None
                listing_name = None
                retailer = None
                chosen_trace = None
                runner_trace = None
                message = "No cost-eligible fresh package was found"
                warnings.append(ItemWarning(code="MISSING_PACKAGE_DATA", message=message))
                warning_traces.append(WarningTrace(code="MISSING_PACKAGE_DATA", message=message))

            consumed_values.append(item_consumed)
            retail_values.append(item_retail)
            items.append(ItemizedCalculation(
                ingredient=ingredient.name,
                canonical_key=key,
                listing_name=listing_name,
                retailer=retailer,
                consumed_amount_g=grams,
                consumed_cost_sgd=round_money(item_consumed),
                retail_package_cost_sgd=round_money(item_retail),
                nutrients=_public_nutrients(scaled),
                warnings=warnings,
            ))

            edge_evidence = [
                EdgeEvidenceTrace(
                    freshness_status=package.freshness_status,
                    approval_status=package.approval_status,
                )
                for fact in accepted for package in fact.packages
            ]
            trace.ingredients.append(IngredientTrace(
                canonical_key=key,
                resolver_match_type=match_type,
                resolver_confidence=resolver_confidence,
                nutrient_winners=winners,
                chosen_package=chosen_trace,
                runner_up_package=runner_trace,
                edge_evidence=edge_evidence,
                warnings=warning_traces,
            ))

        total_nutrients = sum_nutrients(nutrient_values)
        total_consumed = (
            sum(value for value in consumed_values if value is not None)
            if all(value is not None for value in consumed_values) else None
        )
        total_retail = (
            sum(value for value in retail_values if value is not None)
            if all(value is not None for value in retail_values) else None
        )
        response = CostNutritionResponse(
            servings=request.servings,
            summary=CalculationSummary(
                total_consumed_cost_sgd=round_money(total_consumed),
                total_retail_package_cost_sgd=round_money(total_retail),
                nutrients=_public_nutrients(total_nutrients),
                nutrients_per_serving=_public_nutrients(per_serving(total_nutrients, request.servings)),
            ),
            itemized=items,
        )
        return response, trace
