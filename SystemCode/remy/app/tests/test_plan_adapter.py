from api.features.plan.models import NamedConstraint, RecipeOutcome, RequirementOutcome
from api.features.plan.schemas import ConstraintOutcomeResponse, PlanResponse, RecipeOutcomeResponse
from api.features.plan.trace import PlanTrace
from app.plan_adapter import PlanServiceAdapter
from workflows.models import PlanInput


class Service:
    def __init__(self, response, trace):
        self.response = response
        self.trace = trace

    def generate(self, request):
        self.request = request
        return self.response, self.trace


def _response():
    return PlanResponse(
        plan_id="p1",
        status="complete",
        message="ok",
        validation_summary={},
        horizon_totals={},
        days=[],
        recipe_outcomes=[RecipeOutcomeResponse(recipe_id="r1", outcome="selected")],
        constraint_outcomes=[ConstraintOutcomeResponse(recipe_id="r1", requirement_id="q1", requirement_text="vegan", constraint="dietary", state="pass", warnings=["warn"])],
    )


def test_adapter_maps_real_tuple_losslessly():
    trace = PlanTrace(binding_constraints=[NamedConstraint("plan", "horizon", "horizon")], recipes=[RecipeOutcome("r1", "selected")], requirements=[RequirementOutcome("r1", "q1", "dietary", "pass")])
    service = Service(_response(), trace)
    result, trace_view = PlanServiceAdapter(service).generate(PlanInput(2, 2))

    assert service.request.horizon_days == 2
    assert result.recipe_outcomes[0].recipe_id == "r1"
    assert trace_view.binding_constraints[0].code == "horizon"
    assert result.constraint_outcomes[0].requirement_id == "q1"
    assert result.constraint_outcomes[0].warnings == ("warn",)
    assert trace_view.requirements[0].requirement_id == "q1"
