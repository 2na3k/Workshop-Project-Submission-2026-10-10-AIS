---
feature: p2-001-constraint-evidence-filtering
---

# Plan - Constraint evidence filtering

## Approach

- **Chosen:** Extend the existing plan candidate-evaluation path so it evaluates
  each requested constraint against explicit evidence, records per-constraint
  outcomes plus a top-level drop cause, and returns retained recipes and
  ingredient-scoped warnings through the existing `PlanService` path. Add
  focused rule fixtures first, then fix the existing commented-out or missing
  checks and verify the repository-to-service path end to end.
- **Rejected alternative:** Add a parallel filtering service or infer missing
  evidence from ingredient text, because that would duplicate the existing
  API path, violate conservative R-5/R-7 behavior, and leave downstream callers
  with inconsistent outcomes.

## Design

1. **Candidate evidence hydration.** Extend the existing repository projection
   used by plan candidates so the filtering path receives the evidence required
   by R-5 through R-10: allergen and dietary evidence, nutrition presence and
   values, offer freshness, package quantity, and compatible unit-basis facts.
   Preserve the canonical graph direction and existing `BEST_FULFILLMENT` read
   path; do not introduce a second graph schema or a new data source.

2. **Constraint evaluation.** Replace the current implicit `failed` boolean
   behavior with explicit per-constraint evaluation. Each requested constraint
   produces a retained/pass, warning, present-evidence-excludes, or
   evidence-absent result as appropriate. Missing evidence is never converted
   to pass, compliance, or zero. Severe allergen matches exclude; mild matches
   retain with an ingredient-scoped warning; unknown dietary and nutrition
   evidence excludes as evidence-absent; stale offers are unavailable; and
   incompatible unit bases are not cost-eligible.

3. **Resolved clarification policy.** Apply the clarified constants and
   precedence directly in evaluation: an offer exactly 24 hours old is fresh,
   an older offer is stale; present-evidence-excludes is the top-level cause
   when both causes occur, while subordinate per-constraint outcomes remain
   available; allergen severity comes from the request and omitted severity is
   severe. No mapping-confidence floor or ranking behavior is changed.

4. **Outcome propagation.** Add the smallest domain-level outcome information
   needed for the plan service and downstream consumers to distinguish retained
   candidates, warnings, evidence-absent drops, present-evidence exclusions,
   and — distinctly — an unmapped requirement whose candidate set is empty.
   That last state is a third outcome from the two named in the roadmap's shared
   contract; where the two-cause vocabulary is consumed by p2-002/p2-003, the
   unmapped case is carried alongside without collapsing into either cause. If
   downstream consumers need `unmapped` in the named shared contract rather
   than as an additional field, that is a spec-level change routed upstream,
   not extended locally. Keep the plan response boundary free of audit-only
   provenance; this feature owns candidate evaluation, not the p3 response
   schema. Existing validation errors for unsupported allergen, dietary, and
   nutrient codes remain input errors rather than candidate drops.

5. **Fixture-first verification.** Add the constitution-named dietary-domain
   fixture coverage for R-5 through R-7 and calculator-domain fixture coverage
   for R-8 through R-10. Extend the existing calculator tests where they already
   own nutrition, cost, and conversion behavior; add the missing dietary and
   filtering outcome coverage at the domain boundary rather than testing only
   SQL text or commented code. Cover the mandatory fail-closed edge cases
   (isolate-able ingredient identity, partial nutrition profile, empty candidate
   set), the input-error / drop distinction, and the all-recipes-drop
   aggregation case with dedicated tests.

## Files to touch

- `SystemCode/remy/api/src/api/features/plan/filtering.py` — implement explicit
  per-constraint evaluation, clarified precedence, freshness boundary, the
  empty-candidate-set (unmapped) outcome, the input-error distinction, and
  evidence-absent/present-exclusion outcomes.
- `SystemCode/remy/api/src/api/features/plan/models.py` — carry the minimal
  candidate-evaluation and ingredient-warning information required by the
  filtering/service boundary, including the unmapped outcome field.
- `SystemCode/remy/api/src/api/features/plan/repository.py` — hydrate the
  freshness, package/unit-basis, and dietary/allergen evidence already present
  on canonical `FULFILLS` records for the real filtering path.
- `SystemCode/remy/api/src/api/features/plan/service.py` — propagate the real
  filtering outcome into the existing plan-generation result without redoing
  filtering or converting absent evidence into success.
- `SystemCode/remy/api/tests/features/dietary/test_domain_rules.py` — new
  fixture coverage for R-5, R-6, and R-7, including ingredient-scoped mild
  warnings, distinct drop causes, and the fail-closed case where the offending
  ingredient's identity cannot be isolated.
