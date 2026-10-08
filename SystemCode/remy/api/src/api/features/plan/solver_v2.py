import math

from .exceptions import PlanInfeasible, SolverUnavailable
from .models import NamedConstraint, Recipe


def solve_v2(recipes: list[Recipe], request):
    """Solve the meal-plan CP-SAT model with optional nutrient-bound widening."""
    try:
        from ortools.sat.python import cp_model
    except ImportError as exc:
        raise SolverUnavailable("The constraint solver is unavailable") from exc

    recipes = list(recipes)
    recipe_by_idx = {j: recipe for j, recipe in enumerate(recipes)}
    recipe_count = len(recipes)
    horizon = request.horizon_days
    meals_per_day = request.meals_per_day
    scale = 1000

    nutrient_specs = []
    for nutrient in request.nutrients or []:
        code = nutrient.code
        goal = None if nutrient.goal is None else int(round(nutrient.goal.value * scale))
        lo = None
        hi = None
        if nutrient.limit is not None:
            if nutrient.limit.min is not None:
                lo = int(round(nutrient.limit.min * scale))
            if nutrient.limit.max is not None:
                hi = int(round(nutrient.limit.max * scale))

        if goal is None and lo is None and hi is None:
            continue

        nutrient_key = {
            "calories": "calories",
            "protein": "protein_g",
            "carbs": "carbs_g",
            "fat": "fat_g",
            "saturated_fat": "saturated_fat_g",
            "fiber": "fiber_g",
            "sugar": "sugar_g",
            "sodium": "sodium_mg",
            "cholesterol": "cholesterol_mg",
        }.get(code, code)
        nutrient_specs.append(
            {
                "code": code,
                "goal": goal,
                "min": lo,
                "max": hi,
                "values": [
                    int(round((recipe.nutrients.get(nutrient_key, 0) or 0) * scale))
                    for recipe in recipes
                ],
                "weight": 1.0,
            }
        )

    def build_and_solve(specs):
        model = cp_model.CpModel()
        y = {
            (day, recipe): model.NewBoolVar(f"y_{day}_{recipe}")
            for day in range(horizon)
            for recipe in range(recipe_count)
        }
        n = {
            (day, recipe): model.NewIntVar(0, 1, f"n_{day}_{recipe}")
            for day in range(horizon)
            for recipe in range(recipe_count)
        }

        for day in range(horizon):
            model.Add(sum(n[day, recipe] for recipe in range(recipe_count)) == meals_per_day)
            for recipe in range(recipe_count):
                model.Add(n[day, recipe] <= meals_per_day * y[day, recipe])
                model.Add(n[day, recipe] >= y[day, recipe])

        max_days = math.ceil(horizon / 3)
        for recipe in range(recipe_count):
            model.Add(sum(y[day, recipe] for day in range(horizon)) <= max_days)
            for day in range(horizon - 1):
                model.Add(y[day, recipe] + y[day + 1, recipe] <= 1)

        deviation_terms = []
        for spec in specs:
            code = spec["code"]
            for day in range(horizon):
                day_total = sum(
                    n[day, recipe] * spec["values"][recipe]
                    for recipe in range(recipe_count)
                )
                if spec["min"] is not None:
                    model.Add(day_total >= spec["min"])
                if spec["max"] is not None:
                    model.Add(day_total <= spec["max"])
                if spec["goal"] is not None:
                    dev_over = model.NewIntVar(0, 10**9, f"dev_over_{day}_{code}")
                    dev_under = model.NewIntVar(0, 10**9, f"dev_under_{day}_{code}")
                    model.Add(day_total - spec["goal"] == dev_over - dev_under)
                    deviation_terms.append(spec["weight"] * (dev_over + dev_under))

        primary = sum(deviation_terms) if deviation_terms else 0
        secondary = sum(
            (recipe + 1) * n[day, recipe]
            for day in range(horizon)
            for recipe in range(recipe_count)
        )
        model.Minimize(primary + secondary)

        solver = cp_model.CpSolver()
        solver.parameters.random_seed = 0
        solver.parameters.num_search_workers = 1
        status = solver.Solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None
        return solver, n

    effective_specs = nutrient_specs
    result = build_and_solve(effective_specs)
    applied_relaxations = []
    tolerance_pct = request.nutrient_tolerance_pct

    if result is None and tolerance_pct > 0:
        widened_specs = [dict(spec) for spec in nutrient_specs]
        has_bounds = False
        for spec in widened_specs:
            if spec["min"] is not None:
                spec["min"] = int(round(spec["min"] * (1 - tolerance_pct / 100)))
                has_bounds = True
            if spec["max"] is not None:
                spec["max"] = int(round(spec["max"] * (1 + tolerance_pct / 100)))
                has_bounds = True
        if has_bounds:
            effective_specs = widened_specs
            result = build_and_solve(effective_specs)
            if result is not None:
                applied_relaxations.append(
                    {
                        "stage": 1,
                        "kind": "widen_nutrient_bounds",
                        "detail": {"applied_tolerance_pct": tolerance_pct},
                    }
                )

    if result is None:
        reason = "no-recipes-survived" if not recipes else "no-assignment"
        binding_constraints = []
        if not recipes:
            binding_constraints.append(
                NamedConstraint(scope="plan", code="horizon", kind="horizon")
            )
        else:
            for index, spec in enumerate(effective_specs):
                if spec["min"] is None and spec["max"] is None:
                    continue
                relaxed_specs = [dict(item) for item in effective_specs]
                relaxed_specs[index]["min"] = None
                relaxed_specs[index]["max"] = None
                if build_and_solve(relaxed_specs) is not None:
                    binding_constraints.append(
                        NamedConstraint(
                            scope="plan",
                            code=spec["code"],
                            kind="nutrient-bound",
                        )
                    )
            if not binding_constraints:
                binding_constraints.append(
                    NamedConstraint(scope="plan", code="horizon", kind="horizon")
                )
        raise PlanInfeasible(
            "No feasible plan under the requested nutrient tolerance",
            binding_constraints=binding_constraints,
            reason=reason,
        )

    solver, n = result
    days = []
    for day in range(horizon):
        meals = []
        for recipe_idx in range(recipe_count):
            meals.extend([recipe_by_idx[recipe_idx]] * solver.Value(n[day, recipe_idx]))
        days.append(
            sorted(
                meals,
                key=lambda recipe: (
                    -float(recipe.nutrients.get("calories", 0) or 0),
                    recipe.recipe_id,
                ),
            )
        )

    return days, applied_relaxations
