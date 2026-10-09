"""Repository adapter for plan candidates.

Uses :BEST_FULFILLMENT materialization for fast reads.
Run scripts/rebuild_best_fulfillment.py after each data prep cycle.
"""
import time
from typing import Optional, cast

from domain import Nutrition
from .models import Ingredient, Recipe, RecipeRequirement, RequirementRef

# ---------------------------------------------------------------------------
# Runtime query — reads pre-computed :BEST_FULFILLMENT edges.
#
# No sort, no head(collect()), no fan-out over all FULFILLS candidates.
# Single hop: (FoodConcept)-[:BEST_FULFILLMENT]->(Food)
#
# The second OPTIONAL MATCH reuses the SAME `f` variable, so it only
# traverses FULFILLS edges ending at the winning food (cheap).
#
# Requirements:
#   - Index: :Recipe(recipe_id)
#   - Index: :FoodConcept(canonical_key)
#   - Materialization: scripts/rebuild_best_fulfillment.py
# ---------------------------------------------------------------------------
QUERY = """
MATCH (r:Recipe)
WHERE r.recipe_id IS NOT NULL
WITH r
ORDER BY r.recipe_id
LIMIT $limit

MATCH (r)-[req:REQUIRES]->(fc:FoodConcept)
OPTIONAL MATCH (fc)-[best:BEST_FULFILLMENT]->(f:Food)

WITH r, collect({
  has_requirement: req IS NOT NULL,
  quantity: req.quantity, unit: req.unit, optional: req.optional,
  preparation: req.preparation, raw_text: req.raw_text,
  cleaned_text: req.cleaned_text,
  position: req.position,
  canonical_key: fc.canonical_key, concept_name: fc.name,
  best_food_key: f.food_key,
  serving_size: f.serving_size, serving_size_unit: f.serving_size_unit,
  nutrition_basis: f.nutrition_basis, energy_kcal: f.energy_kcal,
  protein_g: f.protein_g, fat_g: f.fat_g, saturated_fat_g: f.saturated_fat_g,
  carbohydrate_g: f.carbohydrate_g, fiber_g: f.fiber_g, sugars_g: f.sugars_g,
  sodium_mg: f.sodium_mg, cholesterol_mg: f.cholesterol_mg
  // ,vegetarian_status: best.vegetarian_status,
  // vegetarian_evidence_kind: best.vegetarian_evidence_kind,
  // vegetarian_concerns: best.vegetarian_concerns,
  // may_non_vegetarian: best.may_non_vegetarian,
  // halal_status: best.halal_status,
  // halal_evidence_kind: best.halal_evidence_kind,
  // halal_freshness_status: best.halal_freshness_status,
  // freshness_status: best.freshness_status,
  // observed_at: best.observed_at,
  // package_mass_g: best.package_mass_g,
  // price_basis: best.price_basis,
  // cost_basis_compatible: best.cost_basis_compatible,
  // allergen_evidence_kinds: best.allergen_evidence_kinds,
  // potential_allergens: best.potential_allergens,
  // may_allergic: best.may_allergic,
  // allergen_screening_status: best.allergen_screening_status
}) AS ingredients

RETURN r.recipe_id AS recipe_id,
       r.Title AS title,
       r.Instructions AS instructions,
       ingredients
ORDER BY recipe_id
"""