- `SystemCode/remy/api/tests/features/calculator/test_domain_nutrition.py` —
  extend coverage for R-9 profile absence and non-zero/non-pass behavior,
  including the partial-profile case where the requested nutrient's value is
  missing.
- `SystemCode/remy/api/tests/features/calculator/test_domain_cost.py` — extend
  coverage for R-8 freshness and evidence-absent no-fresh-offer behavior.
- `SystemCode/remy/api/tests/features/calculator/test_domain_conversion.py` —
  extend coverage for R-10 incompatible unit basis and evidence-absent drop.
- `SystemCode/remy/api/tests/features/plan/test_filtering.py` — new focused
  tests for retained outcomes, cause precedence, distinct causes, clarified
  severity defaults, the input-error / evidence-absent distinction, the
  empty-candidate-set outcome, and the all-recipes-drop aggregation case.
- `SystemCode/remy/api/tests/features/plan/test_service_integration.py` —
  end-to-end repository-to-filter-to-service test using the real API classes and
  a controlled driver dependency.

## Constitution alignment

- **R-5** → Missing, blank, or undeclared evidence produces an
  evidence-absent drop and is never treated as pass, compliance, or zero.
- **R-6** → Severe declared allergen excludes; mild declared allergen retains
  with an ingredient-scoped warning; undeclared allergen evidence drops as
  evidence-absent.
- **R-7** → Halal, vegan, and vegetarian requests retain only explicit compliant
  evidence; unknown, blank, and undeclared states drop as evidence-absent.
- **R-8** → Offers older than 24 hours are unavailable, the 24-hour boundary is
  inclusive, and no fresh offer produces an evidence-absent drop.
- **R-9** → A missing nutrition profile cannot satisfy a nutrient constraint or
  contribute zero; no profiled candidate produces an evidence-absent drop; a
  partial profile with the requested nutrient missing cannot satisfy the
  constraint and is not read as zero.
- **R-10** → Cost eligibility requires a compatible recipe/package unit basis;
  incompatible products are excluded and no compatible product drops as
  evidence-absent.
- **R-2** → Changes remain in the existing router/service/repository/model
  direction; workflow rule calls use their public rule functions and no feature
  imports another feature's internals.
- **R-3** → Uses the existing Python API, domain models, graph store, and
  constraint-solving shape; no parallel framework, store, or solver is added.
- **R-16** → Preserves the preconditions for R-16: candidate evaluation retains
  audit data internally, and the plan's user-facing response boundary is not
  widened by this feature.
- **R-17** → Preserves the preconditions for R-17: the outcome carries distinct
  evidence-absent and present-evidence-excludes causes at constraint granularity
  for p3-002 to render, without this feature owning the explanation surface.

## Test strategy

