# Decisions - Graph test infrastructure

## Decisions

### D-1 Cloud Neo4j instance, not testcontainers
- Date: 2026-10-04
- Context: The integration fixture needs a Neo4j instance. The development environment cannot run Docker (insufficient RAM), and the CI runner is not guaranteed to have Docker available.
- Decision: Use a dedicated cloud Neo4j test instance (Aura free tier) whose connection details are read from a gitignored `.env.test` file (or CI environment variables). No Docker or testcontainers dependency.
- Alternatives: testcontainers — rejected (no Docker in dev/CI); docker compose service — rejected (same reason); developer-managed local Neo4j — rejected (undocumented local setup, cannot run Neo4j server).
- Affects: Every integration test in the data-preparation package.
- Source: p1-001b plan, Design section 2; plan review F-3.

### D-2 Local skip / CI fail for unconfigured integration tests
- Date: 2026-10-04
- Context: The spec requires that CI runs fail (not silently skip) when the test instance is unconfigured, while local runs should skip with a clear reason.
- Decision: The `load_test_env` fixture checks process environment first, then `.env.test`. If any of the three required variables is missing: under CI (`CI` env var set), call `pytest.fail()`; locally, call `pytest.skip()` with the same message naming the missing variables.
- Alternatives: Always skip — rejected (CI would silently pass); always fail — rejected (blocks local development).
- Affects: CI workflow behavior and local developer experience.
- Source: p1-001b spec AC-5; plan Design section 2; plan review F-2.

### D-3 Function-scoped database clear for test isolation
- Date: 2026-10-04
- Context: Integration tests must not leak state between tests (AC-3).
- Decision: The `neo4j_driver` fixture is function-scoped and runs `MATCH (n) DETACH DELETE n` before each test, then closes the driver after the test.
- Alternatives: Session-scoped clear — rejected (would not isolate tests); transaction rollback — rejected (Neo4j doesn't support nested transactions cleanly for this use case).
- Affects: Test isolation guarantees for all integration tests.
- Source: p1-001b spec AC-3; plan Design section 2.

### D-4 python-dotenv as dev-only dependency
- Date: 2026-10-04
- Context: The fixture needs to load `.env.test` for local development.
- Decision: Add `python-dotenv>=1,<2` to the existing `[dependency-groups] dev` in `pyproject.toml` (additive, not replacing). The `neo4j` driver remains the only runtime dependency.
- Alternatives: Manual env parsing — rejected (error-prone); add to production deps — rejected (not needed at runtime).
- Affects: Local development setup; CI installs dev group.
- Source: p1-001b plan Design section 3; plan review F-3.

### D-5 Separate SystemCode/.gitignore for .env.test.example negation
- Date: 2026-10-04
- Context: The root `.gitignore` ignores `.env.*` which also hides `.env.test.example`. The example file should be committable.
- Decision: Create `SystemCode/.gitignore` with `!.env.test.example` to un-ignore the example file while keeping `.env.test` ignored via the root rule.
- Alternatives: Modify root `.gitignore` — rejected (root ignore is shared across packages); commit `.env.test` — rejected (security).
- Affects: Which env files are tracked vs ignored.
- Source: p1-001b plan T-8; plan verification step 2.

## Overrides

None.
