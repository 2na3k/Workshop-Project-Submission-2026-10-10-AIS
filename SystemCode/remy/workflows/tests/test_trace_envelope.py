def test_trace_envelope_reaches_plan_reasoning_and_records_llm_calls():
    from workflows.graph import build
    from workflows.models import PlanResult, PlanTraceView, RecipeOutcomeView

    class LLM:
        provider = "fake"
        model = "fake"

        def __init__(self, response):
            self.response = response

        def invoke(self, prompt):
            return self.response

    class Port:
        def generate(self, request):
            recipe = RecipeOutcomeView("r1", "selected")
            result = PlanResult("p1", "complete", "ok", recipe_outcomes=(recipe,))
            return result, PlanTraceView("feasible", None, recipes=(recipe,))

    result = build(
        extract_llm=LLM({"horizon_days": 1, "meals_per_day": 1}),
        plan_port=Port(),
        response_llm=LLM({"text": "ok", "recipe_ids": ["r1"], "requirement_ids": [], "drop_causes": []}),
    ).invoke({"raw_message": "one day"})
    trace = result["trace"]
    assert trace.schema_version
    assert trace.raw_message == "one day"
    assert trace.plan_trace.recipes[0].recipe_id == "r1"
    assert len(trace.llm_invocations) == 2


# def test_trace_side_provenance_gap_is_deferred():
#     import pytest
#
#     pytest.xfail("F-P3-1: PlanTrace does not carry R-16 provenance fields")
#     assert False
