### p1-001-reproducible-source-pipeline - Reproducible, snapshot-pinned source pipeline (2026-10-03)

- Added/Changed/Fixed:
  - Added a versioned source registry declaring the three declared sources
    (FoodData Central, recipe dataset, FairPrice listings) with landed paths,
    snapshot ids, and capture-metadata locations
    (`SystemCode/remy/data-preparation/reproducibility/source_registry.json`).
  - Added `SystemCode/remy/data-preparation/scripts/reproducibility_manifest.py`:
    streaming, deterministic source snapshot hashing (name/size framed,
    path-sorted) plus canonical mart content checksums, emitting one versioned
    JSON source snapshot manifest; fails closed on missing/unreadable/empty
    sources and on missing or invalid capture metadata.
  - Added `SystemCode/remy/data-preparation/scripts/check_reproducibility.py`:
    validates manifest completeness (exactly three declared sources, all required
    marts) and compares mart content checksums against pinned expectations, with
    deterministic non-zero diagnostics naming the divergent mart or missing source.
  - Added `SystemCode/remy/data-preparation/reproducibility/expected_checksums.json`
    (versioned pinned expectations; ships empty under override O-1).
  - Added `SystemCode/remy/data-preparation/tests/test_reproducibility_manifest.py`.
  - Fixed mart relation reads to the canonical `lake.main_mart` (R-1).
  - Changed `SystemCode/Makefile`: the `dbt` target now emits the manifest; added
    `reproducible-manifest`, `reproducibility-check`, and `reproducible-build`
    targets, and made `ci` run `reproducible-build` plus the configured
    test/lint/typecheck `check` target.
  - Documented the source registry/capture-metadata contract, manifest location,
    checker invocation, and reviewed reference-checksum refresh procedure in
    `SystemCode/remy/data-preparation/README.md`.
- Acceptance criteria: AC-1 .. AC-8
- Decisions: docs/sdd/features/p1-001-reproducible-source-pipeline/decisions.md
- Breaking: none

### p1-001b-test-infrastructure - Graph test infrastructure (2026-10-04)

- Added/Changed/Fixed:
  - Added `tests/conftest.py` with `fake_driver` fixture emulating the Neo4j
    driver/session/result surface used by the serving model
    (`models/serving/recipe_graph_to_neo4j.py`), recording each
    `run(cypher, **params)` for assertion in orchestration tests.
  - Added `tests/graph/conftest.py` with cloud Neo4j integration fixtures:
    `load_test_env` (process env → `.env.test`, empty string = missing,
    local skip / CI fail), `neo4j_test_connection` (one `verify_connectivity`),
    `neo4j_driver` (function-scoped, `MATCH (n) DETACH DELETE n` before each
    test, driver closed after).
  - Added `tests/graph/__init__.py` to avoid mypy duplicate-module error with
    two `conftest.py` files.
  - Added `tests/test_fake_driver_smoke.py` with smoke tests for the fake
    driver (serving model runs through fake, records statements, marker
    registration).
  - Added `tests/graph/test_fixture_smoke.py` with integration smoke tests
    (write/read round-trip, clean state between tests).
  - Added `python-dotenv>=1,<2` to `[dependency-groups] dev` in
    `pyproject.toml` (additive); registered `integration` pytest marker.
  - Added `.env.test.example` with three placeholder variables and header
    documenting copy-to-repo-root, dedicated-instance requirement, and
    `.env.nonprod` separation.
  - Created `SystemCode/.gitignore` with `!.env.test.example` negation
    (root `.gitignore` already ignores `.env.test` via `.env.*`).
  - Created `.github/workflows/data-preparation.yml` at repo root with two
    steps: unit/orchestration tests (`-m "not integration"`), then integration
    tests (`-m integration` with `CI=true` and secrets from GitHub).
  - Documented fixtures, marker, env vars, dedicated-instance requirement,
    and local-skip/CI-fail behavior in `README.md`.
- Acceptance criteria: AC-1 .. AC-5
- Decisions: docs/sdd/features/p1-001b-test-infrastructure/decisions.md
- Breaking: none

### p1-002-provenance-graph-model - Provenance-preserving canonical graph model (2026-10-05)

