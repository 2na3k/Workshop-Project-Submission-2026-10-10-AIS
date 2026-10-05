# Review - Coverage and quality reporting

Verdict: REVISE

## CI evidence

OVERALL: PASS (`ci-results.md`, run 2026-10-05T11:31:19+08:00; test 49 passed,
lint PASS, typecheck PASS). Independently re-run in WSL:
`uv run --package remy-data-preparation pytest -q remy/data-preparation/tests`
→ `49 passed`. CI is conclusive, so this review proceeds.

Review gate: PASS (`python3 .sdd/scripts/sdd.py gate review
p1-003-coverage-quality-reporting`).

Note on the gate: running the harness with the native-Windows interpreter
(`python .sdd/scripts/sdd.py gate review …`) reports `spec_hash`/`plan_hash`/
`tasks_hash` drift. That is an environment artifact, not drift: `sdd.py` reads
artifacts with `Path.read_text()` (no explicit encoding), which decodes the
UTF-8 files as `cp1252` on this host (`locale.getpreferredencoding()` =
`cp1252`), while the recorded hashes were computed as UTF-8. The artifact bytes
are identical to `HEAD`, and under `PYTHONUTF8=1` or WSL `python3` the gate
passes. Not a finding against this feature.

The dbt singular test (`tests/coverage_quality_report.sql`) compiles but does not
execute; its execution remains deferred under p1-001 O-1. This review treats the
dbt half of AC-11 as deferred, matching how p1-001 and p1-002 were reviewed.

## Acceptance criteria

| AC | PASS/FAIL | test name or file:line |
|---|---|---|
| AC-1 (one build-associated report, five measures) | FAIL | `test_coverage_quality_report.py::test_build_publishes_exactly_five_dimensions` only counts the five string literals in the `.sql` text; the build association it must carry is NULL (see F-1). |
| AC-2 (nutrition covered/denominator/percentage) | FAIL | Only `test_nutrition_measure_uses_requirement_denominator` (`test_coverage_quality_report.py:35`) — a substring grep; no fixture computes a covered count/denominator/percentage. |
| AC-3 (price covered/denominator/percentage) | FAIL | `test_price_measure_uses_estimated_price_status` (`:41`) — substring grep only; no computed measurement. |
| AC-4 (conversion covered/denominator/percentage) | FAIL | `test_conversion_measure_requires_compatible_unit_basis` (`:46`) — substring grep only. |
| AC-5 (dietary covered/denominator/percentage) | FAIL | `test_dietary_measure_requires_explicit_supported_evidence` (`:51`) — substring grep only. |
| AC-6 (whole-recipe covered/denominator/percentage) | FAIL | `test_whole_recipe_requires_all_four_requirement_dimensions` (`:57`) — substring grep only; no recipe-level aggregation is executed. |
| AC-7 (nutrition-only ≠ price-covered ≠ whole-recipe) | FAIL | `test_nutrition_only_requirement_is_not_price_or_whole_recipe_complete` (`:66`) asserts `"price_covered, false" not in SQL`, a tautology; the required nutrition-present/price-absent fixture is not constructed. |
| AC-8 (zero population → explicit, no 100%) | FAIL | `test_zero_populations_are_explicit_not_100_percent` (`:72`) greps `case when denominator = 0 then null`; no zero-population fixture is evaluated for all five dimensions. |
| AC-9 (five comparison points identical across runs) | FAIL | `test_repeated_report_comparison_points_are_content_columns` (`:85`) only checks field names appear in the `.sql`; no two runs are compared. |
| AC-10 (association + bounds vs reproducibility/graph-quality) | FAIL | `test_reproducibility_manifest.py::test_report_matches_source_and_mart_manifest_association` (`:24`) asserts constant membership only; the report is never tied to a manifest, and contents are never bounded. The `edge_requires`/`node_recipe` denominator bounds live only in the unexecuted dbt test. |
| AC-11 (invalid inputs fail, no report) | PASS (Python half) / deferred (dbt half) | `test_missing_source_snapshot_publishes_no_report`, `test_missing_canonical_mart_publishes_no_report`, `test_uncomputable_coverage_report_publishes_no_report` (`:98`, `:108`, `:130`) genuinely assert a raise **and** `not output.exists()`. |
| AC-12 (absent evidence → uncovered, distinct gap) | FAIL | `test_missing_evidence_is_reported_as_uncovered` (`:146`) greps `coalesce(...)` substrings; no fixture asserts distinct uncovered counts or that no inference occurs. |
| AC-13 (exactly five dimensions + named association) | FAIL | The dimension vocabulary is correct (`models/mart/schema.yml:142-159`, `tests/coverage_quality_report.sql:1-7`), but the association must "name the source snapshot identity and mart content checksum it measures" and those columns are NULL (see F-1). |

