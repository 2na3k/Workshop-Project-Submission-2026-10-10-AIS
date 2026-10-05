---
feature: p1-003-coverage-quality-reporting
---

# Plan - Coverage and quality reporting

## Approach

- **Chosen:** Add one canonical coverage-report relation to the existing dbt
  mart build, derive all five dimensions from a requirement-level capability
  spine with deterministic existence/counting rules, and emit a build-linked
  report whose source snapshot and mart checksums are supplied by the existing
  reproducibility manifest. Preserve the structural graph-quality manifest and
  p1-002 admission contract while extending build verification for the new
  report.
- **Rejected alternative:** Encode the five measures as free-form text inside
  `graph_quality_manifest.capability_reason`; this would lose typed
  denominators/percentages, prevent independent validation, and make downstream
  consumers parse an unstable diagnostic string.

## Design

1. **Canonical report boundary.** Introduce a single coverage report over the
   canonical mart relations. It has exactly five dimension identities:
   nutrition coverage, price availability, package-unit conversion coverage,
   dietary-evidence coverage, and whole-recipe completeness. Each dimension
   carries a covered count, denominator, percentage or explicit no-population
   state, and a build association. The existing `graph_quality_manifest`
   remains responsible for node/relationship counts, allocations, and structural
   quality facts used by p1-002; it is not replaced by a second structural
   vocabulary.

2. **Requirement and recipe populations.** Build a deterministic requirement
   spine from the canonical `REQUIRES` relation and a distinct recipe
   population from the canonical recipe node relation. Join fulfillment
   candidates by the established food-concept identity and calculate each
   capability with existence semantics: a requirement is counted at most once
   per dimension even when it has multiple candidates. Whole-recipe coverage is
   calculated only after all requirement-level flags exist and requires every
   requirement for the recipe to satisfy all four requirement-level dimensions.

3. **Dimension predicates.** Use the canonical mart status and evidence fields
   with the exact accepted values the marts produce, not inference or candidate
   row counts:
    - **Nutrition coverage** requires an eligible candidate whose
      `nutrition_status = 'validated'` (the canonical accepted value on
      `node_food`, produced in `node_food.sql:39`). `'missing'`, blank, or null
      is uncovered.
    - **Price coverage** requires a candidate whose `price_status = 'estimated'`
      on `edge_fulfills`. This is the only accepted value
      `int_price_fulfillment_candidates.sql` produces (lines 43 and 77).
      `'unavailable'`, blank, or null is uncovered. Stale offers do not count as
      available.
    - **Conversion coverage** requires a candidate whose
      `cost_basis_compatible` is true on `edge_fulfills`. Absent or false is
      uncovered even when price or nutrition evidence exists.
    - **Dietary coverage** requires explicit evidence for the supported dietary
      screens, using the accepted sets `graph_quality_manifest.sql:18-20`
      already applies: `halal_status IN ('certified', 'retailer_claim',
     'ingredient_screen_pass')` **or** `vegetarian_status IN
     ('retailer_claim', 'ingredient_screen_pass')`. Any value outside those
      sets — including `'unknown'`, blank, or null — is uncovered.
      A candidate may satisfy one dimension without satisfying another.

4. **Metric validity and empty populations.** Validate that counts are
   non-negative, covered counts do not exceed denominators, percentages are
   calculated deterministically and remain bounded, and dimension identities
   are unique and exactly the five specified values. A zero denominator emits a
   typed no-population result rather than a fabricated percentage or a divide
   by zero. The build fails closed if any dimension cannot be computed or if
   the report is internally inconsistent.

5. **Build association and reproducibility.** Extend the existing manifest
   generation contract to include the coverage report's deterministic content
   checksum and report content columns. Associate the report with the accepted
   source snapshot identity and the canonical mart checksums it measures in the
   generated build artifact. Regenerate it after every accepted canonical mart
   build; never reuse a previous report when source or mart content changes.
   Keep observation timestamp changes distinct from content determinism.

6. **Quality and downstream interfaces.** Add schema-level contracts for the
   report and a singular quality test for invalid metrics, duplicate dimensions,
   and denominator/population mismatches. The serving model's `schema.yml` is
   updated to declare explicitly that the coverage report is consumed as
   build-quality metadata and is not projected into the graph as nodes or edges.
   Keep the graph loader's structural `graph_quality_manifest` input unchanged;
   p1-003 reports descriptive completeness and does not introduce a minimum
   percentage threshold or alter graph admission.

