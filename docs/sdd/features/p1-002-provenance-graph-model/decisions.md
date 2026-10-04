### D-n Defer dbt singular test execution pending O-1

- Date: 2026-10-04
- Context: T-5's `tests/mart_edge_provenance.sql` cannot execute because
  `make dbt` fails at the staging layer (missing seeds, per p1-001's O-1).
  The test file is written and its assertions are complete; only its
  execution is deferred.
- Decision: Write the test; defer execution. Same class as p1-001's F-3.
- Alternatives: Skip T-5 entirely (rejected — the file must exist for the
  feature to be complete); substitute a Python fixture-based duplicate
  (rejected — duplicates dbt logic, risks drift); block the feature
  (rejected — the rest of the feature is independent of the mart layer).
- Affects: T-5's verification, T-12's evidence, the review's dbt-test row.
- Source: Plan T-5; p1-001 decisions O-1.