## Constitution compliance

Violations: none.

| Rule | Result | Evidence |
|---|---|---|
| R-1 | PASS | One canonical dimension vocabulary; `accepted_values` on `dimension` rejects alternates (`models/mart/schema.yml:149-159`). |
| R-2 | PASS | Changes stay inside the data-preparation mart/manifest/serving boundary. |
| R-3 | PASS | No new store, framework, or solver; Python/dbt/DuckDB/Neo4j retained. |
| R-4 | PASS | `REQUIRES`/`FULFILLS` provenance is untouched. |
| R-5 | PARTIAL | `coalesce(nf.nutrition_status,'missing') = 'validated'` and `coalesce(f.price_status,'unavailable') = 'estimated'` express "absent drops", but the behavior is not verified (F-3). |
| R-6 | PASS | Allergen policy untouched by this feature. |
| R-7 | PARTIAL | Dietary uses explicit accepted sets (`coverage_quality_report.sql:18-21`); behavior unverified. |
| R-8 | PARTIAL | Price uses canonical `estimated`; freshness is not independently checked (nit N-3). |
| R-9 | PARTIAL | Missing nutrition profile is uncovered by predicate; behavior unverified. |
| R-10 | PARTIAL | `cost_basis_compatible` is required; behavior unverified. |
| R-11, R-12, R-13, R-14, R-16, R-17 | PASS | Out of this feature's scope; no contract changed. |
| R-15 | PARTIAL | The report is not demonstrably linked to the accepted source snapshot/mart checksums, and its validity guard is not fail-closed (F-1, F-2, F-5). R-15's own named check (p1-002 entity counts + dangling `REQUIRES`/`FULFILLS` gate) still passes. |

## Plan adherence

Deviations from the approved plan:

1. **"Controlled fixture population" was not built.** Plan Design §7 and Tasks
   T-2/T-3/T-7/T-9 require fixtures that *compute* covered count, denominator,
   and percentage per dimension. The delivered tests read the model's `.sql`
   text and assert substrings; no dimension is ever calculated. This is the root
   cause of the AC-2…AC-10, AC-12 failures above.
2. **Planned test names/locations were not honored.** The Test-strategy table
   names `test_repeated_report_generation_matches_all_fields` (AC-9),
   `test_missing_evidence_is_reported_as_gap` (AC-12), and
   `test_invalid_inputs_publish_no_report` (AC-11). None exist; the substitutes
   assert far less.
