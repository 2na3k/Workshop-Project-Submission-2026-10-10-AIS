# DuckDB and DuckLake — requirements prompt

Copy the complete prompt below. It includes its own project context.

```text
Remy is a meal-planning application combining recipes, food nutrition,
Singapore grocery prices, and dietary evidence. Its web UI uses an account
backend for user data and a recommendation API for plans/calculations. A Python
chat application composes an in-process LangGraph workflow with those services.
Data preparation publishes source-backed recipe and food evidence to Neo4j.

Design and implement the component described below within the approved project
scope. Follow repository governing instructions and artifact ownership. Preserve
compatible interfaces with adjacent components; surface conflicts rather than
silently expanding scope or rewriting another component.

Ground results in available data. Keep missing evidence explicit. Do not invent
nutrition values, prices, ingredients, certifications, or successful constraint
checks. This is a requirements brief, not an assertion that the current code
already satisfies every requirement.

YOUR COMPONENT: DUCKDB AND DUCKLAKE
Repository location: SystemCode/remy/data-preparation/profiles.yml and SystemCode/remy/data-preparation/models

REQUIREMENTS

Design the analytical storage used by the dbt data-preparation component.

DuckDB/DuckLake owns analytical build intermediates and curated marts. It is
the transformation workspace, not the browser-facing application database.

Inputs: declared recipe, FoodData Central, and FairPrice source snapshots plus
the data-preparation component's transformation models.
Outputs: staging/intermediate relations, canonical graph-ready marts, and the
build data needed for quality reporting and reproducibility manifests.

Keep source lineage, snapshot association, nutrient basis, units, missingness,
and mapping/evidence metadata available to downstream models. Keep nonprod and
production build targets distinct. Coordinate relation names and schemas with
the dbt models and manifest generator. Publish graph data through the owning
serving step only after its provenance and quality requirements are satisfied.

ACCEPTANCE CRITERIA

The configured build target produces inspectable relations consumed by data preparation and the manifest generator. Identical declared inputs support deterministic outputs, and missing data is not replaced by fabricated values.

VERIFICATION

Use commands from SystemCode/ unless a check specifies another directory.
Python checks must run through uv inside WSL as required by AGENTS.md; if WSL
or a required tool/data/service is unavailable, report the check as blocked.
Use existing checks first and add focused verification only for uncovered
requirements within the approved scope. Separate fixture-based checks from
live integrations. Record method/command, inputs, expected versus actual result,
and pass/fail/skipped/blocked/not-run status without exposing secrets.

1. dbt/profile check: inspect profiles.yml and dbt_project.yml, resolve the
   nonprod database/catalog/data paths, and run from the preparation directory:
   uv run --package remy-data-preparation dbt debug --profiles-dir .
   Report connection/configuration results separately from model correctness.
2. Build/catalog check: in an isolated target with declared source snapshots,
   run dbt build through uv with --profiles-dir . --exclude tag:serving.
   Inspect information_schema.tables, column types, staging/intermediate/mart
   relations, and the attached DuckLake catalogue. Check run_results.json for
   actual successes, failures, skips, and disabled models.
3. SQL integrity checks: query duplicate/null canonical keys and orphan
   recipe/food/concept links; reconcile row counts with the graph-quality and
   reproducibility manifests. Compare a source row through staging and marts,
   preserving units, nulls, nutrition basis, and provenance.
4. Determinism/target isolation: repeat a build from the same declared sources
   into separate scratch paths and compare canonical content checksums. Verify
   configured nonprod outputs do not point to production database/catalog/data
   paths. Test missing seeds or unavailable required extensions explicitly.
5. Missingness/coverage check: use fixtures with incomplete nutrition, absent
   offers, incompatible units, and empty populations. Verify SQL does not
   coerce missing evidence into success or zero cost. If coverage reporting is
   enabled, validate its five dimensions and supplied build associations.

DELIVERABLE

Provide a concise component specification covering responsibilities, owned
data, input/output contracts, dependencies, failure behavior, and acceptance
criteria. Identify the contracts needed from adjacent components and flag
unresolved requirements. If implementation is authorized, keep changes within
this component's ownership and report what was actually verified.
```
