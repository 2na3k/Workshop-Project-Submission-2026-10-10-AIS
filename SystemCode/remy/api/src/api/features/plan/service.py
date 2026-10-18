import secrets

from api.features.calculator import \
    CandidateRecipe as CalculatorCandidateRecipe
from api.features.calculator import (CandidateRequirement,
                                     CostNutritionRepository,
                                     CostNutritionService)
from api.features.calculator.models import RecipeNutritionSignal
from domain.exceptions import DomainError
from domain.types import REQUEST_TO_CANONICAL, NutrientProfile
from domain.units import to_grams

from .aggregation import aggregate
from .exceptions import InvalidNutrientRange, PlanInfeasible, UnknownNutrient
from .filtering import filter_candidates
from .models import NamedConstraint, RecipeOutcome, RequirementOutcome
from .ranking import rank_candidates
from .schemas import (ConstraintOutcomeResponse, DayResponse,
                      MealIngredientResponse, MealResponse,
                      NamedConstraintResponse, PlanResponse,
                      RecipeOutcomeResponse, SelectedOfferResponse)
from .solver_v2 import solve_v2
from .trace import PlanTrace

CAUSE_PRECEDENCE = (
    "present-evidence-excludes",
    "evidence-absent",
    "unmapped",
)


# NUTRIENT_CANONICAL_FIELDS = {
#     "calories": "calories_kcal",
#     "protein": "protein_g",
#     "carbs": "carbs_g",
#     "fat": "fat_g",
#     "saturated_fat": "saturated_fat_g",
#     "fiber": "fiber_g",
#     "sugar": "sugar_g",
#     "sodium": "sodium_mg",
#     "cholesterol": "cholesterol_mg",
# }


def resolve_recipe_causes(causes: list[str]) -> list[str]:
    """Deduplicate causes and return them in the constitutional precedence order."""
    present = set(causes)
    return [cause for cause in CAUSE_PRECEDENCE if cause in present]


def _canonical_profile(nutrients: dict | None) -> NutrientProfile:
    values = nutrients or {}
    return NutrientProfile(
        energy_kcal=values.get("energy_kcal"),
        protein_g=values.get("protein_g"),
        fat_g=values.get("fat_g"),
        saturated_fat_g=values.get("saturated_fat_g"),
        carbohydrate_g=values.get("carbohydrate_g"),
        fiber_g=values.get("fiber_g"),
        sugars_g=values.get("sugars_g"),
        sodium_mg=values.get("sodium_mg"),
        cholesterol_mg=values.get("cholesterol_mg"),
    )


def _calculator_candidates(recipes: list, servings: int) -> list[CalculatorCandidateRecipe]:
    candidates = []
    for recipe in recipes:
        requirements = []
        for ingredient in recipe.ingredients:
            if (not ingredient.canonical_key or ingredient.quantity is None
                    or ingredient.quantity <= 0 or not ingredient.unit):
                continue
            try:
                grams, _warnings = to_grams(ingredient.quantity * servings, ingredient.unit)
            except DomainError:
                continue
            requirements.append(CandidateRequirement(
                canonical_key=ingredient.canonical_key,
                scaled_grams=grams,
                occurrence_id=ingredient.occurrence_id,
            ))
        candidates.append(CalculatorCandidateRecipe(
            recipe_id=recipe.recipe_id,
            requirements=requirements,
            nutrient_profiles=[
                _canonical_profile(ingredient.nutrients) for ingredient in recipe.ingredients
            ],
        ))
    return candidates


def _calculator_skeleton_candidates(recipes: list, servings: int) -> list[
    CalculatorCandidateRecipe]:
    """Build offer-selection inputs without loading full ingredient profiles."""
    candidates = []
    for recipe in recipes:
        requirements = []
        for requirement in recipe.requirements:
            if requirement.quantity is None or requirement.quantity <= 0 or not requirement.unit:
                continue
            try:
                grams, _warnings = to_grams(requirement.quantity * servings, requirement.unit)
            except DomainError:
                continue
            requirements.append(CandidateRequirement(
                canonical_key=requirement.canonical_key,
                scaled_grams=grams,
                occurrence_id=requirement.occurrence_id,
            ))
        candidates.append(CalculatorCandidateRecipe(
            recipe_id=recipe.recipe_id,
            requirements=requirements,
            nutrient_profiles=[],
        ))
    return candidates


