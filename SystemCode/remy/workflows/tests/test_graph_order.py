from workflows.graph import build
from workflows.models import PlanResult, PlanTraceView


class LLM:
    provider = "fake"
    model = "fake"

    def __init__(self, response):
        self.response = response
        self.calls = 0

    def invoke(self, prompt):
        self.calls += 1
        return self.response


class Port:
    def __init__(self):
        self.calls = 0

    def generate(self, request):
        self.calls += 1
        result = PlanResult("p1", "complete", "ok")
        return result, PlanTraceView("feasible", None)


def test_three_nodes_run_in_order_and_return_one_outcome_and_trace():
    graph = build(
        extract_llm=LLM({"horizon_days": 2, "meals_per_day": 2}),
        plan_port=Port(),
        response_llm=LLM({"text": "done", "recipe_ids": [], "requirement_ids": [], "drop_causes": []}),
    )
    result = graph.invoke({"raw_message": "plan two days"})
    assert [entry.node for entry in result["trace"].node_runs] == ["Extract Constraints", "Plan", "Generate Response"]
    assert result["outcome"].kind == "plan"
    assert result["trace"].outcome == result["outcome"]


def test_extract_failure_skips_plan_and_generate():
    port = Port()
    graph = build(extract_llm=LLM({"meals_per_day": 2}), plan_port=port, response_llm=LLM({}))
    result = graph.invoke({"raw_message": "missing horizon"})
    assert result["outcome"].kind == "failure"
    assert port.calls == 0
    assert [entry.node for entry in result["trace"].node_runs] == ["Extract Constraints"]
