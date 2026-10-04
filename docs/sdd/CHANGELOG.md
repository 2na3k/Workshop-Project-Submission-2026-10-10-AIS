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