7. **Verification strategy.** Use controlled DuckDB/dbt fixture relations or
   pure report-calculation fixtures for all five dimensions, including a
   nutrition-only/price-missing case, incompatible-unit case, unknown dietary
   evidence, multiple candidates, zero populations, and invalid metrics. Extend
   reproducibility-manifest tests to compare all report fields and the build
   association across repeated runs. Real seeded dbt execution remains subject
   to p1-001 O-1; no fabricated checksum baseline is introduced.

## Files to touch

- `SystemCode/remy/data-preparation/models/mart/coverage_quality_report.sql` —
  add the canonical five-dimension report derived from requirement and recipe
  populations and fulfillment capability evidence.
- `SystemCode/remy/data-preparation/models/mart/schema.yml` — declare the
  report columns, exact dimension values, count/percentage constraints, and
  reproducibility content columns.
- `SystemCode/remy/data-preparation/scripts/reproducibility_manifest.py` — add
  the coverage report to the deterministic content/checksum contract and retain
  source/mart association metadata for the report artifact. Increment
  `MANIFEST_SCHEMA_VERSION` to signal the contract change.
- `SystemCode/remy/data-preparation/models/serving/recipe_graph_to_neo4j.py` —
  update the serving model's accepted manifest schema version constant to match
  the extended manifest. No behavior change to admission semantics.
- `SystemCode/remy/data-preparation/models/serving/schema.yml` — declare that
  the coverage report is build-quality metadata consumed by CI and operators,
  not projected as graph nodes or edges.
- `SystemCode/remy/data-preparation/tests/coverage_quality_report.sql` — add a
  dbt singular test for duplicate/missing dimensions, invalid counts or
  percentages, and population mismatches.
- `SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py` —
  verify dimension predicates, existence counting, cross-dimension independence,
  zero denominators, whole-recipe aggregation, missing evidence, invalid inputs,
  and deterministic output with controlled fixtures.
- `SystemCode/remy/data-preparation/tests/test_reproducibility_manifest.py` —
  extend required-mart and repeated-build assertions to include the report and
  its association/checksum fields.
- `SystemCode/remy/data-preparation/README.md` — document the five report
  dimensions, the exact accepted predicate values, empty-population behavior,
  build association, and regeneration command/output.
- `SystemCode/Makefile` — keep report generation/checking in the existing dbt,
  reproducibility-manifest, and CI sequence.

## Constitution alignment

- **R-1** → The report has exactly one canonical dimension vocabulary and
  rejects duplicate or alternate dimension names; no aliasing or second schema
  is introduced.
- **R-2** → Work remains inside the data-preparation mart, manifest, and test
  boundary and does not add cross-layer backend dependencies.
- **R-3** → The existing Python/dbt/DuckDB/Neo4j architecture is retained; the
  report is another declarative data-preparation output, not a new store or
  framework.
- **R-5** → Null, blank, unknown, and inferred-only evidence produces an
  uncovered result and never increases a coverage numerator.
- **R-7** → Dietary coverage requires explicit evidence and does not infer
  halal, vegan, or vegetarian compliance from absence of concerns.
- **R-8** → Price availability uses the canonical accepted/freshness evidence
  status and does not make stale or unavailable offers count as available.
- **R-9** → Nutrition coverage requires a usable nutrition profile and never
  treats a missing profile as zero or covered.
- **R-10** → Package-unit coverage requires the canonical compatible-unit
  evidence and does not infer compatibility from a price or nutrition match.
- **R-15** → The report is generated from accepted reproducible canonical marts,
  linked to source/mart checksums, deterministic across runs, and rejected when
  required inputs or metrics are invalid.

## Test strategy

