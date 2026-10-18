import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from workflows.models import Outcome, PlanResult, PlanTraceView, TraceEnvelope


ALLOWED_EVENTS = {"metadata", "token", "plan_updated", "error", "done"}


class WorkflowStub:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def invoke(self, state):
        self.calls.append(state)
        if self.error is not None:
            raise self.error
        return self.result


def _envelope(message="Plan a meal", *, text="Here's a meal plan."):
    return {
        "trace": TraceEnvelope(
            schema_version="p3-001.v1",
            outcome=Outcome(
                kind="plan",
                plan=PlanResult("plan-1", "complete", "ok"),
                text=text,
            ),
            raw_message=message,
            plan_trace=PlanTraceView("feasible", None),
        )
    }


def _frames(response):
    frames = []
    for frame in response.text.strip().split("\n\n"):
        if not frame:
            continue
        event_type = next(line[7:] for line in frame.splitlines() if line.startswith("event: "))
        data = json.loads(next(line[6:] for line in frame.splitlines() if line.startswith("data: ")))
        frames.append((event_type, data))
    return frames


def _keys(value):
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key
            yield from _keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _keys(nested)


@pytest.fixture
def workflow_factory(monkeypatch):
    import app.chat_router as chat_router

    workflows = []

    def factory(plan_service, **kwargs):
        workflow = WorkflowStub(result=_envelope())
        workflows.append(workflow)
        return workflow

    monkeypatch.setattr(chat_router.composition, "create_workflow", factory)
    return workflows


def test_valid_request_starts_event_stream(workflow_factory):
    with TestClient(create_app(object())) as client:
        response = client.post("/api/v1/chat", json={
            "session_id": "session-1",
            "message": "Plan a meal",
        })

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert workflow_factory[0].calls[0]["raw_message"] == "Plan a meal"


@pytest.mark.parametrize("body", [
    {"message": "Plan a meal"},
    {"session_id": "session-1"},
])
def test_missing_field_rejected(body):
    with TestClient(create_app(object())) as client:
        response = client.post("/api/v1/chat", json=body)

    assert response.status_code == 422


def test_only_five_event_types_emitted(workflow_factory):
    with TestClient(create_app(object())) as client:
        response = client.post("/api/v1/chat", json={
            "session_id": "session-1",
            "message": "Plan a meal",
        })

    assert {kind for kind, _data in _frames(response)} <= ALLOWED_EVENTS


def test_trace_id_present_trace_not_embedded(workflow_factory):
    with TestClient(create_app(object())) as client:
        response = client.post("/api/v1/chat", json={
            "session_id": "session-1",
            "message": "Plan a meal",
        })

    frames = _frames(response)
    assert frames[0][0] == "metadata"
    trace_id = frames[0][1]["trace_id"]
    assert trace_id
    assert any(data.get("trace_id") == trace_id for _kind, data in frames)
    assert all("trace" not in data for _kind, data in frames)


def test_failure_emits_single_error_event(monkeypatch):
    import app.chat_router as chat_router

    workflow = WorkflowStub(error=RuntimeError("workflow unavailable"))
    monkeypatch.setattr(chat_router.composition, "create_workflow", lambda *args, **kwargs: workflow)
    with TestClient(create_app(object())) as client:
        response = client.post("/api/v1/chat", json={
            "session_id": "session-1",
            "message": "Plan a meal",
        })

    frames = _frames(response)
    assert [kind for kind, _data in frames] == ["error"]
    assert frames[0][1]["code"]
    assert frames[0][1]["message"]


def test_two_independent_requests_no_shared_state(workflow_factory):
    with TestClient(create_app(object())) as client:
        first = client.post("/api/v1/chat", json={
            "session_id": "session-1",
            "message": "First request",
        })
        second = client.post("/api/v1/chat", json={
            "session_id": "session-2",
            "message": "Second request",
        })

    assert workflow_factory[0].calls[0]["raw_message"] == "First request"
    assert workflow_factory[1].calls[0]["raw_message"] == "Second request"
    first_frames, second_frames = _frames(first), _frames(second)
    assert first_frames[0][1]["session_id"] == "session-1"
    assert second_frames[0][1]["session_id"] == "session-2"
    assert first_frames[0][1]["trace_id"] != second_frames[0][1]["trace_id"]


