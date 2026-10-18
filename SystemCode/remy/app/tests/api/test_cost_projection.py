import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from api.features.calculator.models import FoodFacts, NutrientProfile, RetailSKU
from api.features.calculator.service import CostNutritionService
from app.main import create_app
from workflows.models import (
    ConstraintSet,
    Outcome,
    PlanResult,
    PlanTraceView,
    RecipeOutcomeView,
    RequirementOutcomeView,
    TraceEnvelope,
)


class CalculatorSpy:
    def __init__(self, result=None):
        self.result = result or SimpleNamespace(itemized=[SimpleNamespace(
            ingredient="black pepper",
            consumed_cost_sgd=0.2,
            retail_package_cost_sgd=1.0,
            warnings=[],
        )])
        self.calls = []

    def calculate(self, request):
        self.calls.append(request)
        return self.result, None


class Repository:
    def __init__(self, package):
        self.package = package

    def resolve_candidates(self, _names):
        return {"black pepper": ["black_pepper"]}

    def fetch_food_facts(self, _keys):
        return {"black_pepper": [FoodFacts(
            canonical_key="black_pepper",
            canonical_name="Black pepper",
            fdc_id="1",
            description="Black pepper",
            nutrients=NutrientProfile(protein_g=1),
            approval_status="accepted",
            food_key="food:1",
            packages=[self.package],
        )]}


class WorkflowStub:
    def __init__(self, envelope):
        self.envelope = envelope

    def invoke(self, state):
        return {"trace": self.envelope}


def _envelope(cost_query):
    recipe = RecipeOutcomeView("recipe-1", "selected")
    requirement = RequirementOutcomeView(
        recipe_id="recipe-1",
        requirement_id="ingredient-1",
        constraint="requirement",
        state="selected",
        requirement_text="black pepper",
        resolved_concept="Black pepper",
    )
    plan = PlanResult(
        "plan-1",
        "complete",
        "ok",
        recipe_outcomes=(recipe,),
        constraint_outcomes=(requirement,),
        days=({"day": 1, "meals": [{
            "slot": "meal_1",
            "recipe_id": "recipe-1",
            "ingredients": [{"text": "black pepper", "quantity": 20, "unit": "g"}],
        }]},),
    )
    return TraceEnvelope(
        schema_version="p3-001.v1",
        outcome=Outcome(kind="plan", plan=plan, text="Recommended."),
        raw_message="What is the price?",
        parsed_constraints=ConstraintSet(1, 1, cost_query=cost_query),
        plan_trace=PlanTraceView(
            "plan-produced", None, recipes=(recipe,), requirements=(requirement,)
        ),
    )


def _token_text(response):
    values = []
    for frame in response.text.strip().split("\n\n"):
        if not frame:
            continue
        event_type = next(line[7:] for line in frame.splitlines() if line.startswith("event: "))
        data = json.loads(next(line[6:] for line in frame.splitlines() if line.startswith("data: ")))
        if event_type == "token":
            values.append(data["delta"])
    return "".join(values)


def _send(monkeypatch, *, cost_query, calculator):
    import app.chat_router as chat_router

    monkeypatch.setattr(
        chat_router.composition,
        "create_workflow",
        lambda *args, **kwargs: WorkflowStub(_envelope(cost_query)),
    )
    application = create_app(object())
    application.state.calculator_service = calculator
    with TestClient(application) as client:
        return client.post("/api/v1/chat", json={
            "session_id": "session-1",
            "message": "What is the price?" if cost_query else "Plan a meal",
        })


def _package(**overrides):
    values = dict(
        retailer="A",
        listing_name="pepper",
        reference_price_minor=100,
        currency="SGD",
        package_mass_g=100,
        package_count=1,
        price_basis="package_mass",
        cost_basis_compatible=True,
        confidence=1.0,
        fdc_id="1",
        price_status="estimated",
        price_match_status="accepted",
        freshness_status="fresh",
        package_volume_ml=None,
        food_key="food:1",
        approval_status="accepted",
    )
    values.update(overrides)
    return RetailSKU(**values)


def test_cost_surfaced_on_cost_intent(monkeypatch):
    calculator = CalculatorSpy()

    response = _send(monkeypatch, cost_query=True, calculator=calculator)

    assert response.status_code == 200
    assert len(calculator.calls) == 1
    assert "consumed cost SGD 0.20" in _token_text(response)
    assert "retail package cost SGD 1.00" in _token_text(response)


def test_no_cost_without_intent(monkeypatch):
    calculator = CalculatorSpy()

    response = _send(monkeypatch, cost_query=False, calculator=calculator)

    assert response.status_code == 200
    assert calculator.calls == []
    assert "cost SGD" not in _token_text(response)


def test_consumed_and_retail_distinct_via_calculator(monkeypatch):
    calculator = CostNutritionService(Repository(_package()))

    response = _send(monkeypatch, cost_query=True, calculator=calculator)
    text = _token_text(response)

    assert "consumed cost SGD 0.20" in text
    assert "retail package cost SGD 1.00" in text


def test_missing_package_reported_not_fabricated(monkeypatch):
    calculator = CostNutritionService(Repository(_package(freshness_status="stale")))

    response = _send(monkeypatch, cost_query=True, calculator=calculator)
    text = _token_text(response)

    assert "MISSING_PACKAGE_DATA" in text
    assert "consumed cost SGD 0.00" not in text
    assert "retail package cost SGD 0.00" not in text


def test_cost_query_branches_handler(monkeypatch):
    from workflows.graph import build

    class ExtractLLM:
        provider = "test"
        model = "extract"

        def invoke(self, _prompt):
            return {"horizon_days": 1, "meals_per_day": 1}

    class PlanPort:
        def generate(self, request):
            assert request.cost_query is True
            plan = _envelope(True).outcome.plan
            trace = _envelope(True).plan_trace
            return plan, trace

    class ResponseLLM:
        provider = "test"
        model = "response"

        def invoke(self, _prompt):
            return {"text": "Recommended."}

    import app.chat_router as chat_router

    calculator = CalculatorSpy()
    workflow = build(
        extract_llm=ExtractLLM(), plan_port=PlanPort(), response_llm=ResponseLLM()
    )
    monkeypatch.setattr(chat_router.composition, "create_workflow", lambda *args, **kwargs: workflow)
    application = create_app(object())
    application.state.calculator_service = calculator
    with TestClient(application) as client:
        response = client.post("/api/v1/chat", json={
            "session_id": "session-1",
            "message": "What is the price?",
        })

    assert response.status_code == 200
    assert len(calculator.calls) == 1
    assert "consumed cost SGD 0.20" in _token_text(response)