| AC | Test type | Test location / name | Notes |
|---|---|---|---|
| AC-1 | Controlled build/report integration | `tests/test_coverage_quality_report.py::test_build_publishes_exactly_five_dimensions` | Build a fixture population and assert one report with all five named dimensions and a build association. |
| AC-2 | Dimension calculation fixture | `tests/test_coverage_quality_report.py::test_nutrition_measure_uses_requirement_denominator` | Assert covered count, denominator, and percentage use distinct canonical requirements and `nutrition_status = 'validated'`; `'missing'` is uncovered. |
| AC-3 | Dimension calculation fixture | `tests/test_coverage_quality_report.py::test_price_measure_uses_estimated_price_status` | Assert `price_status = 'estimated'` counts; `'unavailable'`, blank, or null does not; coverage is independent of nutrition and conversion. |
| AC-4 | Dimension calculation fixture | `tests/test_coverage_quality_report.py::test_conversion_measure_requires_compatible_unit_basis` | Assert `cost_basis_compatible = true` is required; incompatible bases remain uncovered even when price or nutrition exists. |
| AC-5 | Dimension calculation fixture | `tests/test_coverage_quality_report.py::test_dietary_measure_requires_explicit_supported_evidence` | Assert `halal_status IN ('certified', 'retailer_claim', 'ingredient_screen_pass')` or `vegetarian_status IN ('retailer_claim', 'ingredient_screen_pass')` counts; `'unknown'`, blank, null, or other values do not. |
| AC-6 | Recipe aggregation fixture | `tests/test_coverage_quality_report.py::test_whole_recipe_requires_all_four_requirement_dimensions` | Assert distinct recipe denominator and that one uncovered requirement prevents recipe completeness. |
| AC-7 | Cross-dimension regression fixture | `tests/test_coverage_quality_report.py::test_nutrition_only_requirement_is_not_price_or_whole_recipe_complete` | Use nutrition-present/price-absent evidence and assert only nutrition numerator changes. |
| AC-8 | Empty-population fixture | `tests/test_coverage_quality_report.py::test_zero_populations_are_explicit_not_100_percent` | Assert all requirement dimensions and recipe completeness expose zero denominators and no fabricated percentage. |
| AC-9 | Determinism/reproducibility test | `tests/test_coverage_quality_report.py::test_repeated_report_generation_matches_all_fields` | Compare counts, denominators, percentages, dimension identities, and build association across repeated runs. |
| AC-10 | Manifest contract test | `tests/test_reproducibility_manifest.py::test_report_matches_source_and_mart_manifest_association` | Assert the report names the same accepted source snapshot and canonical mart checksums and respects population bounds. |
| AC-11 | Negative build/contract test | `tests/coverage_quality_report.sql` (dbt singular) plus `tests/test_coverage_quality_report.py::test_invalid_inputs_publish_no_report` (Python, asserts no report is written) | The dbt test fails the build on invalid metrics; the Python test asserts no accepted report is published when inputs are missing or uncomputable. Both halves are required. |
| AC-12 | Missing-evidence fixture | `tests/test_coverage_quality_report.py::test_missing_evidence_is_reported_as_gap` | Parameterize nutrition (`missing`), price (`unavailable`), conversion (`false`), and dietary (`unknown`) absence; assert distinct uncovered counts and no inference. |
| AC-13 | Exact vocabulary/association test | `tests/test_coverage_quality_report.py::test_report_has_exactly_five_dimensions_and_association` | Enumerate dimensions and assert no extras plus source snapshot identity and mart checksum association. |

## Risks & mitigations

- **Predicate values must match the canonical statuses exactly.** `price_status`
  is `'estimated'` (from `int_price_fulfillment_candidates.sql:43,77`);
  `nutrition_status = 'validated'` (from `node_food.sql:39`);
  `halal_status` and `vegetarian_status` use the accepted sets from
  `graph_quality_manifest.sql:18-20`. A predicate using values the marts don't
  produce will silently report zero coverage. The AC tests name the exact
  values, and each predicate cites the model that produces it.
- **The new report changes the reproducibility manifest contract owned by
  p1-001.** The manifest schema version increments (1 → 2). The serving model's
  `MANIFEST_SCHEMA_VERSION` and acceptance check are updated in the same change
  so p1-002's admission still accepts the extended manifest. Update the
  required-mart/content-column set and its tests together, preserve existing
  graph-mart checksums, and record the intentional contract change in p1-003
  close decisions. Do not rewrite pinned values automatically.
- **The current graph-quality manifest has structural consumers.** Keep its
  node/relationship totals and admission semantics intact; use a dedicated
  report relation rather than overloading allocation rows or diagnostic text.
- **Coverage predicates can accidentally count candidates instead of
  requirements.** Use distinct requirement identities and explicit existence
  aggregation; test multiple candidates and a single requirement with mixed
  capabilities.
- **Whole-recipe completeness can be dominated by optional/alternative
  requirements.** Use the accepted canonical `REQUIRES` population exactly as
  emitted, document that denominator, and test optional/alternative rows rather
  than silently excluding them.
