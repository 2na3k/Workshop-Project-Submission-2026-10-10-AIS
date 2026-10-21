"""Service and HTTP rejection checks for invalid units and missing evidence."""

import pytest
from fastapi.testclient import TestClient

from api.features.calculator.dependencies import get_calculator_service
from api.features.calculator.exceptions import MissingUnitConversion, UnresolvableIngredient
from api.features.calculator.models import FoodFacts, NutrientProfile
from api.features.calculator.schemas import CostNutritionRequest, IngredientRequest
from api.features.calculator.service import CostNutritionService
from api.main import app


class _Repository:
    def __init__(self, facts):
        self.facts = facts

    def resolve_candidates(self, _names):
        return {"blackberry": ["blackberry"]}

    def fetch_food_facts(self, _keys):
        return {"blackberry": self.facts}


def _fact(approval="accepted"):
    return FoodFacts(
        canonical_key="blackberry", canonical_name="blackberry", fdc_id=None,
        description=None, nutrients=NutrientProfile(protein_g=1),
        approval_status=approval, food_key="fdc:1",
    )


def _request(unit, quantity=1):
    ingredient = IngredientRequest.model_construct(
        name="blackberry", quantity=quantity, unit=unit,
    )
    return CostNutritionRequest.model_construct(
        servings=1, budget=None, ingredients=[ingredient],
    )


def test_unsupported_unit_and_nonfinite_reject():
    service = CostNutritionService(_Repository([_fact()]))
    with pytest.raises(MissingUnitConversion):
        service.calculate(_request("unsupported"))
    with pytest.raises(MissingUnitConversion):
        service.calculate(_request("g", float("inf")))


def test_unresolvable_and_no_accepted_reject():
    service = CostNutritionService(_Repository([_fact(approval="rejected")]))
    with pytest.raises(UnresolvableIngredient):
        service.calculate(_request("g"))

    app.dependency_overrides[get_calculator_service] = lambda: service
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/v1/calculate/cost-and-nutrition", json={
                "servings": 1,
                "ingredients": [{"name": "blackberry", "quantity": 1, "unit": "g"}],
            })
    finally:
        app.dependency_overrides.pop(get_calculator_service, None)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNRESOLVABLE_INGREDIENT"
    assert set(response.json()["error"]) == {"code", "message", "details", "timestamp"}