def _selected_ids(days: list[list]) -> set[str]:
    return {recipe.recipe_id for day in days for recipe in day}


def _recipe_outcome_records(recipes: list, causes: dict[str, list[str]], selected: set[str]):
    result = []
    for recipe in recipes:
        ordered_causes = resolve_recipe_causes(causes.get(recipe.recipe_id, []))
        if ordered_causes:
            result.append(RecipeOutcome(
                recipe_id=recipe.recipe_id,
                outcome="dropped",
                cause=ordered_causes[0],
                causes=tuple(ordered_causes),
            ))
        else:
            result.append(RecipeOutcome(
                recipe_id=recipe.recipe_id,
                outcome="selected" if recipe.recipe_id in selected else "retained-unselected",
            ))
    return result


def _named_constraint_response(constraint: NamedConstraint) -> NamedConstraintResponse:
    return NamedConstraintResponse(
        scope=constraint.scope,
        code=constraint.code,
        kind=constraint.kind,
    )


def _named_drop_constraints(
        recipes: list,
        causes: dict[str, list[str]],
        constraint_records: list[RequirementOutcome],
) -> list[NamedConstraint]:
    named = []
    for recipe in recipes:
        recipe_causes = causes.get(recipe.recipe_id, [])
        for requirement in recipe.unmapped_requirements:
            code = requirement.normalized_name or requirement.raw_text or requirement.occurrence_id or recipe.recipe_id
            named.append(NamedConstraint(scope="requirement", code=code, kind="unmapped"))
        for cause in recipe_causes:
            if cause == "evidence-absent":
                continue
            if cause == "present-evidence-excludes":
                named.append(NamedConstraint(
                    scope="recipe", code=recipe.recipe_id, kind="present-evidence-excludes"
                ))
    for record in constraint_records:
        if record.state == "present-evidence-excludes":
            named.append(NamedConstraint(
                scope="recipe", code=record.constraint, kind="present-evidence-excludes"
            ))
        elif record.state == "evidence-absent":
            named.append(NamedConstraint(
                scope="recipe", code=record.constraint, kind="evidence-absent"
            ))
    return list(dict.fromkeys(named))


