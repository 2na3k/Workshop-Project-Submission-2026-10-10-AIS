"""Repository adapter for plan candidates.

Uses :BEST_FULFILLMENT materialization for fast reads.
Run scripts/rebuild_best_fulfillment.py after each data prep cycle.
"""
import time
from typing import Optional

from domain import Nutrition, NUTRIENT_FIELDS, calculate_portion_nutrients, DomainError, to_grams, \
    sum_nutrition
from .models import Ingredient, Recipe, RequirementRef, RecipeRequirement

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
  AND NOT EXISTS {
    MATCH (r)-[bad:REQUIRES]->(:FoodConcept)
    WHERE bad.unit IS NULL
       OR bad.quantity IS NULL
       OR bad.quantity = 0
  }
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
  // cost_basis_compatible: best.cost_basis_compatible
  , potential_allergens: best.potential_allergens,
  may_allergic: best.may_allergic,
  allergen_screening_status: best.allergen_screening_status
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
      AND NOT EXISTS {
        MATCH (r)-[bad:REQUIRES]->(:FoodConcept)
        WHERE bad.unit IS NULL
           OR bad.quantity IS NULL
           OR bad.quantity = 0
      }
    WITH r
    ORDER BY r.recipe_id
    LIMIT $limit
    
    MATCH (r)-[req:REQUIRES]->(fc:FoodConcept)
    OPTIONAL MATCH (fc)-[best:BEST_FULFILLMENT]->(f:Food)
    RETURN r.recipe_id           AS recipe_id,
           r.Title               AS title,
           r.Instructions        AS instructions,
           req.quantity          AS quantity,
           req.unit              AS unit,
           req.optional          AS optional,
           req.preparation       AS preparation,
           req.raw_text          AS raw_text,
           req.cleaned_text      AS cleaned_text,
           req.occurrence_id     AS occurrence_id,
           req.normalized_name   AS normalized_name,
           req.position          AS position,
           fc.canonical_key      AS canonical_key,
           fc.name               AS concept_name,
           f.food_key            AS best_food_key,
           f.nutrition_basis     AS nutrition_basis,
           f.serving_size        AS serving_size,
           f.serving_size_unit   AS serving_size_unit,
           f.energy_kcal         AS energy_kcal,
           f.protein_g           AS protein_g,
           f.fat_g               AS fat_g,
           f.saturated_fat_g     AS saturated_fat_g,
           f.carbohydrate_g      AS carbohydrate_g,
           f.fiber_g             AS fiber_g,
           f.sugars_g            AS sugars_g,
           f.sodium_mg           AS sodium_mg,
           f.cholesterol_mg      AS cholesterol_mg,
           best.allergen_evidence_kinds      AS allergen_evidence_kinds,
           best.potential_allergens          AS potential_allergens,
           best.may_allergic                 AS may_allergic,
           best.allergen_screening_status    AS allergen_screening_status
           // , best.halal_status                 AS halal_status,
           // best.halal_evidence_kind          AS halal_evidence_kind,
           // best.vegetarian_status            AS vegetarian_status,
           // best.vegetarian_evidence_kind     AS vegetarian_evidence_kind,
           // best.vegetarian_concerns          AS vegetarian_concerns,
           // best.may_non_vegetarian           AS may_non_vegetarian
    ORDER BY recipe_id, position
"""

QUERY_INGREDIENTS = """
MATCH (r:Recipe)-[req:REQUIRES]->(fc:FoodConcept)
WHERE r.recipe_id IN $recipe_ids
OPTIONAL MATCH (fc)-[best:BEST_FULFILLMENT]->(f:Food)
RETURN r.recipe_id         AS recipe_id,
       req.quantity        AS quantity,
       req.unit            AS unit,
       req.optional        AS optional,
       req.preparation     AS preparation,
       req.raw_text        AS raw_text,
       req.cleaned_text    AS cleaned_text,
       req.occurrence_id   AS occurrence_id,
       req.normalized_name AS normalized_name,
       req.position        AS position,
       fc.canonical_key    AS canonical_key,
       fc.name             AS concept_name,
       f.food_key          AS best_food_key,
       f.description       AS description,
       f.ingredients       AS ingredients,
       f.serving_size      AS serving_size,
       f.serving_size_unit AS serving_size_unit,
       f.nutrition_basis   AS nutrition_basis,
       f.energy_kcal       AS energy_kcal,
       f.protein_g         AS protein_g,
       f.fat_g             AS fat_g,
       f.saturated_fat_g   AS saturated_fat_g,
       f.carbohydrate_g    AS carbohydrate_g,
       f.fiber_g           AS fiber_g,
       f.sugars_g          AS sugars_g,
       f.sodium_mg         AS sodium_mg,
       f.cholesterol_mg    AS cholesterol_mg
ORDER BY recipe_id, position
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


def _recipe_nutrients_from_rows(
        rows: list[dict],
) -> tuple[Nutrition, list[str]]:
    """Sum per-ingredient nutrients using to_grams and per-100g profiles.

    Returns
    -------
    (nutrition, missing_fields)
        ``nutrition`` is the recipe's summed per-nutrient totals. A field is
        ``None`` when any contributing ingredient lacks a value for it (R-9).
        ``missing_fields`` lists the canonical field names for which at least
        one contributing ingredient lacked a value.
    """
    portions: list[Nutrition] = []
    missing: set[str] = set()

    for row in rows:
        qty = row.get("quantity")
        unit = row.get("unit")
        if qty is None or unit is None:
            # Filtered at query level; defensive.
            continue

        profile = {field: row.get(field) for field in NUTRIENT_FIELDS}
        for field in NUTRIENT_FIELDS:
            if profile.get(field) is None:
                missing.add(field)

        profile = _normalise_profile_from_row(row, profile)
        if profile is None:
            # Unrecognised nutrition_basis; skip.
            continue

        try:
            grams, _warnings = to_grams(qty, unit)
        except DomainError:
            continue

        portion = calculate_portion_nutrients(
            nutrition_per_100g=profile,
            quantity_g=grams,
            unit="g",  # already in grams; to_grams(grams, "g") is exact
            servings=1,
        )
        if portion is not None:
            portions.append(portion)

    totals = sum_nutrition(portions) if portions else {}
    return totals, sorted(missing)