- **p1-001 O-1 still blocks a real seeded dbt run.** Complete deterministic
  fixture and contract evidence without fabricated checksums, and document the
  real-data execution deferral until the seeds and reviewed reference baseline
  are restored.
- **A report may be generated from a different build than its metadata.** Carry
  the source snapshot and mart checksum association through one build boundary
  and fail when the association cannot be verified before publication.
- **Future consumers may mistake descriptive percentages for policy gates.**
  Document that this feature reports readiness only; no minimum coverage
  threshold or constraint-pass decision is introduced.

## Scope check

Fits one working context: **yes.** The feature is one cohesive data-preparation
change: one canonical report relation, its schema and singular validation,
manifest/build wiring, and deterministic fixture tests. It does not alter the
p1-002 graph loader's admission semantics or implement later reasoning policy.
The p1-001 O-1 seed restoration is an external prerequisite for real-data
evidence, not a reason to split the feature.

## Revision notes

- F-1 → Initial plan drafted from the approved spec.
- F-2 → Resolved plan-review nit 1: named the canonical price-evidence
  predicate.
- F-3 → Resolved plan-review nit 3: the `models/serving/schema.yml` touch is
  now a definite deliverable, not an "only if."
- F-4 → Resolved plan-review nit 2: split the AC-11 test row explicitly into
  the dbt singular half and the Python half.
- F-5 → Added the manifest schema-version compatibility task: the extension to
  `reproducibility_manifest.py` increments `MANIFEST_SCHEMA_VERSION` (1 → 2),
  and the serving model's version constant is updated in the same change.
- F-6 → Added the canonical status predicates to Design §3 and the test rows.
- F-7 → Corrected the predicates after grepping the actual marts: the canonical
  accepted price status is `'estimated'` (from
  `int_price_fulfillment_candidates.sql:43,77`), not `'available'`/`'reference'`.
  Nutrition coverage requires `nutrition_status = 'validated'` (from
  `node_food.sql:39`). Dietary coverage uses the exact accepted sets from
  `graph_quality_manifest.sql:18-20` (`halal_status IN ('certified',
  'retailer_claim', 'ingredient_screen_pass')`, `vegetarian_status IN
  ('retailer_claim', 'ingredient_screen_pass')`). Applied to Design §3, the
  AC-2/AC-3/AC-5 test rows, and the Risks section.

## Tasks

- [x] **T-1** Verify predicate values and the manifest-version compatibility before writing code
    - Type: prerequisite
    - Covers: plan Risks "predicate values must match" and "manifest contract" bullets
    - Files: (read-only)
    - Done when: `nutrition_status = 'validated'`, `price_status = 'estimated'`, `cost_basis_compatible = true`, `halal_status IN ('certified', 'retailer_claim', 'ingredient_screen_pass')`, `vegetarian_status IN ('retailer_claim', 'ingredient_screen_pass')` are confirmed present in the canonical marts; `MANIFEST_SCHEMA_VERSION` in `reproducibility_manifest.py` and the serving model's accepted version constant are named. If any predicate value has no producer in the marts, stop and route to spec.

- [x] **T-2** Write failing tests for the five dimensions (AC-1 through AC-6)
    - Type: test
    - Covers: AC-1, AC-2, AC-3, AC-4, AC-5, AC-6
    - Files: `SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py`
    - Done when: each test constructs a controlled fixture population and asserts the covered count, denominator, and percentage for its dimension; each fails because the report does not exist yet. Nutrition uses `nutrition_status = 'validated'`; price uses `price_status = 'estimated'`; conversion requires `cost_basis_compatible = true`; dietary uses the exact accepted sets; whole-recipe uses a distinct recipe denominator.

- [x] **T-3** Write failing tests for cross-dimension independence and empty populations (AC-7, AC-8)
    - Type: test
    - Covers: AC-7, AC-8
    - Files: `SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py`
    - Done when: the nutrition-only/price-absent fixture asserts independent counting (nutrition numerator 1, price numerator 0, whole-recipe not complete); the empty fixture asserts typed no-population results for all five dimensions with no fabricated percentage.

