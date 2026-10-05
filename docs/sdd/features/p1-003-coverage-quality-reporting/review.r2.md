# Review - Coverage and quality reporting

Verdict: REVISE

## CI evidence

OVERALL: PASS (`ci-results.md`, run 2026-10-05T14:20:01+08:00; test 50 passed,
lint PASS, typecheck PASS). Independently re-run by this reviewer in WSL:
`uv run --package remy-data-preparation pytest -q remy/data-preparation/tests`
→ `50 passed in 16.05s`. CI is conclusive, so this review proceeds.

Review gate: PASS (`PYTHONUTF8=1 python .sdd/scripts/sdd.py gate review
p1-003-coverage-quality-reporting`).

Note on the gate: run with the native-Windows interpreter, the harness reports
`spec_hash`/`plan_hash`/`tasks_hash` drift. That is an environment artifact, not
drift: `sdd.py` decodes artifacts with the platform default encoding
(`cp1252` on this host) while the recorded hashes were computed as UTF-8. The
artifact bytes are identical to `HEAD`, and under `PYTHONUTF8=1` (or WSL
`python3`) the gate passes. Not a finding against this feature (carry-over of
r1 N-4; harness defect in `.sdd/`).

The dbt singular test (`tests/coverage_quality_report.sql`) compiles but does not
execute; its execution remains deferred under p1-001 O-1, matching how p1-001 and
p1-002 were reviewed.

`python .sdd/scripts/sdd.py check` → `STATE: FAIL` for this feature only:
`stage ci-passed but plan_review_verdict=None` (no `plan-review` artifact). See
F-4.

This round re-reviews the implementation after `review.r1.md` (REVISE). The AC
tests are no longer source-text greps: they now execute the report SQL against a
DuckDB fixture (`test_coverage_quality_report.py:28-62`) and the model fails
closed via `error(...)` (`coverage_quality_report.sql:92-113`).

## Acceptance criteria

| AC | PASS/FAIL | test name or file:line |
|---|---|---|
| AC-1 (one build-associated report, five measures) | FAIL | `test_coverage_quality_report.py::test_build_publishes_exactly_five_dimensions` (`:75`) executes the report and proves exactly five dimensions, but the build association is only present because the fixture *injects* it; a real build emits NULL (F-1). |
| AC-2 (nutrition covered/denominator/percentage) | PASS | `test_nutrition_measure_uses_requirement_denominator` (`:89`) computes `covered=1, denominator=2, percentage=0.5`. |
| AC-3 (price covered/denominator/percentage) | PASS | `test_price_measure_uses_estimated_price_status` (`:96`) computes `covered=1, denominator=2, percentage=0.5`; `unavailable`/blank/null stay uncovered. |
| AC-4 (conversion covered/denominator/percentage) | PASS | `test_conversion_measure_requires_compatible_unit_basis` (`:103`) computes `covered=1, denominator=2` from `cost_basis_compatible`. |
| AC-5 (dietary covered/denominator/percentage) | PASS | `test_dietary_measure_requires_explicit_supported_evidence` (`:109`) computes `covered=1, denominator=2`; `unknown` is uncovered. |
| AC-6 (whole-recipe covered/denominator/percentage) | PASS | `test_whole_recipe_requires_all_four_requirement_dimensions` (`:115`) computes `covered=0, denominator=2`; one uncovered requirement blocks completeness. Recipe-vs-requirement denominator distinctness is not isolated (N-1). |
| AC-7 (nutrition-only ≠ price-covered ≠ whole-recipe) | PASS | `test_nutrition_only_requirement_is_not_price_or_whole_recipe_complete` (`:121`): nutrition `1`, price `0`, whole-recipe `0`. |
| AC-8 (zero population → explicit, no 100%) | PASS | `test_zero_populations_are_explicit_not_100_percent` (`:133`) asserts all five dimensions get `denominator=0`, `percentage=None`, `population_status='no_population'`. |
| AC-9 (five comparison points identical across runs) | PASS | `test_repeated_report_comparison_points_are_content_columns` (`:148`) runs the report twice and compares `covered_count`, `denominator`, `percentage`, `dimension`, `source_snapshot_id`, `mart_content_checksum`. Observation-timestamp determinism is not exercised (F-3). |
| AC-10 (association + bounds vs reproducibility/graph-quality) | FAIL | `test_reproducibility_manifest.py::test_report_matches_source_and_mart_manifest_association` (`:24`) proves the manifest *contract* requires the report and its association columns, but no produced report is compared to the manifest (association unwired, F-1) and the denominator-bound check lives only in the unexecuted dbt test (F-2). |
| AC-11 (invalid inputs fail, no report) | PASS (Python half) / deferred (dbt half) | `test_missing_source_snapshot_publishes_no_report` (`:165`), `test_missing_canonical_mart_publishes_no_report` (`:175`), `test_uncomputable_coverage_report_publishes_no_report` (`:197`) assert both the raise and `not output.exists()`. Model now fails closed via `error(...)` (`coverage_quality_report.sql:92-113`) instead of a row filter. |
| AC-12 (absent evidence → uncovered, distinct gap) | PASS | `test_missing_evidence_is_reported_as_uncovered` (`:213`) asserts price/conversion/dietary uncovered counts are `0` for present-but-unusable evidence and never inferred. Null/blank nutrition and a per-dimension gap count are not parameterised (N-2). |
| AC-13 (exactly five dimensions + named association) | FAIL | Vocabulary passes (`test_build_publishes_exactly_five_dimensions` `:75`), but the association half is only grep-asserted (`test_report_has_exactly_five_dimensions_and_association` `:141`, `field in SQL`) and a real build names NULL (F-1). |

