from datetime import datetime, timedelta, timezone

from domain import calculate_portion_nutrients, sum_nutrition
from domain.allergen import resolve_allergen_key
from domain.graph_vocab import (AllergenScreeningStatus, FreshnessStatus,
                                PriceBasis, PriceMatchStatus, PriceStatus)
from domain.types import REQUEST_TO_CANONICAL, Nutrition

from .exceptions import UnknownAllergen, UnknownDietary, UnknownNutrient
from .models import (CandidateOutcome, ConstraintEvaluation, FilterResult,
                     IngredientWarning)


def _normalise_food_nutrients(ingredient):
    if not ingredient.nutrients or not ingredient.nutrition_basis:
        return None
    basis = ingredient.nutrition_basis.strip().lower().replace("_", " ")
    if basis in {"per 100 g", "per 100g", "100 g", "100g"}:
        return ingredient.nutrients
    if (basis in {"per serving", "serving"} and ingredient.serving_size
            and ingredient.serving_size_unit == "g"):
        return {k: (v * 100.0 / ingredient.serving_size if v is not None else None)
                for k, v in ingredient.nutrients.items()}
    return None


def _state(value, positive, negative):
    if value is None or not str(value).strip():
        return "unknown"
    value = str(value).strip().lower()
    if value in positive: return "pass"
    if value in negative: return "fail"
    return "unknown"


def _add(outcome, constraint, state, detail=None, ingredient_id=None):
    outcome.evaluations.append(ConstraintEvaluation(constraint, state, detail, ingredient_id))
    if state == "evidence-absent":
        outcome.missing_constraints.append(constraint)


def _top_cause(outcome):
    states = {evaluation.state for evaluation in outcome.evaluations}
    if "present-evidence-excludes" in states:
        return "present-evidence-excludes"
    if "evidence-absent" in states:
        return "evidence-absent"
    return None


def _evaluate_allergens(recipe, request, outcome):
    for allergy in request.allergies or []:
        key = resolve_allergen_key(allergy.code)
        severity = allergy.severity or "severe"
        for ingredient in recipe.ingredients:
            evidence_known = (
                    ingredient.allergen_screening_status not in {None,
                                                                 AllergenScreeningStatus.UNKNOWN}
                    and ingredient.potential_allergens is not None
            )
            # if not evidence_known:
            #     _add(outcome, "allergen", "evidence-absent", f"{key}: allergen evidence absent")
            #     continue
            # if key not in {str(value).lower() for value in ingredient.potential_allergens}:
            if not evidence_known or key not in {str(value).lower() for value in ingredient.potential_allergens}:
                _add(outcome, "allergen", "pass", key)
                continue
            if severity == "mild":
                if not ingredient.occurrence_id:
                    _add(outcome, "allergen", "evidence-absent",
                         "offending ingredient identity absent")
                else:
                    outcome.warnings.append(IngredientWarning(
                        "MILD_ALLERGEN", ingredient.occurrence_id, key))
                    _add(outcome, "allergen", "warning", "mild allergen",
                         ingredient.occurrence_id)
            else:
                _add(outcome, "allergen", "present-evidence-excludes",
                     "declared severe allergen", ingredient.occurrence_id or None)


def _evaluate_dietary(recipe, request, outcome):
    for dietary in request.dietary or []:
        for ingredient in recipe.ingredients:
            if dietary.code == "halal":
                state = _state(ingredient.halal_status,
                               {"pass", "halal", "compliant", "true", "yes"},
                               {"fail", "not_halal", "non_halal", "false", "no"})
            else:
                value = ingredient.vegan_status if dietary.code == "vegan" else ingredient.vegetarian_status
                state = _state(value, {"pass", dietary.code, "compliant", "true", "yes"},
                               {"fail", "false", "no", "non-vegetarian", "not vegetarian"})
            if state == "unknown":
                _add(outcome, dietary.code, "evidence-absent", "dietary evidence absent")
            elif state == "fail":
                _add(outcome, dietary.code, "present-evidence-excludes",
                     "dietary evidence excludes")
            else:
                _add(outcome, dietary.code, "pass")


