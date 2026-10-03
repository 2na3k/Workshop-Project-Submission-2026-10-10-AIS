## Overrides

### O-1 Defer F-3 pending seed restoration

- Applies to: F-3 from review of 2026-10-03
- Reason: F-3 requires pinning real checksums from an accepted reference build.
  The build cannot run because `seeds/branded_food.csv` (and sibling seed
  files) are absent from the repository and are not recoverable from git
  history. The seeds are a pre-existing dependency of the data-preparation
  pipeline, not a p1-001 artifact. The pipeline has never been built end to
  end in this repository state, and populating the pinned reference requires
  first restoring the seeds — work that is out of scope for p1-001.
- Decision: F-3 deferred. The remaining 10 findings (F-1, F-2, F-4, F-5, F-6,
  F-7, F-8, F-9, F-10, F-11) are resolved in this loop. The `expected_checksums.json`
  file remains empty and `make reproducibility-check` continues to fail with a
  clear "no pinned value" error. That is intentional: the file must not carry
  a fabricated baseline.
- Impact: R-15's gate is not satisfiable end-to-end until the seeds exist.
  `sdd.py ci` passes because its checks (test/lint/typecheck) do not exercise
  `make reproducibility-check`; the p1-001 code is verified as typed, lint-clean,
  and unit-tested, but its end-to-end reproducibility claim is not yet demonstrated.
- Who: <your name>
- When: 2026-10-03
- Follow-up: Restore seeds; run `make dbt DBT_TARGET=nonprod`; pin the resulting
  checksums into `expected_checksums.json`; add the integration tests F-4/F-6/F-7
  that require a real build; re-review and close F-3. Track as a separate work
  item named "restore data-preparation seeds and pin reproducibility reference."
