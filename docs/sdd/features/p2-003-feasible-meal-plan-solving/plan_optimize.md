## Scope

**In scope** (repository changes are required):
- `SystemCode/remy/api/src/api/features/plan/repository.py` — the four query
  changes below, plus `_build_recipe_skeleton` extensions.
- `SystemCode/remy/api/src/api/features/plan/service.py` — new `generate_v2`.
- `SystemCode/remy/api/src/api/features/plan/models.py` — only if new fields
  are needed on `Recipe`.
- `SystemCode/remy/api/tests/features/plan/test_service_integration.py`.
- `SystemCode/remy/api/tests/features/plan/test_plan_calculator_integration.py`.

**Out of scope:**
- `calculator/`, `domain/`, `schemas.py`, `solver_v2.py`.

## Required query changes to `QUERY_RECIPES`

The current `QUERY_RECIPES` is a partial draft. It has four defects that must
be fixed before the v2 path can preserve the plan's signals:

### 1. Per-nutrient missing counts

The current query coalesces missing nutrient values to zero, which loses
R-9's evidence-absent signal. Add a missing count per nutrient:

```cypher
sum(CASE WHEN f.energy_kcal IS NULL AND req IS NOT NULL THEN 1 ELSE 0 END)
    AS energy_kcal_missing_count
```

Repeat for all nine canonical fields: `protein_g`, `fat_g`, `saturated_fat_g`,
`carbohydrate_g`, `fiber_g`, `sugars_g`, `sodium_mg`, `cholesterol_mg`.

A nutrient is "missing" for a recipe when its `_missing_count > 0`.
`_build_recipe_skeleton` populates `recipe.missing_nutrients: list[str]` from
these counts.

### 2. Per-recipe unmapped-requirement facts

The current query returns only `unmapped_best_fulfillment_count`. AC-13 needs
the actual requirement facts. Add a `collect` of unmapped requirement maps:

```cypher
WITH r, req, fc, f, qty, ...,
     CASE
       WHEN req IS NOT NULL AND fc IS NULL THEN
         {occurrence_id: req.occurrence_id,
          normalized_name: req.normalized_name,
          raw_text: req.raw_text, cleaned_text: req.cleaned_text,
          position: req.position, reason: "missing-food-concept"}
       WHEN req IS NOT NULL AND fc IS NOT NULL AND f IS NULL THEN
         {occurrence_id: req.occurrence_id,
          normalized_name: req.normalized_name,
          raw_text: req.raw_text, cleaned_text: req.cleaned_text,
          position: req.position, reason: "missing-best-fulfillment"}
     END AS unmapped_entry
...
collect(unmapped_entry) AS unmapped_entries
```

Filter nulls in Python (or use `collect` + a comprehension).

### 3. `fc` must be in scope at the `RETURN`

The current query drops `fc` from the `WITH` chain but references it in a
`RETURN` CASE. Carry `fc` through every `WITH`. Without this fix, the query
either errors or silently never matches the CASE.

### 4. Per-recipe requirement details

`inspect_candidates` needs per-recipe requirement facts (canonical_key,
quantity, unit, occurrence_id) for offer selection. Add a small `collect`:

```cypher
collect({
  canonical_key: fc.canonical_key,
  quantity: req.quantity,
  unit: req.unit,
  occurrence_id: req.occurrence_id
}) AS requirements
