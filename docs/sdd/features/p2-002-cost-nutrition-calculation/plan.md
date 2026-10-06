---
feature: p2-002-cost-nutrition-calculation
---

# Plan - Cost and nutrition calculation

## Approach

- **Chosen:** Extend the existing calculator domain/service/repository path with
  source-aware nutrition selection, validated candidate metadata, compatible
  cost eligibility, deterministic ranking, and response/trace assertions; prove
  behavior first with focused calculator fixtures and one real service-path
  integration fixture.
- **Rejected alternative:** Rebuild calculation in the workflow or introduce a
  second calculator API; this would duplicate the existing public boundary and
  violate the inward dependency shape without improving the required contracts.

## Design

1. **Evidence projection and selection.** Preserve, from the canonical graph
   query through the repository result, the evidence needed to distinguish
   generic USDA nutrition from branded product nutrition, compare crawl
   timestamps and product identifiers, rank mapping scores, and retain
   confidence. Select one deterministic nutrient value per tracked nutrient:
   branded over generic, newest branded observation, then lexicographically
   smallest product identifier. Precedence is evaluated **per nutrient**, not
   per candidate: within one candidate, nutrient A may resolve to a branded
   value while nutrient B resolves to a generic-only value, and both selections
   stand. Reject duplicate conflicting evidence with the same product identity
   and timestamp rather than choosing nondeterministically. Candidate selection
   accepts the closed confidence interval [0, 1], applies no confidence floor,
   ranks by score, and uses stable secondary ordering.

2. **Portion nutrition.** Keep the existing grams conversion and null-preserving
   scaling/summing semantics. Ensure the selected profile is scaled by consumed
   grams, recipe totals sum available nutrient values independently, and
   per-serving values divide the total by the validated serving count. Preserve
   an explicit warning for assumed non-mass conversions and never turn absent
   nutrient evidence into zero.

3. **Cost eligibility and result semantics.** Treat only positive SGD package
   evidence with a positive amount and compatible unit basis as cost-eligible.
   Exclude incompatible or unusable products before selection. Calculate
   consumed cost proportionally to the used quantity and retail cost from the
   whole-package count; expose both independently at item and summary levels.

   **Cost is request-dependent.** The request supplies a budget constraint
   (`request.budget` non-null); when present, cost is required for every
   ingredient: an ingredient with no compatible, usable cost evidence is an
   evidence-absent drop for the recipe. When `request.budget` is null, cost is
   computed opportunistically — an ingredient with cost evidence gets both cost
   fields, an ingredient without cost evidence is retained with cost marked
   absent, and the calculation succeeds. The "cost is required" condition in
   the spec's AC-5 is `request.budget is not None`. The freshness policy
   (24-hour boundary, inclusive) is consumed from p2-001 and never
   re-implemented or weakened here.

4. **Boundary and trace.** Run the real calculator service against a repository
   fixture at the service boundary so repository-produced facts become the
   response consumed by the API-facing result. Keep confidence and source
   metadata in the execution trace only; assert that the public response retains
   the existing R-16 boundary. The plan does not expand the public response to
   expose audit provenance.

5. **Compatibility and validation.** Make the smallest compatible changes to
   existing calculator models, repository mapping, domain calculation helpers,
   and service orchestration. Validate request errors through the existing
   Pydantic/application error boundary, and preserve the established import
   direction. Existing p2-001 filtering remains the owner of freshness and
   candidate constraint causes; this feature consumes its outcomes. Request-level
   validation (servings, ingredient count) is enforced at the schema/service
   boundary and rejects before calculation runs.

## Files to touch

- `SystemCode/remy/api/src/api/features/calculator/models.py` — carry the
  additional evidence fields required for deterministic source precedence,
  score/confidence selection, and trace recording.
- `SystemCode/remy/api/src/api/features/calculator/repository.py` — project the
  canonical graph evidence needed by the calculator and preserve deterministic
  candidate/nutrition metadata when building calculator facts.
- `SystemCode/remy/api/src/api/features/calculator/domain/cost.py` — enforce
  cost eligibility, stable best-score selection, whole-package counting,
  separate consumed/package cost arithmetic, and the request-dependent
  cost-required outcome.
- `SystemCode/remy/api/src/api/features/calculator/domain/nutrition.py` — add or
  refine per-nutrient source-precedence selection and deterministic
  null-preserving nutrient aggregation without changing the public response
  boundary.
