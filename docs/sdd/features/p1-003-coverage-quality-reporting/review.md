# Review - Coverage and quality reporting

Verdict: APPROVE

## CI evidence

OVERALL: PASS (`ci-results.md`, run 2026-10-05T16:25:24+08:00; test 53 passed, lint PASS, typecheck PASS).
Independently re-run by reviewer in WSL:
- `uv run --package remy-data-preparation pytest -q remy/data-preparation/tests` → `53 passed in 13.35s`
- `uv run --package remy-data-preparation ruff check remy/data-preparation --select F,E9` → `All checks passed!`
- `uv run --package remy-data-preparation mypy remy/data-preparation --ignore-missing-imports --exclude tests/test_serving_model.py` → `Success: no issues found in 18 source files`

Review gate: PASS (`python3 .sdd/scripts/sdd.py gate review p1-003-coverage-quality-reporting`).

The dbt singular test (`tests/coverage_quality_report.sql`) compiles; its execution remains deferred under p1-001 O-1, formally recorded in [decisions.md](./decisions.md) (D-1), matching the reviewed precedent established in p1-001 and p1-002.

This is round 4 review following `review.r1.md`, `review.r2.md`, and `review.r3.md`.

## Acceptance criteria

| AC | PASS/FAIL | test name or file:line |
|---|---|---|
| AC-1 (one build-associated report, five measures) | PASS | [`test_build_publishes_exactly_five_dimensions`](../../../../SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py#L75-L80) and [`test_report_association_matches_manifest_values`](../../../../SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py#L266-L285) prove exactly one report with five dimensions, and association matching manifest values. |
| AC-2 (nutrition covered/denominator/percentage) | PASS | [`test_nutrition_measure_uses_requirement_denominator`](../../../../SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py#L89-L93) computes `covered=1, denominator=2, percentage=0.5` using canonical `nutrition_status = 'validated'`. |
| AC-3 (price covered/denominator/percentage) | PASS | [`test_price_measure_uses_estimated_price_status`](../../../../SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py#L96-L100) computes `covered=1, denominator=2, percentage=0.5` using canonical `price_status = 'estimated'`. |
| AC-4 (conversion covered/denominator/percentage) | PASS | [`test_conversion_measure_requires_compatible_unit_basis`](../../../../SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py#L103-L106) computes `covered=1, denominator=2` from canonical `cost_basis_compatible = true`. |
| AC-5 (dietary covered/denominator/percentage) | PASS | [`test_dietary_measure_requires_explicit_supported_evidence`](../../../../SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py#L109-L112) computes `covered=1, denominator=2` using canonical sets for halal and vegetarian; unknown is uncovered. |
| AC-6 (whole-recipe covered/denominator/percentage) | PASS | [`test_whole_recipe_denominator_is_distinct_from_requirement_denominator`](../../../../SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py#L115-L128) asserts recipe denominator (2 recipes) is distinct from requirement denominator (3 requirements), requiring all 4 dimensions. |
| AC-7 (nutrition-only != price-covered != whole-recipe) | PASS | [`test_nutrition_only_requirement_is_not_price_or_whole_recipe_complete`](../../../../SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py#L131-L140) verifies independent counting: nutrition `1`, price `0`, whole-recipe `0`. |
| AC-8 (zero population -> explicit, no 100%) | PASS | [`test_zero_populations_are_explicit_not_100_percent`](../../../../SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py#L143-L148) asserts all 5 rows get `denominator=0, percentage=None, population_status='no_population'`. |
| AC-9 (five comparison points identical across runs) | PASS | [`test_repeated_report_comparison_points_are_content_columns`](../../../../SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py#L167-L180) and [`test_report_content_is_stable_across_observation_timestamps`](../../../../SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py#L183-L202) verify determinism across runs and stability across observation timestamps. |
| AC-10 (association + bounds vs reproducibility/graph-quality) | PASS | [`test_reproducibility_manifest.py::test_report_matches_source_and_mart_manifest_association`](../../../../SystemCode/remy/data-preparation/tests/test_reproducibility_manifest.py#L24-L46) and [`test_report_association_matches_manifest_values`](../../../../SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py#L266-L285); singular test population bounds compiled in [`tests/coverage_quality_report.sql`](../../../../SystemCode/remy/data-preparation/tests/coverage_quality_report.sql#L30-L39) with execution deferred under documented D-1 / p1-001 O-1. |
| AC-11 (invalid inputs fail, no report) | PASS | [`test_missing_source_snapshot_publishes_no_report`](../../../../SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py#L205-L212), [`test_missing_canonical_mart_publishes_no_report`](../../../../SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py#L215-L234), [`test_uncomputable_coverage_report_publishes_no_report`](../../../../SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py#L237-L250), [`test_invalid_metrics_fail_closed_instead_of_being_filtered`](../../../../SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py#L83-L86), and [`test_unset_association_fails_closed`](../../../../SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py#L287-L296) assert fail-closed behaviour and absence of output report. dbt test execution deferred under D-1. |
| AC-12 (absent evidence -> uncovered, distinct gap) | PASS | [`test_missing_evidence_is_reported_as_uncovered`](../../../../SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py#L253-L264) asserts missing/unavailable/unknown evidence yields covered count 0. |
| AC-13 (exactly five dimensions + named association) | PASS | [`test_report_has_exactly_five_dimensions_and_association`](../../../../SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py#L151-L164) and [`test_report_association_matches_manifest_values`](../../../../SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py#L266-L285) confirm exact 5 canonical dimensions and executed build association. |

## Constitution compliance

Violations: none.

| Rule | Result | Evidence |
|---|---|---|
| R-1 | PASS | One canonical dimension vocabulary; schema.yml enforces `accepted_values` on `dimension` ([`schema.yml`](../../../../SystemCode/remy/data-preparation/models/mart/schema.yml#L149-L159)). |
| R-2 | PASS | All changes remain strictly inside the data-preparation mart/manifest/serving boundary. |
| R-3 | PASS | No new store, framework, or solver; Python/dbt/DuckDB/Neo4j architecture retained. |
| R-4 | PASS | `REQUIRES` and `FULFILLS` graph edge definitions and provenance untouched. |
| R-5 | PASS | Absent, unavailable, or unknown evidence stays uncovered and is never inferred ([`test_missing_evidence_is_reported_as_uncovered`](../../../../SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py#L253-L264), [`coverage_quality_report.sql`](../../../../SystemCode/remy/data-preparation/models/mart/coverage_quality_report.sql#L20-L28)). |
| R-6 | PASS | Allergen policy untouched by this feature. |
| R-7 | PASS | Dietary coverage uses explicit accepted sets ([`coverage_quality_report.sql`](../../../../SystemCode/remy/data-preparation/models/mart/coverage_quality_report.sql#L25-L28)); unknown is uncovered. |
| R-8 | PASS | Price availability counts canonical `price_status = 'estimated'`; unavailable/blank/null stay uncovered. |
| R-9 | PASS | Missing/incomplete nutrition is uncovered; only `nutrition_status = 'validated'` counts. |
| R-10 | PASS | `cost_basis_compatible` is required for conversion coverage. |
| R-11, R-12, R-13, R-14, R-16, R-17 | PASS | Out of scope for data-preparation quality reporting; contracts unchanged. |
| R-15 | PASS | The report is generated from accepted marts and refused when metrics or build association are invalid; build association is verified end-to-end against manifest values; dbt execution deferred under documented D-1 / p1-001 O-1. |

## Plan adherence

The implementation adheres to the approved plan and resolves all findings identified in `review.r3.md`:
1. **r3 F-1 resolved**: Build association is verified end-to-end via [`test_report_association_matches_manifest_values`](../../../../SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py#L266-L285), and [`coverage_quality_report.sql`](../../../../SystemCode/remy/data-preparation/models/mart/coverage_quality_report.sql#L93-L97) fails closed via `error(...)` when any association environment variable is missing or blank (verified by [`test_unset_association_fails_closed`](../../../../SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py#L287-L296)).
2. **r3 F-2 resolved**: Deferral of dbt singular test execution pending p1-001 O-1 is properly recorded in [decisions.md](./decisions.md) (D-1), matching T-15.
3. **r3 F-3 resolved**: Tasks T-14 through T-18 are ticked in [plan.md](./plan.md) with Revision note F-10 documenting the landing reconciliation.
4. **r3 F-4 resolved**: Duplicate `ci:` and `check:` recipes and the `.PHONY` continuation in [`SystemCode/Makefile`](../../../../SystemCode/Makefile) have been cleaned up.

## Findings

None.

## Nits (non-blocking)

- N-1 (carry-over of r3 N-2): Task T-19 remains unticked in [plan.md](./plan.md). The AC-12 fixture covers missing price (`unavailable`), conversion (`False`), and dietary (`unknown`), while nutrition missing parameterization and per-dimension gap counts remain open for follow-up test hardening.
- N-2 (carry-over of r3 N-3): The price predicate counts `price_status = 'estimated'` without independently asserting freshness; it currently holds because `edge_fulfills.sql:65` sets `'unavailable'` for null-snapshot/no-offer rows.
- N-3 (carry-over of r3 N-4): `reproducibility/source_registry.json:2` still declares `"schema_version": 1` while the manifest contract is version 2.
- N-4 (carry-over of r3 N-5): `tests/test_reproducibility_manifest.py:120-142` and `:282-331` retain commented-out test bodies.
- N-5 (carry-over of r3 N-7): The plan lists `SystemCode/Makefile` twice in "Files to touch" (`plan.md:129` and `:131-133`).