QUERY_RECIPES = """
MATCH (r:Recipe)
WHERE r.recipe_id IS NOT NULL
WITH r ORDER BY r.recipe_id LIMIT $limit
OPTIONAL MATCH (r)-[req:REQUIRES]->(fc:FoodConcept)
OPTIONAL MATCH (fc)-[best:BEST_FULFILLMENT]->(f:Food)
WITH r, req, fc, best, f,
     CASE WHEN req IS NULL OR req.quantity IS NULL THEN 0 ELSE req.quantity END AS qty
WITH r, req, fc, best, f, qty,
     coalesce(f.energy_kcal, 0) * qty / 100.0       AS energy_kcal,
     coalesce(f.protein_g, 0) * qty / 100.0         AS protein_g,
     coalesce(f.fat_g, 0) * qty / 100.0             AS fat_g,
     coalesce(f.saturated_fat_g, 0) * qty / 100.0   AS saturated_fat_g,
     coalesce(f.carbohydrate_g, 0) * qty / 100.0    AS carbohydrate_g,
     coalesce(f.fiber_g, 0) * qty / 100.0           AS fiber_g,
     coalesce(f.sugars_g, 0) * qty / 100.0          AS sugars_g,
     coalesce(f.sodium_mg, 0) * qty / 100.0         AS sodium_mg,
     coalesce(f.cholesterol_mg, 0) * qty / 100.0    AS cholesterol_mg,
     CASE WHEN req IS NOT NULL AND fc IS NULL THEN {
       occurrence_id: req.occurrence_id, normalized_name: req.normalized_name,
       raw_text: req.raw_text, cleaned_text: req.cleaned_text,
       position: req.position, reason: 'missing-food-concept'
     } WHEN req IS NOT NULL AND fc IS NOT NULL AND f IS NULL THEN {
       occurrence_id: req.occurrence_id, normalized_name: req.normalized_name,
       raw_text: req.raw_text, cleaned_text: req.cleaned_text,
       position: req.position, reason: 'missing-best-fulfillment'
     } END AS unmapped_entry,
     CASE WHEN req IS NOT NULL AND fc IS NOT NULL THEN {
       canonical_key: fc.canonical_key, quantity: req.quantity,
       unit: req.unit, occurrence_id: req.occurrence_id
     } END AS requirement_entry,
     // Minimal per-requirement fields used by the unchanged p2-001 filter.
     // The aggregate nutrient totals are attached to one filter-only ingredient
     // in _build_recipe_skeleton; full ingredient details are fetched post-solve.
     CASE WHEN req IS NOT NULL AND fc IS NOT NULL THEN {
       quantity: req.quantity, unit: req.unit, optional: req.optional,
       preparation: req.preparation, raw_text: req.raw_text,
       cleaned_text: req.cleaned_text, occurrence_id: req.occurrence_id,
       normalized_name: req.normalized_name, position: req.position,
       canonical_key: fc.canonical_key, concept_name: fc.name,
       best_food_key: f.food_key, nutrition_basis: f.nutrition_basis,
       serving_size: f.serving_size, serving_size_unit: f.serving_size_unit,
       allergen_evidence_kinds: best.allergen_evidence_kinds,
       potential_allergens: best.potential_allergens,
       may_allergic: best.may_allergic,
       allergen_screening_status: best.allergen_screening_status,
       halal_status: best.halal_status,
       halal_evidence_kind: best.halal_evidence_kind,
       vegetarian_status: best.vegetarian_status,
       vegetarian_evidence_kind: best.vegetarian_evidence_kind,
       vegetarian_concerns: best.vegetarian_concerns,
       may_non_vegetarian: best.may_non_vegetarian
     } END AS filter_evidence,
     CASE WHEN req IS NOT NULL AND f.energy_kcal IS NULL THEN 1 ELSE 0 END AS energy_kcal_missing,
     CASE WHEN req IS NOT NULL AND f.protein_g IS NULL THEN 1 ELSE 0 END AS protein_g_missing,
     CASE WHEN req IS NOT NULL AND f.fat_g IS NULL THEN 1 ELSE 0 END AS fat_g_missing,
     CASE WHEN req IS NOT NULL AND f.saturated_fat_g IS NULL THEN 1 ELSE 0 END AS saturated_fat_g_missing,
     CASE WHEN req IS NOT NULL AND f.carbohydrate_g IS NULL THEN 1 ELSE 0 END AS carbohydrate_g_missing,
     CASE WHEN req IS NOT NULL AND f.fiber_g IS NULL THEN 1 ELSE 0 END AS fiber_g_missing,
     CASE WHEN req IS NOT NULL AND f.sugars_g IS NULL THEN 1 ELSE 0 END AS sugars_g_missing,
     CASE WHEN req IS NOT NULL AND f.sodium_mg IS NULL THEN 1 ELSE 0 END AS sodium_mg_missing,
     CASE WHEN req IS NOT NULL AND f.cholesterol_mg IS NULL THEN 1 ELSE 0 END AS cholesterol_mg_missing
RETURN r.recipe_id AS recipe_id,
       r.Title AS title,
       r.Instructions AS instructions,
       sum(energy_kcal)      AS energy_kcal,
       sum(protein_g)        AS protein_g,
       sum(fat_g)            AS fat_g,
       sum(saturated_fat_g)  AS saturated_fat_g,
       sum(carbohydrate_g)   AS carbohydrate_g,
       sum(fiber_g)          AS fiber_g,
       sum(sugars_g)         AS sugars_g,
       sum(sodium_mg)        AS sodium_mg,
       sum(cholesterol_mg)   AS cholesterol_mg,
       count(req)            AS requirement_count,
       count(CASE WHEN req IS NOT NULL AND f.energy_kcal IS NOT NULL THEN 1 END)
           AS energy_kcal_value_count,
       count(CASE WHEN req IS NOT NULL AND f.protein_g IS NOT NULL THEN 1 END)
           AS protein_g_value_count,
       count(CASE WHEN req IS NOT NULL AND f.fat_g IS NOT NULL THEN 1 END)
           AS fat_g_value_count,
       count(CASE WHEN req IS NOT NULL AND f.saturated_fat_g IS NOT NULL THEN 1 END)
           AS saturated_fat_g_value_count,
       count(CASE WHEN req IS NOT NULL AND f.carbohydrate_g IS NOT NULL THEN 1 END)
           AS carbohydrate_g_value_count,
       count(CASE WHEN req IS NOT NULL AND f.fiber_g IS NOT NULL THEN 1 END)
           AS fiber_g_value_count,
       count(CASE WHEN req IS NOT NULL AND f.sugars_g IS NOT NULL THEN 1 END)
           AS sugars_g_value_count,
       count(CASE WHEN req IS NOT NULL AND f.sodium_mg IS NOT NULL THEN 1 END)
           AS sodium_mg_value_count,
       count(CASE WHEN req IS NOT NULL AND f.cholesterol_mg IS NOT NULL THEN 1 END)
           AS cholesterol_mg_value_count,
       sum(energy_kcal_missing) AS energy_kcal_missing_count,
       sum(protein_g_missing) AS protein_g_missing_count,
       sum(fat_g_missing) AS fat_g_missing_count,
       sum(saturated_fat_g_missing) AS saturated_fat_g_missing_count,
       sum(carbohydrate_g_missing) AS carbohydrate_g_missing_count,
       sum(fiber_g_missing) AS fiber_g_missing_count,
       sum(sugars_g_missing) AS sugars_g_missing_count,
       sum(sodium_mg_missing) AS sodium_mg_missing_count,
       sum(cholesterol_mg_missing) AS cholesterol_mg_missing_count,
       count(CASE WHEN unmapped_entry IS NOT NULL THEN 1 END)
           AS unmapped_best_fulfillment_count,
       collect(unmapped_entry) AS unmapped_requirements,
       collect(requirement_entry) AS requirements,
       collect(filter_evidence) AS filter_evidence
ORDER BY recipe_id
"""

