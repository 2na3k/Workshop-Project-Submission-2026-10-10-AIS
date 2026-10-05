### D-1 Defer dbt singular test execution pending p1-001 O-1

- Date: 2026-10-05
- Context: `tests/coverage_quality_report.sql` cannot execute because
  `make dbt` fails at the staging layer (missing seeds, p1-001 O-1).
- Decision: The test file exists and its assertions are complete; execution is
  deferred. Same class as p1-001 F-3 and p1-002 T-5.
- Alternatives: Fabricate seeds (rejected); skip the test (rejected — the file
  must exist for AC-10's dbt half).
- Affects: AC-10 (denominator bounds), AC-11 (dbt half), T-15.
- Source: p1-001 decisions O-1.