- [x] **T-4** Implement the coverage report mart (AC-1 through AC-6)
    - Type: impl
    - Covers: AC-1, AC-2, AC-3, AC-4, AC-5, AC-6
    - Files: `SystemCode/remy/data-preparation/models/mart/coverage_quality_report.sql`, `SystemCode/remy/data-preparation/models/mart/schema.yml`
    - Done when: T-2 passes; the report exposes exactly five named dimensions with counts, denominators, and percentages.

- [x] **T-5** Implement empty-population and cross-dimension behavior (AC-7, AC-8)
    - Type: impl
    - Covers: AC-7, AC-8
    - Files: `SystemCode/remy/data-preparation/models/mart/coverage_quality_report.sql`
    - Done when: T-3 passes; zero denominators emit typed no-population results; cross-dimension counting is independent.

- [x] **T-6** Write the dbt singular test for metric validity (AC-11, dbt half)
    - Type: test
    - Covers: AC-11 (dbt half)
    - Files: `SystemCode/remy/data-preparation/tests/coverage_quality_report.sql`
    - Done when: the singular test fails the build on duplicate or missing dimensions, negative counts, covered > denominator, or percentages out of bounds.

- [x] **T-7** Write failing tests for determinism, build association, and exact vocabulary (AC-9, AC-10, AC-13)
    - Type: test
    - Covers: AC-9, AC-10, AC-13
    - Files: `SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py`, `SystemCode/remy/data-preparation/tests/test_reproducibility_manifest.py`
    - Done when: the determinism test compares all five comparison points (counts, denominators, percentages, dimension identities, build association); the association test ties the report to the manifest's source snapshot and mart checksums; the vocabulary test asserts exactly five dimensions and names the association fields.

- [ ] **T-8** Implement the manifest contract extension and version compatibility (AC-9, AC-10, AC-13)
    - Type: impl
    - Covers: AC-9, AC-10, AC-13
    - Files: `SystemCode/remy/data-preparation/scripts/reproducibility_manifest.py`, `SystemCode/remy/data-preparation/models/serving/recipe_graph_to_neo4j.py`, `SystemCode/remy/data-preparation/models/mart/schema.yml`
    - Done when: T-7 passes; the manifest schema version is incremented and the report is included in the required-mart set with its deterministic content checksum; the serving model's accepted version constant matches so p1-002's admission still accepts the extended manifest.

- [ ] **T-9** Write the negative test for missing or uncomputable inputs (AC-11, Python half)
    - Type: test
    - Covers: AC-11 (Python half)
    - Files: `SystemCode/remy/data-preparation/tests/test_coverage_quality_report.py`
    - Done when: missing source snapshot, missing canonical mart, or an uncomputable dimension each cause the report generation to fail non-zero and publish no accepted report; the test asserts the absence of an output report, not only the raised error.

- [ ] **T-10** Implement fail-closed behavior for missing or invalid inputs (AC-11, AC-12)
    - Type: impl
    - Covers: AC-11, AC-12
    - Files: `SystemCode/remy/data-preparation/models/mart/coverage_quality_report.sql`, `SystemCode/remy/data-preparation/scripts/reproducibility_manifest.py`
    - Done when: T-9 passes; missing evidence is reported as uncovered with a distinct gap count (`nutrition_status = 'missing'`, `price_status = 'unavailable'`, `cost_basis_compatible = false`, dietary status outside the accepted sets); invalid inputs fail the build.

- [ ] **T-11** Declare the coverage report as build-quality metadata in the serving schema
    - Type: impl
    - Covers: plan Design §6
    - Files: `SystemCode/remy/data-preparation/models/serving/schema.yml`
    - Done when: the serving schema declares that the coverage report is consumed as build-quality metadata and is not projected as graph nodes or edges.

- [ ] **T-12** Document the report in the README
    - Type: impl
    - Covers: the spec's User-facing behavior section
    - Files: `SystemCode/remy/data-preparation/README.md`
    - Done when: the README documents the five dimensions, the exact predicate values (and the models that produce them), empty-population behavior, build association, regeneration, and the "descriptive, not threshold" posture.

- [ ] **T-13** Run `pytest`, `sdd.py ci`, and `make ci`; record evidence
    - Type: verification
    - Covers: AC-1 through AC-13
    - Files: (all above)
    - Done when: `sdd.py ci` reports OVERALL PASS; the dbt singular test compiles and its execution is either completed by `make ci` or documented as blocked by the p1-001 O-1 seed dependency; the report's real-mart demonstration is recorded as O-1-deferred; no fabricated checksum is introduced.
