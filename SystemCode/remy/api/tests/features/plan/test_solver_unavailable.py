import builtins

import pytest
from fastapi.testclient import TestClient

from api.features.plan.dependencies import get_plan_service
from api.features.plan.solver_v2 import solve_v2
from api.main import app


@pytest.mark.parametrize("tolerance", [-1, 26, 1.5])
def test_tolerance_out_of_range_rejected_without_solver_invocation(tolerance):
    class SolverSpy:
        called = False

        def generate(self, request):
            self.called = True
            raise AssertionError("solver service must not run for an invalid request")

    service = SolverSpy()
    app.dependency_overrides[get_plan_service] = lambda: service
    try:
        response = TestClient(app).post(
            "/api/v1/plan",
            json={
                "horizon_days": 1,
                "meals_per_day": 1,
                "nutrient_tolerance_pct": tolerance,
            },
        )
    finally:
        app.dependency_overrides.pop(get_plan_service, None)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert service.called is False


def test_solver_unavailable_hard_fail(monkeypatch):
    class Service:
        def generate(self, request):
            return solve_v2([], request)

    app.dependency_overrides[get_plan_service] = lambda: Service()
    original_import = builtins.__import__

    def without_ortools(name, *args, **kwargs):
        if name.startswith("ortools"):
            raise ImportError("simulated missing OR-Tools")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_ortools)
    try:
        response = TestClient(app).post(
            "/api/v1/plan",
            json={"horizon_days": 1, "meals_per_day": 1},
        )
    finally:
        app.dependency_overrides.pop(get_plan_service, None)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SOLVER_UNAVAILABLE"
    assert "days" not in response.json()
