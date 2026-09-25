import secrets
from .filtering import filter_candidates
from .ranking import rank_candidates
from .repository import PlanRepository
# from .solver import solve
from .solver_v2 import solve_v2
from .aggregation import aggregate
from .schemas import PlanResponse, DayResponse, MealResponse, MealIngredientResponse
from .exceptions import InvalidNutrientRange, UnknownNutrient
from .filtering import SUPPORTED_NUTRIENTS


class PlanService:
    def __init__(self, repository: PlanRepository):
        self.repository = repository

    def generate(self, request):
        for n in request.nutrients or []:
            if n.code not in SUPPORTED_NUTRIENTS:
                raise UnknownNutrient(f"Unknown nutrient: {n.code}")
            if n.limit and n.limit.min is not None and n.limit.max is not None and n.limit.min > n.limit.max: raise InvalidNutrientRange(
                "min cannot exceed max")
        recipes = rank_candidates(
            filter_candidates(
                self.repository.fetch_candidates(), request
            ),
            request
        )
        days, relaxations = solve_v2(recipes, request)
        response_days = []
        for d, meals in enumerate(days, 1):
            response_days.append(DayResponse(day=d, meals=[
                MealResponse(
                    slot=f"meal_{i}",
                    recipe_id=r.recipe_id,
                    title=r.title,
                    nutrients={
                        k: round((v or 0) * request.servings, 2) for k, v in
                        r.nutrients.items() if v is not None
                    },
                    ingredients=[MealIngredientResponse(
                        quantity=None if ing.quantity is None else round(ing.quantity * request.servings, 2),
                        unit=ing.unit,
                        text=ing.cleaned_text or ing.raw_text or ing.description or ing.canonical_key,
                        preparation=ing.preparation,
                        optional=bool(ing.optional),
                    ) for ing in sorted(r.ingredients, key=lambda ing: (
                        ing.position if ing.position is not None else 0, ing.occurrence_id or ""))],
                    instructions=r.instructions,
                ) for i, r in
                enumerate(meals, 1)
            ]))
        return PlanResponse(plan_id="plan_" + secrets.token_hex(5),
                            status="partial" if relaxations else "complete",
                            message=f"Successfully generated a {request.horizon_days}-day meal "
                                    f"plan.",
                            validation_summary={
                                "allergen_status": "passed" if request.allergies else "not_requested",
                                "dietary_status": "passed" if request.dietary else "not_requested"},
                            relaxations=relaxations, horizon_totals=aggregate(days, request),
                            days=response_days)
