# Fix — p1-003 loop-back round 2

Fixing the round-2 review findings. Read 
[review.md](../../../docs/sdd/features/p1-003-coverage-quality-reporting/review.r2.md) before starting. Four findings, one blocker.

**F-1 [BLOCKER] — wire the build association.**

`models/mart/coverage_quality_report.sql:87-89` reads `env_var("REMY_SOURCE_SNAPSHOT_ID")`, `env_var("REMY_MART_CONTENT_CHECKSUM")`, and `env_var("REMY_BUILD_ID")`, but nothing sets them. Every real build emits NULL association, so AC-1, AC-10, and AC-13 fail.

Fix, in this order:

1. **First, determine the source of each value.**
    - `source_snapshot_id`: the accepted source snapshot identity. That's a fact in p1-001's manifest (`target/$(DBT_TARGET)/source_snapshot_manifest.json`). The model can't read the file directly in SQL, so the value must come from either a dbt variable set by the Makefile or a macro that opens the manifest.
    - `mart_content_checksum`: the content checksum of the `coverage_quality_report` mart itself, as recorded by the reproducibility manifest. **This is circular** — the manifest computes the report's checksum from the report's content, but the report wants to embed its own checksum. Resolve the circularity: either (a) the checksum field is the *build's* mart checksum (a value that names the build, not the report's own content), or (b) the report does not carry its own checksum and the association is carried externally. Inspect what p1-001's manifest produces and what p1-002's serving model reads; match that convention. If the correct value can't be determined from the manifest structure, **stop and route to `spec`** — the spec's AC-10 says "reference the same accepted source snapshot and canonical mart content," and if that's ambiguous, it's a spec-level question.
    - `build_id`: must be deterministic (AC-9 requires identical reports across runs). Do **not** use the current time. Use a content-derived value: the manifest's own identifier, or a hash of the source snapshot ids. If nothing provides a deterministic build id, use the manifest's `source_snapshot_id` composite or leave the field for the association to compute externally, and note the choice.

2. **Then wire the producer.** Add a Makefile target (or extend an existing one) that reads the manifest, extracts the values, and passes them as env vars to the dbt run that builds the report. `SystemCode/Makefile` is the natural place — it already invokes dbt and already passes `NEO4J_SOURCE_MANIFEST`.

   Because this changes the plan (the plan's Files to touch omitted a producer), the plan must be updated first. Stop and report the plan change needed; do **not** edit `plan.md` yourself. The finding routes to `plan`.

3. **Add the integration test.** The AC-1 test (`test_coverage_quality_report.py:75`) currently injects the association from the fixture. Replace that with a test that reads the association the *model* produces — via the env vars — and asserts the values match the manifest's `source_snapshot_id` and the mart's content checksum. If the fixture injection is the only way to test AC-1 today (because the real producer needs seeds), keep the fixture test **and** add the integration test marked `@pytest.mark.integration`, and note the O-1 dependency in its docstring.

**F-2 [MINOR] — execute the dbt singular test or record the deferral.**

The denominator-bound half of AC-10 and the dbt half of AC-11 live in `tests/coverage_quality_report.sql:30-39`, which can't run until the seeds exist (p1-001 O-1). Two options:

- If the seeds are available in your environment, run `make dbt` and confirm the singular test executes.
- If the seeds are still missing, this is a documented deferral, not a fix. Record it in `../../../docs/sdd/features/p1-003-coverage-quality-reporting/decisions.md` as an O-1 deferral (same pattern as p1-002's T-5), and note in the AC-10/AC-11 test rows that the dbt half is deferred. Do **not** fabricate seed data.

**F-3 [MINOR] — assert executed values, not SQL text.**

`test_coverage_quality_report.py:141-145` (`test_report_has_exactly_five_dimensions_and_association`) asserts `field in SQL` against the model text. Rewrite it to execute the report against the fixture DuckDB and assert the *executed* row values:

- Exactly five distinct `dimension` values in the output, matching the canonical set.
- The association fields (`source_snapshot_id`, `mart_content_checksum`) present in every row and equal to the fixture-supplied values.
- No other `dimension` values.

Additionally, the fixture currently fixes `{{ run_started_at }}` (`:57`), so observation-timestamp determinism isn't exercised. Add a case where two runs against the same fixture but with different `run_started_at` produce identical report content (the observation-timestamp is provenance, not content; AC-9 requires the *content* to match).

**F-4 [MINOR] — record the plan-review artifact and state.**

`python .sdd/scripts/sdd.py check` reports `STATE: FAIL` for this feature: `stage ci-passed but plan_review_verdict=None`. The plan was approved, but the approval was never written into `state.json` and no `plan-review.md` exists in the feature directory.

This is bookkeeping, and it routes to the plan-review stage owner (not the implementer). But since you're in the loop-back, do the mechanical part:

- If `plan-review.md` exists elsewhere or was never written, note that the plan was approved (the plan review's verdict is a fact from the earlier session). Write a minimal `plan-review.md` capturing the original APPROVE (or note its absence and the plan's approval provenance) — **do not fabricate** a review that didn't happen. If you don't have the original review content, leave `plan-review.md` absent and report that the artifact is missing; the plan-review stage owner records it, not you.
- Add `"plan_review_verdict": "APPROVE"` to `state.json` if it's genuinely absent and the plan was approved. If you're unsure, stop and report — do not guess.

**Two carry-over nits, do them while the file is open:**

- **N-1** — `tests/test_coverage_quality_report.py:72` sets `node_recipe = [1, 2]` so the recipe denominator equals the requirement denominator. Change the fixture so the two denominators *differ* (e.g., 3 requirements across 2 recipes, or 2 requirements in 1 recipe and a second recipe with 0 requirements), and assert the distinct recipe denominator. This actually proves AC-6's "distinct from the requirement-level denominators."

- **N-2** — `tests/test_coverage_quality_report.py:46` has the fixture candidate resolve `food-1` → `validated`, so nutrition is always covered and only price/conversion/dietary are exercised for absence. Parameterize the fixture so nutrition `'missing'`/blank is also tested, and add a per-dimension distinct gap count assertion.

**Do not:**

- Edit `spec.md`, `plan.md` (beyond checkbox state), `constitution.md`, or any review artifact.
- Change task text, add tasks, or reword the plan.
- Weaken or delete tests to get green.
- Fabricate seeds, checksums, or a plan-review artifact.
- Introduce new dependencies.

**Stop and report if:**

- F-1's association source is ambiguous (route to `spec`).
- F-1 requires a plan change (route to `plan`).
- F-4's plan-review artifact can't be honestly reconstructed (route to the plan-review stage owner).
- The seeds are missing and the dbt singular test can't execute (document the O-1 deferral; don't fix).

**Evidence when done:**

- Full test suite count (`uv run --package remy-data-preparation pytest -q remy/data-preparation/tests`).
- `sdd.py ci p1-003-coverage-quality-reporting` result.
- Which findings resolved, which deferred (with the deferral reason).
- Any new findings discovered during the work.
