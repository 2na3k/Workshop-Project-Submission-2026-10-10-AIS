# Data preparation — requirements prompt

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

YOUR COMPONENT: DATA PREPARATION
Repository location: SystemCode/remy/data-preparation

REQUIREMENTS

Use dbt with DuckDB/DuckLake to combine recipe data, FoodData Central nutrition,
and FairPrice retail evidence into curated graph-ready records.

Requirements:
- Normalize ingredient names while preserving each original recipe occurrence,
  quantity, unit, preparation, and optional/alternative information.
- Resolve food concepts to candidate nutrition profiles and retail products
  without collapsing generic food, branded food, and retail offers together.
- Preserve nutrition basis, conversion factors, mapping confidence, evidence
  references, observation freshness, source snapshot IDs, and mapping versions.
- Produce canonical nodes/edges, quality checks, deterministic source/mart
  checksums, and a reproducibility manifest.
- Report nutrition coverage, price availability, package/unit conversion
  coverage, dietary evidence coverage, and whole-recipe completeness.
- Require accepted provenance/quality inputs before publishing to Neo4j.
  A failed build or missing manifest must not appear as a successful refresh.

Inputs: landed datasets and source capture records. Outputs: validated marts,
quality/provenance artifacts, and a curated Neo4j projection for API queries.

ACCEPTANCE CRITERIA

The same declared source snapshots produce reproducible curated outputs and quality artifacts. Ingredient occurrences and evidence remain traceable. Missing or rejected provenance prevents graph publication.

VERIFICATION

Use commands from SystemCode/ unless a check specifies another directory.
Python checks must run through uv inside WSL as required by AGENTS.md; if WSL
or a required tool/data/service is unavailable, report the check as blocked.
Use existing checks first and add focused verification only for uncovered
requirements within the approved scope. Separate fixture-based checks from
live integrations. Record method/command, inputs, expected versus actual result,
and pass/fail/skipped/blocked/not-run status without exposing secrets.

1. Python regression without live graph mutation: run:
   uv run --package remy-data-preparation pytest -q remy/data-preparation/tests -m "not integration"
   Review serving, fake-driver, manifest, and coverage-report tests. Use copied
   inputs and disposable build outputs for negative and reproducibility cases.
2. dbt contracts: from SystemCode/remy/data-preparation/ on a disposable nonprod
   build target with declared seeds, run:
   uv run --package remy-data-preparation dbt build --profiles-dir . --exclude tag:serving
   Inspect compiled SQL, manifest.json, and run_results.json. Assert key
   uniqueness, not-null fields, relationships, and accepted values; list
   disabled or unselected models separately rather than counting them as passed.
3. Reproducibility: build twice from identical declared source snapshots into
   separate outputs and compare source/mart content checksums with the approved
   expected_checksums.json using scripts/check_reproducibility.py. Exclude
   volatile metadata only according to the declared checksum contract.
4. Fail-closed checks: use a fake driver with a missing/malformed manifest,
   missing source identity, checksum/row-count mismatch, or rejected quality
   result. Assert rejection before any graph mutation and preserve the prior
   accepted graph. Do not modify approved checksums merely to make a test pass.
5. Evidence/coverage checks: trace sample recipe occurrences through concept,
   food, offer, mapping version, and snapshot. Verify all five coverage
   dimensions, covered_count <= denominator, ratios in [0,1], and null ratios
   for no_population. Confirm whether the optional report model is enabled and
   supplied its required build-association inputs before expecting its output.
6. Live publication: use only a dedicated Neo4j test instance for marked graph
   tests. Verify accepted fixture publication, provenance, and repeated-load
   behavior; never aim the graph-clearing fixtures at app or production data.

DELIVERABLE

Provide a concise component specification covering responsibilities, owned
data, input/output contracts, dependencies, failure behavior, and acceptance
criteria. Identify the contracts needed from adjacent components and flag
unresolved requirements. If implementation is authorized, keep changes within
this component's ownership and report what was actually verified.
```
