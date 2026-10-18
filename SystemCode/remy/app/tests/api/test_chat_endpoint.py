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