def test_cost_intent_turn_drops_uncosted_recipe_end_to_end(monkeypatch):
    from api.features.calculator.models import OfferRef, RecipeNutritionSignal, RequirementOffer
    from api.features.plan.repository import PlanRepository
    from api.features.plan.service import PlanService
    from app import composition

    rows = []
    for recipe_id in ("uncosted", "costed"):
        rows.append({
            "recipe_id": recipe_id,
            "title": recipe_id,
            "ingredients": [{
                "quantity": 100,
                "unit": "g",
                "occurrence_id": f"{recipe_id}-ingredient",
                "normalized_name": "pepper",
                "canonical_key": "black_pepper",
                "concept_name": "Black pepper",
                "best_food_key": f"food:{recipe_id}",
                "energy_kcal": 10,
                "protein_g": 1,
                "sodium_mg": 1,
                "nutrition_basis": "per 100 g",
                "halal_status": "halal",
                "vegetarian_status": "vegetarian",
                "freshness_status": "fresh",
            }],
        })

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def run(self, query, **params):
            return rows

    class Driver:
        def session(self):
            return Session()

    class SignalInspector:
        def inspect_candidates(self, recipes, servings):
            return {
                recipe.recipe_id: RecipeNutritionSignal(
                    recipe_id=recipe.recipe_id,
                    missing_nutrients=[],
                    selected_offers=[RequirementOffer(
                        occurrence_id=f"{recipe.recipe_id}-ingredient",
                        canonical_key="black_pepper",
                        selected_offer=(
                            None if recipe.recipe_id == "uncosted"
                            else OfferRef("food:costed", "pepper", "market")
                        ),
                    )],
                )
                for recipe in recipes
            }

    class ExtractLLM:
        provider = "fake"
        model = "extract"

        def invoke(self, prompt):
            return {"horizon_days": 1, "meals_per_day": 1}

    class ResponseLLM:
        provider = "fake"
        model = "response"

        def invoke(self, prompt):
            return {
                "recipe_ids": ["uncosted", "costed"],
                "requirement_ids": ["uncosted-ingredient", "costed-ingredient"],
                "drop_causes": ["evidence-absent"],
                "selected_recipe_ids": ["costed"],
                "text": "The costed recipe is selected; uncosted was dropped for evidence-absent.",
            }

    class CalculatorSpy:
        def __init__(self):
            self.calls = []

        def calculate(self, request):
            self.calls.append(request)
            return SimpleNamespace(itemized=[]), None

    from types import SimpleNamespace

    plan_service = PlanService(PlanRepository(Driver()))
    plan_service.calculator_service = SignalInspector()
    real_create_workflow = composition.create_workflow

    def workflow_factory(service, **kwargs):
        assert service is plan_service
        return real_create_workflow(
            service,
            extract_llm=ExtractLLM(),
            response_llm=ResponseLLM(),
        )

    import app.chat_router as chat_router
    monkeypatch.setattr(chat_router.composition, "create_workflow", workflow_factory)
    calculator = CalculatorSpy()
    application = create_app(plan_service)
    application.state.calculator_service = calculator
    with TestClient(application) as client:
        response = client.post("/api/v1/chat", json={
            "session_id": "session-cost",
            "message": "Find the cheapest meal",
        })

    frames = _frames(response)
    text = "".join(data["delta"] for kind, data in frames if kind == "token")
    updates = [data for kind, data in frames if kind == "plan_updated"]
    assert response.status_code == 200
    assert len(calculator.calls) == 1
    assert "uncosted" in text and "evidence-absent" in text
    assert "costed" in text and "selected" in text
    assert updates and updates[0]["explanation"]["recipe"]["recipe_id"] == "costed"
    assert updates[0]["explanation"]["recipe"]["outcome"] == "selected"


