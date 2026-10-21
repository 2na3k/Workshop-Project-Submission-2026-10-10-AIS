from workflows.graph import build
from workflows.models import PlanResult, PlanTraceView


def test_extracted_constraints_reach_plan_port():
    class LLM:
        provider = "fake"
        model = "fake"

        def invoke(self, prompt):
            return {"horizon_days": 3, "meals_per_day": 2, "dietary": [{"code": "vegan"}]}

    class Port:
        request = None

        def generate(self, request):
            self.request = request
            return PlanResult("p1", "complete", "ok"), PlanTraceView("feasible", None)

    port = Port()
    build(extract_llm=LLM(), plan_port=port, response_llm=LLM()).invoke({"raw_message": "vegan for three days"})
    assert port.request.horizon_days == 3
    assert port.request.dietary[0].code == "vegan"
