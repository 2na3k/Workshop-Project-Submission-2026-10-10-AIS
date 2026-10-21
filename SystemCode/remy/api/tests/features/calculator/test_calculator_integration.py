"""Recorded FULFILLS rows through repository, calculator, and HTTP response."""

from fastapi.testclient import TestClient

from api.features.calculator.dependencies import get_calculator_repository
from api.features.calculator.repository import CostNutritionRepository
from api.features.calculator.schemas import CostNutritionRequest, IngredientRequest
from api.features.calculator.service import CostNutritionService
from api.main import app


def _fulfills_rows():
    common = {
        "canonical_key": "blackberry",
        "description": "Blackberries",
        "approval_status": "accepted",
        "price_status": "estimated",
        "price_match_status": "accepted",
        "freshness_status": "fresh",
        "currency": "SGD",
        "price_basis": "package_mass",
        "reference_price_minor": 200,
        "package_mass_g": 200,
        "package_volume_ml": None,
        "package_count": 1,
        "cost_basis_compatible": False,
        "nutrition_rank": 0,
        "selection_priority": 1,
        "conversions": [],
    }
    branded = {
        **common,
        "fdc_id": "900001",
        "food_key": "brand:900001",
        "energy_kcal": 80,
        "protein_g": 20,
        "fat_g": None,
        "saturated_fat_g": None,
        "carbohydrate_g": None,
        "fiber_g": None,
        "sugars_g": None,
        "sodium_mg": None,
        "cholesterol_mg": None,
        "nutrition_source": "crawler_fdc_profile",
        "candidate_key": "candidate:brand:900001",
        "confidence": 0.0,
        "price_basis": "package_volume",
        "reference_price_minor": 100,
        "package_mass_g": None,
        "package_volume_ml": 100,
        "retailer": "volume-store",
        "listing_name": "Volume package",
        "listing_key": "listing:volume",
    }
    generic = {
        **common,
        "fdc_id": "900002",
        "food_key": "fdc:900002",
        "energy_kcal": 100,
        "protein_g": 10,
        "fat_g": 2,
        "saturated_fat_g": 1,
        "carbohydrate_g": 5,
        "fiber_g": 2,
        "sugars_g": 1,
        "sodium_mg": 5,
        "cholesterol_mg": None,
        "nutrition_source": "fooddata_central",
        "candidate_key": "candidate:fdc:900002",
        "confidence": 0.8,
        "retailer": "mass-store",
        "listing_name": "Mass package",
        "listing_key": "listing:mass",
    }
    return [branded, generic]


class _Session:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def run(self, query, **parameters):
        if "UNWIND $normalized_names" in query:
            return [
                {"normalized_name": name, "canonical_key": "blackberry"}
                for name in parameters["normalized_names"]
                if name == "blackberry"
            ]
        if "UNWIND $unresolved" in query:
            return []
        if "UNWIND $canonical_keys" in query:
            return _fulfills_rows()
        raise AssertionError("unexpected repository query")


class _Driver:
    def session(self):
        return _Session()


def _repository():
    return CostNutritionRepository(_Driver())


def test_end_to_end_repo_to_serialized_payload():
    repository = _repository()
    request = CostNutritionRequest(
        servings=2,
        ingredients=[IngredientRequest(name="blackberry", quantity=50, unit="g")],
    )
    calculation, trace = CostNutritionService(repository).calculate(request)
    ingredient_trace = trace.ingredients[0]
    assert ingredient_trace.nutrient_winners["protein_g"].source_kind == "crawler_fdc_profile"
    assert ingredient_trace.nutrient_winners["sodium_mg"].source_kind == "fooddata_central"
    assert ingredient_trace.chosen_package.food_key == "brand:900001"
    assert ingredient_trace.chosen_package.confidence == 0.0
    assert ingredient_trace.runner_up_package.food_key == "fdc:900002"
    assert calculation.itemized[0].consumed_cost_sgd == 0.5
    assert calculation.itemized[0].retail_package_cost_sgd == 1.0

    app.dependency_overrides[get_calculator_repository] = _repository
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/v1/calculate/cost-and-nutrition", json={
                "servings": 2,
                "ingredients": [{"name": "blackberry", "quantity": 50, "unit": "g"}],
            })
            rejected = client.post("/api/v1/calculate/cost-and-nutrition", json={
                "servings": 2,
                "ingredients": [{"name": "unknown", "quantity": 50, "unit": "g"}],
            })
    finally:
        app.dependency_overrides.pop(get_calculator_repository, None)

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"status", "servings", "summary", "itemized"}
    assert set(payload["itemized"][0]) == {
        "ingredient", "canonical_key", "listing_name", "retailer",
        "consumed_amount_g", "consumed_cost_sgd", "retail_package_cost_sgd",
        "nutrients", "warnings",
    }
    assert "trace" not in payload
    assert "confidence" not in str(payload)
    assert response.json()["itemized"][0]["warnings"][0]["message"].startswith("Missing nutrients:")
    assert rejected.status_code == 400
    assert rejected.json()["error"]["code"] == "UNRESOLVABLE_INGREDIENT"