| AC | Test type | Test location / name | Notes |
|---|---|---|---|
| AC-1 | Unit fixture | `features/plan/test_filtering.py::test_unknown_constraint_evidence_drops_as_absent` | Parameterize unknown, blank, and undeclared states; assert the named constraint and absence from retained recipes. |
| AC-2 | Unit fixture | `features/plan/test_filtering.py::test_absent_evidence_is_not_pass_compliant_or_zero` | Assert no retained candidate, compliant state, or numeric zero is produced from absent evidence. |
| AC-3 | Unit fixture | `features/dietary/test_domain_rules.py::test_severe_allergen_drops_as_present_exclusion` | Assert the top-level cause is present-evidence-excludes and differs from evidence-absent. |
| AC-4 | Unit fixture | `features/dietary/test_domain_rules.py::test_mild_allergen_retains_with_ingredient_warning` | Assert retention and warning association to the offending ingredient identifier. |
| AC-4b | Unit fixture | `features/dietary/test_domain_rules.py::test_mild_allergen_without_ingredient_identity_fails` | **F-1a.** A mild match whose offending-ingredient identity cannot be isolated fails rather than attaching the warning to the recipe as a whole. |
| AC-5 | Unit fixture | `features/dietary/test_domain_rules.py::test_undeclared_allergen_drops_as_evidence_absent` | Assert unknown/undeclared allergen evidence cannot pass. |
| AC-6 | Unit fixture | `features/dietary/test_domain_rules.py::test_unknown_dietary_state_drops_and_explicit_compliance_retains` | Cover halal, vegan, and vegetarian request paths, including explicit compliant evidence. |
| AC-7 | Unit fixture | `features/calculator/test_domain_nutrition.py::test_profileless_candidate_is_not_zero_and_drops_when_required` | Assert missing profile contributes no value and no profiled candidate yields evidence-absent. |
| AC-7b | Unit fixture | `features/calculator/test_domain_nutrition.py::test_partial_profile_with_missing_requested_nutrient_is_not_zero` | **F-1b.** A present-but-partial profile where the requested nutrient's value is missing cannot be satisfied and is not read as zero. |
| AC-8 | Unit fixture | `features/calculator/test_domain_cost.py::test_stale_offer_excluded_and_24_hour_boundary_is_fresh` | Parameterize older-than-24-hour and exactly-24-hour offers; assert no-fresh-offer drop. |
| AC-9 | Unit fixture | `features/calculator/test_domain_conversion.py::test_incompatible_unit_basis_is_excluded_and_drops_when_only_option` | Assert incompatible product is not cost-eligible and the requirement drops when none remain. |
| AC-10 | Unit fixture | `features/plan/test_filtering.py::test_compliant_present_evidence_retains_without_drop_cause` | Assert retained result has null/absent cause, not a sentinel. |
| AC-11 | Unit fixture | `features/plan/test_filtering.py::test_absent_and_present_exclusion_causes_are_distinct` | Produce both outcomes in one run and compare cause values. |
| AC-12 | Unit fixture | `features/plan/test_filtering.py::test_present_exclusion_precedes_absent_evidence` | Combine severe allergen evidence with unknown dietary evidence; assert top-level precedence and retained subordinate outcomes. |
| AC-13 | Unit fixture | `features/dietary/test_domain_rules.py::test_missing_allergen_severity_defaults_to_severe` | Assert omitted request severity causes a matching candidate to drop as present-evidence-excludes. |
| AC-14 | Unit fixture | `features/plan/test_filtering.py::test_empty_candidate_set_is_reported_distinctly_from_constraint_drop` | **F-1c.** An empty candidate set (unmapped requirement) is reported distinctly from a drop caused by a failed or absent constraint on a resolved candidate. |
| AC-15 | Unit fixture (parameterized) | `features/plan/test_filtering.py::test_unsupported_codes_are_input_errors_not_evidence_absent` | **F-2.** Parameterize over unresolvable allergen key, unsupported dietary code, untracked nutrient code; each rejects as an input error, not as a drop. |
| AC-16 | Unit fixture | `features/plan/test_filtering.py::test_all_recipes_drop_returns_empty_pool_with_per_requirement_causes` | **F-3.** Every recipe drops for the same constraint; result is an empty eligible pool with per-requirement causes, not an unhandled error. |

## Integration per interface

| Interface (producer → consumer) | Test type | Test location / name | Notes |
|---|---|---|---|
| `PlanRepository.fetch_candidates` → `filter_candidates` | End-to-end API integration | `features/plan/test_service_integration.py::test_repository_evidence_reaches_filtering` | Run the real `PlanRepository`, `filter_candidates`, and `PlanService` with a controlled driver dependency returning canonical-shaped candidate rows. Assert repository-hydrated freshness, dietary/allergen, nutrition, and unit evidence changes the real service result; do not mock the code under test. |
| `filter_candidates` → `PlanService.generate` | End-to-end API integration | `features/plan/test_service_integration.py::test_service_propagates_distinct_filter_outcomes` | Invoke the real service with a fixture repository/driver, then assert retained recipes, ingredient warning behavior, and distinct drop-cause data observed at the service boundary. The solver dependency may be constrained with a minimal deterministic candidate set, but filtering and service execute for real. |
| canonical `FULFILLS` evidence projection → `PlanRepository` | Repository integration | `features/plan/test_service_integration.py::test_canonical_evidence_fields_are_consumed` | Feed rows using the canonical graph evidence vocabulary documented by the Neo4j design and assert the real repository maps those fields into `Ingredient` values consumed by filtering. A live Neo4j instance is not required because the external driver is the dependency being controlled. |

## Risks & mitigations

- **Existing filtering has disabled allergen/dietary checks and a single boolean
  failure path.** Write fixtures first and make the cause precedence explicit;
  do not preserve the old silent-retention behavior.
- **The repository query currently omits some evidence needed by R-8 and R-10.**
  Treat query hydration as part of this feature and add an integration assertion
  that canonical fields reach the filtering consumer.
- **The current `Ingredient` model has no explicit outcome fields.** Add only
  the minimal outcome contract required by the spec, including the unmapped
  outcome; avoid exposing audit-only provenance or redesigning p3 response
  models. If downstream consumers need `unmapped` in the shared cause vocabulary
  rather than an adjacent field, route to spec rather than extending locally.
- **The graph/data-preparation price-path finding remains unresolved.** Keep
  this feature's verification fixture-based as permitted by the p1 phase review;
  the repository-to-service integration uses controlled producer rows and must
  not claim an end-to-end real-mart demonstration.
- **A changed filtering result may affect plan solver behavior.** Use a minimal
  deterministic integration fixture and run the existing API package checks
  before review; failures outside this feature's stated outcome contract are
  routed upstream rather than silently relaxed.
