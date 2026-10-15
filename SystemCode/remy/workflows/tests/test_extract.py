from workflows.models import AllergyConstraint, ConstraintSet, DietaryConstraint
from workflows.nodes import extract_constraints


def _state(message="plan meals for three days with a severe peanut allergy"):
    return {"raw_message": message, "unapplied_constraints": []}


def test_natural_language_extracts_constraints_and_records_llm(fake_llm):
    result = extract_constraints(_state(), llm=fake_llm)

    parsed = result["parsed_constraints"]
    assert parsed.horizon_days == 3
    assert parsed.allergies == (AllergyConstraint("peanut", "severe"),)
    assert parsed.dietary == (DietaryConstraint("vegan"),)
    assert result["llm_invocations"][0].raw_response == fake_llm.response
    assert result["llm_invocations"][0].parsed_response == fake_llm.response


def test_structured_constraints_are_passed_through_without_calling_llm(fake_llm):
    constraints = ConstraintSet(horizon_days=2, meals_per_day=3)
    state = {**_state(), "structured_constraints": constraints}

    result = extract_constraints(state, llm=fake_llm)

    assert result["parsed_constraints"] == constraints
    assert fake_llm.calls == 0


def test_invalid_constraint_sets_fail_before_plan_is_called():
    for invalid in (
        {"meals_per_day": 2},
        {"horizon_days": 2, "meals_per_day": 2, "nutrient_tolerance_pct": 26},
        {"horizon_days": 2, "meals_per_day": 2, "nutrients": [{"code": "unknown"}]},
        {
            "horizon_days": 2,
            "meals_per_day": 2,
            "nutrients": [{"code": "protein", "minimum": 10, "maximum": 1}],
        },
    ):
        result = extract_constraints({"raw_message": "", "structured_constraints": invalid}, llm=None)
        assert result["outcome"].kind == "failure"
        assert result["outcome"].node == "Extract Constraints"


def test_unapplied_constraints_are_retained_in_outcome_and_trace():
    class LLM:
        provider = "fake"
        model = "fake"

        def invoke(self, prompt):
            return {
                "horizon_days": 2,
                "meals_per_day": 2,
                "unapplied": ["budget", "dislike", "cuisine"],
            }

    result = extract_constraints(_state("cheap meals, no mushrooms, Italian food"), llm=LLM())
    assert result["unapplied_constraints"] == ["budget", "dislike", "cuisine"]
    assert result["outcome"].unapplied_constraints == ("budget", "dislike", "cuisine")
    assert result["trace"].unapplied_constraints == ("budget", "dislike", "cuisine")


def test_ambiguous_severity_is_not_invented_and_tolerance_defaults_to_zero():
    class LLM:
        provider = "fake"
        model = "fake"

        def invoke(self, prompt):
            return {
                "horizon_days": 2,
                "meals_per_day": 2,
                "allergies": [{"code": "peanut", "severity": "mild"}],
            }

    result = extract_constraints(_state("I am a bit allergic to peanuts"), llm=LLM())
    assert result["parsed_constraints"].allergies[0].severity is None
    assert result["parsed_constraints"].nutrient_tolerance_pct == 0
