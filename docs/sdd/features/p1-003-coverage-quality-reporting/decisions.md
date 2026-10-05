### D-1 Defer dbt execution and real-mart demonstration pending p1-001 O-1

- Date: 2026-10-05
- Context: `make dbt`, `dbt ls`, and `make ci` all fail at the parse
  stage because `stg_branded_food.sql` depends on a node `branded_food`
  that the missing seeds don't produce (p1-001 O-1). The coverage report's
  own guard is no longer the failure; the parse failure is upstream.
- Decision: The report's SQL is verified against the Python fixture
  (`test_coverage_quality_report.py`, 18 tests). The dbt-level verifications
  are deferred: the singular test execution (T-15), the report's gating
  verification through `dbt ls`, and the real-mart demonstration.
- Alternatives: Stub the seed with a placeholder CSV — rejected (hides
  the O-1 state); skip the report's dbt verification entirely — rejected
  (the deferral must be recorded, not silent).
- Affects: T-15; the review's dbt-test row; the report's end-to-end
  demonstration.
- Source: p1-001 decisions O-1.
