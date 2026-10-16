"""Workflow R-17 mirror of the constitution's tests/api/test_explanation_shape.py.

No API fixture with that name exists in this checkout. The local assertion
defines the workflow equivalent; the missing authoritative fixture is routed
to phase review in p3-001 plan BD-2.
"""

from workflows.graph import build
from workflows.models import (
    NamedConstraintView,
    PlanResult,
    PlanTraceView,
    RecipeOutcomeView,
    RequirementOutcomeView,
)


class _LLM:
    provider = "fake"
    model = "fake"

    def __init__(self, response):
        self.response = response

    def invoke(self, prompt):
        return self.response


def test_outcome_has_three_levels_and_distinct_drop_causes():
    recipes = (
        RecipeOutcomeView("absent", "dropped", "evidence-absent", ("evidence-absent",)),
        RecipeOutcomeView("excluded", "dropped", "present-evidence-excludes", ("present-evidence-excludes",)),
        RecipeOutcomeView("unmapped", "dropped", "unmapped", ("unmapped",)),
    )
    requirements = tuple(
        RequirementOutcomeView(recipe.recipe_id, f"req-{index}", "dietary", "fail", "vegan")
        for index, recipe in enumerate(recipes)
    )
    bindings = tuple(
        NamedConstraintView("plan", recipe.cause or "", "evidence-absent" if recipe.cause == "evidence-absent" else "present-evidence-excludes" if recipe.cause == "present-evidence-excludes" else "unmapped")
        for recipe in recipes
    )
    plan_result = PlanResult(
        "plan-1",
        "partial",
        "No eligible plan",
        feasibility_outcome="infeasible",
        binding_constraints=bindings,
        recipe_outcomes=recipes,
        constraint_outcomes=requirements,
    )

    class _Port:
        def generate(self, request):
            return plan_result, PlanTraceView("infeasible", "no-recipes-survived", bindings, recipes=recipes, requirements=requirements)

    state = build(
        extract_llm=_LLM({"horizon_days": 1, "meals_per_day": 1}),
        plan_port=_Port(),
        response_llm=_LLM({
            "text": "Three candidates were excluded for distinct reasons.",
            "recipe_ids": [item.recipe_id for item in recipes],
            "requirement_ids": [item.requirement_id for item in requirements],
            "drop_causes": [item.cause for item in recipes],
        }),
    ).invoke({"raw_message": "Plan one day"})

    outcome = state["outcome"]
    assert outcome.kind == "infeasible"
    assert outcome.plan.binding_constraints == bindings
    assert outcome.plan.recipe_outcomes == recipes
    assert outcome.plan.constraint_outcomes == requirements
    assert {item.cause for item in outcome.plan.recipe_outcomes} == {
        "evidence-absent",
        "present-evidence-excludes",
        "unmapped",
    }