## Constitution compliance

Violations: none.

| Rule | Result | Evidence |
|---|---|---|
| R-1 | PASS | One canonical dimension vocabulary; `accepted_values` on `dimension` rejects alternates (`models/mart/schema.yml:149-159`). |
| R-2 | PASS | Changes stay inside the data-preparation mart/manifest/serving boundary. |
| R-3 | PASS | No new store, framework, or solver; Python/dbt/DuckDB/Neo4j retained. |
| R-4 | PASS | `REQUIRES`/`FULFILLS` provenance is untouched. |
| R-5 | PASS | Executed fixture proves absent/`unavailable`/`unknown` evidence stays uncovered (`test_missing_evidence_is_reported_as_uncovered`, `coverage_quality_report.sql:15-21`). |
| R-6 | PASS | Allergen policy untouched by this feature. |
| R-7 | PASS | Dietary uses the explicit accepted sets (`coverage_quality_report.sql:18-21`); `unknown` is uncovered (fixture `:69-71`, `:213`). |
| R-8 | PASS | Price counts only canonical `estimated` (`coverage_quality_report.sql:16`); `unavailable`/blank/null uncovered. Freshness is not independently asserted (N-3). |
| R-9 | PASS | Missing/incomplete nutrition is uncovered; only `validated` counts (`coverage_quality_report.sql:15`). |
| R-10 | PASS | `cost_basis_compatible` is required for conversion (`coverage_quality_report.sql:17`). |
| R-11, R-12, R-13, R-14, R-16, R-17 | PASS | Out of this feature's scope; no contract changed. |
| R-15 | PARTIAL | The report is generated from accepted marts and refused when metrics are invalid, but its link to the accepted source snapshot/mart checksums is not demonstrable because the association is unwired (F-1). R-15's own named p1-002 quality gate still passes. |

## Plan adherence

Improvements since `review.r1.md`: r1 F-2 (fail-closed) is resolved
(`coverage_quality_report.sql:92-113` uses `error(...)`, not a row filter),
r1 F-3 (behavioral tests) is resolved (DuckDB fixture harness), r1 F-4
(determinism/association) is largely resolved for AC-9, and r1 F-5 is resolved
(`expected_checksums.json` now pins `manifest_schema_version: 2`).

Remaining deviations from the approved plan:

1. **Build association is still unwired.** Design §5 and the plan's
   "Build association and reproducibility" bullet require the report to name
   the accepted source snapshot identity and canonical mart checksum. The model
   reads them from `env_var("REMY_SOURCE_SNAPSHOT_ID" / "REMY_MART_CONTENT_CHECKSUM" /
   "REMY_BUILD_ID")` (`coverage_quality_report.sql:87-89`) but no producer sets
   them (no `.env*` entry, no Makefile target, no manifest step), and the plan's
   "Files to touch" still has no producer entry. This is the root of the
   AC-1/AC-10/AC-13 failures (F-1).
2. **Planned test names were not honored** (substance now present): the
   Test-strategy table names `test_repeated_report_generation_matches_all_fields`
   (AC-9), `test_missing_evidence_is_reported_as_gap` (AC-12), and
   `test_invalid_inputs_publish_no_report` (AC-11). Delivered names differ
   (`:148`, `:213`, `:165`+`:175`+`:197`); the AC-11 Python half is split across
   three tests rather than one.
3. **Extra hardening beyond the plan's file list:** `models/serving/recipe_graph_to_neo4j.py`
   adds a `_relation()` literal-ref helper (`recipe_graph_to_neo4j.py:340-357`),
   and `tests/test_fake_driver_smoke.py`, `tests/test_serving_model.py`, and
   `reproducibility/expected_checksums.json` were touched — none are in the
   plan's "Files to touch". All are justified (parser discovery; the schema-version
   bump the plan's manifest risk required "together") but are undocumented
   deviations.
