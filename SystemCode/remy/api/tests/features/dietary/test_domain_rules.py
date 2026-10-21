from api.features.plan.filtering import filter_candidates
from api.features.plan.models import Ingredient, Recipe
from api.features.plan.schemas import AllergyRequest, DietaryRequest, PlanRequest


def _recipe(recipe_id="r-1", **kwargs):
    fields = {"nutrients": {"protein_g": 1}, "nutrition_basis": "per 100 g"}
    fields.update(kwargs)
    return Recipe(recipe_id, "Recipe", [Ingredient(100, "g", **fields)])


def test_severe_allergen_drops_as_present_exclusion():
    request = PlanRequest(horizon_days=1, meals_per_day=1,
                          allergies=[AllergyRequest(code="peanut", severity="severe")])
    result = filter_candidates([_recipe(potential_allergens=["peanut"],
                                         allergen_screening_status="potential_contains")], request)
    assert result == []
    assert result.drop_outcomes["r-1"].cause == "present-evidence-excludes"


def test_mild_allergen_retains_with_ingredient_warning():
    request = PlanRequest(horizon_days=1, meals_per_day=1,
                          allergies=[AllergyRequest(code="peanut", severity="mild")])
    result = filter_candidates([_recipe(occurrence_id="ingredient-1",
                                         potential_allergens=["peanut"],
                                         allergen_screening_status="potential_contains")], request)
    assert [r.recipe_id for r in result] == ["r-1"]
    assert result.outcomes["r-1"].warnings[0].ingredient_id == "ingredient-1"


def test_mild_allergen_without_ingredient_identity_fails():
    request = PlanRequest(horizon_days=1, meals_per_day=1,
                          allergies=[AllergyRequest(code="peanut", severity="mild")])
    result = filter_candidates([_recipe(potential_allergens=["peanut"],
                                         allergen_screening_status="potential_contains")], request)
    assert result == []
    assert result.drop_outcomes["r-1"].cause == "evidence-absent"


def test_undeclared_allergen_drops_as_evidence_absent():
    request = PlanRequest(horizon_days=1, meals_per_day=1,
                          allergies=[AllergyRequest(code="peanut")])
    result = filter_candidates([_recipe(potential_allergens=None,
                                         allergen_screening_status="unknown")], request)
    assert result == []
    assert result.drop_outcomes["r-1"].cause == "evidence-absent"


def test_unknown_dietary_state_drops_and_explicit_compliance_retains():
    unknown_request = PlanRequest(horizon_days=1, meals_per_day=1,
                                  dietary=[DietaryRequest(code="halal")])
    unknown = filter_candidates([_recipe(halal_status=None)], unknown_request)
    assert unknown == []
    assert unknown.drop_outcomes["r-1"].cause == "evidence-absent"

    compliant = filter_candidates([_recipe(halal_status="halal")], unknown_request)
    assert [r.recipe_id for r in compliant] == ["r-1"]


def test_missing_allergen_severity_defaults_to_severe():
    request = PlanRequest(horizon_days=1, meals_per_day=1,
                          allergies=[AllergyRequest(code="peanut")])
    result = filter_candidates([_recipe(potential_allergens=["peanut"],
                                         allergen_screening_status="potential_contains")], request)
    assert result == []
    assert result.drop_outcomes["r-1"].cause == "present-evidence-excludes"
