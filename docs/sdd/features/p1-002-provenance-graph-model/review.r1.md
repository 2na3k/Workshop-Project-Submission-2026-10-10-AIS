# Review - Provenance-preserving canonical graph model

Verdict: REVISE

## CI evidence

OVERALL: PASS (`ci-results.md`, run 2026-10-04T22:21:01+08:00)

Review gate: PASS (`sdd.py gate review p1-002-provenance-graph-model`).

The recorded checks report 33 passed tests, lint PASS, and typecheck PASS. The
dbt singular test was not executed because the plan records the p1-001 O-1 seed
blocker; therefore the PASS does not establish the dbt portions of AC-5 and
AC-7.

## Acceptance criteria

| AC | PASS/FAIL | test name or file:line |
|---|---|---|
| AC-1 | PASS | `tests/test_serving_model.py::test_accepted_manifest_loads_canonical_graph` |
| AC-2 | PASS | `tests/test_serving_model.py::test_missing_or_failed_manifest_preserves_graph` |
| AC-3 | PASS | `tests/graph/test_edge_provenance.py::test_requires_provenance_is_preserved` |
| AC-4 | PASS | `tests/graph/test_edge_provenance.py::test_fulfills_provenance_is_preserved` |
| AC-5 | FAIL | `tests/mart_edge_provenance.sql:22-91` references `mapping_version` and `observation_timestamp` for `edge_requires`, while the model contract declares `normalization_version` and `observed_at` (`models/mart/schema.yml:57-82`). In addition, `models/serving/recipe_graph_to_neo4j.py:398-402` fills missing snapshot, observation, and freshness values instead of rejecting a populated link. Route F-1 and F-2 below. |
| AC-6 | PASS | `tests/graph/test_schema_conformance.py::test_only_canonical_property_names_are_emitted` |
| AC-7 | FAIL | `tests/mart_edge_provenance.sql:94-127` is not runnable against the declared `edge_requires` contract because of the mismatched provenance columns above; the serving negative path is covered by `tests/test_serving_model.py::test_failed_allocation_or_integrity_rolls_back`, but the required dbt quality/load evidence is incomplete. Route F-1. |
| AC-8 | PASS | `tests/graph/test_edge_provenance.py::test_write_read_provenance_matches_input` |
| AC-9 | FAIL | `tests/test_serving_model.py::test_repeated_accepted_load_is_content_identical` is marked integration but accepts `fake_driver`, checks only for a second `MERGE`, and does not compare graph records or duplicate counts. This does not prove the specified real-graph content identity. Route F-3. |
| AC-10 | PASS | `tests/test_serving_model.py::test_failed_allocation_or_integrity_rolls_back` |

## Constitution compliance

| Rule | Result | Evidence |
|---|---|---|
| R-1 | PASS | Canonical allowlists and `test_only_canonical_property_names_are_emitted`; legacy `confidence` is rejected. |
| R-2 | PASS | Changes remain in the data-preparation mart/serving boundary; no prohibited backend dependency is introduced. |
| R-3 | PASS | Existing Python/dbt/DuckDB/Neo4j architecture is retained. |
| R-4 | FAIL | The final positive path carries edge provenance, but missing edge provenance is synthesized at `recipe_graph_to_neo4j.py:398-402` rather than rejected, contrary to the edge-level fail-closed requirement. Route F-2 to implement. |
| R-5 | PASS | Not exercised by this feature's changed behavior. |
| R-6 | PASS | Not exercised by this feature's changed behavior. |
| R-7 | PASS | Not exercised by this feature's changed behavior. |
| R-8 | PASS | Not exercised by this feature's changed behavior. |
| R-9 | PASS | Not exercised by this feature's changed behavior. |
| R-10 | PASS | Not exercised by this feature's changed behavior. |
| R-11 | PASS | Not exercised by this feature's changed behavior. |
| R-12 | PASS | Not exercised by this feature's changed behavior. |
| R-13 | PASS | Not exercised by this feature's changed behavior. |
| R-14 | PASS | Not exercised by this feature's changed behavior. |
| R-15 | FAIL | Admission and dangling-reference checks exist, but the dbt quality-gate evidence is incomplete and the singular test is inconsistent with the declared mart schema. Route F-1 to implement. |
| R-16 | PASS | No user-facing response contract is changed by this feature. |
| R-17 | PASS | No recommendation explanation contract is changed by this feature. |

## Plan adherence

The implementation follows the planned in-place canonical loader, manifest
admission, ownership-scoped transaction, and allowlist approach. However, it
deviates from the verification plan: T-12's dbt singular test execution is
deferred, and T-9 specifies a real-Neo4j integration test while the delivered
test uses `fake_driver` and asserts only statement shape. The plan's explicit
deferred seed dependency explains why the dbt evidence is absent, but does not
make the malformed SQL or the weak AC-9 proof acceptable for approval.

## Findings

- [ ] F-1 [BLOCKER] `tests/mart_edge_provenance.sql:22-91` uses `mapping_version` and `observation_timestamp` for `edge_requires`, which are absent from the model output and schema contract (`models/mart/edge_requires.sql:89-90`, `models/mart/schema.yml:57-82`). The required dbt provenance and dangling-reference gate therefore cannot be accepted as implemented. Route: implement.
- [ ] F-2 [MAJOR] `models/serving/recipe_graph_to_neo4j.py:398-402` defaults missing `source_snapshot_id`, `observed_at`, and `freshness_status` from the manifest. AC-5 and R-4 require a populated linking record with missing required provenance to be rejected, not repaired implicitly. Route: implement.
- [ ] F-3 [MAJOR] `tests/test_serving_model.py::test_repeated_accepted_load_is_content_identical` uses `fake_driver` despite the plan's real-Neo4j boundary and does not assert content identity or absence of duplicate relationships. Route: implement.

## Nits (non-blocking)

- The README heading says `AC-15`, but this feature defines AC-1 through AC-10; update the reference when the implementation findings are fixed (`README.md:45`).