- `SystemCode/remy/api/src/api/features/calculator/service.py` — orchestrate
  evidence selection, portion calculation, cost outcomes, warnings, request
  validation, and the audit-only execution trace while preserving the existing
  response contract.
- `SystemCode/remy/api/src/api/features/calculator/schemas.py` — enforce
  request-level validation (servings, ingredient count, budget nullability) and
  internal trace plumbing; do not expose audit-only provenance in the
  user-facing schemas.
- `SystemCode/remy/api/tests/features/calculator/test_domain_cost.py` — cover
  compatible/incompatible packages, consumed/package separation, unusable price
  evidence, confidence boundaries, score ordering, and deterministic ties.
- `SystemCode/remy/api/tests/features/calculator/test_domain_nutrition.py` —
  cover portion scaling, null-preserving aggregation, per-nutrient source
  precedence, timestamp/product-ID tie breaking, and repeatability.
- `SystemCode/remy/api/tests/features/calculator/test_domain_conversion.py` —
  cover assumed-unit warnings and invalid conversion behavior at the calculator
  boundary.
- `SystemCode/remy/api/tests/features/calculator/test_service_integration.py` —
  add a real repository-to-service-to-response fixture covering the result
  contract, the trace boundary, request validation, and the request-dependent
  cost-required outcome.
- `SystemCode/remy/api/tests/features/calculator/test_repository_integration.py`
  — exercise canonical query-row projection into calculator facts using the
  repository code under test.

## Constitution alignment

- **R-1** — Use the canonical graph property names and one calculator vocabulary;
  no legacy aliases or parallel field names are accepted.
- **R-2** — Keep the dependency flow router/service/repository/models and pure
  calculation helpers inward; do not move calculator logic into workflows or
  import API internals into domain.
- **R-3** — Retain the Python backend and graph-serving architecture; no new
  backend, store, or heuristic solver is introduced.
- **R-5** — Missing resolution, nutrient evidence, or required cost evidence is
  never converted into a passing result or zero; the appropriate error or
  evidence-absent outcome is preserved.
- **R-8** — Reuse p2-001's inclusive 24-hour freshness rule and never select a
  stale offer.
- **R-9** — Profile-less and nutrient-missing evidence contributes no implicit
  zero and cannot satisfy a requested nutrient constraint.
- **R-10** — Cost selection admits only a compatible package/unit basis and drops
  the requirement as evidence-absent when none remains and cost is required.
- **R-11** — Consumed ingredient cost and whole-package purchase cost are
  calculated and exposed as distinct fields at item and summary levels.
- **R-12** — Nutrition conflict resolution follows branded, newest observation,
  then lexicographically smallest product ID precedence deterministically, and
  applies **per nutrient** rather than per candidate.
- **R-13** — Existing candidates are selected by best score with confidence in
  the closed interval [0, 1], without a minimum confidence floor; confidence is
  retained in the trace.
- **R-16** — Source IDs, confidence, normalization/version metadata, and other
  audit-only fields remain outside the user-facing response.

## Test strategy

