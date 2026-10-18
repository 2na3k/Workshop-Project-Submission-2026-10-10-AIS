"""F-3: the composed app serves api + chat with the shared error envelope."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


def test_health_served_unprefixed(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_calculate_route_mounted(client):
    response = client.post("/api/v1/calculate/cost-and-nutrition", json={})
    assert response.status_code != 404


def test_plan_route_mounted(client):
    response = client.post("/api/v1/plan", json={})
    assert response.status_code != 404


def test_chat_route_mounted(client):
    response = client.post("/api/v1/chat", json={})
    assert response.status_code != 404


def test_chat_workflow_failure_uses_error_envelope(client, monkeypatch):
    """A raised exception in the chat handler must emit the standard error
    SSE event (AC-17), not FastAPI's default 500 body."""
    from app import chat_router

    def boom(*args, **kwargs):
        raise RuntimeError("forced")

    monkeypatch.setattr(chat_router, "_resolve_services", boom)
    with client.stream(
        "POST", "/api/v1/chat", json={"session_id": "s", "message": "hi"}
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = "".join(response.iter_text())
    assert "event: error" in body