def _normalise_profile_from_row(row: dict, profile: dict) -> dict | None:
    """Convert the row's profile to per-100g. Mirrors `_normalise_food_nutrients`."""
    basis = (row.get("nutrition_basis") or "").strip().lower().replace("_", " ")
    if basis in {"per 100 g", "per 100g", "100 g", "100g"}:
        return profile
    if basis in {"per serving", "serving"}:
        size = row.get("serving_size")
        unit = row.get("serving_size_unit")
        if size and unit == "g":
            return {k: (v * 100.0 / size if v is not None else None)
                    for k, v in profile.items()}
    return None


def _build_requirements(rows: list[dict]) -> list[RecipeRequirement]:
    """Per-recipe requirement list for the calculator's inspect_candidates."""
    result: list[RecipeRequirement] = []
    for row in rows:
        canonical_key = row.get("canonical_key")
        quantity = row.get("quantity")
        unit = row.get("unit")
        if canonical_key is None or quantity is None or unit is None:
            continue
        result.append(RecipeRequirement(
            canonical_key=canonical_key,
            quantity=quantity,
            unit=unit,
            occurrence_id=row.get("occurrence_id"),
        ))
    return result


def _build_unmapped(rows: list[dict]) -> list[RequirementRef]:
    """Per-recipe unmapped requirement facts from the query rows."""
    result: list[RequirementRef] = []
    for row in rows:
        if row.get("canonical_key") is None:
            result.append(RequirementRef(
                occurrence_id=row.get("occurrence_id"),
                normalized_name=row.get("normalized_name"),
                raw_text=row.get("raw_text"),
                cleaned_text=row.get("cleaned_text"),
                position=row.get("position"),
                reason="missing-food-concept",
            ))
        elif row.get("best_food_key") is None:
            result.append(RequirementRef(
                occurrence_id=row.get("occurrence_id"),
                normalized_name=row.get("normalized_name"),
                raw_text=row.get("raw_text"),
                cleaned_text=row.get("cleaned_text"),
                position=row.get("position"),
                reason="missing-best-fulfillment",
            ))
    return result


def _build_recipe_skeleton(rows: list[dict]) -> Recipe | None:
    """One recipe, grouped from its rows.

    Uses the dataclass constructor so every default field is set. Overrides
    the fields the skeleton computes from the query rows.
    """
    if not rows:
        return None

    first = rows[0]
    recipe = Recipe(
        recipe_id=str(first["recipe_id"]),
        title=first.get("title") or str(first["recipe_id"]),
        instructions=first.get("instructions"),
    )

    # Ingredients: one per query row (the p2-001 filter needs these pre-solve).
    recipe.ingredients = [_build_ingredient(row) for row in rows]
    recipe.filter_ingredients = recipe.ingredients  # same objects for the filter

    # Nutrition: summed per-recipe totals + the missing-field list for R-9.
    recipe.nutrients, recipe.missing_nutrients = _recipe_nutrients_from_rows(rows)

    # Unmapped requirement facts (AC-13).
    recipe.unmapped_requirements = _build_unmapped(rows)

    # Requirements for the calculator's offer selection.
    recipe.requirements = _build_requirements(rows)

    # `score` stays at its dataclass default (0.0); set by rank_candidates.
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
        # print(
        #     f"fetch_candidates: neo4j={(t1 - t0) * 1000:.0f}ms "
        #     f"python={(t2 - t1) * 1000:.0f}ms "
        #     f"total={(t2 - t0) * 1000:.0f}ms "
        #     f"recipes={len(result)}"
        # )
        return result

    def fetch_candidates_v2(self, limit: int = 600) -> list[Recipe]:
        t0 = time.perf_counter()
        with self.driver.session() as session:
            flat_rows = [dict(r) for r in session.run(QUERY_RECIPES, limit=limit)]
        t1 = time.perf_counter()

        # Group rows by recipe_id (rows are already ordered by recipe_id).
        grouped: dict[str, list[dict]] = {}
        for row in flat_rows:
            grouped.setdefault(str(row["recipe_id"]), []).append(row)

        result = []
        for recipe_id, rows in grouped.items():
            skeleton = _build_recipe_skeleton(rows)
            if skeleton is not None:
                result.append(skeleton)

        t2 = time.perf_counter()
        print(f"fetch_candidates_v2: neo4j={(t1 - t0) * 1000:.0f}ms "
              f"python={(t2 - t1) * 1000:.0f}ms recipes={len(result)}")
        return result

    def fetch_ingredients(self, recipe_ids: list[str]) -> dict[str, list[Ingredient]]:
        if not recipe_ids:
            return {}
        with self.driver.session() as session:
            rows = [dict(r) for r in session.run(QUERY_INGREDIENTS, recipe_ids=recipe_ids)]
        grouped: dict[str, list[dict]] = {}
        for row in rows:
            grouped.setdefault(str(row["recipe_id"]), []).append(row)
        return {
            recipe_id: [_build_ingredient(row) for row in recipe_rows]
            for recipe_id, recipe_rows in grouped.items()
        }
