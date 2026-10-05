# Decisions - Coverage and quality reporting

## Decisions

### D-1 Defer dbt execution and real-mart demonstration pending the data-preparation price-path finding
- Date: 2026-10-05
- Context: `make dbt`, `dbt ls`, and `make ci` all fail at the parse stage.
  The block is not the coverage report's guard; it is upstream, in the
  data-preparation package, at `models/staging/stg_retail_listing.sql`,
  which references `retail_aisle_listing` and `retail_search_listing` —
  two nodes that no model, seed, or source produces. The seeds themselves
  are present and used by the other staging models (`branded_food`, `food`,
  `food_component`, `13k-recipes`, `price_mapped_nutrients`). The
  data-preparation package is not owned by this effort; see
  `docs/findings/data-prep-price-path.md`.
- Decision: The report's SQL is verified against the Python fixture
  (`test_coverage_quality_report.py`, 18 tests). The dbt-level verifications
  are deferred pending the price-path finding's resolution: the singular
  test execution (T-15), the report's gating verification through `dbt ls`,
  and the real-mart demonstration.
- Alternatives: Stub the missing nodes with placeholder data — rejected
  (hides the finding and modifies a package this effort does not own);
  modify the data-preparation package to rewire the price path — rejected
  (out of scope; the change is the package owner's to make); skip the
  report's dbt verification entirely — rejected (the deferral must be
  recorded, not silent).
- Affects: T-15; the review's dbt-test row; the report's end-to-end
  demonstration.
- Source: Plan T-15, review r3 F-2, `docs/findings/data-prep-price-path.md`.

### D-2 Manifest schema version increment from 1 to 2
- Date: 2026-10-05
- Context: Adding `coverage_quality_report` to `REQUIRED_MARTS` and requiring
  its content checksum and content columns in the reproducibility manifest
  extends the manifest contract.
- Decision: Increment `MANIFEST_SCHEMA_VERSION` from 1 to 2 in
  `reproducibility_manifest.py`, and update the serving model's
  (`recipe_graph_to_neo4j.py`) accepted manifest schema version constant
  to 2 in the same change so graph admission continues to accept the
  extended manifest.
- Alternatives: Retain version 1 with optional mart — rejected (fails closed
  reproducible contract); introduce a separate quality-only manifest —
  rejected (splits source snapshot and mart checksum truth).
- Affects: `reproducibility_manifest.py`, `recipe_graph_to_neo4j.py`,
  `test_reproducibility_manifest.py`, `test_serving_model.py`.
- Source: Plan Design §5, T-8, review r3 F-5.

### D-3 Fail-closed build association verification
- Date: 2026-10-05
- Context: Unset or blank build association environment variables could
  silently publish NULL association columns, contrary to spec AC-11.
- Decision: Enforce non-empty `REMY_SOURCE_SNAPSHOT_ID`,
  `REMY_MART_CONTENT_CHECKSUM`, and `REMY_BUILD_ID` in the report's
  `validated` CTE, raising `error('coverage_quality_report failed closed: build association is not configured')`
  if any variable is missing or empty.
- Alternatives: Default-fill with placeholder strings — rejected (misrepresents
  reproducibility provenance); emit NULLs — rejected (violates spec AC-11
  fail-closed contract).
- Affects: `coverage_quality_report.sql`, `test_coverage_quality_report.py`.
- Source: Review r3 F-1, commit bd06ed3.

## Overrides
None.
