from app.chat_contract import from_trace_envelope
from workflows.models import Outcome, PlanTraceView, RecipeOutcomeView, RequirementOutcomeView
from workflows.trace import assemble_trace


def _dropped_trace(recipe_id: str, causes: tuple[str, ...]):
    return assemble_trace(
        raw_message="Plan a meal",
        parsed_constraints=None,
        unapplied_constraints=(),
        outcome=Outcome(kind="infeasible", reason="No eligible recipes"),
        plan_trace=PlanTraceView(
            feasibility_outcome="infeasible",
            reason="No eligible recipes",
            recipes=(RecipeOutcomeView(recipe_id, "dropped", cause=causes[0], causes=causes),),
            requirements=(
                RequirementOutcomeView(
                    recipe_id=recipe_id,
                    requirement_id=f"{recipe_id}-requirement",
                    constraint="vegan",
                    state="evidence_absent",
                    requirement_text="tofu",
                    resolved_concept=None,
                    selected_offer=None,
                    warnings=(),
                ),
            ),
        ),
    )


def test_all_three_levels_present():
    absent = from_trace_envelope(_dropped_trace("r-absent", ("evidence-absent",)), "t-absent")
    excluded = from_trace_envelope(
        _dropped_trace("r-excluded", ("present-evidence-excludes",)), "t-excluded"
    )
    for response in (absent, excluded):
        assert response.plan is not None
        assert response.plan.recipes
        assert response.plan.recipes[0].constraints


def test_drop_causes_are_distinct():
    absent = from_trace_envelope(_dropped_trace("r-absent", ("evidence-absent",)), "t-absent")
    excluded = from_trace_envelope(
        _dropped_trace("r-excluded", ("present-evidence-excludes",)), "t-excluded"
    )
    absent_cause = absent.plan.recipes[0].drop_causes[0].value
    excluded_cause = excluded.plan.recipes[0].drop_causes[0].value
    assert absent_cause == "evidence-absent"
    assert excluded_cause == "present-evidence-excludes"
    assert absent_cause != excluded_cause
    assert "unmapped" not in (absent_cause, excluded_cause)


def test_multi_cause_precedence_preserved():
    response = from_trace_envelope(
        _dropped_trace(
            "r-multiple",
            ("unmapped", "evidence-absent", "present-evidence-excludes"),
        ),
        "t-multiple",
    )
    assert [cause.value for cause in response.plan.recipes[0].drop_causes] == [
        "present-evidence-excludes",
        "evidence-absent",
        "unmapped",
    ]