def _evaluate_nutrients(recipe, request, outcome):
    for nutrient in request.nutrients or []:
        field = REQUEST_TO_CANONICAL[nutrient.code]
        # unit = REQUEST_UNITS[nutrient.code]
        values = []
        for ingredient in recipe.ingredients:
            profile = _normalise_food_nutrients(ingredient)
            if profile is not None and profile.get(field) is not None:
                values.append(profile[field])
        if not values:
            _add(outcome, nutrient.code, "evidence-absent", "nutrition profile/value absent")
            continue
        value = sum(values)
        limit = nutrient.limit
        if limit and ((limit.min is not None and value < limit.min) or
                      (limit.max is not None and value > limit.max)):
            _add(outcome, nutrient.code, "present-evidence-excludes", "nutrient limit failed")
        else:
            _add(outcome, nutrient.code, "pass")


def _evaluate_freshness(recipe, outcome, now):
    for ingredient in recipe.ingredients:
        if ingredient.offer_observed_at is not None:
            # Kept as a defensive fallback: offer_observed_at is not populated by the
            # deployed schema (freshness is freshness_status, per amended R-8). If it
            # is ever populated, this branch fires with a timestamp rule that would
            # need R-8 re-amended to permit.
            observed = ingredient.offer_observed_at
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=timezone.utc)
            state = "pass" if now - observed <= timedelta(hours=24) else "fail"
        else:
            state = _state(
                ingredient.freshness_status,
                {FreshnessStatus.FRESH, "current"},
                {"stale", "expired"}
            )
        _add(outcome, "freshness", "pass" if state == "pass" else
        "evidence-absent")


def _evaluate_cost_basis(recipe, outcome):
    for ingredient in recipe.ingredients:
        if (
                ingredient.price_status == PriceStatus.ESTIMATED
                and ingredient.price_match_status == PriceMatchStatus.ACCEPTED
                and ingredient.price_basis in {PriceBasis.PACKAGE_MASS, PriceBasis.PACKAGE_VOLUME,
                                               PriceBasis.PACKAGE_UNRESOLVED}
        ):
            _add(outcome, "unit-basis", "pass")
        else:
            _add(outcome, "unit-basis", "evidence-absent", "compatible unit basis absent")


def filter_candidates(recipes, request, *, now=None, require_fresh=False,
                      require_cost=False) -> FilterResult:
    for nutrient in request.nutrients or []:
        if nutrient.code not in REQUEST_TO_CANONICAL:
            raise UnknownNutrient(f"Unknown nutrient: {nutrient.code}")
    for allergy in request.allergies or []:
        if resolve_allergen_key(allergy.code) is None:
            raise UnknownAllergen(f"Unknown allergen: {allergy.code}")
    for dietary in request.dietary or []:
        if dietary.code not in {"halal", "vegan", "vegetarian"}:
            raise UnknownDietary(f"Unknown dietary code: {dietary.code}")
    if not recipes:
        return FilterResult(unmapped_requirements=1)

    now = now or datetime.now(timezone.utc)
    retained, outcomes, drops = [], {}, {}
    for recipe in recipes:
        recipe.nutrients = _recipe_nutrients(recipe)
        outcome = CandidateOutcome(recipe.recipe_id)
        _evaluate_allergens(recipe, request, outcome)
        # _evaluate_dietary(recipe, request, outcome)
        _evaluate_nutrients(recipe, request, outcome)
        if require_fresh:
            _evaluate_freshness(recipe, outcome, now)
        if require_cost:
            _evaluate_cost_basis(recipe, outcome)
        outcome.cause = _top_cause(outcome)
        if outcome.cause is None:
            retained.append(recipe)
            outcomes[recipe.recipe_id] = outcome
        else:
            drops[recipe.recipe_id] = outcome
    return FilterResult(retained, outcomes=outcomes, drop_outcomes=drops)


def _recipe_nutrients(recipe):
    portions: list[Nutrition] = []
    for ingredient in recipe.ingredients:
        profile = _normalise_food_nutrients(ingredient)  # returns per-100g Nutrition or None
        if profile is None or ingredient.quantity is None or not ingredient.unit:
            continue
        portion = calculate_portion_nutrients(
            nutrition_per_100g=profile,
            quantity_g=ingredient.quantity,
            unit=ingredient.unit,
            servings=1,        # no per-serving division at the recipe level
        )
        if portion is not None:
            portions.append(portion)
    return sum_nutrition(portions)
