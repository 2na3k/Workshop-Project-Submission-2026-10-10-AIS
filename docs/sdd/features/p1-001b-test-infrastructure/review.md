# Review - Graph test infrastructure

Verdict: APPROVE

## CI evidence
OVERALL: PASS

| Check | Command | Result |
|---|---|---|
| test | `uv run --package remy-data-preparation pytest -q remy/data-preparation/tests` | PASS (17 passed) |
| lint | `uv run --package remy-data-preparation ruff check remy/data-preparation --select F,E9` | PASS |
| typecheck | `uv run --package remy-data-preparation mypy remy/data-preparation --ignore-missing-imports --exclude tests/test_serving_model.py` | PASS |

## Acceptance criteria

| AC | PASS/FAIL | test name or file:line |
|---|---|---|
| AC-1 | PASS | `tests/test_fake_driver_smoke.py::test_serving_model_runs_through_fake` (line 69), `tests/test_fake_driver_smoke.py::test_fake_records_statements` (line 91) |
| AC-2 | PASS | `tests/graph/test_fixture_smoke.py::test_write_read_through_fixture` (line 17) |
| AC-3 | PASS | `tests/graph/test_fixture_smoke.py::test_second_test_sees_clean_state` (line 36) |
| AC-4 | PASS | `tests/test_fake_driver_smoke.py::test_integration_marker_registered` (line 113) |
| AC-5 | PASS | CI workflow `.github/workflows/data-preparation.yml` runs `pytest -m integration` with `CI=true` and secrets; verified locally: CI=true + unconfigured → FAIL, local unconfigured → SKIP |

## Constitution compliance
Violations: none

- **R-3 (Stack shape is fixed unless amended)**: The feature uses the existing Python/pytest/CI stack. It adds `python-dotenv>=1,<2` as a dev-only dependency (not production), registers the `integration` pytest marker, and creates no new framework, store, or solver. The existing `neo4j` runtime dependency is reused. Compliant.

- **R-1, R-2, R-4–R-17**: Not directly applicable to this test-infrastructure feature. The feature enables downstream provenance tests (p1-002) but does not itself implement graph provenance, reasoning safety, cost/nutrition logic, or explainability.

## Plan adherence
All 11 tasks completed as specified in the plan:

- T-1: Verified CI workflow (none existed, created in T-9), `.gitignore` (root already ignores `.env.test` via `.env.*`), dev group (confirmed `pytest`, `ruff`, `mypy` present).
- T-2: Added `python-dotenv>=1,<2` to dev group and registered `integration` marker in `pyproject.toml`.
- T-3: Wrote failing fake-driver smoke tests (`test_serving_model_runs_through_fake`, `test_fake_records_statements`).
- T-4: Implemented `fake_driver` fixture in `tests/conftest.py` with driver/session/transaction/result stand-ins recording `run(cypher, **params)`.
- T-5: Added `test_integration_marker_registered` asserting marker via `pytestconfig.getini("markers")`.
- T-6: Wrote failing integration fixture smoke tests (`test_write_read_through_fixture`, `test_second_test_sees_clean_state`).
- T-7: Implemented cloud Neo4j integration fixture in `tests/graph/conftest.py` with `load_test_env` (process env → `.env.test`, empty string = missing, local skip / CI fail), `neo4j_test_connection` (one `verify_connectivity`), `neo4j_driver` (function-scoped, `MATCH (n) DETACH DELETE n` before each test, driver closed after). Added `tests/graph/__init__.py` to avoid mypy duplicate-module error.
- T-8: Added `.env.test.example` with three placeholders and header; added `!.env.test.example` to `SystemCode/.gitignore` (root `.gitignore` already ignores `.env.test`).
- T-9: Created `.github/workflows/data-preparation.yml` at repo root with two steps: unit tests (`-m "not integration"`), then integration tests (`-m integration` with `CI=true` and secrets).
- T-10: Documented fixtures, marker, env vars, dedicated-instance requirement, and local-skip/CI-fail behavior in `README.md`; corrected `.env.test.example` header (repo root is three levels up from package dir).
- T-11: Ran full suite (17 passed), `sdd.py ci` → OVERALL PASS, feature advanced to `ci-passed` stage.

No deviations from the plan.

## Findings
None.

## Nits (non-blocking)
- The `SystemCode/.gitignore` file was created solely for the `!.env.test.example` negation. This is correct per the plan's fallback (no `SystemCode/.gitignore` existed), but note that the root `.gitignore` already handles `.env.test` ignoring. The separate file is harmless and keeps the negation scoped to the package.
- The mypy duplicate-module issue with two `conftest.py` files was resolved by adding `tests/graph/__init__.py`. This is a standard pytest/mypy workaround and does not affect test behavior.