- Added/Changed/Fixed:
  - Canonical edge vocabulary (`REQUIRES`, `FULFILLS`) with provenance properties (source, source snapshot, mapping confidence, mapping/normalization version, freshness/observation timestamp) emitted in `edge_requires.sql` and `edge_fulfills.sql`.
  - Fail-closed manifest admission preflight in serving model (`recipe_graph_to_neo4j.py`): validates p1-001 source/quality manifest, schema, accepted allocation/referential-integrity, deterministic totals, and mart coverage before creating Neo4j driver/session.
  - Atomic ownership-scoped refresh preserved; rollback on any load/post-load validation error.
  - Schema conformance demonstration enforcing canonical property allowlist (R-1); legacy aliases rejected.
  - Real-Neo4j provenance write/read tests (AC-3, AC-4, AC-8) and idempotence proof (AC-9) verified; fake-driver admission/rollback tests (AC-1, AC-2, AC-10) verified.
  - dbt singular test (`tests/mart_edge_provenance.sql`) for provenance and dangling endpoint rejection (AC-5, AC-7) written; execution deferred by p1-001 O-1 (documented deviation D-1, not an implementation deviation).
  - Makefile `serve-neo4j` target passes manifest path; README documents manifest input and fail-closed refresh.
- Acceptance criteria: AC-1 .. AC-10
- Decisions: docs/sdd/features/p1-002-provenance-graph-model/decisions.md
- Breaking: none

### p1-003-coverage-quality-reporting - Coverage and quality reporting (2026-10-05)

- Added/Changed/Fixed:
  - Added canonical coverage quality report mart (`SystemCode/remy/data-preparation/models/mart/coverage_quality_report.sql`) exposing exactly five named dimensions: `nutrition_coverage`, `price_availability`, `package_unit_conversion_coverage`, `dietary_evidence_coverage`, and `whole_recipe_completeness`.
  - Added schema contract for coverage quality report declaring exact dimension allowlist, count and bounded percentage rules, and reproducibility content columns (`models/mart/schema.yml`).
  - Added dbt singular test (`tests/coverage_quality_report.sql`) validating metrics, distinct dimensions, and population denominator bounds against canonical `edge_requires` and `node_recipe` populations (execution deferred under p1-001 O-1).
  - Added comprehensive unit and contract tests (`tests/test_coverage_quality_report.py`) covering all five dimensions, cross-dimension independence, zero-population handling, determinism across runs, observation-timestamp stability, fail-closed validation, and build association integrity.
  - Extended reproducibility manifest contract (`scripts/reproducibility_manifest.py`) to include `coverage_quality_report` in `REQUIRED_MARTS` with content checksum and content columns, bumping `MANIFEST_SCHEMA_VERSION` from 1 to 2; updated serving model (`recipe_graph_to_neo4j.py`) accepted version constant to 2 for continuous graph admission compatibility.
  - Declared coverage quality report as build-quality metadata in serving schema (`models/serving/schema.yml`), confirming it is not projected into graph store as nodes or edges.
  - Added `coverage-report` target and build association wiring to `SystemCode/Makefile`, and documented the five dimensions, predicate values, empty-population behavior, and build association in `remy/data-preparation/README.md`.
- Acceptance criteria: AC-1 .. AC-13
- Decisions: docs/sdd/features/p1-003-coverage-quality-reporting/decisions.md
- Breaking: none

### p2-001-constraint-evidence-filtering - Constraint evidence filtering (2026-10-05)

- Added/Changed/Fixed:
  - Added explicit per-constraint candidate evaluation in `SystemCode/remy/api/src/api/features/plan/filtering.py` enforcing constitutional reasoning-safety rules (R-5 through R-10).
  - Implemented distinct top-level drop causes (`evidence-absent` vs `present-evidence-excludes`) with fixed cause precedence (`present-evidence-excludes` precedes `evidence-absent`) and ingredient-scoped warnings for mild allergens (`IngredientWarning`).
  - Added conservative default handling: undeclared/unknown dietary and allergen evidence drops as `evidence-absent`, omitted request allergen severity defaults to `severe`, and offers older than 24 hours are excluded with inclusive 24-hour boundary.
  - Added input validation in `filter_candidates` rejecting unknown allergens, unsupported dietary codes, and untracked nutrients as input errors rather than candidate drops.
  - Added candidate outcome models (`CandidateOutcome`, `ConstraintEvaluation`, `IngredientWarning`, `FilterResult`) in `models.py` carrying constraint-level evaluation history, drop causes, and unmapped requirement counts.
  - Extended repository candidate hydration in `repository.py` to project freshness, package unit compatibility, and dietary/allergen evidence from canonical `FULFILLS` edges.
  - Updated `PlanService.generate` in `service.py` to propagate filtered outcomes.
  - Added comprehensive test suites: dietary domain rules (`tests/features/dietary/test_domain_rules.py`), calculator domain extensions for nutrition, cost, and conversion (`tests/features/calculator/`), filtering contract and edge cases (`tests/features/plan/test_filtering.py`), and repository-to-service integration tests (`tests/features/plan/test_service_integration.py`).
