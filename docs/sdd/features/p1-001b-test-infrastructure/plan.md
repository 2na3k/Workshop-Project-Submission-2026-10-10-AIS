---
feature: p1-001b-test-infrastructure
---

# Plan - Graph test infrastructure

## Approach

- **Chosen:** Provide both fixtures from a small `tests/conftest.py` and a new
  `tests/graph/conftest.py`. The Neo4j integration fixture connects to a
  dedicated cloud Neo4j test instance whose connection details are read from a
  gitignored `.env.test` file (or from CI environment variables). No Docker or
  testcontainers dependency. Register the `integration` marker in
  `pyproject.toml` so local runs can skip the integration tests with
  `-m "not integration"`.
- **Rejected alternative (testcontainers):** A local Neo4j container started by
  testcontainers. Rejected because the development environment cannot run
  Docker (insufficient RAM), and because the CI runner is not guaranteed to
  have Docker available. A cloud instance removes both constraints.
- **Rejected alternative (docker compose service):** Rejected for the same
  reason as testcontainers — requires Docker, which is not available.
- **Rejected alternative (developer-managed local Neo4j):** Rejected because
  it makes integration tests depend on undocumented local setup and because
  the local machine cannot run a Neo4j server.

## Design

1. **Fake driver fixture.** A `tests/conftest.py` module providing a
   `fake_driver` fixture that returns an object with the same shape as the
   serving model's driver/session/transaction interface. The method surface is
   derived from the serving model's actual driver usage in
   `models/serving/recipe_graph_to_neo4j.py`: the driver methods it calls
   (`session`, `close`, and any connection check), the session methods it calls
   (`run`, `close`, `__enter__`, `__exit__`), and the result methods it calls
   (`.data()`, `.single()`, or iteration, whichever the serving model uses).
   The fixture records each `run(cypher, **params)` as a `(cypher, params)`
   entry in an ordered list exposed on the fixture; tests assert against that
   list. The fixture's docstring documents the surface it emulates.
   A smoke test asserts that the serving model can be driven end-to-end through
   the fake without raising `AttributeError`, so a missing method is caught
   immediately rather than at first real test.

2. **Neo4j integration fixture (cloud instance).** A `tests/graph/conftest.py`
   providing:

   - A `load_test_env` session-scoped fixture that reads `NEO4J_TEST_URI`,
     `NEO4J_TEST_USERNAME`, and `NEO4J_TEST_PASSWORD` from environment
     variables, first checking the process environment and then loading
     `.env.test` from the repository root if the variables are not already set.
     The `python-dotenv` package is added as a dev dependency to support this.
     If any of the three variables is missing after both checks:
     - Under CI (`CI` env var set to `1`/`true`/`yes`), the fixture calls
       `pytest.fail(...)` with a message naming the missing variables. This
       satisfies AC-5: a skipped integration test under CI is a failure.
     - Otherwise (local), the fixture calls `pytest.skip(...)` with the same
       message. This satisfies the spec's local-skip edge case.
   - A session-scoped `neo4j_test_connection` fixture that returns a
     `(uri, auth)` tuple. It calls `driver.verify_connectivity()` once; on
     failure it raises a message naming the URI (never the password), and
     under CI this is a failure, locally a skip.
   - A function-scoped `neo4j_driver` fixture that constructs a driver from
     the connection, clears the database before each test with
     `MATCH (n) DETACH DELETE n`, and closes the driver after the test. Tests
     marked `@pytest.mark.integration` receive the driver; unmarked tests do
     not.

   **No `.env.nonprod` is read.** `.env.nonprod` configures the development /
   production Neo4j used by `make serve-neo4j` and `make dbt-all`. The test
   fixture reads only `NEO4J_TEST_URI`, `NEO4J_TEST_USERNAME`, and
   `NEO4J_TEST_PASSWORD` from `.env.test` or the process environment, so
   integration tests can never accidentally run against the nonprod instance.

   **The test instance is dedicated.** Because `neo4j_driver` clears the
   database before each test, the cloud instance behind `NEO4J_TEST_URI` must
   be a dedicated test database. The `.env.test.example` file documents this.

3. **Marker registration and dev dependency.** In
   `SystemCode/remy/data-preparation/pyproject.toml`:

   - **Add** `python-dotenv>=1,<2` to the **existing**
     `[dependency-groups] dev` list. The existing entries (`pytest`, `ruff`,
     `mypy`) are unchanged; this change is additive. Do not replace the group.
     Verify the current contents before editing:
     ```bash
     grep -A6 "dependency-groups" pyproject.toml
     ```
   - Register the marker in the existing `[tool.pytest.ini_options]` section
     (or add the section if absent):

     ```toml
     [tool.pytest.ini_options]
     markers = [
         "integration: tests that require a live Neo4j instance (skipped locally when NEO4J_TEST_URI is not configured; fails in CI when unconfigured)",
     ]
     ```

   The `neo4j` driver is already a project dependency of
   `remy-data-preparation`; no additional runtime dependency is added.