- **Freshness timestamps and boundary arithmetic can be timezone-sensitive.**
  Use timezone-aware fixed test times and assert the 24-hour inclusive boundary
  explicitly.

## Scope check

Fits one working context: yes. The work is one API candidate-evaluation change
with focused rule fixtures and one repository-to-service integration path. It
must not expand into p2-002 cost/nutrient calculation, p2-003 solver behavior,
or p3 response/explanation design.

## Revision notes

- F-1 → Added test rows for the three mandatory fail-closed edge cases:
  mild allergen without isolate-able ingredient identity fails
  (`AC-4b`); partial nutrition profile with missing requested nutrient is not
  zero and cannot satisfy the constraint (`AC-7b`); empty candidate set is
  reported distinctly from a constraint drop (`AC-14`). All three were
  spec-mandated behavior with no test coverage.
- F-2 → Added a parameterized test asserting unresolvable allergen keys,
  unsupported dietary codes, and untracked nutrient codes reject as input
  errors, not as evidence-absent drops (`AC-15`). This is the input-error /
  drop distinction the spec names in Edge cases & errors.
- F-3 → Added a test for the all-recipes-drop aggregation case: empty eligible
  pool with per-requirement causes, not an unhandled error (`AC-16`).
- R-16 / R-17 alignment reworded from "satisfies" to "preserves the
  preconditions for," since neither rule's named check is touched by this
  feature. The outcome shape remains compatible with p3-002's explanation
  contract; the response boundary is not widened.
- Real-mart verification remains deferred under the roadmap's tracked
  `docs/findings/data-prep-price-path.md`; fixture-backed repository rows are
  the permitted verification boundary for this feature.

## Tasks

- [ ] **T-1** Write failing fixture tests for the dietary rules (R-5/R-6/R-7)
    - Type: test
    - Covers: AC-1, AC-2, AC-3, AC-4, AC-4b, AC-5, AC-6, AC-13
    - Files: `SystemCode/remy/api/tests/features/dietary/test_domain_rules.py`
    - Done when: each test in the AC-1..AC-6, AC-4b, AC-13 rows is written, exercises the real rule function, and fails for the reason the row describes (not an import error).

- [ ] **T-2** Write failing fixture tests for the calculator rules (R-8/R-9/R-10)
    - Type: test
    - Covers: AC-7, AC-7b, AC-8, AC-9
    - Files: `SystemCode/remy/api/tests/features/calculator/test_domain_nutrition.py`, `.../test_domain_cost.py`, `.../test_domain_conversion.py`
    - Done when: the four calculator-domain tests are written, exercise the real rule functions, and fail for the reasons their rows describe.

- [ ] **T-3** Write failing tests for the filtering outcome contract and edge cases
    - Type: test
    - Covers: AC-10, AC-11, AC-12, AC-14, AC-15, AC-16
    - Files: `SystemCode/remy/api/tests/features/plan/test_filtering.py`
    - Done when: the six filtering tests are written; each fails because the current filtering path doesn't produce the outcome the test expects (silent retention, missing causes, no input-error distinction, no empty-candidate-set handling).

- [ ] **T-4** Write the failing integration tests
    - Type: test
    - Covers: the three Integration per interface rows
    - Files: `SystemCode/remy/api/tests/features/plan/test_service_integration.py`
    - Done when: the three integration tests are written, run the real repository/filter/service with a controlled driver, and fail because the real path doesn't yet propagate evidence or causes as the plan specifies.

- [ ] **T-5** Implement explicit per-constraint evaluation in the filtering path
    - Type: impl
    - Covers: AC-1..AC-6, AC-7, AC-7b, AC-8, AC-9, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15
    - Files: `.../plan/filtering.py`, `.../plan/models.py`
    - Done when: T-1, T-2, T-3 pass; the filtering path produces per-constraint outcomes plus a top-level cause; absent evidence never passes; the precedence and severity-default rules apply; unsupported codes reject before evaluation; empty candidate sets report as unmapped.

- [ ] **T-6** Implement repository hydration and service propagation
    - Type: impl
    - Covers: AC-7, AC-8, AC-9, the three Integration per interface rows
    - Files: `.../plan/repository.py`, `.../plan/service.py`
    - Done when: T-4 passes; the repository hydrates the freshness, package/unit, and dietary/allergen evidence from canonical `FULFILLS` fields; the service propagates the real outcome without re-filtering or converting absent evidence to success.

- [ ] **T-7** Run the full API test suite and `sdd.py ci`
    - Type: verification
    - Covers: all ACs and interfaces
    - Files: (all above)
    - Done when: `pytest` passes for the API package; `sdd.py ci p2-001-constraint-evidence-filtering` reports `OVERALL: PASS`; the real-mart demonstration remains deferred under `docs/findings/data-prep-price-path.md` and is recorded as such.