QUERY_INGREDIENTS = """
MATCH (r:Recipe)-[req:REQUIRES]->(fc:FoodConcept)
WHERE r.recipe_id IN $recipe_ids
OPTIONAL MATCH (fc)-[best:BEST_FULFILLMENT]->(f:Food)
WITH r, collect({
  has_requirement: true,
  quantity: req.quantity, unit: req.unit, optional: req.optional,
  preparation: req.preparation, raw_text: req.raw_text,
  cleaned_text: req.cleaned_text,
  occurrence_id: req.occurrence_id, normalized_name: req.normalized_name,
  position: req.position,
  canonical_key: fc.canonical_key, concept_name: fc.name,
  best_food_key: f.food_key,
  serving_size: f.serving_size, serving_size_unit: f.serving_size_unit,
  nutrition_basis: f.nutrition_basis,
  energy_kcal: f.energy_kcal, protein_g: f.protein_g, fat_g: f.fat_g,
  saturated_fat_g: f.saturated_fat_g, carbohydrate_g: f.carbohydrate_g,
  fiber_g: f.fiber_g, sugars_g: f.sugars_g, sodium_mg: f.sodium_mg,
  cholesterol_mg: f.cholesterol_mg
}) AS ingredients
RETURN r.recipe_id AS recipe_id, ingredients
"""


