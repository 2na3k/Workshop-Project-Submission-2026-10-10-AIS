import pytest

from api.features.plan.exceptions import PlanInfeasible
from api.features.plan.models import NamedConstraint, Recipe
from api.features.plan.schemas import NutrientLimit, NutrientRequest, PlanRequest
from api.features.plan.solver_v2 import solve_v2
from api.features.calculator.models import OfferRef, RecipeNutritionSignal, RequirementOffer
from api.features.plan.repository import PlanRepository
from api.features.plan.service import PlanService


class Session:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def run(self, query, **params):
        return self.rows


class Driver:
    def __init__(self, rows):
        self.rows = rows

    def session(self):
        return Session(self.rows)


class Inspector:
    def inspect_candidates(self, recipes, servings):
        return {
            recipe.recipe_id: RecipeNutritionSignal(
                recipe_id=recipe.recipe_id,
                missing_nutrients=[],
                selected_offers=[
                    RequirementOffer(
                        occurrence_id="ingredient-1",
                        canonical_key="black_pepper",
                        selected_offer=OfferRef(
                            food_key="food-audit-only",
                            listing_name="Pepper offer",
                            retailer="Example Market",
                        ),
                    )
                ],
            )
            for recipe in recipes
        }


def _plan_response():
    row = {
        "recipe_id": "recipe-1",
        "title": "Pepper recipe",
        "ingredients": [{
            "quantity": 10,
            "unit": "g",
            "occurrence_id": "ingredient-1",
            "canonical_key": "black_pepper",
            "concept_name": "Black pepper",
            "best_food_key": "food-best",
            "cleaned_text": "10 g black pepper",
            "energy_kcal": 10,
            "nutrition_basis": "per 100 g",
        }],
    }
    return PlanService(
        PlanRepository(Driver([row])), calculator_service=Inspector()
    ).generate(PlanRequest(horizon_days=1, meals_per_day=1))


def _infeasible(*, recipes, request):
    with pytest.raises(PlanInfeasible) as caught:
        solve_v2(recipes, request)
    return caught.value


def test_infeasibility_reason_discriminator():
    empty = _infeasible(
        recipes=[],
        request=PlanRequest(horizon_days=1, meals_per_day=1),
    )
    assignment = _infeasible(
        recipes=[Recipe(recipe_id="only", title="Only")],
        request=PlanRequest(horizon_days=2, meals_per_day=1),
    )

    assert empty.reason == "no-recipes-survived"
    assert assignment.reason == "no-assignment"
    assert empty.details[0] == {"field": "reason", "issue": "no-recipes-survived"}
    assert assignment.details[0] == {"field": "reason", "issue": "no-assignment"}


def test_deterministic_across_runs():
    request = PlanRequest(
        horizon_days=1,
        meals_per_day=1,
        nutrient_tolerance_pct=25,
        nutrients=[
            NutrientRequest(
                code="calories",
                unit="kcal",
                limit=NutrientLimit(max=10),
            )
        ],
    )
    recipes = [Recipe(recipe_id="high", title="High", nutrients={"energy_kcal": 20})]

    first = _infeasible(recipes=recipes, request=request)
    second = _infeasible(recipes=recipes, request=request)

    assert first.reason == second.reason == "no-assignment"
    assert first.binding_constraints == second.binding_constraints == [
        NamedConstraint(scope="plan", code="calories", kind="nutrient-bound")
    ]


def test_plan_level_record():
    response, _trace = _plan_response()

    assert response.feasibility_outcome == "plan-produced"
    assert response.relaxed is False
    assert response.applied_tolerance_pct == 0


def test_recipe_level_record():
    response, _trace = _plan_response()

    assert [(item.recipe_id, item.outcome, item.cause) for item in response.recipe_outcomes] == [
        ("recipe-1", "selected", None)
    ]


def test_constraint_level_record():
    response, _trace = _plan_response()

    requirement = next(
        item for item in response.constraint_outcomes if item.constraint == "requirement"
    )
    assert requirement.requirement_text == "10 g black pepper"
    assert requirement.resolved_concept == "Black pepper"
    assert requirement.selected_offer.model_dump() == {
        "listing_name": "Pepper offer",
        "retailer": "Example Market",
    }


def test_no_audit_provenance_in_response():
    response, _trace = _plan_response()
    payload = response.model_dump(mode="json")

    def keys(value):
        if isinstance(value, dict):
            for key, nested in value.items():
                yield key
                yield from keys(nested)
        elif isinstance(value, list):
            for nested in value:
                yield from keys(nested)

    all_keys = set(keys(payload))
    assert not {"confidence", "normalization_version", "food_key", "requirement_id"} & all_keys
    assert not any(key.startswith("source_") for key in all_keys)