| AC | Test type | Test location / name | Notes |
|---|---|---|---|
| AC-1 | unit | `test_domain_nutrition.py::test_portion_total_and_per_serving` | Assert gram scaling, recipe total, and division by servings. |
| AC-2 | unit | `test_domain_nutrition.py::test_partial_values_sum_without_zero_fill` | Assert independent null-preserving nutrient aggregation. |
| AC-3 | unit | `test_domain_cost.py::test_consumed_and_single_package_cost_are_distinct` | Assert P×Q/S versus P for Q<S. |
| AC-4 | unit | `test_domain_cost.py::test_multi_package_purchase_cost_is_whole_package_total` | Assert proportional consumed cost versus ceil(Q/S)×P. |
| AC-5 | unit/contract | `test_domain_cost.py::test_incompatible_basis_is_excluded_and_required_cost_drops` | Assert incompatible candidates are excluded; when `request.budget` is non-null and no compatible product remains, the recipe drops with an evidence-absent cause. |
| AC-5 | unit/contract (negative, per F-4) | `test_domain_cost.py::test_no_compatible_product_without_budget_retains_ingredient` | Same fixture as AC-5 but with `request.budget = null`; ingredient is retained, cost fields marked absent, calculation succeeds. |
| AC-6 | unit | `test_domain_nutrition.py::test_branded_value_precedes_generic_value` | Assert branded evidence wins and generic-only evidence remains usable. |
| AC-7 | unit | `test_domain_nutrition.py::test_branded_timestamp_then_product_id_tiebreak` | Assert newest timestamp and lexicographic tie-break independently. |
| AC-8 | repeatability | `test_domain_nutrition.py::test_conflict_selection_is_repeatable` | Run identical evidence more than once, including equal timestamps. |
| AC-9 | unit | `test_domain_cost.py::test_zero_confidence_candidate_is_accepted` | Assert confidence 0 is selectable and traceable. |
| AC-10 | unit | `test_domain_cost.py::test_best_score_beats_confidence_and_is_traceable` | Assert score ordering, not confidence floor, controls selection. |
| AC-11 | unit/validation | `test_domain_cost.py::test_confidence_closed_interval_validation` | Assert 0 and 1 pass; outside values fail without clamping. |
| AC-12 | unit/API boundary | `test_domain_conversion.py::test_assumed_unit_warning_and_invalid_quantity_errors` | Assert warning and conversion/validation failures. |
| AC-13 | service contract | `test_service_integration.py::test_unresolved_ingredient_is_rejected_without_zero_result` | Run the real service with an empty producer result and assert rejection. |
| AC-6, AC-7 (per-nutrient independence, per F-3) | unit | `test_domain_nutrition.py::test_precedence_is_per_nutrient_independent` | One candidate where nutrient A's winner is branded and nutrient B's winner is generic-only; assert totals reflect per-nutrient selection. |
| Edge case (invalid request, per F-1) | service/schema validation | `test_service_integration.py::test_invalid_request_rejected_before_calculation` | Parameterized over zero servings, negative servings, empty ingredient list, over-limit ingredient count; each rejects at the schema/service boundary without producing a calculation. |
| Edge case (unusable price evidence, per F-2) | unit | `test_domain_cost.py::test_unusable_price_evidence_excluded` | Parameterized over missing price, zero/negative price, non-SGD currency, stale offer (> 24h); each excludes the candidate from cost eligibility. |

## Integration per interface

| Interface (producer → consumer) | Test type | Test location / name | Notes |
|---|---|---|---|
| Canonical graph evidence rows → `CostNutritionRepository.fetch_food_facts` | repository integration | `test_repository_integration.py::test_canonical_rows_project_to_calculator_facts` | The real repository query/projection code runs against the existing fake-driver producer fixture. Real-mart execution is deferred because `docs/findings/data-prep-price-path.md` prevents dbt parsing; the deferral is recorded below and in `decisions.md`. |
| `CostNutritionRepository` facts → `CostNutritionService.calculate` → `CostNutritionResponse` | service integration | `test_service_integration.py::test_repository_facts_flow_to_public_cost_nutrition_response` | Use a real repository fixture and real service; mock only the Neo4j dependency if needed. Assert consumed/package costs, nutrients, warnings, and absence of audit-only fields on the consumer response. |
| Calculator result contract → p2-003 planning consumer | deferred integration | (no test file in this loop) | p2-003 is not implemented in this working context. The deferral is recorded in Revision notes and `decisions.md`. The p2-003 plan must write the consuming integration test when p2-003 begins; it is named there, not stubbed here. |

## Risks & mitigations

- **Canonical real-data path is unavailable.** The data-preparation dbt
  project still fails at parse on missing retail references. Mitigation: use
  canonical-row fixtures and the existing fake-driver infrastructure for this
  feature, mark real-mart verification as deferred, and do not claim end-to-end
  data-pipeline evidence.
- **Current graph projection lacks conflict metadata.** `QUERY_B` and
  `RetailSKU` currently omit source kind, crawl timestamp, and product identity
  needed by R-12. Mitigation: add only the canonical fields needed for
  selection, with fixtures that cover every precedence branch, per-nutrient
  independence, and duplicate identity rejection.
- **Current resolver score is not the same as graph mapping score.** The service
  currently re-resolves already returned canonical candidates and discards the
  returned confidence. Mitigation: preserve the repository candidate score and
  confidence through the selection path, and test score/confidence separately.