def _detailed_envelope():
    from workflows.models import RecipeOutcomeView, RequirementOutcomeView

    recipes = (
        RecipeOutcomeView("selected", "selected"),
        RecipeOutcomeView("absent", "dropped", "evidence-absent", ("evidence-absent",)),
        RecipeOutcomeView(
            "excluded", "dropped", "present-evidence-excludes",
            ("present-evidence-excludes",),
        ),
        RecipeOutcomeView("unmapped", "dropped", "unmapped", ("unmapped",)),
    )
    requirements = (
        RequirementOutcomeView(
            "selected", "selected-req", "dietary", "pass", "vegan",
            resolved_concept="tofu", selected_offer={"listing_name": "Tofu", "retailer": "Market"},
        ),
        RequirementOutcomeView("absent", "absent-req", "budget", "evidence-absent", "pepper"),
        RequirementOutcomeView(
            "excluded", "excluded-req", "allergen", "present-evidence-excludes", "peanut"
        ),
        RequirementOutcomeView("unmapped", "unmapped-req", "unmapped", "unmapped", "rare spice"),
    )
    plan = PlanResult(
        "plan-1", "complete", "ok", recipe_outcomes=recipes,
        constraint_outcomes=requirements,
        days=({"day": 1, "meals": [{
            "slot": "meal_1", "recipe_id": "selected", "ingredients": [],
        }]},),
    )
    return TraceEnvelope(
        schema_version="p3-001.v1",
        outcome=Outcome(kind="plan", plan=plan, text=""),
        raw_message="Update my plan",
        plan_trace=PlanTraceView(
            "plan-produced", None, recipes=recipes, requirements=requirements
        ),
    )


def _post_envelope(monkeypatch, envelope, user_context=None):
    import app.chat_router as chat_router

    workflow = WorkflowStub(result={"trace": envelope})
    monkeypatch.setattr(
        chat_router.composition, "create_workflow", lambda *args, **kwargs: workflow
    )
    with TestClient(create_app(object())) as client:
        return client.post("/api/v1/chat", json={
            "session_id": "session-detail",
            "message": "Update my plan",
            "user_context": user_context,
        })


def test_three_levels_present_in_stream(monkeypatch):
    response = _post_envelope(monkeypatch, _detailed_envelope())
    frames = _frames(response)
    done = next(data for kind, data in frames if kind == "done")
    update = next(data for kind, data in frames if kind == "plan_updated")
    text = "".join(data["delta"] for kind, data in frames if kind == "token")

    assert done["status"] == "plan-produced"
    assert "Plan outcome: plan-produced" in text
    assert update["explanation"]["recipe"]["recipe_id"] == "selected"
    assert update["explanation"]["constraints"][0]["constraint"] == "dietary"


def test_distinct_causes_in_stream(monkeypatch):
    response = _post_envelope(monkeypatch, _detailed_envelope())
    text = "".join(data["delta"] for kind, data in _frames(response) if kind == "token")

    assert "Recipe absent: dropped (evidence-absent)" in text
    assert "Recipe excluded: dropped (present-evidence-excludes)" in text
    assert "Recipe unmapped: dropped (unmapped)" in text


def test_stream_excludes_forbidden_fields(monkeypatch):
    from app.chat_contract import CHAT_FORBIDDEN_FIELDS

    response = _post_envelope(monkeypatch, _detailed_envelope())
    keys = list(_keys([data for _kind, data in _frames(response)]))

    assert not [key for key in keys if any(field in key for field in CHAT_FORBIDDEN_FIELDS)]


def test_plan_updated_has_delta_and_scoped_explanation(monkeypatch):
    context = {"plan": {"days": [{
        "day": 1,
        "meals": [{"slot": "meal_1", "recipe_id": "old-recipe"}],
    }]}}
    response = _post_envelope(monkeypatch, _detailed_envelope(), context)
    updates = [data for kind, data in _frames(response) if kind == "plan_updated"]

    assert len(updates) == 1
    assert updates[0]["delta"] == {"day": 1, "slot": "meal_1", "recipe_id": "selected"}
    assert updates[0]["explanation"]["recipe"]["recipe_id"] == "selected"
    assert updates[0]["explanation"]["constraints"][0]["requirement_id"] == "selected-req"