class PlanService:
    def __init__(self, repository, calculator_service=None):
        self.last_filter_result = None
        self.repository = repository
        self.calculator_service = calculator_service or CostNutritionService(
            CostNutritionRepository(repository.driver)
        )
        self.last_trace: PlanTrace | None = None

    def generate(self, request, *, drop_uncosted: bool = False) -> tuple[PlanResponse, PlanTrace]:
        for nutrient in request.nutrients or []:
            if nutrient.code not in REQUEST_TO_CANONICAL:
                raise UnknownNutrient(f"Unknown nutrient: {nutrient.code}")
            if (nutrient.limit and nutrient.limit.min is not None
                    and nutrient.limit.max is not None
                    and nutrient.limit.min > nutrient.limit.max):
                raise InvalidNutrientRange("min cannot exceed max")

        candidates_per_slot = 75
        pool_size = min(13000,
                        request.meals_per_day *
                        max(200, candidates_per_slot * request.horizon_days)
                        )
        candidates = self.repository.fetch_candidates(limit=pool_size)
        filtered = filter_candidates(candidates, request)
        self.last_filter_result = filtered
        causes: dict[str, list[str]] = {}
        constraint_records: list[RequirementOutcome] = []

        for recipe_id, outcome in filtered.drop_outcomes.items():
            causes.setdefault(recipe_id, []).append(outcome.cause)
            for evaluation in outcome.evaluations:
                if evaluation.state in {"present-evidence-excludes", "evidence-absent"}:
                    constraint_records.append(RequirementOutcome(
                        recipe_id=recipe_id,
                        requirement_id=evaluation.ingredient_id,
                        constraint=evaluation.constraint,
                        state=evaluation.state,
                        warnings=(),
                    ))

        for recipe in candidates:
            for requirement in recipe.unmapped_requirements:
                causes.setdefault(recipe.recipe_id, []).append("unmapped")
                constraint_records.append(RequirementOutcome(
                    recipe_id=recipe.recipe_id,
                    requirement_id=requirement.occurrence_id,
                    constraint="unmapped",
                    state="unmapped",
                    requirement_text=(requirement.cleaned_text or requirement.raw_text
                                      or requirement.normalized_name),
                    resolved_concept=requirement.normalized_name,
                ))

        signals = self.calculator_service.inspect_candidates(
            _calculator_candidates(list(filtered), request.servings), request.servings
        )
        selected_offers = {
            (recipe_id, requirement_offer.occurrence_id): requirement_offer.selected_offer
            for recipe_id, signal in signals.items()
            for requirement_offer in signal.selected_offers
        }
        tracked = {
            nutrient.code: REQUEST_TO_CANONICAL[nutrient.code]
            for nutrient in request.nutrients or []
            if nutrient.goal is not None or nutrient.limit is not None
        }
        nutrition_dropped = set()
        for recipe in filtered:
            signal = signals.get(recipe.recipe_id) or RecipeNutritionSignal(
                recipe_id=recipe.recipe_id, missing_nutrients=[]
            )
            missing = set(signal.missing_nutrients)
            for code, canonical_field in tracked.items():
                if canonical_field in missing:
                    causes.setdefault(recipe.recipe_id, []).append("evidence-absent")
                    nutrition_dropped.add(recipe.recipe_id)
                    constraint_records.append(RequirementOutcome(
                        recipe_id=recipe.recipe_id,
                        requirement_id=None,
                        constraint=code,
                        state="evidence-absent",
                    ))

        cost_dropped = set()
        if drop_uncosted:
            for recipe in filtered:
                signal = signals.get(recipe.recipe_id) or RecipeNutritionSignal(
                    recipe_id=recipe.recipe_id, missing_nutrients=[]
                )
                for requirement_offer in signal.selected_offers:
                    if requirement_offer.selected_offer is None:
                        causes.setdefault(recipe.recipe_id, []).append("evidence-absent")
                        cost_dropped.add(recipe.recipe_id)
                        constraint_records.append(RequirementOutcome(
                            recipe_id=recipe.recipe_id,
                            requirement_id=requirement_offer.occurrence_id,
                            constraint="budget",
                            state="evidence-absent",
                        ))

        eligible = [
            recipe for recipe in filtered
            if not recipe.unmapped_requirements
               and recipe.recipe_id not in nutrition_dropped
               and recipe.recipe_id not in cost_dropped
        ]
        ranked = rank_candidates(eligible, request)
        try:
            days, relaxations = solve_v2(ranked, request)
        except PlanInfeasible as exc:
            if exc.reason == "no-recipes-survived":
                binding = _named_drop_constraints(candidates, causes, constraint_records)
                if binding:
                    exc = PlanInfeasible(str(exc), binding, reason=exc.reason)
            trace = PlanTrace(
                feasibility_outcome="infeasible",
                reason=exc.reason,
                binding_constraints=exc.binding_constraints,
                applied_tolerance_pct=0,
                recipes=_recipe_outcome_records(candidates, causes, set()),
                requirements=constraint_records,
            )
            self.last_trace = trace
            response = PlanResponse(
                plan_id="plan_" + secrets.token_hex(5),
                status="partial",
                message=f"No feasible plan for a {request.horizon_days}-day horizon.",
                validation_summary={
                    "allergen_status": "passed" if request.allergies else "not_requested",
                    "dietary_status": "passed" if request.dietary else "not_requested",
                },
                feasibility_outcome="infeasible",
                relaxed=False,
                applied_tolerance_pct=0,
                binding_constraints=[_named_constraint_response(c) for c in
                                     exc.binding_constraints],
                recipe_outcomes=[
                    RecipeOutcomeResponse(
                        recipe_id=record.recipe_id,
                        outcome=record.outcome,
                        cause=record.cause,
                        causes=list(record.causes),
                    )
                    for record in trace.recipes
                ],
                constraint_outcomes=[
                    ConstraintOutcomeResponse(
                        recipe_id=record.recipe_id,
                        requirement_id=record.requirement_id,
                        requirement_text=record.requirement_text,
                        constraint=record.constraint,
                        state=record.state,
                        resolved_concept=record.resolved_concept,
                        selected_offer=(
                            SelectedOfferResponse(
                                listing_name=record.selected_offer.listing_name,
                                retailer=record.selected_offer.retailer,
                            ) if record.selected_offer is not None else None
                        ),
                        warnings=list(record.warnings),
                    )
                    for record in trace.requirements
                ],
                relaxations=[],
                horizon_totals={},
                days=[],
            )
            return response, trace

        selected = _selected_ids(days)
        recipe_records = _recipe_outcome_records(candidates, causes, selected)
        for recipe in candidates:
            if recipe.recipe_id not in selected or recipe.recipe_id in causes:
                continue
            for ingredient in recipe.ingredients:
                warning_codes = tuple(
                    warning.code for warning in getattr(
                        filtered.outcomes.get(recipe.recipe_id), "warnings", []
                    ) if warning.ingredient_id == ingredient.occurrence_id
                )
                offer = selected_offers.get((recipe.recipe_id, ingredient.occurrence_id))
                constraint_records.append(RequirementOutcome(
                    recipe_id=recipe.recipe_id,
                    requirement_id=ingredient.occurrence_id,
                    constraint="requirement",
                    state="selected",
                    requirement_text=(ingredient.cleaned_text or ingredient.raw_text
                                      or ingredient.description or ingredient.canonical_key),
                    resolved_concept=ingredient.concept_name or ingredient.canonical_key,
                    selected_offer=offer,
                    warnings=warning_codes,
                    confidence=offer.confidence if offer else None,
                    source_snapshot_id=offer.source_snapshot_id if offer else None,
                    mapping_version=offer.mapping_version if offer else None,
                ))

        applied_tolerance = request.nutrient_tolerance_pct if relaxations else 0
        trace = PlanTrace(feasibility_outcome="plan-produced",
                          applied_tolerance_pct=applied_tolerance, recipes=recipe_records,
                          requirements=constraint_records, )
        self.last_trace = trace

        response_days = []
        for day_number, meals in enumerate(days, 1):
            response_days.append(DayResponse(day=day_number, meals=[
                MealResponse(
                    slot=f"meal_{index}",
                    recipe_id=recipe.recipe_id,
                    title=recipe.title,
                    nutrients={
                        key: round((value or 0) * request.servings, 2)
                        for key, value in recipe.nutrients.items() if value is not None
                    },
                    ingredients=[MealIngredientResponse(
                        quantity=None if ingredient.quantity is None else round(
                            ingredient.quantity * request.servings, 2
                        ),
                        unit=ingredient.unit,
                        text=(ingredient.cleaned_text or ingredient.raw_text
                              or ingredient.description or ingredient.canonical_key),
                        preparation=ingredient.preparation,
                        optional=bool(ingredient.optional),
                    ) for ingredient in sorted(recipe.ingredients, key=lambda item: (
                        item.position if item.position is not None else 0,
                        item.occurrence_id or "",
                    ))],
                    instructions=recipe.instructions,
                ) for index, recipe in enumerate(meals, 1)
            ]))

        response_recipes = [
            RecipeOutcomeResponse(
                recipe_id=record.recipe_id,
                outcome=record.outcome,
                cause=record.cause,
                causes=list(record.causes),
            )
            for record in recipe_records
        ]
        response_constraints = [
            ConstraintOutcomeResponse(
                recipe_id=record.recipe_id,
                requirement_id=record.requirement_id,
                requirement_text=record.requirement_text,
                constraint=record.constraint,
                state=record.state,
                resolved_concept=record.resolved_concept,
                selected_offer=(
                    SelectedOfferResponse(
                        listing_name=record.selected_offer.listing_name,
                        retailer=record.selected_offer.retailer,
                    ) if record.selected_offer is not None else None
                ),
                warnings=list(record.warnings),
            )
            for record in constraint_records
        ]
        return PlanResponse(
            plan_id="plan_" + secrets.token_hex(5),
            status="partial" if relaxations else "complete",
            message=f"Successfully generated a {request.horizon_days}-day meal plan.",
            validation_summary={
                "allergen_status": "passed" if request.allergies else "not_requested",
                "dietary_status": "passed" if request.dietary else "not_requested",
            },
            relaxed=bool(relaxations),
            applied_tolerance_pct=applied_tolerance,
            recipe_outcomes=response_recipes,
            constraint_outcomes=response_constraints,
            relaxations=relaxations,
            horizon_totals=aggregate(days, request),
            days=response_days,
        ), trace

    def generate_v2(self, request):
        """Generate a plan from nutrient skeletons, fetching details post-solve."""
        for nutrient in request.nutrients or []:
            if nutrient.code not in REQUEST_TO_CANONICAL:
                raise UnknownNutrient(f"Unknown nutrient: {nutrient.code}")
            if (nutrient.limit and nutrient.limit.min is not None
                    and nutrient.limit.max is not None
                    and nutrient.limit.min > nutrient.limit.max):
                raise InvalidNutrientRange("min cannot exceed max")

        candidates_per_slot = 75
        pool_size = min(13000,
                        request.meals_per_day *
                        max(150, candidates_per_slot * request.horizon_days)
                        )
        candidates = self.repository.fetch_candidates_v2(limit=pool_size)
        for recipe in candidates:
            recipe.ingredients = recipe.filter_ingredients
        filtered = filter_candidates(candidates, request)
        self.last_filter_result = filtered

        causes: dict[str, list[str]] = {}
        constraint_records: list[RequirementOutcome] = []
        for recipe_id, outcome in filtered.drop_outcomes.items():
            causes.setdefault(recipe_id, []).append(outcome.cause)
            for evaluation in outcome.evaluations:
                if evaluation.state in {"present-evidence-excludes", "evidence-absent"}:
                    constraint_records.append(RequirementOutcome(
                        recipe_id=recipe_id,
                        requirement_id=evaluation.ingredient_id,
                        constraint=evaluation.constraint,
                        state=evaluation.state,
                    ))

        for recipe in candidates:
            for requirement in recipe.unmapped_requirements:
                causes.setdefault(recipe.recipe_id, []).append("unmapped")
                constraint_records.append(RequirementOutcome(
                    recipe_id=recipe.recipe_id,
                    requirement_id=requirement.occurrence_id,
                    constraint="unmapped",
                    state="unmapped",
                    requirement_text=(requirement.cleaned_text or requirement.raw_text
                                      or requirement.normalized_name),
                    resolved_concept=requirement.normalized_name,
                ))

        tracked = {
            nutrient.code: REQUEST_TO_CANONICAL[nutrient.code]
            for nutrient in request.nutrients or []
            if nutrient.goal is not None or nutrient.limit is not None
        }
        nutrition_dropped = set()
        for recipe in candidates:
            missing = set(recipe.missing_nutrients)
            for code, canonical_field in tracked.items():
                if canonical_field in missing:
                    causes.setdefault(recipe.recipe_id, []).append("evidence-absent")
                    nutrition_dropped.add(recipe.recipe_id)
                    constraint_records.append(RequirementOutcome(
                        recipe_id=recipe.recipe_id,
                        requirement_id=None,
                        constraint=code,
                        state="evidence-absent",
                    ))

        eligible = [
            recipe for recipe in filtered
            if not recipe.unmapped_requirements
               and recipe.recipe_id not in nutrition_dropped
        ]
        # The query's missing counts are authoritative in v2; the calculator
        # result is used here only for its per-requirement selected offers.
        offers_by_recipe = self.calculator_service.inspect_candidates(
            _calculator_skeleton_candidates(eligible, request.servings), request.servings
        )
        selected_offers = {
            (recipe_id, requirement_offer.occurrence_id): requirement_offer.selected_offer
            for recipe_id, signal in offers_by_recipe.items()
            for requirement_offer in signal.selected_offers
        }

        ranked = rank_candidates(eligible, request)
        try:
            days, relaxations = solve_v2(ranked, request)
        except PlanInfeasible as exc:
            if exc.reason == "no-recipes-survived":
                binding = _named_drop_constraints(candidates, causes, constraint_records)
                if binding:
                    exc = PlanInfeasible(str(exc), binding, reason=exc.reason)
            self.last_trace = PlanTrace(
                feasibility_outcome="infeasible",
                reason=exc.reason,
                binding_constraints=exc.binding_constraints,
                applied_tolerance_pct=0,
                recipes=_recipe_outcome_records(candidates, causes, set()),
                requirements=constraint_records,
            )
            raise exc

        selected = _selected_ids(days)
        recipe_records = _recipe_outcome_records(candidates, causes, selected)
        for recipe in candidates:
            if recipe.recipe_id not in selected or recipe.recipe_id in causes:
                continue
            for ingredient in recipe.ingredients:
                warning_codes = tuple(
                    warning.code for warning in getattr(
                        filtered.outcomes.get(recipe.recipe_id), "warnings", []
                    ) if warning.ingredient_id == ingredient.occurrence_id
                )
                constraint_records.append(RequirementOutcome(
                    recipe_id=recipe.recipe_id,
                    requirement_id=ingredient.occurrence_id,
                    constraint="requirement",
                    state="selected",
                    requirement_text=(ingredient.cleaned_text or ingredient.raw_text
                                      or ingredient.description or ingredient.canonical_key),
                    resolved_concept=ingredient.concept_name or ingredient.canonical_key,
                    selected_offer=selected_offers.get(
                        (recipe.recipe_id, ingredient.occurrence_id)),
                    warnings=warning_codes,
                ))

        applied_tolerance = request.nutrient_tolerance_pct if relaxations else 0
        self.last_trace = PlanTrace(
            feasibility_outcome="plan-produced",
            applied_tolerance_pct=applied_tolerance,
            recipes=recipe_records,
            requirements=constraint_records,
        )

        response_days = []
        for day_number, meals in enumerate(days, 1):
            response_days.append(DayResponse(day=day_number, meals=[
                MealResponse(
                    slot=f"meal_{index}",
                    recipe_id=recipe.recipe_id,
                    title=recipe.title,
                    nutrients={
                        key: round((value or 0) * request.servings, 2)
                        for key, value in recipe.nutrients.items() if value is not None
                    },
                    ingredients=[MealIngredientResponse(
                        quantity=None if ingredient.quantity is None else round(
                            ingredient.quantity * request.servings, 2
                        ),
                        unit=ingredient.unit,
                        text=(ingredient.cleaned_text or ingredient.raw_text
                              or ingredient.description or ingredient.canonical_key),
                        preparation=ingredient.preparation,
                        optional=bool(ingredient.optional),
                    ) for ingredient in sorted(recipe.ingredients, key=lambda item: (
                        item.position if item.position is not None else 0,
                        item.occurrence_id or "",
                    ))],
                    instructions=recipe.instructions,
                ) for index, recipe in enumerate(meals, 1)
            ]))

        return PlanResponse(
            plan_id="plan_" + secrets.token_hex(5),
            status="partial" if relaxations else "complete",
            message=f"Successfully generated a {request.horizon_days}-day meal plan.",
            validation_summary={
                "allergen_status": "passed" if request.allergies else "not_requested",
                "dietary_status": "passed" if request.dietary else "not_requested",
            },
            relaxed=bool(relaxations),
            applied_tolerance_pct=applied_tolerance,
            relaxations=relaxations,
            horizon_totals=aggregate(days, request),
            days=response_days,
        )
