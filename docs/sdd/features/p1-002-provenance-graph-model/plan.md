---
feature: p1-002-provenance-graph-model
---

# Plan - Provenance-preserving canonical graph model

## Approach

- **Chosen:** Extend the existing dbt-to-Neo4j projection in place: make the
  mart contracts emit one canonical provenance vocabulary on both linking
  relations, validate the p1-001 source/quality manifest before opening the
  graph transaction, and prove admission, schema, provenance, referential
  integrity, and repeat-load behavior with isolated fixtures plus the existing
  data-preparation test command.
- **Rejected alternative:** Add a second graph loader or a separate provenance
  graph/metadata store; this would duplicate the canonical schema, violate R-1,
  and leave downstream consumers exposed to two possible sources of truth.

## Design

1. **Canonical edge contract.** Treat the repository's deployed graph direction
   and relationship identities as fixed: `Recipe -[:REQUIRES]-> FoodConcept`,
   `Food -[:FULFILLS]-> FoodConcept`, and the existing `HAS_COMPONENT` support
   relation. Define one canonical set of edge provenance properties in the mart
   and serving schema contracts: source, source snapshot, mapping confidence,
   mapping/normalization version, and freshness/observation timestamp. Populate
   the applicable values in both `edge_requires` and `edge_fulfills`; do not
   preserve an alternate spelling as a compatibility alias. For requirement
   links, use the recipe snapshot and normalization evidence produced by the
   accepted pipeline. For fulfillment links, carry the existing candidate
   mapping, source snapshot, confidence, and observation evidence, normalizing
   the vocabulary where the current model uses a legacy name.

2. **Fail-closed mart validation.** Add dbt contract/tests that reject a
   populated `REQUIRES` or `FULFILLS` row with null/blank provenance, invalid
   confidence, invalid timestamp, or an unresolved endpoint. Keep the existing
   relationship tests and add explicit endpoint and provenance failures so a
   bad mart cannot reach the serving model. Empty relations remain valid only
   when their accepted quality result explicitly reports zero rows.

3. **Manifest admission before publication.** Extend the serving model's
   preflight to consume the p1-001 generated source snapshot manifest together
   with `graph_quality_manifest`. Validate required source identities/snapshot
   identities, manifest schema, accepted allocation and referential-integrity
   results, deterministic totals, and the expected canonical mart coverage
   before creating a Neo4j driver/session or modifying the graph. Make the
   manifest location an explicit serving/build configuration passed by the
   existing `serve-neo4j` command; do not infer acceptance from a successful
   dbt run or filesystem timestamps.

4. **Atomic, ownership-scoped refresh.** Preserve the loader's current
   projection-owner cleanup and capacity gates, but keep all deletion and load
   work inside the existing transaction. Run the new admission and source/mart
   checks before that transaction. On any load or post-load validation error,
   roll back so an invalid or partial build cannot replace the prior graph.
   Repeated accepted loads use the existing canonical relationship identities
   and constraints, producing no duplicate links and preserving supplied
   provenance values.

5. **Schema conformance demonstration.** Define the canonical node and edge
   property allowlists from the serving contract and test the actual Cypher
   statements/loaded records against them. The conformance check must reject
   legacy aliases and must cover all properties required by the deployed graph
   design, not merely the newly added provenance fields.

