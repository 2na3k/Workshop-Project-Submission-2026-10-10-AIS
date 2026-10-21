# Review - Coverage and quality reporting

Verdict: REVISE

## CI evidence

OVERALL: PASS (`ci-results.md`, run 2026-10-05T15:15:08+08:00; test 51 passed,
lint PASS, typecheck PASS). Independently re-run by this reviewer in WSL:
`uv run --package remy-data-preparation pytest -q remy/data-preparation/tests`
→ `51 passed in 10.67s`. CI is conclusive, so this review proceeds.

Review gate: PASS (`PYTHONUTF8=1 python .sdd/scripts/sdd.py gate review
p1-003-coverage-quality-reporting`).

Note on the gate: with the native-Windows interpreter the harness reports
`spec_hash`/`plan_hash`/`tasks_hash` drift. That is an environment artifact, not
drift: `sdd.py` decodes artifacts with the platform default encoding (`cp1252`
on this host) while the recorded hashes were computed as UTF-8. The artifact
bytes are identical to `HEAD`, and under `PYTHONUTF8=1` (or WSL `python3`) the
gate passes. Not a finding against this feature (carry-over of r2 N-4; harness
defect in `.sdd/`).

The dbt singular test (`tests/coverage_quality_report.sql`) compiles but does not
execute; its execution remains deferred under p1-001 O-1, matching how p1-001 and
p1-002 were reviewed.

This is round 3, re-reviewing the implementation after `review.r1.md` and
`review.r2.md` (both REVISE). Prior rounds are retained as `review.r1.md`/
`review.r2.md`; this round is `review.r3.md` (the p1-002 convention).

## Acceptance criteria

| AC | PASS/FAIL | test name or file:line |
|---|---|---|
| AC-1 (one build-associated report, five measures) | FAIL | `test_build_publishes_exactly_five_dimensions` (`test_coverage_quality_report.py:75`) executes `_run_report([], [], [])` — all fixture tables empty — and the association is the harness-injected `snapshot-1`/`mart-1`/`build-1`, not a manifest-derived value. Neither the "accepted build" association nor the manifest-derived association is proven (F-1). |
| AC-2 (nutrition covered/denominator/percentage) | PASS | `test_nutrition_measure_uses_requirement_denominator` (`:89`) computes `covered=1, denominator=2, percentage=0.5`. |
| AC-3 (price covered/denominator/percentage) | PASS | `test_price_measure_uses_estimated_price_status` (`:96`) computes `covered=1, denominator=2, percentage=0.5`; `unavailable`/blank/null stay uncovered. |
| AC-4 (conversion covered/denominator/percentage) | PASS | `test_conversion_measure_requires_compatible_unit_basis` (`:103`) computes `covered=1, denominator=2` from `cost_basis_compatible`. |
| AC-5 (dietary covered/denominator/percentage) | PASS | `test_dietary_measure_requires_explicit_supported_evidence` (`:109`) computes `covered=1, denominator=2`; `unknown` is uncovered. |
| AC-6 (whole-recipe covered/denominator/percentage) | PASS | `test_whole_recipe_denominator_is_distinct_from_requirement_denominator` (`:115`) proves the recipe denominator (`2` recipes) differs from the requirement denominator (`3` requirements). r2 N-1 resolved. |
| AC-7 (nutrition-only ≠ price-covered ≠ whole-recipe) | PASS | `test_nutrition_only_requirement_is_not_price_or_whole_recipe_complete` (`:131`): nutrition `1`, price `0`, whole-recipe `0`. |
| AC-8 (zero population → explicit, no 100%) | PASS | `test_zero_populations_are_explicit_not_100_percent` (`:143`) asserts all five dimensions get `denominator=0`, `percentage=None`, `population_status='no_population'`. |
| AC-9 (five comparison points identical across runs) | PASS | `test_repeated_report_comparison_points_are_content_columns` (`:167`) compares `covered_count`, `denominator`, `percentage`, `dimension`, `source_snapshot_id`, `mart_content_checksum`; the observation-timestamp edge is exercised by `test_report_content_is_stable_across_observation_timestamps` (`:183`). Nit: the timestamp comparison set omits `build_id` (N-1). |
| AC-10 (association + bounds vs reproducibility/graph-quality) | FAIL | `test_reproducibility_manifest.py::test_report_matches_source_and_mart_manifest_association` (`:24`) proves only contract membership (`REQUIRED_MARTS`/`MART_CONTENT_COLUMNS`); no produced report is compared to the manifest's `association` block, and the denominator-bound check lives only in the unexecuted dbt test (F-1, F-2). |
| AC-11 (invalid inputs fail, no report) | PASS (Python half) / deferred (dbt half) | `test_missing_source_snapshot_publishes_no_report` (`:205`), `test_missing_canonical_mart_publishes_no_report` (`:215`), `test_uncomputable_coverage_report_publishes_no_report` (`:237`) assert both the raise and `not output.exists()`. The model now fails closed via `error(...)` (`coverage_quality_report.sql:92-117`), so r2 F-2 is resolved. The dbt half is deferred (F-2). |
| AC-12 (absent evidence → uncovered, distinct gap) | PASS | `test_missing_evidence_is_reported_as_uncovered` (`:253`) asserts price/conversion/dietary uncovered counts are `0` for present-but-unusable evidence and never inferred. Nit: nutrition `'missing'`/blank is not parameterised (N-2; T-19 not started). |
| AC-13 (exactly five dimensions + named association) | FAIL | Vocabulary passes (`test_report_has_exactly_five_dimensions_and_association` `:151` executes the report, asserts the five dimension identities, and checks the association fields on every row — r2 F-3 resolved), but the association values are fixture-injected rather than manifest-derived (F-1). |

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
| R-7 | PASS | Dietary uses the explicit accepted sets (`coverage_quality_report.sql:18-21`); `unknown` is uncovered (fixture `:253`). |
| R-8 | PASS | Price counts only canonical `estimated` (`coverage_quality_report.sql:16`); `unavailable`/blank/null uncovered. Freshness is not independently asserted (N-3). |
| R-9 | PASS | Missing/incomplete nutrition is uncovered; only `validated` counts (`coverage_quality_report.sql:15`). |
| R-10 | PASS | `cost_basis_compatible` is required for conversion (`coverage_quality_report.sql:17`). |
| R-11, R-12, R-13, R-14, R-16, R-17 | PASS | Out of this feature's scope; no contract changed. |
| R-15 | PARTIAL | The report is generated from accepted marts and refused when metrics are invalid, but its link to the accepted source snapshot/mart checksums is still not demonstrable: the report's association is fixture-injected, no test compares it to the manifest, and the model does not fail closed when the association is unverifiable (F-1). R-15's own named p1-002 quality gate still passes. |