- Acceptance criteria: AC-1 .. AC-16
- Decisions: docs/sdd/features/p2-001-constraint-evidence-filtering/decisions.md
- Breaking: none

### p2-002-cost-nutrition-calculation - Cost and nutrition calculation (2026-10-08)

- Added/Changed/Fixed:
  - Updated `CostNutritionRepository.fetch_food_facts` to read deployed canonical property names (`ful.confidence AS confidence`, dropping stale `mapping_confidence`) and project the complete evidence contract: nine canonical nutrients (including `saturated_fat_g` and `cholesterol_mg`), `food_key`, `price_status`, `price_match_status`, `freshness_status`, `price_basis`, `package_volume_ml`, `nutrition_rank`, and `selection_priority` (R-1).
  - Implemented cost eligibility rules in `domain/cost.py` (C-4/R-10/R-8/AC-20): requires `price_status == "estimated"`, `price_match_status == "accepted"`, `freshness_status == "fresh"`, `price_basis in {"package_mass", "package_volume"}`, `currency == "SGD"`, and positive price and package amounts. `cost_basis_compatible` is treated as informational and does not gate selection.
  - Implemented silent volume-to-gram conversion for `package_volume` basis via `domain.units.to_grams`, computing unit prices per gram to rank volume and mass packages like-with-like (AC-13).
  - Added float tolerance `1e-9` to multi-package retail purchase cost calculation (`ceil(Q / S - 1e-9) * P`) to prevent spurious extra package count (D-2/AC-4).
  - Implemented deterministic per-nutrient conflict precedence in `domain/nutrition_select.py` (R-12/AC-6/AC-7/AC-8): branded products (`crawler_fdc_profile`) take precedence over generic USDA (`fooddata_central`/other); same-source ties resolve by smallest `(nutrition_rank, selection_priority, food_key)` tuple with missing ranks sorting last.
  - Enforced null-when-any semantics for recipe and per-serving nutrient totals in `domain/nutrition.py`: recipe and per-serving totals are null whenever any contributing ingredient lacks a value for that nutrient (never zero-filled) (R-5/R-9/AC-2).
  - Implemented item-level evidence-absent warnings: `MISSING_PACKAGE_DATA` (when an ingredient lacks eligible price packages, omitting cost totals from summary while response succeeds) and `PARTIAL_NUTRITION_DATA` (naming the missing canonical nutrients) (C-2/AC-2/AC-5).
  - Implemented best-score package selection without confidence floor in `domain/cost.py` and `service.py` (R-13/AC-10/AC-11/AC-12): ranks by lowest unit price, lowest retail package cost, highest confidence, then lexicographic `(food_key, retailer, listing_name)`. Package with confidence 0 is selectable when sole eligible.
  - Added `CalculationTrace` dataclass in `trace.py` encapsulating audit-only provenance (confidence, chosen/runner-up packages, per-nutrient winners); `service.calculate` returns `(CostNutritionResponse, CalculationTrace)` and `router.py` returns only the public response model, keeping the user payload clean (R-16/AC-18).
  - Added `MAX_REQUEST_INGREDIENTS = 100` constant in `schemas.py` and enforced request bounds (AC-19).
  - Updated response examples in `SystemCode/remy/api/docs/API_doc.md` to reflect canonical response shape without `fdc_id` or audit fields (R-1).
  - Repaired stale unit conversion and resolver tests (T-3, T-4, T-5).
  - Added comprehensive test suites including R-13 named fixture (`test_mapping_selection.py`), repository integration (`test_repository_integration.py`), service error rejection (`test_service_errors.py`), response schema verification (`test_response_schema.py`), and end-to-end integration (`test_calculator_integration.py`).
- Acceptance criteria: AC-1 .. AC-20
- Decisions: docs/sdd/features/p2-002-cost-nutrition-calculation/decisions.md
- Breaking: none
