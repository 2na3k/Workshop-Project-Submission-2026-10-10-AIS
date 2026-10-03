import asyncio
import json
import time

from fastapi.testclient import TestClient

from api.core.exceptions import AppError
from api.features.plan.dependencies import get_plan_service
from api.features.plan.exceptions import PlanInfeasible
from api.features.plan.service import PlanService
from api.features.plan.streaming import KEEP_ALIVE, stream_plan
from api.main import app


class FakePlan:
    def model_dump(self, mode):
        return {"plan_id": "plan_test", "status": "complete", "days": []}


class FakeService:
    def __init__(self, fetch_delay=0.0, solve_error=None):
        self.fetch_delay = fetch_delay
        self.solve_error = solve_error

    def fetch_candidates(self):
        time.sleep(self.fetch_delay)
        return ["recipe"]

    def select_candidates(self, recipes, request):
        return recipes

    def solve(self, recipes, request):
        if self.solve_error:
            raise self.solve_error
        return [[recipes[0]]], []

    def build_response(self, days, relaxations, request):
        return FakePlan()


class EmptyRepository:
    def fetch_candidates(self):
        return []


def collect(service, keep_alive_seconds=10.0):
    async def run():
        return [chunk async for chunk in stream_plan(None, service, keep_alive_seconds)]
    return asyncio.run(run())


def events(chunks):
    parsed = []
    for chunk in chunks:
        if chunk == KEEP_ALIVE:
            parsed.append(("keep-alive", None))
            continue
        lines = dict(line.split(": ", 1) for line in chunk.strip().split("\n"))
        parsed.append((lines["event"], json.loads(lines["data"])))
    return parsed


def test_progress_events_then_the_plan():
    parsed = events(collect(FakeService()))
    assert [name for name, _ in parsed] == ["progress", "progress", "progress", "plan"]
    assert [data["stage"] for _, data in parsed[:3]] == ["loading", "selecting", "solving"]
    assert parsed[0][1] == {"stage": "loading", "message": "Loading recipes", "step": 1, "total": 3}
    assert parsed[-1][1]["plan_id"] == "plan_test"


def test_slow_steps_send_keep_alive_comments():
    chunks = collect(FakeService(fetch_delay=0.2), keep_alive_seconds=0.03)
    assert chunks.count(KEEP_ALIVE) >= 2
    assert events(chunks)[-1][0] == "plan"


def test_planner_failures_become_an_error_event():
    parsed = events(collect(FakeService(solve_error=PlanInfeasible("No feasible plan after all relaxations"))))
    assert parsed[-1][0] == "error"
    assert parsed[-1][1]["error"]["code"] == "PLAN_INFEASIBLE"
    assert parsed[-1][1]["error"]["message"] == "No feasible plan after all relaxations"


def test_unexpected_failures_hide_details():
    parsed = events(collect(FakeService(solve_error=RuntimeError("neo4j password wrong"))))
    assert parsed[-1][1]["error"]["code"] == "INTERNAL_ERROR"
    assert "neo4j" not in json.dumps(parsed[-1][1])


def test_endpoint_streams_with_event_stream_headers():
    app.dependency_overrides[get_plan_service] = lambda: PlanService(EmptyRepository())
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/plan", json={"horizon_days": 1, "meals_per_day": 1})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["connection"] == "keep-alive"
    parsed = events([chunk + "\n\n" for chunk in response.text.strip().split("\n\n")])
    assert [name for name, _ in parsed] == ["progress", "progress", "error"]
    assert parsed[-1][1]["error"]["code"] == "UNSUPPORTED_UNIT"


def test_bad_codes_are_rejected_before_the_stream_starts():
    app.dependency_overrides[get_plan_service] = lambda: PlanService(EmptyRepository())
    try:
        with TestClient(app) as client:
            allergen = client.post("/api/v1/plan", json={"horizon_days": 1, "meals_per_day": 1, "allergies": [{"code": "tree nut"}]})
            dietary = client.post("/api/v1/plan", json={"horizon_days": 1, "meals_per_day": 1, "dietary": [{"code": "keto"}]})
            invalid = client.post("/api/v1/plan", json={"horizon_days": 30, "meals_per_day": 1})
    finally:
        app.dependency_overrides.clear()
    assert (allergen.status_code, allergen.json()["error"]["code"]) == (400, "UNKNOWN_ALLERGEN")
    assert (dietary.status_code, dietary.json()["error"]["code"]) == (400, "UNKNOWN_DIETARY")
    assert (invalid.status_code, invalid.json()["error"]["code"]) == (422, "VALIDATION_ERROR")
    assert all(r.headers["content-type"].startswith("application/json") for r in (allergen, dietary, invalid))


def test_app_errors_keep_their_code_and_details():
    error = AppError("Bad thing", [{"field": "nutrients.0", "issue": "nope"}])
    parsed = events(collect(FakeService(solve_error=error)))
    assert parsed[-1][1]["error"]["details"] == [{"field": "nutrients.0", "issue": "nope"}]