3. **Validity is not fail-closed.** Plan Design §4 / README ("The build fails
   closed … if the report is internally inconsistent") is implemented as a
   `WHERE` filter that *drops* invalid rows (`coverage_quality_report.sql:93-98`)
   rather than failing the build.
4. **Build association is unwired and unproduced.** Design §5 requires the report
   to name the accepted source snapshot identity and canonical mart checksums;
   the model reads them from env vars that nothing produces (F-1). The plan's
   "Files to touch" omits any producer, so the gap is also a plan gap.
5. **`expected_checksums.json` was not updated** to the incremented manifest
   schema version (F-5), which the plan's manifest-contract risk required to be
   changed "together".
6. **No plan-review artifact exists** in the feature directory, so
   `sdd.py check` reports `stage ci-passed but plan_review_verdict=None`.

Within-scope and correct: the dimension vocabulary, the predicate values
(matching `node_food.sql:39`, `int_price_fulfillment_candidates.sql:43,77`,
`graph_quality_manifest.sql:18-20`), the manifest schema-version bump with the
serving-model constant and required-mart set, the serving `schema.yml` metadata
declaration, the README section, and the Python fail-closed tests for AC-11.

## Findings

<!-- - [ ] F-n [BLOCKER|MAJOR] problem (file:line) — route: implement | plan | spec | constitution -->

- [ ] F-1 [BLOCKER] The report's build association is non-functional. `models/mart/coverage_quality_report.sql:87-89` populates `source_snapshot_id`, `mart_content_checksum`, and `build_id` from `env_var("REMY_SOURCE_SNAPSHOT_ID" / "REMY_MART_CONTENT_CHECKSUM" / "REMY_BUILD_ID", "")`; `git grep` shows no producer anywhere (not the Makefile, not `reproducibility_manifest.py`), and README gives no instructions to set them. Every accepted build therefore emits NULL association, so AC-1, AC-10, and AC-13 ("the report's build association names the source snapshot identity and mart content checksum it measures") cannot pass. — route: plan (add a task + "Files to touch" entry that passes the accepted snapshot/checksum into dbt, or derive them from the manifest inside the model). If interpretation is at issue, it is a spec question, but the plan currently has no step for it.
- [ ] F-2 [BLOCKER] Invalid or inconsistent metrics are silently dropped, not failed. `models/mart/coverage_quality_report.sql:93-98` ends with `select * from associated where covered_count >= 0 and denominator >= 0 and covered_count <= denominator and (percentage is null or …)`. A duplicate, out-of-range, or missing dimension is filtered out, so the build still succeeds while publishing fewer than five dimensions — the opposite of the planned/README'd "fails closed if the report is internally inconsistent" and of AC-11's "fails non-zero and publishes no accepted report". — route: implement (make the model fail closed; the dbt singular test already detects the symptom but does not run in CI, so it is not a substitute).
- [ ] F-3 [MAJOR] The AC tests are source-code introspection, not behavior. `tests/test_coverage_quality_report.py` reads the `.sql` text once (`SQL = MODEL.read_text(...)`, `:14-15`) and asserts substrings throughout (`:26-95`, `:146-151`). No test executes the report SQL against a fixture warehouse or computes any count/denominator/percentage, so AC-2…AC-10 and AC-12, and R-5/R-7's behavioral checks, are not proven. The approved plan explicitly required fixture-based calculation. — route: implement (add executing, fixture-based tests).
- [ ] F-4 [MAJOR] AC-9/AC-10/AC-13 verification is circular. `test_repeated_report_comparison_points_are_content_columns` (`:85-95`) only checks field names are present and never compares two runs; `test_report_matches_source_and_mart_manifest_association` (`tests/test_reproducibility_manifest.py:24-29`) only asserts constant membership in `REQUIRED_MARTS`/`MART_CONTENT_COLUMNS`. Neither ties a report to a manifest or repeats a run. — route: implement.
- [ ] F-5 [MAJOR] Stale pinned schema version breaks the reproducibility checker once it can run. `reproducibility/expected_checksums.json:1` still pins `"manifest_schema_version": 1` while `reproducibility_manifest.py:37` sets `MANIFEST_SCHEMA_VERSION = 2`; `scripts/check_reproducibility.py:28-31` fails when the two differ, so `make reproducibility-check` (and thus `make ci`) will fail on the first real build. The plan's manifest-contract risk required these to be updated together. — route: implement (bump the pinned `manifest_schema_version` to 2; the `marts` map stays empty until O-1 seeds are restored).

## Nits (non-blocking)

- N-1 `reproducibility/source_registry.json:2` is `"schema_version": 1` while `test_reproducibility_manifest.py:59` writes `2` and the manifest contract is now version 2. Tolerated because `load_source_entries` does not validate the registry version, but it is an inconsistency.
- N-2 `tests/test_reproducibility_manifest.py:103-124` and `:265-314` contain large commented-out test bodies (including the real-DB AC tests). Dead test code in the delivered artifact should be removed or restored with the O-1 dependency recorded.
- N-3 The price predicate uses `price_status = 'estimated'` and does not independently assert freshness, whereas spec AC-3/edge cases say stale offers must not count as available. It happens to hold because the marts set `freshness_status = 'unknown'` on `estimated` rows; worth an explicit note so a future `estimated`-but-stale producer cannot regress coverage silently.
- N-4 The review-gate hash failure on native Windows is a harness defect, not a feature defect: `sdd.py` (`digest`, `Path.read_text`) should read artifacts with `encoding="utf-8"` (or callers should set `PYTHONUTF8=1`). Route: n/a (`.sdd/` kit tooling, outside the four SDD artifacts).