6. **Verification boundaries.** Split test obligations by what actually needs a
   real graph store versus what a fake driver can prove. The test
   infrastructure this relies on is provided by p1-001b (closed 2026-10-04):

    - **Fake-driver tests** prove orchestration and admission semantics: AC-1,
      AC-2, and AC-10. These use the `fake_driver` fixture from p1-001b's
      `tests/conftest.py`.
    - **Real-Neo4j tests** prove write/read and idempotence: AC-3 through AC-9.
      These use the `neo4j_driver` fixture from p1-001b's
      `tests/graph/conftest.py`, and are marked `@pytest.mark.integration`.
      Locally they skip when the test instance is unconfigured; in CI they
      execute against the cloud instance with `NEO4J_TEST_URI`,
      `NEO4J_TEST_USERNAME`, and `NEO4J_TEST_PASSWORD` from CI secrets and
      fail if those are missing (per p1-001b's D-2).
    - **dbt singular tests** prove mart-level rejection, run under `dbt build`
      which `make dbt` invokes.

   Do not fake the reference checksum. Real end-to-end demonstration against
   seeded data remains gated by p1-001 O-1; this plan proves fail-closed
   behavior with fixtures and reports the blocked real-data evidence rather
   than fabricating a baseline.

## Files to touch

- `SystemCode/remy/data-preparation/models/mart/edge_requires.sql` — emit the
  canonical requirement-link provenance values.
- `SystemCode/remy/data-preparation/models/mart/edge_fulfills.sql` — normalize
  and validate fulfillment-link provenance values.
- `SystemCode/remy/data-preparation/models/mart/schema.yml` — declare the single
  canonical edge properties and dbt contracts/tests for provenance and endpoint
  validity.
- `SystemCode/remy/data-preparation/models/serving/recipe_graph_to_neo4j.py` —
  validate the accepted source/quality manifest, enforce preflight and
  fail-closed publication, and retain atomic ownership-scoped loading.
- `SystemCode/remy/data-preparation/models/serving/schema.yml` — document the
  serving output and admission/load contract.
- `SystemCode/Makefile` — pass the accepted source snapshot manifest to the
  serving command and keep the graph-load command aligned with the configured
  build target.
- `SystemCode/remy/data-preparation/README.md` — document the required accepted
  manifest input and the fail-closed graph refresh behavior.
- `SystemCode/remy/data-preparation/tests/test_serving_model.py` — cover
  accepted/failed admission, preflight rejection, rollback, dangling endpoints,
  and repeat-load behavior using the fake driver fixtures.
- `SystemCode/remy/data-preparation/tests/graph/test_schema_conformance.py` —
  add the R-1 canonical property vocabulary fixture (real Neo4j).
- `SystemCode/remy/data-preparation/tests/graph/test_edge_provenance.py` — add
  the R-4 write/read fixture for populated `REQUIRES` and `FULFILLS` records
  (real Neo4j).
- `SystemCode/remy/data-preparation/tests/mart_edge_provenance.sql` — add a dbt
  singular test for missing or malformed edge provenance and dangling
  relationship endpoints.

## Constitution alignment

- **R-1** → The mart, serving, and graph tests define one canonical property
  vocabulary and reject legacy aliases; no second schema or dual-name read path
  is introduced.
- **R-3** → The existing Python/dbt/DuckDB/Neo4j shape is retained; the change
  extends the current graph projection rather than adding another store or
  framework.
- **R-4** → Both populated `REQUIRES` and `FULFILLS` records carry source,
  snapshot, confidence, version, and freshness evidence, and the named graph
  fixture verifies values after write/read against a real Neo4j.
- **R-15** → The serving preflight requires the p1-001 manifest and accepted
  quality/referential-integrity facts, rejects dangling endpoints, and publishes
  only through an atomic transaction.
- **R-2** → Changes stay within the data-preparation serving/mart/test boundary
  and do not introduce dependencies across the backend package layers.

## Test strategy

All tests in this table depend on the fixtures provided by
p1-001b-test-infrastructure (closed 2026-10-04): the fake driver from
`tests/conftest.py` and the cloud Neo4j integration fixture from
`tests/graph/conftest.py`. The `integration` marker is registered by p1-001b's
`pyproject.toml` change.

| AC | Test type | Test location / name | Notes |
|---|---|---|---|
| AC-1 | Fake-driver serving fixture | `tests/test_serving_model.py::test_accepted_manifest_loads_canonical_graph` | Supply accepted source/quality manifests and assert preflight passes and each canonical load step is called with the expected inputs. |
| AC-2 | Fake-driver negative fixture | `tests/test_serving_model.py::test_missing_or_failed_manifest_preserves_graph` | Exercise missing, malformed, and failed admission before driver mutation; assert non-zero failure and no driver write calls. |
| AC-3 | Real-Neo4j write/read | `tests/graph/test_edge_provenance.py::test_requires_provenance_is_preserved` | Load a populated requirement edge and read it back; assert source, snapshot, version, confidence, and timestamp are non-null and preserved. |
| AC-4 | Real-Neo4j write/read | `tests/graph/test_edge_provenance.py::test_fulfills_provenance_is_preserved` | Use a fulfillment/offer candidate; assert all applicable provenance values survive projection. |
| AC-5 | dbt singular test + real-Neo4j negative | `tests/mart_edge_provenance.sql` (dbt) + `tests/graph/test_edge_provenance.py::test_missing_provenance_fails` | The dbt test fails when the mart carries null/blank/out-of-range values; the graph test asserts the loader refuses such rows. |
| AC-6 | Real-Neo4j schema conformance | `tests/graph/test_schema_conformance.py::test_only_canonical_property_names_are_emitted` | Compare node/edge property names in the loaded graph against the canonical allowlist; reject legacy aliases. |
| AC-7 | dbt singular test + fake-driver negative | `tests/mart_edge_provenance.sql` (dbt) + `tests/test_serving_model.py::test_dangling_endpoint_blocks_load` | The dbt test catches dangling endpoints in the mart; the serving test asserts load is refused before publication. |
| AC-8 | Real-Neo4j write/read | `tests/graph/test_edge_provenance.py::test_write_read_provenance_matches_input` | Exercise the load statements used by the serving model against a real Neo4j; compare read-back values with input values. |
| AC-9 | Real-Neo4j idempotence | `tests/test_serving_model.py::test_repeated_accepted_load_is_content_identical` (with real Neo4j marker) | Run two accepted loads against the same Neo4j instance; assert no duplicate identity and identical canonical property values. |
| AC-10 | Fake-driver negative fixture | `tests/test_serving_model.py::test_failed_allocation_or_integrity_rolls_back` | Inject failed allocation and referential-integrity dimensions; assert named error, non-zero result, and no commit. |

**Marker registration.** `@pytest.mark.integration` is registered in
`pyproject.toml` under `[tool.pytest.ini_options]` so the local `-m "not
integration"` run works and CI can run the full set.

**dbt test execution.** The `make dbt` target runs `dbt build`, which
executes model tests after each model, including the new
`tests/mart_edge_provenance.sql` singular test. The singular test's failure
fails the build before the serving model runs.

## Risks & mitigations

- **p1-001 O-1 blocks a real-data demonstration.** Keep the dependency explicit,
  use deterministic synthetic relations/manifests for unit and contract tests,
  and do not populate fabricated expected checksums. Run the real end-to-end
  graph gate only after the seeds and reviewed reference checksums are restored.
- **Real-Neo4j integration tests depend on the cloud instance.** The tests
  connect via the p1-001b fixture using `NEO4J_TEST_URI` /
  `NEO4J_TEST_USERNAME` / `NEO4J_TEST_PASSWORD` from `.env.test` locally or
  from CI secrets. Locally, an unconfigured environment skips with a clear
  reason; under CI (`CI=true`), an unconfigured environment fails, so a
  misconfigured CI run cannot silently pass while the integration tests never
  ran. If the instance is idle-paused, the fixture's one-time
  `verify_connectivity()` resumes it.
- **Existing edge vocabulary may be consumed by later services.** Derive the
  canonical property list from the deployed schema and update the serving
  contract and tests in the same change; reject aliases rather than silently
  supporting both names. Review downstream query references before changing a
  legacy property.
- **A graph transaction can be destructive if preflight is incomplete.** Make
  all manifest, mart, endpoint, and capacity checks occur before deletion; keep
  deletion and insertion in the existing transaction and assert rollback in
  failure tests.
- **The manifest is produced outside the dbt serving invocation.** Make its
  path/configuration explicit in the Makefile and fail when absent or malformed;
  do not substitute build time or filesystem metadata.
- **Ambiguous provenance for unresolved requirement mappings.** Treat missing
  applicable confidence/version/timestamp as invalid evidence and reject the
  row, rather than assigning a default that would make an unresolved link look
  authoritative.
- **p1-001b dependency satisfied.** The fixtures this feature's tests require
  are provided by p1-001b, which closed on 2026-10-04. If those fixtures are
  later changed or broken, this feature's tests break; the dependency is
  documented in the roadmap and the feature table.

## Scope check

Fits one working context: **yes.** The work is the mart edge contract, the
serving preflight and atomic load, the Makefile and README, and the two graph
test files plus the mart singular test. Test infrastructure is provided by
p1-001b and is not in scope here. The p1-001 O-1 seed restoration remains a
tracked prerequisite for the real-data demonstration and is not a reason to
split.

## Revision notes

- F-1 → Initial plan drafted from the approved spec, constitution, and existing
  data-preparation project.
- F-2 → Added real-vs-fake verification boundary; split Test strategy rows by
  test type.
- F-3 → Clarified that the dbt singular test is a `dbt build`-invoked test.
- F-4 → Sharpened the scope check.
- F-5 → Removed test infrastructure from scope after verification found no
  fixtures, no `tests/graph/`, and no Neo4j test infrastructure existed.
  Inserted p1-001b-test-infrastructure as a prerequisite feature; this plan now
  depends on it.
- F-6 → Updated stale references after p1-001b closed on 2026-10-04: the
  real-Neo4j risk bullet now describes the cloud-instance connection and the
  local-skip / CI-fail behavior rather than ephemeral provisioning; the
  p1-001b-dependency risk bullet now records the dependency as satisfied; the
  Design section 6 and the Test strategy preamble name the closed p1-001b.

## Tasks

- [x] **T-1** Write failing fake-driver serving tests (AC-1, AC-2, AC-10)
    - Type: test
    - Covers: AC-1, AC-2, AC-10
    - Files: `SystemCode/remy/data-preparation/tests/test_serving_model.py`
    - Done when: `test_accepted_manifest_loads_canonical_graph`, `test_missing_or_failed_manifest_preserves_graph`, and `test_failed_allocation_or_integrity_rolls_back` are written and fail because the preflight and admission logic do not exist yet.

- [x] **T-2** Implement manifest admission preflight in the serving model (AC-1, AC-2, AC-10)
    - Type: impl
    - Covers: AC-1, AC-2, AC-10
    - Files: `SystemCode/remy/data-preparation/models/serving/recipe_graph_to_neo4j.py`, `SystemCode/remy/data-preparation/models/serving/schema.yml`
    - Done when: T-1 passes; preflight validates manifest schema, source identities, quality result, deterministic totals, and mart coverage before creating a driver/session; failure paths name the missing dimension and do not write.

- [x] **T-3** Write failing real-Neo4j provenance tests (AC-3, AC-4, AC-5, AC-8)
    - Type: test
    - Covers: AC-3, AC-4, AC-5, AC-8
    - Files: `SystemCode/remy/data-preparation/tests/graph/test_edge_provenance.py`
    - Done when: `test_requires_provenance_is_preserved`, `test_fulfills_provenance_is_preserved`, `test_missing_provenance_fails`, and `test_write_read_provenance_matches_input` are written and marked `@pytest.mark.integration`; each fails when the edge provenance is not emitted.

- [ ] **T-4** Emit canonical provenance on `edge_requires` and `edge_fulfills` (AC-3, AC-4)
    - Type: impl
    - Covers: AC-3, AC-4
    - Files: `SystemCode/remy/data-preparation/models/mart/edge_requires.sql`, `SystemCode/remy/data-preparation/models/mart/edge_fulfills.sql`, `SystemCode/remy/data-preparation/models/mart/schema.yml`
    - Done when: T-3's positive tests pass; the mart columns are the canonical vocabulary (no legacy alias); the schema.yml contract declares them.

- [ ] **T-5** Add dbt singular tests for provenance and endpoints (AC-5, AC-7)
    - Type: test
    - Covers: AC-5, AC-7
    - Files: `SystemCode/remy/data-preparation/tests/mart_edge_provenance.sql`
    - Done when: the singular test fails when a mart row carries null/blank/invalid provenance or a dangling endpoint; the test file carries a comment noting that node-level provenance does not satisfy edge-level provenance (reviewer nit 2).

- [ ] **T-6** Write failing schema-conformance test (AC-6)
    - Type: test
    - Covers: AC-6
    - Files: `SystemCode/remy/data-preparation/tests/graph/test_schema_conformance.py`
    - Done when: `test_only_canonical_property_names_are_emitted` is written and marked `@pytest.mark.integration`; it fails against the current schema because the canonical allowlist is not yet enforced.

- [ ] **T-7** Implement schema conformance (AC-6)
    - Type: impl
    - Covers: AC-6
    - Files: `SystemCode/remy/data-preparation/models/serving/recipe_graph_to_neo4j.py`, `SystemCode/remy/data-preparation/models/serving/schema.yml`
    - Done when: T-6 passes; the loader rejects legacy aliases and enforces the canonical property allowlist; a comment notes that single-valued Neo4j properties mean "conflicting values" reduces to identity duplication, which AC-9 covers (reviewer nit 3).

- [ ] **T-8** Wire the manifest input through the Makefile (AC-1)
    - Type: impl
    - Covers: AC-1
    - Files: `SystemCode/Makefile`
    - Done when: the `serve-neo4j` target passes the accepted source snapshot manifest path to the serving model; the loader fails closed if the path is absent or malformed.

- [ ] **T-9** Write failing idempotence test (AC-9)
    - Type: test
    - Covers: AC-9
    - Files: `SystemCode/remy/data-preparation/tests/test_serving_model.py`
    - Done when: `test_repeated_accepted_load_is_content_identical` is written and marked `@pytest.mark.integration`; it fails until two loads produce content-identical canonical linking records.

- [ ] **T-10** Implement idempotent load (AC-9)
    - Type: impl
    - Covers: AC-9
    - Files: `SystemCode/remy/data-preparation/models/serving/recipe_graph_to_neo4j.py`
    - Done when: T-9 passes; two accepted loads produce no duplicate relationship identity and identical canonical property values.

- [ ] **T-11** Document the manifest input and fail-closed refresh in the README
    - Type: impl
    - Covers: the spec's User-facing behavior section
    - Files: `SystemCode/remy/data-preparation/README.md`
    - Done when: the README documents the required accepted manifest input, the fail-closed refresh behavior, and how to run `make ci` locally.

- [ ] **T-12** Run focused tests, `sdd.py ci`, and `make ci`
    - Type: verification
    - Covers: AC-1 through AC-10
    - Files: (all above)
    - Done when: `pytest` passes locally (integration tests pass when the cloud instance is configured, or skip locally when not); `pytest -m integration` passes under `CI=true` with the three env vars set; `sdd.py ci p1-002-provenance-graph-model` reports OVERALL PASS; `make ci` runs the dbt singular tests to completion and its output is captured (reviewer nit 4).
