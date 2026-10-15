from workflows.graph import build
from workflows.models import PlanResult, PlanTraceView, RecipeOutcomeView


def test_generate_structured_output_drives_final_outcome():
    class ExtractLLM:
        provider = "fake"
        model = "fake"

        def invoke(self, prompt):
            return {"horizon_days": 1, "meals_per_day": 1}

    class ResponseLLM:
        provider = "fake"
        model = "fake"

        def invoke(self, prompt):
            return {"text": "Use r1", "recipe_ids": ["r1"], "requirement_ids": [], "drop_causes": []}

    class Port:
        def generate(self, request):
            recipe = RecipeOutcomeView("r1", "selected")
            return PlanResult("p1", "complete", "ok", recipe_outcomes=(recipe,)), PlanTraceView("feasible", None, recipes=(recipe,))

    result = build(extract_llm=ExtractLLM(), plan_port=Port(), response_llm=ResponseLLM()).invoke({"raw_message": "one day"})
    assert result["generation_output"].recipe_ids == ("r1",)
    assert result["outcome"].text == "Use r1"