4. **CI integration.** The CI workflow gains a step that runs
   `pytest -m integration` with `NEO4J_TEST_URI`, `NEO4J_TEST_USERNAME`, and
   `NEO4J_TEST_PASSWORD` injected from CI secrets and `CI=true` in the
   environment (GitHub Actions sets `CI=true` by default). The workflow file
   is named in Files to touch after the Verification step below confirms the
   name. No Docker step is needed. If the secrets are not configured, the
   fixture calls `pytest.fail` and the job fails — the job does not silently
   pass on a missing instance. This satisfies AC-5.

   The CI-scoped environment variables take precedence over `.env.test`;
   `.env.test` is not committed and does not exist on the runner.

5. **Documentation and example env file.** Add a section to
   `SystemCode/remy/data-preparation/README.md` documenting:

   - The two fixtures (`fake_driver`, `neo4j_driver`) and what each is for.
   - The `integration` marker and how to exclude integration tests locally with
     `-m "not integration"`.
   - The required environment variables (`NEO4J_TEST_URI`,
     `NEO4J_TEST_USERNAME`, `NEO4J_TEST_PASSWORD`) and that they belong in a
     gitignored `.env.test` at the repository root.
   - That the test instance must be dedicated to testing, because the fixture
     clears the database before each test.
   - The skip-vs-fail behavior: local runs skip when unconfigured; CI runs
     fail when unconfigured.

   Add `SystemCode/remy/data-preparation/.env.test.example` with placeholder
   values for the three variables and a header comment explaining that the
   file should be copied to `.env.test` and filled with dedicated test
   credentials. Add `.env.test` to `.gitignore` if not already present.

## Files to touch

- `SystemCode/remy/data-preparation/tests/conftest.py` — fake driver fixture.
- `SystemCode/remy/data-preparation/tests/graph/conftest.py` — cloud Neo4j
  integration fixture (`load_test_env`, `neo4j_test_connection`,
  `neo4j_driver`) with local-skip / CI-fail behavior.
- `SystemCode/remy/data-preparation/tests/graph/test_fixture_smoke.py` — smoke
  tests that prove the integration fixture works (connect, write/read
  round-trip, clean-state between tests).
- `SystemCode/remy/data-preparation/tests/test_fake_driver_smoke.py` — smoke
  test that the serving model can be driven through the fake driver without
  `AttributeError`, plus a marker-registration assertion using `pytestconfig`.
- `SystemCode/remy/data-preparation/pyproject.toml` — add
  `python-dotenv>=1,<2` to the **existing** dev dependency group; register
  the `integration` marker.
- `SystemCode/remy/data-preparation/.env.test.example` — example env file with
  the three test-instance variables and a header comment.
- `SystemCode/.gitignore` — add `.env.test` if not already present.
- `SystemCode/remy/data-preparation/README.md` — document the fixtures,
  marker, env vars, and the skip-vs-fail behavior.
- `SystemCode/.github/workflows/<actual-file>.yml` — add the integration-test
  step with the three env vars from secrets (file name verified before tasks).

## Constitution alignment

- **R-3** → Uses the existing pytest stack and the existing `neo4j` runtime
  dependency; adds `python-dotenv` as a dev-only dependency, not a production
  one. No new framework, store, or solver is introduced.

_Note: this feature enables p1-002's provenance tests but does not itself
verify R-4 or R-15. No direct constitutional rule for provenance applies to
this feature; the citations above are by way of dependency on the downstream
features that will exercise them._

## Test strategy

| AC | Test type | Test location / name | Notes |
|---|---|---|---|
| AC-1 | Fake-driver smoke test | `tests/test_fake_driver_smoke.py::test_serving_model_runs_through_fake` and `tests/test_fake_driver_smoke.py::test_fake_records_statements` | Drive the serving model through the fake without `AttributeError`; assert the fixture records each `run(cypher, params)` in order. |
| AC-2 | Integration smoke test | `tests/graph/test_fixture_smoke.py::test_write_read_through_fixture` | Connect to the cloud instance, write a node through the fixture driver, read it back, assert equality. Skips locally when unconfigured; fails in CI when unconfigured. |
| AC-3 | Integration teardown | `tests/graph/test_fixture_smoke.py::test_second_test_sees_clean_state` | Paired with the write test; the second test asserts it starts with a clean database. Same skip/fail behavior as AC-2. |
| AC-4 | Marker registration + filter | `tests/test_fake_driver_smoke.py::test_integration_marker_registered` | Asserts the `integration` marker is registered via `pytestconfig.getini("markers")`. Filter behavior (`-m "not integration"`) is verified at the CI level, not by a test that invokes pytest as a subprocess. |
| AC-5 | CI job verification | No pytest test. Verified by the CI workflow step named in Design section 4: the step runs `pytest -m integration`, and its success requires the integration tests to have executed (skips under CI fail via `pytest.fail`). | The workflow runs with `CI=true` and the three secrets injected. |

