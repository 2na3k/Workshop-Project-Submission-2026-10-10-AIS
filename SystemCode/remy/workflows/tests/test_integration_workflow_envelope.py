def test_workflow_caller_receives_outcome_and_trace():
    from workflows.graph import build
    from workflows.models import PlanResult, PlanTraceView

    class LLM:
        provider = "fake"
        model = "fake"

        def __init__(self, response):
            self.response = response

        def invoke(self, prompt):
            return self.response

    class Port:
        def generate(self, request):
            return PlanResult("p1", "complete", "ok"), PlanTraceView("feasible", None)

    output = build(
        extract_llm=LLM({"horizon_days": 1, "meals_per_day": 1}),
        plan_port=Port(),
        response_llm=LLM({"text": "ok", "recipe_ids": [], "requirement_ids": [], "drop_causes": []}),
    ).invoke({"raw_message": "one day"})
    assert output["outcome"] is not None
    assert output["trace"] is not None