- **Existing API schemas use nullable cost rather than a drop outcome.**
  Mitigation: the request-dependent cost-required outcome is defined in
  Design §3 and exercised by AC-5's two test rows; the public response shape is
  preserved (absent cost as a null field when the request does not require it),
  and any cross-feature response-shape change routes to the owning p2-003/p3
  plan.
- **Tie behavior can become order-dependent.** Mitigation: explicit stable
  secondary keys and repeated-run tests, including identical timestamp cases.
- **Rounding can hide arithmetic defects.** Mitigation: assert raw domain
  arithmetic where possible and assert documented money/nutrient rounding only
  at the response boundary.

## Scope check

Fits one working context: yes. The work is one calculator vertical slice across
its existing repository, domain helpers, service boundary, and focused tests.
The real data-preparation repair and p2-003 consumer integration are external
or later-feature work and are explicitly deferred rather than split into this
feature.

## Revision notes

- **No review loop-back yet.** This is the initial plan derived from the
  approved specification and current brownfield code.
- **R-1:** Real canonical marts cannot currently be exercised because
  `docs/findings/data-prep-price-path.md` blocks dbt parsing. Fixture-based
  repository integration is planned; real-mart verification is deferred until
  the data-preparation owner repairs the price path.
- **R-2:** p2-003 does not yet exist, so its consumer integration is recorded as
  a named deferral rather than silently omitted. The p2-003 plan must exercise
  the calculator result contract end to end.
- **F-1 (round 1)** → Plan-review fix: added an Edge case test row for invalid
  request rejection (zero/negative servings, empty ingredients, over-limit
  count) at the schema/service boundary.
- **F-2 (round 1)** → Added an Edge case test row for unusable price evidence
  exclusion (missing, non-positive, stale, non-SGD).
- **F-3 (round 1)** → Added a per-nutrient independence test row covering
  AC-6/AC-7's intersection; Design §1 now names per-nutrient precedence
  explicitly.
- **F-4 (round 1)** → Cost is request-dependent. Design §3 states the condition
  (`request.budget is not None`) and AC-5 now has two test rows: the
  budget-present drop case and the budget-absent retain case.
- **F-1 (round 2)** → Plan revision: T-1..T-13 reframed for the prove-and-fix
  baseline. Existing calculator tests already cover AC-1, AC-2, and parts
  of AC-3/AC-4; the tasks now say "confirm and extend" for those and
  "implement" for the actual gaps (source precedence per nutrient,
  confidence selection, request-dependent cost, unusable-price-evidence
  rejection, invalid-request rejection, R-16 boundary assertion). Reason:
  T-1 as written required a failing test against already-passing behavior;
  the implement gate observed the baseline and stopped.
## Tasks