## Risks & mitigations

- **`NEO4J_TEST_URI` not configured locally.** The fixture skips locally; the
  developer runs `-m "not integration"` and the suite passes. Documented in
  the README and `.env.test.example`.
- **CI secrets not configured.** The fixture calls `pytest.fail` under CI, and
  the job fails with a message naming the missing variables. This is
  intentional: a skipped integration test under CI is a failure, not a pass.
  The CI operator configures the three secrets to make the job green.
- **Cloud instance idle-paused.** The `neo4j_test_connection` fixture calls
  `verify_connectivity()` once per session, which resumes a paused Aura
  instance. The one-time latency is acceptable; no per-test cost.
- **Shared test instance polluted by concurrent runs.** The fixture clears the
  database before each test. Two concurrent runs against the same instance
  would interfere; document that `.env.test` and CI secrets should point at a
  dedicated instance. If concurrency becomes a real risk, a per-run database
  name can be introduced later.
- **Credentials leaked into test output.** The skip and error messages name
  the URI but not the password. A reviewer confirms no fixture logs the
  password or the full auth tuple.
- **Fixture bleed between tests.** Function-scoped clear; each test starts
  with an empty database. The AC-3 smoke test proves this.
- **Fake driver missing a method the serving model calls.** A smoke test
  (`tests/test_fake_driver_smoke.py::test_serving_model_runs_through_fake`)
  drives the serving model through the fake; a missing method raises
  `AttributeError` and fails the test before any dependent test runs.
- **`.env.test` accidentally committed.** The `.gitignore` change is part of
  this feature; a reviewer confirms the ignore rule is present and that
  `.env.test.example` (with placeholder values) is the only committed file.

## Scope check

Fits one working context: **yes.** Ten test-side files plus one
`pyproject.toml` change, one `.gitignore` change, and one CI workflow change.
No production code, no Docker, no testcontainers. The largest risk to the
scope is the CI workflow if it needs more than the one env-var-injected step;
verify the workflow file before writing tasks.

## Verification before tasks

Three items must be checked before tasks are written, so the plan's file list
and CI assumption are accurate:

1. **CI workflow file name.**

   ```bash
   ls SystemCode/.github/workflows/
   ```

Replace the `<actual-file>` placeholder in Files to touch with the workflow
that runs the Python tests. If no such workflow exists, this plan includes
creating one.

2. **`.env.test` in `.gitignore`.**

   ```bash
   grep -n "env.test\|\.env" SystemCode/.gitignore
   ```

   If the pattern is absent, the `.gitignore` change is in scope. If it is
   present, remove that file from Files to touch.

3. **The existing dev dependency group.**

   ```bash
   cd SystemCode/remy/data-preparation
   grep -A6 "dependency-groups" pyproject.toml
   ```

   Confirm the group already contains `pytest`, `ruff`, and `mypy`. The plan's
   change is to add `python-dotenv` — one line, additive.

## Revision notes

- F-1 → Initial plan drafted from the approved spec.
- F-2 → Named the fake driver's method surface and added a serving-model smoke
  test to prove compatibility (Design section 1).
- F-3 → Replaced the testcontainers integration fixture with a cloud Neo4j
  fixture reading from `.env.test`. Reason: development environment cannot run
  Docker (insufficient RAM) and CI cannot be assumed to have Docker.
- F-4 → Added the local-skip / CI-fail distinction for unconfigured
  integration tests (Design section 2, AC-5 in the spec, Test strategy row).
  Reason: plan review F-2 — CI must not silently pass when the integration
  tests skip.
- F-5 → Clarified that the dev dependency change is additive to the existing
  group, not a replacement (Design section 3, Verification step). Reason: plan
  review F-3.
- F-6 → Removed `tests/graph/__init__.py` from Files to touch; pytest collects
  under `tests/` without it. Reason: plan review nit.