## Plan adherence

Resolved since `review.r2.md`: r2 F-2 (fail-closed) is resolved
(`coverage_quality_report.sql:92-117` uses `error(...)`), r2 F-3 (executed
association assertion) is resolved (`:151`), r2 F-4 is recorded
(`state.json` `plan_review_verdict=APPROVE`; `sdd.py check` → `STATE: PASS`),
r2 N-1 is resolved (`:115`), and r2 F-1's *wiring* gap is addressed
(`Makefile:66-71` `coverage-report`; `reproducibility_manifest.py:407-428`
`association`).

Remaining deviations from the revised plan (T-14..T-19):

1. **The revised plan's implementation landed inside the plan-revision commit
   and is unrecorded.** `e49a9af` ("plan revision T-14..T-19; plan-review
   artifact; state fix") also modified `SystemCode/Makefile`,
   `scripts/reproducibility_manifest.py`, and
   `tests/test_coverage_quality_report.py` — the T-14 producer, the manifest
   `association` block, and the T-16/T-17/T-18 tests — yet T-14..T-19 all remain
   unchecked, and `prompts/features/p1-003-coverage-quality-reporting/fix.md`
   and the commit message are written as if only the plan changed. Code and task
   state disagree (F-3).
2. **The manifest association is produced but not compared.** The plan's
   Test-strategy row for AC-10 names
   `test_report_matches_source_and_mart_manifest_association` and its "Files to
   touch" require `test_reproducibility_manifest.py` to "extend required-mart
   and repeated-build assertions to include the report and its
   association/checksum fields". The delivered test asserts constant membership
   only; no test reads the manifest's `association` values and compares them to
   a report row (F-1).
3. **The dbt deferral is recorded at the wrong path.** T-15 names
   `docs/sdd/features/p1-003-coverage-quality-reporting/decisions.md` as the
   evidence artifact; the O-1 deferral was written to
   `decisions.md`, and the
   artifact the plan declares does not exist (F-2).
4. **T-14..T-19 are not delivered as written.** T-14's stated laws (non-null
   association after a fixture-backed run; a Python test that "executes the
   report with the env vars set and asserts the association equals the
   manifest's values") are not met; T-19 is not started (N-2).

Within-scope and correct: the five-dimension vocabulary, predicate values
(`node_food.sql:39`, `int_price_fulfillment_candidates.sql:43,77`,
`graph_quality_manifest.sql:18-20`), the fail-closed validity guard, the
manifest schema-version bump with the serving-model constant and required-mart
set, the deterministic `build_id`, the serving `schema.yml` metadata
declaration, the README section, the dbt singular test shape, and the
fixture-based Python tests.

## Findings

<!-- - [ ] F-n [BLOCKER|MAJOR] problem (file:line) — route: implement | plan | spec | constitution -->

- [ ] F-1 [BLOCKER] The build association is produced but never verified, and the model does not fail closed on it. The producer now exists (`Makefile:66-71` passes `REMY_SOURCE_SNAPSHOT_ID`/`REMY_MART_CONTENT_CHECKSUM`/`REMY_BUILD_ID` from the manifest's `association` block; `reproducibility_manifest.py:407-428` computes them), but no test asserts them: a repository-wide search finds `association` only in the manifest producer, the Makefile consumer, and `.pytest_cache` (no test). `test_build_publishes_exactly_five_dimensions` (`test_coverage_quality_report.py:75`) runs with all tables empty and reused injected env values, and `test_report_has_exactly_five_dimensions_and_association` (`:151`) asserts the harness-injected `snapshot-1`/`mart-1`/`build-1`. Consequently AC-1's "accepted build" association, AC-10's manifest comparison, and AC-13's "names the source snapshot identity and mart content checksum it measures" remain unproven. In addition `coverage_quality_report.sql:87-89` still emits `nullif('{{ env_var(...) }}', '')`, so an unset/blank env publishes an all-NULL association silently — contrary to the spec edge case "source snapshot identity or mart content changes between metric computation and report publication: reject the report" (`spec.md:170-172`) and AC-11. — route: implement (assert the producer's values end-to-end in a test, and make the model fail closed when the association cannot be verified). The wiring plan change from r2 F-1 is closed; this residue is implementation, not plan.

- [ ] F-2 [MINOR] The denominator-bound half of AC-10 and the dbt half of AC-11 are unverified, and the deferral is recorded at the wrong path. `tests/coverage_quality_report.sql:30-39` asserts requirement/recipe denominators against `edge_requires`/`node_recipe`, but the singular test does not execute (p1-001 O-1). T-15 requires the deferral in `docs/sdd/features/p1-003-coverage-quality-reporting/decisions.md`; that file does not exist — the deferral was written to `prompts/features/p1-003-coverage-quality-reporting/decisions.md:1` (D-1), so the plan-declared evidence artifact is missing (both closed features, p1-001 and p1-002, carry one at the `docs/` path). — route: implement (record D-1 at the path T-15 names). No code defect.

- [ ] F-3 [MAJOR] The revised plan's implementation landed inside the plan-revision commit and contradicts its own evidence. `e49a9af` modified `SystemCode/Makefile` (T-14 producer), `scripts/reproducibility_manifest.py:407-428` (`association`), and `tests/test_coverage_quality_report.py:115-128`/`:151-164`/`:183-203` (T-16/T-17/T-18), yet T-14..T-19 are all unchecked, and `prompts/features/p1-003-coverage-quality-reporting/fix.md` plus the commit message describe the association producer as a *needed* fix while the plan's Revision note F-8 claims "round-1 F-1 routed to plan; this revision closes it". Code and task state therefore disagree, and r2 F-3/N-1 appear resolved without a recorded implement cycle. — route: implement (tick T-14/T-16/T-17/T-18 with evidence, or revert the code to the recorded state; do not leave the tasks and the code disagreeing). If the landing sequence is a process concern, that is a constitution/AGENTS question, but the artifact-level repair is implement.

- [ ] F-4 [MINOR] `SystemCode/Makefile` now defines duplicated and malformed targets. `ci: reproducible-build check` appears twice (`:81` and `:120`), `check:` twice (`:45` and `:122`), and the `.PHONY` list has a stray backslash continuation (`:14-16`: `... reproducible-build coverage-report ci \` then a second physical line), so the phony list is split across a continuation and a fresh line. Duplicate recipe targets are a Make warning and make the CI entry point ambiguous. — route: implement (remove the duplicates; fix the `.PHONY` continuation).

## Nits (non-blocking)

- N-1 AC-9's executed comparison omits `build_id`: `test_repeated_report_comparison_points_are_content_columns` (`:167`) and the timestamp test (`:183`) compare `source_snapshot_id` and `mart_content_checksum` but not `build_id`. The plan's AC-9 row lists the same six fields, so this matches the plan; the third association field is nevertheless untested (overlaps F-1).
- N-2 AC-12's fixture candidate resolves `food-1` → `validated` (`:46`), so nutrition is covered and only price/conversion/dietary absence is exercised; nutrition `'missing'`/blank and a per-dimension "distinct gap count" are not parameterised. T-19 is not started (carry-over of r2 N-2).
- N-3 The price predicate counts `price_status = 'estimated'` without independently asserting freshness; it currently holds because `edge_fulfills.sql:65` sets `'unavailable'` for null-snapshot/no-offer rows, so `estimated` implies a real offer. Worth an explicit note so a future `estimated`-but-stale producer cannot silently regress coverage (carry-over of r1 N-3 / r2 N-3).
- N-4 `reproducibility/source_registry.json:2` still declares `"schema_version": 1` while the manifest contract is now version 2; tolerated because `load_source_entries` does not validate the registry version (carry-over of r2 N-5).
- N-5 `tests/test_reproducibility_manifest.py:120-142` and `:282-331` retain large commented-out test bodies; dead test code should be removed or restored with the O-1 dependency recorded (carry-over of r2 N-6).
- N-6 The review-gate hash drift on native Windows is a harness defect in `.sdd/` tooling (`sdd.py` should read artifacts with `encoding="utf-8"`), not a feature defect. Route: n/a (outside the four SDD artifacts; carry-over of r2 N-4).
- N-7 The plan lists `SystemCode/Makefile` twice in "Files to touch" (`plan.md:129` and `:131-133`), which keeps `sdd.py collision p1` reporting a HIGH collision. Tidy the duplicate entry at the next plan revision (the artifact it owns).
