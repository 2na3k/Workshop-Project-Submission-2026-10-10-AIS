"""Repository integration checks for the canonical deployed FULFILLS contract."""

from api.features.calculator.repository import CostNutritionRepository


class _Session:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def run(self, _query, **_parameters):
        return self.rows


class _Driver:
    def __init__(self, rows):
        self.rows = rows

    def session(self):
        return _Session(self.rows)


def test_query_b_reads_deployed_names_and_full_contract():
    row = {
        "canonical_key": "blackberry",
        "fdc_id": "372684",
        "food_key": "fdc:372684",
        "description": "Blackberries",
        "energy_kcal": 43,
        "protein_g": 1.4,
        "fat_g": 0.5,
        "saturated_fat_g": 0.0,
        "carbohydrate_g": 9.6,
        "fiber_g": 5.3,
        "sugars_g": 4.9,
        "sodium_mg": 1,
        "cholesterol_mg": 0.0,
        "candidate_key": "candidate:blackberry",
        "nutrition_source": "fooddata_central",
        "confidence": 0.0,
        "approval_status": "accepted",
        "price_status": "estimated",
        "price_match_status": "accepted",
        "freshness_status": "fresh",
        "price_basis": "package_volume",
        "package_mass_g": None,
        "package_volume_ml": 125,
        "reference_price_minor": 695,
        "currency": "SGD",
        "nutrition_rank": 1,
        "selection_priority": 2,
        "retailer": "fairprice",
        "listing_name": "Blackberries",
        "conversions": [],
    }
    facts = CostNutritionRepository(_Driver([row])).fetch_food_facts(
        ["blackberry", "missing"]
    )

    assert "mapping_confidence" not in row
    assert facts["blackberry"]
    fact = facts["blackberry"][0]
    assert fact.nutrients.saturated_fat_g == 0.0
    assert fact.nutrients.cholesterol_mg == 0.0
    assert fact.food_key == "fdc:372684"
    package = fact.packages[0]
    assert package.confidence == 0.0
    assert package.price_status == "estimated"
    assert package.price_match_status == "accepted"
    assert package.freshness_status == "fresh"
    assert package.price_basis == "package_volume"
    assert package.package_mass_g is None
    assert package.package_volume_ml == 125
    assert package.nutrition_rank == 1
    assert package.selection_priority == 2
    assert package.food_key == "fdc:372684"
    assert facts.get("missing", []) == []
