import pytest

from api.features.plan.exceptions import UnknownAllergen, UnknownDietary, UnknownNutrient
from api.features.plan.filtering import filter_candidates
from api.features.plan.models import Ingredient, Recipe
from api.features.plan.schemas import AllergyRequest, DietaryRequest, NutrientRequest, NutrientLimit, PlanRequest


def recipe(recipe_id, **kwargs):
    fields = {"nutrients": {"protein_g": 1}, "nutrition_basis": "per 100 g"}
    fields.update(kwargs)
    return Recipe(recipe_id, recipe_id, [Ingredient(100, "g", **fields)])


def test_compliant_present_evidence_retains_without_drop_cause():
    request = PlanRequest(horizon_days=1, meals_per_day=1)
    result = filter_candidates([recipe("r-1")], request)
    assert [r.recipe_id for r in result] == ["r-1"]
    assert result.outcomes["r-1"].cause is None


def test_absent_and_present_exclusion_causes_are_distinct():
    request = PlanRequest(horizon_days=1, meals_per_day=1,
                          dietary=[DietaryRequest(code="halal")])
    result = filter_candidates([recipe("absent", halal_status=None),
                                recipe("excluded", halal_status="not_halal")], request)
    assert result.drop_outcomes["absent"].cause == "evidence-absent"
    assert result.drop_outcomes["excluded"].cause == "present-evidence-excludes"


def test_present_exclusion_precedes_absent_evidence():
    request = PlanRequest(horizon_days=1, meals_per_day=1,
                          allergies=[AllergyRequest(code="peanut")],
                          dietary=[DietaryRequest(code="halal")])
    result = filter_candidates([recipe("r-1", potential_allergens=["peanut"],
                                        allergen_screening_status="potential_contains",
                                        halal_status=None)], request)
    assert result.drop_outcomes["r-1"].cause == "present-evidence-excludes"
    assert {x.constraint for x in result.drop_outcomes["r-1"].evaluations} == {"allergen", "halal"}


def test_empty_candidate_set_is_reported_distinctly_from_constraint_drop():
    request = PlanRequest(horizon_days=1, meals_per_day=1)
    result = filter_candidates([recipe("drop", halal_status=None)],
                               PlanRequest(horizon_days=1, meals_per_day=1,
                                           dietary=[DietaryRequest(code="halal")]))
    unmapped = filter_candidates([], request)
    assert result.drop_outcomes["drop"].cause == "evidence-absent"
    assert unmapped.unmapped_requirements == 1
    assert not unmapped.drop_outcomes


@pytest.mark.parametrize("request_obj, error", [
    (PlanRequest(horizon_days=1, meals_per_day=1,
                 allergies=[AllergyRequest(code="not-a-real-allergen")]), UnknownAllergen),
    (PlanRequest(horizon_days=1, meals_per_day=1,
                 dietary=[DietaryRequest(code="pescatarian")]), UnknownDietary),
    (PlanRequest(horizon_days=1, meals_per_day=1,
                 nutrients=[NutrientRequest(code="vitamin_c", unit="mg",
                                             limit=NutrientLimit(min=1))]), UnknownNutrient),
])
def test_unsupported_codes_are_input_errors_not_evidence_absent(request_obj, error):
    with pytest.raises(error):
        filter_candidates([recipe("r-1")], request_obj)


def test_all_recipes_drop_returns_empty_pool_with_per_requirement_causes():
    request = PlanRequest(horizon_days=1, meals_per_day=1,
                          dietary=[DietaryRequest(code="halal")])
    result = filter_candidates([recipe("r-1", halal_status=None),
                                recipe("r-2", halal_status="not_halal")], request)
    assert result == []
    assert set(result.drop_outcomes) == {"r-1", "r-2"}