def _build_nutrients(x: dict) -> Nutrition:
    return {
        "energy_kcal": x.get("energy_kcal"),
        "protein_g": x.get("protein_g"),
        "fat_g": x.get("fat_g"),
        "saturated_fat_g": x.get("saturated_fat_g"),
        "carbohydrate_g": x.get("carbohydrate_g"),
        "fiber_g": x.get("fiber_g"),
        "sugars_g": x.get("sugars_g"),
        "sodium_mg": x.get("sodium_mg"),
        "cholesterol_mg": x.get("cholesterol_mg"),
    }


def _fallback_text(x: dict) -> Optional[str]:
    return (
            x.get("cleaned_text")
            or x.get("raw_text")
            or x.get("description")
            or x.get("concept_name")
            or x.get("canonical_key")
    )


def _build_ingredient(x: dict) -> Ingredient:
    """Construct Ingredient without Pydantic validation overhead (fast path)."""
    ing = Ingredient.__new__(Ingredient)
    ing.quantity = x.get("quantity")
    ing.unit = x.get("unit")
    ing.text = _fallback_text(x)
    ing.preparation = x.get("preparation")
    ing.optional = bool(x.get("optional", False))
    ing.position = x.get("position")
    ing.occurrence_id = x.get("occurrence_id")
    ing.raw_text = x.get("raw_text")
    ing.cleaned_text = x.get("cleaned_text")
    ing.description = x.get("description")
    ing.concept_name = x.get("concept_name")
    ing.canonical_key = x.get("canonical_key")
    ing.ingredients = x.get("ingredients")
    ing.allergen_evidence_kinds = x.get("allergen_evidence_kinds")
    ing.potential_allergens = x.get("potential_allergens")
    ing.may_allergic = x.get("may_allergic")
    ing.allergen_screening_status = x.get("allergen_screening_status")
    ing.halal_status = x.get("halal_status")
    ing.halal_evidence_kind = x.get("halal_evidence_kind")
    ing.halal_freshness_status = x.get("halal_freshness_status")
    ing.freshness_status = x.get("freshness_status")
    ing.offer_observed_at = x.get("observed_at")
    ing.package_mass_g = x.get("package_mass_g")
    ing.package_unit_basis = x.get("price_basis")
    ing.price_status = x.get("price_status")
    ing.price_match_status = x.get("price_match_status")
    ing.price_basis = x.get("price_basis")
    ing.cost_basis_compatible = x.get("cost_basis_compatible")
    ing.vegan_status = x.get("vegan_status")
    ing.vegetarian_status = x.get("vegetarian_status")
    ing.vegetarian_evidence_kind = x.get("vegetarian_evidence_kind")
    ing.vegetarian_concerns = x.get("vegetarian_concerns")
    ing.may_non_vegetarian = x.get("may_non_vegetarian")
    ing.nutrients = _build_nutrients(x)
    ing.nutrition_basis = x.get("nutrition_basis")
    ing.serving_size = x.get("serving_size")
    ing.serving_size_unit = x.get("serving_size_unit")
    return ing


def _build_recipe(row: dict) -> Optional[Recipe]:
    ingredients_raw = row.get("ingredients") or []

    unmapped_requirements = []
    quantifiable = []
    for item in ingredients_raw:
        if item.get("has_requirement") is False:
            continue
        if item.get("canonical_key") is None:
            unmapped_requirements.append(
                RequirementRef(
                    occurrence_id=item.get("occurrence_id"),
                    normalized_name=item.get("normalized_name"),
                    raw_text=item.get("raw_text"),
                    cleaned_text=item.get("cleaned_text"),
                    position=item.get("position"),
                    reason="missing-food-concept",
                )
            )
            continue
        if item.get("best_food_key") is None:
            unmapped_requirements.append(
                RequirementRef(
                    occurrence_id=item.get("occurrence_id"),
                    normalized_name=item.get("normalized_name"),
                    raw_text=item.get("raw_text"),
                    cleaned_text=item.get("cleaned_text"),
                    position=item.get("position"),
                    reason="missing-best-fulfillment",
                )
            )
            continue
        if (item.get("quantity") or 0) != 0:
            quantifiable.append(item)

    if not quantifiable and not unmapped_requirements:
        return None

    recipe_id = str(row["recipe_id"])
    recipe = Recipe.__new__(Recipe)
    recipe.recipe_id = recipe_id
    recipe.title = row.get("title") or recipe_id
    recipe.instructions = row.get("instructions")
    recipe.ingredients = [_build_ingredient(x) for x in quantifiable]
    recipe.unmapped_requirements = unmapped_requirements
    return recipe


