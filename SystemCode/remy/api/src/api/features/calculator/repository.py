from collections import defaultdict
from .models import FoodFacts, NutrientProfile, RetailSKU
from .resolver import normalize_name

QUERY_A = """
UNWIND $normalized_names AS normalized_name
MATCH (fc:FoodConcept)
WHERE fc.canonical_key = normalized_name
   OR toLower(replace(fc.canonical_key, '_', ' ')) CONTAINS normalized_name
RETURN normalized_name, fc.canonical_key AS canonical_key
"""

QUERY_A2 = """
UNWIND $unresolved AS unresolved_name
MATCH (fc:FoodConcept)
WHERE toLower(fc.canonical_key) STARTS WITH unresolved_name
   OR toLower(fc.canonical_key) CONTAINS unresolved_name
RETURN unresolved_name, fc.canonical_key AS canonical_key
LIMIT 20
"""

QUERY_B = """
UNWIND $canonical_keys AS canonical_key
MATCH (fc:FoodConcept {canonical_key: canonical_key})
OPTIONAL MATCH (f:Food)-[ful:FULFILLS {approval_status: 'accepted'}]->(fc)
WITH canonical_key, fc, f, ful
CALL {
  WITH f
  OPTIONAL MATCH (f)-[hc:HAS_COMPONENT]->(component:Component)
  RETURN collect(DISTINCT {grams_per_tbsp: coalesce(hc.grams_per_tbsp, component.grams_per_tbsp),
                           grams_per_piece: coalesce(hc.grams_per_piece, component.grams_per_piece)}) AS conversions
}
RETURN canonical_key, toString(f.fdc_id) AS fdc_id, f.food_key AS food_key,
       f.description AS description, f.energy_kcal AS energy_kcal, f.protein_g AS protein_g,
       f.carbohydrate_g AS carbohydrate_g, f.fat_g AS fat_g,
       f.saturated_fat_g AS saturated_fat_g, f.fiber_g AS fiber_g,
       f.sugars_g AS sugars_g, f.sodium_mg AS sodium_mg, f.calcium_mg AS calcium_mg,
       f.cholesterol_mg AS cholesterol_mg, ful.candidate_key AS candidate_key,
       f.nutrition_source AS nutrition_source,
       ful.listing_key AS listing_key,
       ful.confidence AS confidence, 
       ful.source_snapshot_id AS source_snapshot_id,
       ful.mapping_version AS mapping_version,
       ful.approval_status AS approval_status,
       ful.price_status AS price_status,
       ful.price_match_status AS price_match_status,
       ful.freshness_status AS freshness_status,
       ful.price_basis AS price_basis, ful.cost_basis_compatible AS cost_basis_compatible,
       ful.reference_price_minor AS reference_price_minor, ful.currency AS currency,
       ful.package_mass_g AS package_mass_g, ful.package_volume_ml AS package_volume_ml,
       ful.package_count AS package_count, ful.nutrition_rank AS nutrition_rank,
       ful.selection_priority AS selection_priority,
       ful.retailer AS retailer, ful.listing_name AS listing_name, conversions
"""


class CostNutritionRepository:
    def __init__(self, driver):
        self.driver = driver

    def resolve_candidates(self, names: list[str]) -> dict[str, list[str]]:
        normalized = [normalize_name(name) for name in names]
        with self.driver.session() as session:
            rows = session.run(QUERY_A, normalized_names=normalized)
            result = defaultdict(list)
            for row in rows:
                result[row["normalized_name"]].append(row["canonical_key"])
            unresolved = [name for name in normalized if not result[name]]
            if unresolved:
                rows = session.run(QUERY_A2, unresolved=unresolved)
                for row in rows:
                    result[row["unresolved_name"]].append(row["canonical_key"])
        return dict(result)

    def fetch_food_facts(self, canonical_keys: list[str]) -> dict[str, list[FoodFacts]]:
        with self.driver.session() as session:
            rows = session.run(QUERY_B, canonical_keys=list(dict.fromkeys(canonical_keys)))
            grouped: dict[str, list[FoodFacts]] = defaultdict(list)
            for row in rows:
                data = dict(row)
                key = data["canonical_key"]
                facts = FoodFacts(
                    canonical_key=key, canonical_name=key.replace("_", " "),
                    fdc_id=data.get("fdc_id"), description=data.get("description"),
                    nutrients=NutrientProfile(
                        energy_kcal=data.get("energy_kcal"),
                        protein_g=data.get("protein_g"),
                        carbohydrate_g=data.get("carbohydrate_g"),
                        fat_g=data.get("fat_g"),
                        saturated_fat_g=data.get("saturated_fat_g"),
                        fiber_g=data.get("fiber_g"),
                        sugars_g=data.get("sugars_g"),
                        sodium_mg=data.get("sodium_mg"),
                        cholesterol_mg=data.get("cholesterol_mg"),
                    ),
                    source_kind=data.get("nutrition_source"),
                    candidate_key=data.get("candidate_key"),
                    nutrition_rank=data.get("nutrition_rank"),
                    selection_priority=data.get("selection_priority"),
                    food_key=data.get("food_key"),
                    approval_status=data.get("approval_status"),
                    product_id=data.get("listing_key"),
                )
                conversions = data.get("conversions") or []
                for conversion in conversions:
                    facts.grams_per_tbsp = facts.grams_per_tbsp or conversion.get("grams_per_tbsp")
                    facts.grams_per_piece = facts.grams_per_piece or conversion.get("grams_per_piece")
                if data.get("candidate_key") is not None:
                    facts.packages.append(RetailSKU(
                        retailer=data.get("retailer"), listing_name=data.get("listing_name") or data.get("description"),
                        reference_price_minor=data.get("reference_price_minor"), currency=data.get("currency"),
                        package_mass_g=data.get("package_mass_g"), package_count=data.get("package_count"),
                        price_basis=data.get("price_basis"), cost_basis_compatible=data.get("cost_basis_compatible"),
                        confidence=data.get("confidence"), fdc_id=str(data.get("fdc_id") or ""),
                        price_status=data.get("price_status"),
                        price_match_status=data.get("price_match_status"),
                        freshness_status=data.get("freshness_status"),
                        package_volume_ml=data.get("package_volume_ml"),
                        food_key=data.get("food_key"),
                        nutrition_rank=data.get("nutrition_rank"),
                        selection_priority=data.get("selection_priority"),
                        source_snapshot_id=data.get("source_snapshot_id"),
                        mapping_version=data.get("mapping_version"),
                        approval_status=data.get("approval_status")))
                    grouped[key].append(facts)
            return dict(grouped)
