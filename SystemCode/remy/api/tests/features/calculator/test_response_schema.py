"""R-16 user response contract and request limit checks for calculator responses."""

from fastapi.testclient import TestClient

from api.features.calculator.dependencies import get_calculator_service
from api.features.calculator.schemas import (
    MAX_REQUEST_INGREDIENTS, CalculationSummary, CostNutritionResponse,
    ItemizedCalculation, ItemWarning, Nutrients,
)
from api.main import app


def test_user_payload_field_set():
    response = CostNutritionResponse(
        servings=1,
        summary=CalculationSummary(
            total_consumed_cost_sgd=0.5,
            total_retail_package_cost_sgd=1.0,
            nutrients=Nutrients(protein_g=1.0),
            nutrients_per_serving=Nutrients(protein_g=1.0),
        ),
        itemized=[ItemizedCalculation(
            ingredient="blackberry", canonical_key="blackberry",
            listing_name="Fresh blackberries", retailer="store",
            consumed_amount_g=50, consumed_cost_sgd=0.5,
            retail_package_cost_sgd=1.0, nutrients=Nutrients(protein_g=1.0),
            warnings=[ItemWarning(code="PARTIAL_NUTRITION_DATA",
                                  message="Missing nutrients: calories_kcal")],
        )],
    )
    payload = response.model_dump()
    item = payload["itemized"][0]
    assert set(payload) == {"status", "servings", "summary", "itemized"}
    assert set(item) == {
        "ingredient", "canonical_key", "listing_name", "retailer",
        "consumed_amount_g", "consumed_cost_sgd", "retail_package_cost_sgd",
        "nutrients", "warnings",
    }
    assert not any(key in str(payload) for key in (
        "confidence", "food_key", "fdc_id", "source_", "normalization_version",
        "mapping_version", "nutrition_rank", "selection_priority", "approval_status",
    ))


class _NoCallService:
    def __init__(self):
        self.called = False

    def calculate(self, _request):
        self.called = True
        raise AssertionError("validation must reject before calculation")


def test_invalid_request_rejected_custom_envelope():
    service = _NoCallService()
    app.dependency_overrides[get_calculator_service] = lambda: service
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            requests = [
                {"servings": 0, "ingredients": [{"name": "a", "quantity": 1, "unit": "g"}]},
                {"servings": 1, "ingredients": []},
                {"servings": 1, "ingredients": [
                    {"name": "a", "quantity": 1, "unit": "g"}
                    for _ in range(MAX_REQUEST_INGREDIENTS + 1)
                ]},
            ]
            responses = [client.post("/api/v1/calculate/cost-and-nutrition", json=body)
                         for body in requests]
    finally:
        app.dependency_overrides.pop(get_calculator_service, None)
    assert all(response.status_code == 422 for response in responses)
    for response in responses:
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
        assert set(response.json()["error"]) == {"code", "message", "details", "timestamp"}
    assert not service.called
