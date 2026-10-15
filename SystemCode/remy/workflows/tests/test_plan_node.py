from workflows.models import (
    ConstraintSet,
    IngredientWarningView,
    NamedConstraintView,
    PlanResult,
    PlanTraceView,
    RecipeOutcomeView,
    RequirementOutcomeView,
)
from workflows.nodes import plan


class FakePort:
    def __init__(self, result, trace):
        self.result = result
        self.trace = trace
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return self.result, self.trace


def _trace(feasibility="feasible", reason=None):
    return PlanTraceView(feasibility, reason)


def _state(constraints=None):
    return {"raw_message": "", "parsed_constraints": constraints or ConstraintSet(2, 2), "unapplied_constraints": []}


def test_feasible_result_preserves_slots_and_three_level_reasoning():
    recipe = RecipeOutcomeView("r1", "selected")
    requirement = RequirementOutcomeView("r1", "q1", "dietary", "pass", "vegan")
    result = PlanResult("p1", "complete", "ok", days=("day-1",), recipe_outcomes=(recipe,), constraint_outcomes=(requirement,))
    port = FakePort(result, _trace())

    updated = plan(_state(), port=port)

    assert updated["outcome"].kind == "plan"
    assert updated["outcome"].plan == result
    assert updated["plan_trace"] == _trace()
    assert port.requests[0].horizon_days == 2


def test_infeasible_result_preserves_binding_constraints_and_dropped_candidates():
    binding = NamedConstraintView("plan", "horizon", "horizon")
    dropped = RecipeOutcomeView("r2", "dropped", "evidence-absent", ("evidence-absent",))
    result = PlanResult("p1", "partial", "no plan", feasibility_outcome="infeasible", binding_constraints=(binding,), recipe_outcomes=(dropped,))
    updated = plan(_state(), port=FakePort(result, PlanTraceView("infeasible", "no-assignment", (binding,), recipes=(dropped,))))
    assert updated["outcome"].kind == "infeasible"
    assert updated["outcome"].plan.binding_constraints == (binding,)
    assert updated["plan_trace"].recipes == (dropped,)


def test_relaxed_label_and_tolerance_are_unchanged():
    result = PlanResult("p1", "complete", "relaxed", relaxed=True, applied_tolerance_pct=10)
    updated = plan(_state(), port=FakePort(result, _trace()))
    assert updated["outcome"].plan.relaxed is True
    assert updated["outcome"].plan.applied_tolerance_pct == 10


def test_port_failure_is_a_plan_failure_without_feasibility_claim():
    class BrokenPort:
        def generate(self, request):
            raise RuntimeError("solver unavailable")

    updated = plan(_state(), port=BrokenPort())
    assert updated["outcome"].kind == "failure"
    assert updated["outcome"].node == "Plan"
    assert updated["plan_result"] is None


def test_empty_pool_and_no_assignment_remain_distinct():
    for reason, expected in (("no-recipes-survived", "no-recipes-survived"), ("no-assignment", "no-assignment")):
        result = PlanResult("p1", "partial", reason, feasibility_outcome="infeasible")
        updated = plan(_state(), port=FakePort(result, _trace("infeasible", reason)))
        assert updated["outcome"].reason == expected


def test_mild_allergen_warning_is_preserved():
    warning = IngredientWarningView("mild-allergen", "ingredient-1", "contains peanut")
    requirement = RequirementOutcomeView("r1", "q1", "allergen", "warn", "peanut", warnings=(warning,))
    result = PlanResult("p1", "complete", "ok", constraint_outcomes=(requirement,))
    updated = plan(_state(), port=FakePort(result, _trace()))
    assert updated["outcome"].plan.constraint_outcomes[0].warnings == (warning,)


def test_horizon_only_request_is_sent_unchanged():
    constraints = ConstraintSet(4, 3)
    port = FakePort(PlanResult("p1", "complete", "ok"), _trace())
    plan({"raw_message": "", "parsed_constraints": constraints, "unapplied_constraints": []}, port=port)
    assert port.requests[0].horizon_days == 4
    assert port.requests[0].allergies == ()
    assert port.requests[0].nutrients == ()