- F-7 → Replaced the subprocess-based marker-filter test with a
  `pytestconfig`-based marker-registration assertion. Reason: plan review nit.
- F-8 → Removed the R-15 citation; kept R-3 only, with a note that the feature
  enables downstream provenance tests indirectly. Reason: plan review nit.

## Tasks

- [x] **T-1** Verify the CI workflow file, `.gitignore`, and existing dev group
    - Type: prerequisite
    - Covers: plan's "Verification before tasks" items
    - Files: (read-only)
    - Done when: the CI workflow file name is confirmed and named in a follow-up comment; `.env.test` presence in `.gitignore` is confirmed (present → no change; absent → `.gitignore` is a T-8 deliverable); the existing `[dependency-groups] dev` in `pyproject.toml` is confirmed to contain `pytest`, `ruff`, `mypy` and the change is additive.

- [x] **T-2** Add `python-dotenv>=1,<2` to the existing dev group and register the `integration` marker
    - Type: impl
    - Covers: prerequisite for AC-4, AC-5
    - Files: `SystemCode/remy/data-preparation/pyproject.toml`
    - Done when: `uv sync --all-packages` resolves; `uv run --package remy-data-preparation pytest --markers` lists `integration`; the existing dev entries are unchanged.

- [x] **T-3** Write failing tests for the fake driver fixture (AC-1)
    - Type: test
    - Covers: AC-1
    - Files: `SystemCode/remy/data-preparation/tests/test_fake_driver_smoke.py`
    - Done when: `test_serving_model_runs_through_fake` and `test_fake_records_statements` fail because the fixture does not exist yet.

- [x] **T-4** Implement the fake driver fixture
    - Type: impl
    - Covers: AC-1
    - Files: `SystemCode/remy/data-preparation/tests/conftest.py`
    - Done when: T-3 passes; the fixture records each `run(cypher, **params)` in order; the serving model can be driven end-to-end through the fake without `AttributeError`.

- [x] **T-5** Write a failing test for the marker registration (AC-4)
    - Type: test
    - Covers: AC-4
    - Files: `SystemCode/remy/data-preparation/tests/test_fake_driver_smoke.py` (or a sibling)
    - Done when: the test asserts the `integration` marker is registered via `pytestconfig.getini("markers")` and fails until T-2 lands.

- [x] **T-6** Write failing tests for the cloud Neo4j integration fixture (AC-2, AC-3)
    - Type: test
    - Covers: AC-2, AC-3
    - Files: `SystemCode/remy/data-preparation/tests/graph/test_fixture_smoke.py`
    - Done when: `test_write_read_through_fixture` and `test_second_test_sees_clean_state` are written and fail because the fixture does not exist yet.

- [ ] **T-7** Implement the cloud Neo4j integration fixture
    - Type: impl
    - Covers: AC-2, AC-3, AC-5 (the fixture's local-skip / CI-fail branch)
    - Files: `SystemCode/remy/data-preparation/tests/graph/conftest.py`
    - Done when: T-6 passes when the instance is configured; the fixture skips locally when unconfigured and fails under `CI=true`; an empty-string variable is treated as missing; the failure message names the URI but not the password.

- [ ] **T-8** Add `.env.test.example` and update `.gitignore`
    - Type: impl
    - Covers: prerequisite for local runs and for the CI documentation
    - Files: `SystemCode/remy/data-preparation/.env.test.example`, `SystemCode/.gitignore`
    - Done when: the example file exists with the three placeholder variables and a header comment; `.env.test` is gitignored.

- [ ] **T-9** Wire the CI workflow
    - Type: impl
    - Covers: AC-5
    - Files: the confirmed CI workflow file
    - Done when: the workflow runs `pytest -m "not integration"` first, then `pytest -m integration` with `NEO4J_TEST_URI`, `NEO4J_TEST_USERNAME`, `NEO4J_TEST_PASSWORD` from secrets and `CI=true`; a missing secret causes the integration step to fail.

- [ ] **T-10** Document the fixtures, marker, env vars, and skip-vs-fail behavior
    - Type: impl
    - Covers: AC-4, AC-5
    - Files: `SystemCode/remy/data-preparation/README.md`
    - Done when: the README covers both fixtures, the `integration` marker, the three env vars, the dedicated-instance requirement, the local-skip / CI-fail distinction, and notes that locally exporting `CI=1` turns skips into failures.

- [ ] **T-11** Run the focused tests and `sdd.py ci`
    - Type: verification
    - Covers: AC-1 through AC-5
    - Done when: unit tests pass; integration tests pass when the instance is configured (or skip locally when it is not); `sdd.py ci p1-001b-test-infrastructure` produces PASS evidence.
