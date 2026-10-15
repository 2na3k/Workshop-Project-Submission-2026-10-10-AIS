from workflows.models import Outcome, PlanResult, RecipeOutcomeView, RequirementOutcomeView
from workflows.nodes import generate_response


def _state(plan_result=None):
    plan_result = plan_result or PlanResult(
        "p1",
        "complete",
        "ok",
        recipe_outcomes=(RecipeOutcomeView("r1", "selected"), RecipeOutcomeView("r2", "dropped", "evidence-absent")),
        constraint_outcomes=(RequirementOutcomeView("r1", "q1", "dietary", "pass", "vegan"),),
    )
    return {"raw_message": "make a plan", "plan_result": plan_result, "outcome": Outcome("plan", plan=plan_result)}


class FakeResponseLLM:
    provider = "fake"
    model = "fake"

    def __init__(self, response=None, error=None):
        self.response = response or {"text": "Use recipe r1.", "recipe_ids": ["r1"], "requirement_ids": ["q1"], "drop_causes": ["evidence-absent"]}
        self.error = error
        self.prompt = ""

    def invoke(self, prompt):
        self.prompt = prompt
        if self.error:
            raise self.error
        return self.response


def test_structured_generation_preserves_evidence_absent_and_returns_text():
    result = generate_response(_state(), llm=FakeResponseLLM())
    assert result["generation_output"].drop_causes == ("evidence-absent",)
    assert "r1" in result["generation_text"]
    assert result["outcome"].kind == "plan"


def test_structured_references_must_be_subsets_of_plan():
    llm = FakeResponseLLM({"text": "", "recipe_ids": ["unknown"], "requirement_ids": [], "drop_causes": []})
    result = generate_response(_state(), llm=llm)
    assert result["outcome"].kind == "failure"
    assert result["outcome"].node == "Generate Response"


def test_selected_evidence_absent_output_fails_deterministic_check():
    result = generate_response(
        _state(PlanResult("p1", "complete", "ok", recipe_outcomes=(RecipeOutcomeView("r1", "selected", "evidence-absent"),))),
        llm=FakeResponseLLM({"text": "", "recipe_ids": ["r1"], "requirement_ids": [], "drop_causes": ["evidence-absent"], "selected_recipe_ids": ["r1"]}),
    )
    assert result["outcome"].kind == "failure"


def test_generation_prompt_and_payload_exclude_audit_provenance():
    llm = FakeResponseLLM()
    result = generate_response(_state(), llm=llm)
    forbidden = ("confidence", "normalization_version", "source_", "recipe_id")
    assert not any(field in llm.prompt for field in forbidden)
    assert not any(field in result["generation_output"].__dict__ for field in forbidden)


def test_llm_failure_is_explicit():
    result = generate_response(_state(), llm=FakeResponseLLM(error=TimeoutError("timed out")))
    assert result["outcome"].kind == "failure"
    assert result["outcome"].node == "Generate Response"