def _build_recipe_skeleton(row: dict) -> Optional[Recipe]:
    requirement_count = row.get("requirement_count", 0) or 0
    unmapped_rows = row.get("unmapped_requirements") or []
    if requirement_count == 0 and not unmapped_rows:
        return None

    recipe_id = str(row["recipe_id"])
    recipe = Recipe.__new__(Recipe)
    recipe.recipe_id = recipe_id
    recipe.title = row.get("title") or recipe_id
    recipe.instructions = row.get("instructions")
    recipe.ingredients = []  # populated later by fetch_ingredients for selected recipes
    nutrient_fields = (
        "energy_kcal", "protein_g", "fat_g", "saturated_fat_g",
        "carbohydrate_g", "fiber_g", "sugars_g", "sodium_mg", "cholesterol_mg",
    )
    recipe.nutrients = cast(Nutrition, {
        field: row[field]
        for field in nutrient_fields
        if row.get(field) is not None and row.get(f"{field}_value_count", 1) > 0
    })
    recipe.missing_nutrients = [
        field for field in nutrient_fields
        if (row.get(f"{field}_missing_count", 0) or 0) > 0
    ]
    recipe.unmapped_requirements = [
        RequirementRef(
            occurrence_id=item.get("occurrence_id"),
            normalized_name=item.get("normalized_name"),
            raw_text=item.get("raw_text"),
            cleaned_text=item.get("cleaned_text"),
            position=item.get("position"),
            reason=item["reason"],
        )
        for item in unmapped_rows
    ]
    recipe.requirements = [
        RecipeRequirement(
            canonical_key=item["canonical_key"],
            quantity=item.get("quantity"),
            unit=item.get("unit"),
            occurrence_id=item.get("occurrence_id"),
        )
        for item in row.get("requirements", [])
        if item is not None and item.get("canonical_key") is not None
    ]
    filter_rows = row.get("filter_evidence") or []
    recipe.filter_ingredients = [_build_ingredient(item) for item in filter_rows]
    if recipe.filter_ingredients:
        recipe.filter_ingredients[0].nutrients = recipe.nutrients
        recipe.filter_ingredients[0].nutrition_basis = "per 100 g"
    return recipe

class PlanRepository:
    def __init__(self, driver):
        self.driver = driver

    def fetch_candidates(self, limit: int = 600) -> list[Recipe]:
        t0 = time.perf_counter()

        with self.driver.session() as session:
            rows = list(session.run(QUERY, limit=limit))

        t1 = time.perf_counter()

        result = [
            r for r in (_build_recipe(row) for row in rows) if r is not None
        ]

        t2 = time.perf_counter()
        print(
            f"fetch_candidates: neo4j={(t1 - t0) * 1000:.0f}ms "
            f"python={(t2 - t1) * 1000:.0f}ms "
            f"total={(t2 - t0) * 1000:.0f}ms "
            f"recipes={len(result)}"
        )
        return result

    def fetch_candidates_v2(self, limit: int = 600) -> list[Recipe]:
        t0 = time.perf_counter()
        with self.driver.session() as session:
            rows = list(session.run(QUERY_RECIPES, limit=limit))
        t1 = time.perf_counter()
        result = [r for r in (_build_recipe_skeleton(row) for row in rows) if r is not None]
        t2 = time.perf_counter()
        print(f"fetch_candidates: neo4j={(t1-t0)*1000:.0f}ms "
              f"python={(t2-t1)*1000:.0f}ms recipes={len(result)}")
        return result

    def fetch_ingredients(self, recipe_ids: list[str]) -> dict[str, list[Ingredient]]:
        if not recipe_ids:
            return {}
        with self.driver.session() as session:
            rows = list(session.run(QUERY_INGREDIENTS, recipe_ids=recipe_ids))
        return {
            row["recipe_id"]: [_build_ingredient(x) for x in row["ingredients"]]
            for row in rows
        }