4. **No `plan-review` artifact** → `sdd.py check` reports `STATE: FAIL` (F-4).

Within-scope and correct: the five-dimension vocabulary, predicate values
(`node_food.sql:39`, `int_price_fulfillment_candidates.sql:43,77`,
`graph_quality_manifest.sql:18-20`), the fail-closed validity guard, the manifest
schema-version bump with the serving-model constant and required-mart set, the
serving `schema.yml` metadata declaration, the README section, the dbt singular
test shape, and the fixture-based Python tests.

## Findings

<!-- - [ ] F-n [BLOCKER|MAJOR] problem (file:line) — route: implement | plan | spec | constitution -->

- [ ] F-1 [BLOCKER] The report's build association is non-functional. `models/mart/coverage_quality_report.sql:87-89` populates `source_snapshot_id`, `mart_content_checksum`, and `build_id` from `env_var("REMY_SOURCE_SNAPSHOT_ID" / "REMY_MART_CONTENT_CHECKSUM" / "REMY_BUILD_ID", "")`; a repository-wide search finds no producer (not the Makefile, not `reproducibility_manifest.py`, no `.env*` entry) and the README gives no instructions to set them. Every accepted build therefore emits NULL association, so AC-1, AC-10, and AC-13 — which require the report to name the source snapshot identity and mart content checksum it measures — cannot pass. Unresolved from r1 F-1. — route: plan (add a task + "Files to touch" entry that supplies the accepted snapshot/checksum to dbt, or derive them from the manifest inside the model). If the intended source is ambiguous, that is a spec question; the plan currently has no step for it. The model change itself is `implement`.
- [ ] F-2 [MINOR] The denominator-bound half of AC-10 and the dbt half of AC-11 are unverified. `tests/coverage_quality_report.sql:30-39` asserts requirement/recipe denominators against `edge_requires`/`node_recipe`, but the singular test does not execute (p1-001 O-1), so no run proves "denominators do not exceed the corresponding canonical populations". — route: implement (execute the dbt test when seeds return) or `plan` (record the O-1 deferral explicitly in T-13's evidence). No code defect.
- [ ] F-3 [MINOR] AC-13's association assertion is still textual. `test_coverage_quality_report.py:141-145` asserts `field in SQL` and `SQL.count(" as dimension") == 1` against the model text rather than the executed row values, and the fixture fixes `{{ run_started_at }}` (`:57`) so observation-timestamp determinism (spec edge case) is not exercised. — route: implement (assert the executed association values; add a differing-timestamp case).
- [ ] F-4 [MINOR] No `plan-review` artifact exists for this feature, so `sdd.py check` reports `STATE: FAIL` (`stage ci-passed but plan_review_verdict=None`) and the `plan_review_verdict`/loop bookkeeping is absent. — route: plan (the plan-review stage owner records the artifact and state, not the reviewer).

## Nits (non-blocking)

- N-1 AC-6's fixture sets `node_recipe = [1, 2]` (`test_coverage_quality_report.py:72`) so the recipe denominator equals the requirement denominator (`2`); a fixture where the two differ would actually prove AC-6's "distinct from the requirement-level denominators".
- N-2 AC-12's fixture candidate resolves `food-1` → `validated` (`:46`), so nutrition is covered and only price/conversion/dietary absence is exercised; nutrition `'missing'`/blank and a per-dimension "distinct gap count" are not parameterised (the plan named `test_missing_evidence_is_reported_as_gap`).
- N-3 The price predicate counts `price_status = 'estimated'` without independently asserting freshness; it currently holds because `edge_fulfills.sql:65` sets `'unavailable'` for null-snapshot/no-offer rows, so `estimated` implies a real offer. Worth an explicit note so a future `estimated`-but-stale producer cannot silently regress coverage (carry-over of r1 N-3).
- N-4 The review-gate hash drift on native Windows is a harness defect in `.sdd/` tooling (`sdd.py` should read artifacts with `encoding="utf-8"`), not a feature defect. Route: n/a (outside the four SDD artifacts).
- N-5 `reproducibility/source_registry.json:2` still declares `"schema_version": 1` while the manifest contract is now version 2; tolerated because `load_source_entries` does not validate the registry version (carry-over of r1 N-1).
- N-6 `tests/test_reproducibility_manifest.py:120-142` and `:282-331` retain large commented-out test bodies; dead test code should be removed or restored with the O-1 dependency recorded (carry-over of r1 N-2).
