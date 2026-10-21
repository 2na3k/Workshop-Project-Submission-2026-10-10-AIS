# Review - Provenance-preserving canonical graph model

Verdict: APPROVE

## CI evidence

OVERALL: PASS (`ci-results.md`, run 2026-10-04T23:43:18+08:00).

Review gate: PASS (`sdd.py gate review p1-002-provenance-graph-model`).

The recorded checks report 34 passed tests, lint PASS, and typecheck PASS. The
dbt singular test compiles and its execution remains deferred by the documented
p1-001 O-1 seed dependency.

## Acceptance criteria

| AC | PASS/FAIL | test name or file:line |
|---|---|---|
| AC-1 | PASS | `tests/test_serving_model.py::test_accepted_manifest_loads_canonical_graph` |
| AC-2 | PASS | `tests/test_serving_model.py::test_missing_or_failed_manifest_preserves_graph` |
| AC-3 | PASS | `tests/graph/test_edge_provenance.py::test_requires_provenance_is_preserved` |
| AC-4 | PASS | `tests/graph/test_edge_provenance.py::test_fulfills_provenance_is_preserved` |
| AC-5 | PASS | `tests/graph/test_edge_provenance.py::test_missing_provenance_fails` and `test_populated_link_with_missing_provenance_is_rejected`; dbt contract: `tests/mart_edge_provenance.sql:22-92` |
| AC-6 | PASS | `tests/graph/test_schema_conformance.py::test_only_canonical_property_names_are_emitted` |
| AC-7 | PASS | `tests/test_serving_model.py::test_failed_allocation_or_integrity_rolls_back`; dbt dangling-reference contract: `tests/mart_edge_provenance.sql:94-127` |
| AC-8 | PASS | `tests/graph/test_edge_provenance.py::test_write_read_provenance_matches_input` |
| AC-9 | PASS | `tests/graph/test_idempotence.py::test_repeated_accepted_load_is_content_identical` verifies one relationship identity after two real-Neo4j loads |
| AC-10 | PASS | `tests/test_serving_model.py::test_failed_allocation_or_integrity_rolls_back` |

## Constitution compliance

| Rule | Result | Evidence |
|---|---|---|
| R-1 | PASS | Canonical allowlists reject legacy aliases in `test_schema_conformance.py`. |
| R-2 | PASS | Changes remain within the data-preparation mart/serving boundary. |
| R-3 | PASS | Existing Python/dbt/DuckDB/Neo4j architecture is retained. |
| R-4 | PASS | Real graph provenance tests verify `REQUIRES` and `FULFILLS`; missing values are rejected by `_assert_edge_provenance`. |
| R-5 | PASS | No behavior covered by this feature weakens absent-evidence handling. |
| R-6 | PASS | No behavior covered by this feature changes allergen handling. |
| R-7 | PASS | No behavior covered by this feature changes dietary handling. |
| R-8 | PASS | No behavior covered by this feature changes offer freshness rules. |
| R-9 | PASS | No behavior covered by this feature changes nutrition-profile rules. |
| R-10 | PASS | No behavior covered by this feature changes unit-basis cost rules. |
| R-11 | PASS | No behavior covered by this feature changes cost output fields. |
| R-12 | PASS | No behavior covered by this feature changes nutrient precedence. |
| R-13 | PASS | No behavior covered by this feature changes mapping selection policy. |
| R-14 | PASS | No behavior covered by this feature changes plan feasibility. |
| R-15 | PASS | Admission, quality-count, endpoint, and provenance gates are implemented; dbt execution is deferred only by the documented upstream seed dependency. |
| R-16 | PASS | No user-facing response contract is changed. |
| R-17 | PASS | No explanation contract is changed. |

## Plan adherence

The implementation follows the approved plan: canonical edge vocabulary,
fail-closed manifest admission, atomic ownership-scoped refresh, endpoint and
provenance validation, schema conformance, and real-Neo4j idempotence proof.
F-1, F-2, F-3, and the README AC-reference nit are resolved. The only deferred
verification is dbt execution, which is explicitly attributed to p1-001 O-1 in
the plan and is not an implementation deviation.

## Findings

None.

## Nits (non-blocking)

None. The README acceptance-reference heading now uses AC-1 through AC-10.