- [x] **T-1** Confirm and extend tests for nutrition scaling and aggregation (AC-1, AC-2)
    - Type: test
    - Covers: AC-1, AC-2
    - Files: `SystemCode/remy/api/tests/features/calculator/test_domain_nutrition.py`
    - Done when: existing tests covering AC-1/AC-2 are identified and confirmed passing; any uncovered case (per the spec's edge cases for null-preserving aggregation) is added as a new test. If the baseline fully covers AC-1 and AC-2, this task ticks with no new test and the existing tests are cited as the evidence.

- [ ] **T-2** Write failing tests for cost separation and eligibility (AC-3, AC-4, AC-5, Edge case: unusable price evidence)
    - Type: test
    - Covers: AC-3, AC-4, AC-5 (both budget-present and budget-absent rows), the unusable-price-evidence edge case
    - Files: `SystemCode/remy/api/tests/features/calculator/test_domain_cost.py`
    - Done when: tests exist and fail because consumed/package separation, multi-package counting, unusable-evidence exclusion, and the request-dependent cost-required outcome are not implemented.

- [ ] **T-3** Write failing tests for source precedence and per-nutrient independence (AC-6, AC-7, AC-8)
    - Type: test
    - Covers: AC-6, AC-7, AC-8, the per-nutrient independence row
    - Files: `SystemCode/remy/api/tests/features/calculator/test_domain_nutrition.py`
    - Done when: tests exist and fail because the deterministic per-nutrient precedence is not implemented.

- [ ] **T-4** Write failing tests for confidence-interval selection (AC-9, AC-10, AC-11)
    - Type: test
    - Covers: AC-9, AC-10, AC-11
    - Files: `SystemCode/remy/api/tests/features/calculator/test_domain_cost.py`
    - Done when: tests exist and fail because best-score selection with no floor and closed-interval validation are not implemented.

- [ ] **T-5** Write failing tests for conversion warnings and unit errors (AC-12)
    - Type: test
    - Covers: AC-12
    - Files: `SystemCode/remy/api/tests/features/calculator/test_domain_conversion.py`
    - Done when: tests exist and fail because assumed-unit warnings and unsupported-unit/invalid-quantity errors are not implemented.

- [ ] **T-6** Write failing tests for unresolved-ingredient rejection and invalid-request rejection (AC-13, Edge case: invalid request)
    - Type: test
    - Covers: AC-13 and the invalid-request edge case
    - Files: `SystemCode/remy/api/tests/features/calculator/test_service_integration.py`
    - Done when: tests exist and fail because the service returns a partial or zero-filled result rather than rejecting.

- [ ] **T-7** Write the failing integration tests for the two interfaces (repository → service, service → response)
    - Type: test
    - Covers: the two `## Integration per interface` rows
    - Files: `SystemCode/remy/api/tests/features/calculator/test_repository_integration.py`, `SystemCode/remy/api/tests/features/calculator/test_service_integration.py`
    - Done when: each integration test runs the real repository/service against a fixture producer and fails because the interface is not yet implemented. The p2-003 interface row is not written (deferred; see T-13).

- [ ] **T-8** Implement or confirm source-aware nutrition selection and aggregation (AC-1, AC-2, AC-6, AC-7, AC-8)
    - Type: impl
    - Covers: AC-1, AC-2, AC-6, AC-7, AC-8, per-nutrient independence
    - Files: `SystemCode/remy/api/src/api/features/calculator/domain/nutrition.py`, `SystemCode/remy/api/src/api/features/calculator/models.py`
    - Done when: T-1 and T-3 pass; AC-1/AC-2 behaviors confirmed present in the existing domain helpers; AC-6/AC-7/AC-8 (source precedence, tie-break, determinism, per-nutrient independence) implemented or confirmed present with new tests proving them.

- [ ] **T-9** Implement cost eligibility, separation, and best-score selection (AC-3, AC-4, AC-5, AC-9, AC-10, AC-11, Edge case: unusable price evidence)
    - Type: impl
    - Covers: AC-3, AC-4, AC-5, AC-9, AC-10, AC-11, the unusable-price-evidence edge case
    - Files: `SystemCode/remy/api/src/api/features/calculator/domain/cost.py`
    - Done when: T-2 and T-4 pass; unusable-evidence exclusion, consumed/package separation, closed-interval validation, best-score selection, and the request-dependent cost-required outcome are implemented.

- [ ] **T-10** Implement conversion warnings and unit validation (AC-12)
    - Type: impl
    - Covers: AC-12
    - Files: `SystemCode/remy/api/src/api/features/calculator/domain/` (conversion helper)
    - Done when: T-5 passes.

- [ ] **T-11** Implement request validation and unresolved-ingredient rejection (AC-13, Edge case: invalid request)
    - Type: impl
    - Covers: AC-13 and the invalid-request edge case
    - Files: `SystemCode/remy/api/src/api/features/calculator/schemas.py`, `SystemCode/remy/api/src/api/features/calculator/service.py`
    - Done when: T-6 passes; invalid requests and unresolved ingredients reject without a partial result.

- [ ] **T-12** Wire the repository projection and service orchestration (integration interfaces)
    - Type: impl
    - Covers: the two `## Integration per interface` rows
    - Files: `SystemCode/remy/api/src/api/features/calculator/repository.py`, `SystemCode/remy/api/src/api/features/calculator/service.py`, `SystemCode/remy/api/src/api/features/calculator/models.py`
    - Done when: T-7 passes; repository facts flow to the response with the R-16 boundary intact and audit provenance retained in the trace.

- [ ] **T-13** Run the full focused test suite and `sdd.py ci`; record deferrals
    - Type: verification
    - Covers: AC-1 through AC-13, all edge cases, both integration interfaces
    - Files: (all above)
    - Done when: `sdd.py ci p2-002-cost-nutrition-calculation` reports PASS; the deferred p2-003 interface test and real-mart execution are recorded in `decisions.md` with named follow-ups. Do not create a skipped placeholder test for the p2-003 interface; the obligation is named, not stubbed.
