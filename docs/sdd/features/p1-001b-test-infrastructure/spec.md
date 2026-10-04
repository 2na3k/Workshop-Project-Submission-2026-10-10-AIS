---
feature: p1-001b-test-infrastructure
---

# Spec - Graph test infrastructure

## Summary

This feature establishes the test infrastructure that p1-002 and p1-003
require for their graph conformance and write/read demonstrations. It adds a
fake driver/session/transaction fixture for orchestration tests that must not
touch a live Neo4j, a real Neo4j integration fixture that connects to a
dedicated cloud test instance configured via `.env.test` (or CI environment
variables), the dev dependency that provides the environment loading, and the
CI configuration that runs the integration tests with the instance's
credentials. No production code changes; the feature exists so that downstream
features can prove their behavior against a real graph store.

## Traces to

- **G-4** and **G-7** — indirectly: this feature enables the graph provenance
  and reproducibility demonstrations those goals require.
- **Roadmap phase p1 → p1-001b-test-infrastructure** *(new)* — graph test
  infrastructure prerequisite for p1-002 and p1-003.
- **Constitutional rule:** **R-3** (stack shape — the test infra must use the
  existing Python/pytest/CI stack).

## User-facing behavior

No end-user surface. The observable consumers are the p1-002 and p1-003 test
suites and the CI pipeline.

- A test author can write an orchestration test that exercises the serving
  model's preflight and load sequence without a live Neo4j.
- A test author can write a real-Neo4j test that writes a record through the
  serving model's load path and reads it back to assert values.
- CI runs the integration tests against the configured cloud Neo4j instance;
  if that instance is not configured or unreachable under CI, the job fails
  with a clear error naming the missing configuration — it does not silently
  skip.
- A local developer without access to the test instance can run
  `pytest -m "not integration"` and the suite passes; the integration tests
  skip with a clear reason.

## Acceptance criteria

- **AC-1** Given the fake driver fixture, when an orchestration test constructs
  a serving session through it, then the test can assert which load statements
  were issued and their inputs without contacting a live Neo4j.

- **AC-2** Given the cloud Neo4j integration fixture, when a test writes a
  record through the serving model's load path, then the record is readable
  back from the same fixture within the test.

- **AC-3** Given the integration fixture, when the test session begins, then
  the database is cleared and each test starts from an empty graph; no state
  leaks from one test to the next.

- **AC-4** Given `pytest -m "not integration"`, when the test suite runs, then
  orchestration tests execute and integration tests are skipped; given
  `pytest -m integration` with the instance configured, the reverse.

- **AC-5** Given the CI environment (the `CI` environment variable is set),
  when the test suite runs, then the integration tests execute against the
  configured cloud Neo4j instance and the job **fails** if
  `NEO4J_TEST_URI`/`NEO4J_TEST_USERNAME`/`NEO4J_TEST_PASSWORD` are missing,
  malformed, or the instance is unreachable. A skipped integration test under
  CI is a CI failure.

## Edge cases & errors

- Local run without `.env.test` and without the environment variables:
  integration tests skip with a clear reason naming the three variables; the
  rest of the suite runs normally.
- CI run without the required secrets configured: the integration run fails,
  naming the missing variables. It does not silently skip.
- CI run with the secrets configured but the instance unreachable (paused,
  network-blocked, wrong URI): `verify_connectivity()` raises and the run
  fails, naming the URI (but not the password).
- The instance is reachable but the database name in the URI is wrong: the
  fixture's `verify_connectivity()` fails, same as unreachable.
- Two integration tests run in sequence and the second must not see the
  first's data: the function-scoped clear satisfies this.
- The `.env.test` file is present but partially filled (some variables set,
  others empty): treated as unconfigured, with the missing variable names
  reported.
- `.env.test` is absent and the process environment has the variables: the
  fixture uses the process environment (this is the CI path).

## Non-goals

- Not writing the graph conformance or provenance tests themselves; those
  belong to p1-002.
- Not changing production code, the serving model, or the mart contracts.
- Not adding a second test framework; the existing pytest structure is kept.
- Not provisioning a cloud Neo4j instance; the operator (developer or CI
  secret owner) provides the instance and its credentials.

## Interfaces & dependencies

- **Consumed by:** p1-002-provenance-graph-model and
  p1-003-coverage-quality-reporting.
- **Depends on:** p1-001-reproducible-source-pipeline (closed) for the general
  test layout and the `make ci` target.
- **Provides:** a fake driver/session/transaction fixture, a cloud-Neo4j
  integration fixture, a `python-dotenv` dev dependency for loading `.env.test`,
  a registered `integration` pytest marker, and a CI step that runs the
  integration tests with credentials from CI secrets.

## Open questions

_None blocking. The choice between Aura free/pro and self-hosted cloud
instance is an operator decision, not a spec decision._

## Clarifications

_No clarifications recorded._
