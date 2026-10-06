---
feature: p2-002-cost-nutrition-calculation
---

# Plan - Cost and nutrition calculation

## Approach

- **Chosen:** Extend the existing calculator domain/service/repository path with
  per-candidate food facts, source-aware nutrition selection, validated
  candidate metadata, compatible cost eligibility, deterministic ranking, and
  response/trace assertions; prove behavior first with focused calculator
  fixtures and one real service-path integration fixture.
- **Rejected alternative:** Resolve nutrition conflicts inside `QUERY_B` and
  hand the calculator a pre-winner profile. Rejected because the R-12
  precedence is a constitutional rule with a named check; keeping the
  resolution in the calculator makes the rule testable at the domain boundary
  and keeps the graph query a plain projection.

## Reference

**Evidence source for the three properties the selection requires:**
`node_food.nutrition_source`, `edge_fulfills.observed_at`, and
`edge_fulfills.listing_key` are canonical mart columns declared in
`SystemCode/remy/data-preparation/models/mart/schema.yml` and enumerated in
`SystemCode/remy/data-preparation/scripts/reproducibility_manifest.py`'s
`MART_CONTENT_COLUMNS`. Verified present by grep on 2026-10-06
(`nutrition_source` at schema.yml:35 and reproducibility_manifest.py:84;
`listing_key` at schema.yml:86 and reproducibility_manifest.py:129;
`observed_at` at schema.yml:172 and reproducibility_manifest.py:132).

p1-002-provenance-graph-model governs the *provenance* of linking records
(source, snapshot, confidence, version, freshness). The nutrition-source,
observation-timestamp, and product-identity fields are the marts' payload
content; they are governed by the mart schema contract, not by p1-002's edge
spec. `QUERY_B` extends to read these three canonical columns.

## Design

### 0. Baseline (prove-and-fix inventory)

The code already exists. This table records, per AC, what is present in the
codebase today, where it lives, and what must be added before a failing test
can be written. Task ordering follows from this table.

| AC | Behavior exists? | Field/surface exists? | What must be added first |
|---|---|---|---|
| AC-1 | Yes — scaling in `domain/nutrition.py` | n/a | — |
| AC-2 | Yes — null-preserving aggregation in `domain/nutrition.py` | n/a | — |
| AC-3 | Yes — cost helper produces consumed vs package cost; response carries `consumed_cost_sgd` and `retail_package_cost_sgd` | response fields exist | — |
| AC-4 | Yes — package counting via `RetailSKU.package_count` | `package_count` exists | — |
| AC-5 | No — no budget condition in the request | `CostNutritionRequest` has no `budget` | Add `budget: float \| None = None` |
| AC-6 | No — no source-kind field to discriminate on | nothing discriminates branded vs generic | Add `source_kind` to `FoodFacts`; project it in `QUERY_B` from `f.nutrition_source` |
| AC-7 | No — no timestamp, no product identity | `RetailSKU` has `fdc_id`, `listing_name` only | Add `observed_at: str \| None` and `product_id: str \| None` to `FoodFacts`; project `ful.observed_at` and `ful.listing_key` in `QUERY_B` |
| AC-8 | Follows AC-6/7 | — | — |
| AC-9 | Likely yes — selection exists; confirm no confidence gate | `RetailSKU.confidence` exists | Confirm selection path; no field add |
| AC-10 | Likely yes — confirm ranking key | as above | Confirm ranking key; no field add |
| AC-11 | No — `RetailSKU.confidence: float \| None` has no constraint | — | Add a `__post_init__` check to `RetailSKU` (frozen dataclass) that rejects confidence outside [0, 1] |
| AC-12 | Partially — conversion helper exists; `ItemWarning` exists on the response | `IngredientRequest.unit` is a `Literal`; `ItemWarning.code` is free-form | Confirm the warning's emission point and code |
| AC-13 | Likely yes — service rejects unresolved; confirm | — | Confirm the rejection path; no field add |
| F-1 edge case | Yes — Pydantic on `CostNutritionRequest` | — | — |
| F-2 edge case | No — no freshness field to test stale-price exclusion | `currency`, `reference_price_minor` exist; `observed_at` missing | Add `observed_at` (covered under AC-7) |

**Confirmed by reading** `models.py`, `schemas.py`, and `repository.py`. If the
implementation stage finds a row in this table is wrong, it stops and routes a
finding to `plan` — the inventory is the plan's premise, not a suggestion.

### 1. Model shape — per-candidate food facts

`FoodFacts.nutrients` is a single `NutrientProfile`. `QUERY_B` currently
returns one row per accepted candidate but `fetch_food_facts` groups by
`canonical_key` and constructs the profile once per key, so a second candidate
for the same key does not contribute a second profile. R-12's precedence
requires two competing profiles to exist simultaneously for the calculator to
arbitrate.

The fix: `fetch_food_facts` returns one `FoodFacts` per accepted candidate
(keyed by `candidate_key`, not `canonical_key`), each carrying its own
`NutrientProfile` and its own `source_kind`, `observed_at`, and `product_id`.
The calculator receives a **list of candidate facts for a concept** and applies
the per-nutrient precedence across them. This preserves the R-12 rule in the
calculator (where it is testable at the domain boundary) and keeps `QUERY_B` a
plain projection.

Consequences:
- `FoodFacts` gains `source_kind: str | None`, `candidate_key: str | None`,
  `observed_at: str | None`, `product_id: str | None`.
- The repository's return type changes from `dict[str, FoodFacts]` to
  `dict[str, list[FoodFacts]]` (concept → candidates).
- The service takes the candidate list and calls the domain selector.

### 2. Evidence projection and selection

Preserve, from the canonical graph query through the repository result, the
evidence needed to distinguish generic USDA nutrition from branded product
nutrition, compare crawl timestamps and product identifiers, rank mapping
scores, and retain confidence. Select one deterministic nutrient value **per
tracked nutrient**: branded over generic, newest branded observation, then
lexicographically smallest product identifier. Precedence is per nutrient, not
per candidate — within one concept, nutrient A may resolve to a branded value
while nutrient B resolves to a generic-only value, and both selections stand.
Reject duplicate conflicting evidence with the same product identity and
timestamp rather than choosing nondeterministically. Candidate selection
accepts the closed confidence interval [0, 1], applies no confidence floor,
ranks by score, and uses stable secondary ordering.

### 3. Portion nutrition

Keep the existing grams conversion and null-preserving scaling/summing
semantics. Ensure the selected profile is scaled by consumed grams, recipe
totals sum available nutrient values independently, and per-serving values
divide the total by the validated serving count. Preserve an explicit warning
for assumed non-mass conversions and never turn absent nutrient evidence into
zero.

### 4. Cost eligibility and result semantics

Treat only positive SGD package evidence with a positive amount and compatible
unit basis as cost-eligible. Exclude incompatible or unusable products before
selection. Calculate consumed cost proportionally to the used quantity and
retail cost from the whole-package count; expose both independently at item and
summary levels. The response schema already carries `consumed_cost_sgd`,
`retail_package_cost_sgd`, and the two summary totals — no response-shape
change is required for the separation itself.

**Cost is request-dependent.** The request supplies a budget constraint
(`request.budget` non-null); when present, cost is required for every
ingredient: an ingredient with no compatible, usable cost evidence is an
evidence-absent drop for the recipe. When `request.budget` is null, cost is
computed opportunistically — an ingredient with cost evidence gets both cost
fields, an ingredient without cost evidence is retained with cost marked
absent, and the calculation succeeds. The "cost is required" condition in the
spec's AC-5 is `request.budget is not None`. The freshness policy (24-hour
boundary, inclusive) is consumed from p2-001 and never re-implemented or
weakened here.

### 5. Boundary and trace

Run the real calculator service against a repository fixture at the service
boundary so repository-produced facts become the response consumed by the
API-facing result. Keep confidence and source metadata in the execution trace
only; assert that the public response retains the existing R-16 boundary. The
plan does not expand the public response to expose audit provenance.

### 6. Compatibility and validation

Make the smallest compatible changes to existing calculator models, repository
mapping, domain calculation helpers, and service orchestration. Validate
request errors through the existing Pydantic/application error boundary, and
preserve the established import direction. Existing p2-001 filtering remains
the owner of freshness and candidate constraint causes; this feature consumes
its outcomes. Request-level validation (servings, ingredient count) is already
enforced by `CostNutritionRequest`'s Pydantic field constraints.

## Files to touch

- `SystemCode/remy/api/src/api/features/calculator/models.py` — add
  `source_kind`, `observed_at`, `product_id`, and `candidate_key` to
  `FoodFacts`; add `__post_init__` validation on `RetailSKU.confidence`.
- `SystemCode/remy/api/src/api/features/calculator/repository.py` — extend
  `QUERY_B` with `f.nutrition_source`, `ful.observed_at`, `ful.listing_key`;
  change `fetch_food_facts` to return `dict[str, list[FoodFacts]]` (one per
  candidate).
- `SystemCode/remy/api/src/api/features/calculator/domain/cost.py` — cost
  eligibility, best-score selection, whole-package counting, separate
  consumed/package arithmetic, and the request-dependent cost-required outcome.
- `SystemCode/remy/api/src/api/features/calculator/domain/nutrition.py` —
  per-nutrient source precedence across candidates; null-preserving
  aggregation unchanged.
- `SystemCode/remy/api/src/api/features/calculator/service.py` — orchestrate
  candidate resolution, evidence selection, portion calculation, cost
  outcomes, warnings, and the audit-only execution trace.
- `SystemCode/remy/api/src/api/features/calculator/schemas.py` — add
  `budget: float | None = None` to `CostNutritionRequest`. Do not expose
  audit-only provenance in the user-facing schemas.
- `SystemCode/remy/api/tests/features/calculator/test_domain_cost.py` — cover
  compatible/incompatible packages, consumed/package separation, unusable
  price evidence, confidence boundaries, score ordering, deterministic ties,
  and the two budget-dependent rows.
- `SystemCode/remy/api/tests/features/calculator/test_domain_nutrition.py` —
  cover portion scaling, null-preserving aggregation, per-nutrient source
  precedence, timestamp/product-ID tie-breaking, per-nutrient independence,
  and repeatability.
- `SystemCode/remy/api/tests/features/calculator/test_domain_conversion.py` —
  cover assumed-unit warnings and invalid conversion behavior.
- `SystemCode/remy/api/tests/features/calculator/test_service_integration.py`
  — real repository-to-service-to-response fixture; request validation;
  unresolved-ingredient rejection; request-dependent cost-required outcome.
- `SystemCode/remy/api/tests/features/calculator/test_repository_integration.py`
  — canonical query-row projection into per-candidate `FoodFacts`.

## Constitution alignment

- **R-1** — Canonical graph property names; one calculator vocabulary; no
  legacy aliases.
- **R-2** — Dependency flow router/service/repository/models and pure
  calculation helpers inward.
- **R-3** — Python backend and graph-serving architecture retained.
- **R-5** — Missing resolution, nutrient evidence, or required cost evidence
  never becomes a passing result or zero.
- **R-8** — p2-001's inclusive 24-hour freshness rule reused.
- **R-9** — Profile-less and nutrient-missing evidence contributes no implicit
  zero.
- **R-10** — Cost selection admits only a compatible package/unit basis; drops
  the requirement as evidence-absent when none remains and cost is required.
- **R-11** — Consumed and whole-package costs exposed as distinct fields at
  item and summary levels.
- **R-12** — Branded, newest observation, lexicographically smallest product ID
  precedence; deterministic; per nutrient.
- **R-13** — Best-score selection, closed-interval [0, 1] confidence, no
  confidence floor; confidence retained in trace.
- **R-16** — Audit-only fields remain outside the user-facing response.

## Test strategy

| AC | Test type | Test location / name | Notes |
|---|---|---|---|
| AC-1 | unit | `test_domain_nutrition.py::test_portion_total_and_per_serving` | Confirm existing behavior. |
| AC-2 | unit | `test_domain_nutrition.py::test_partial_values_sum_without_zero_fill` | Confirm existing behavior. |
| AC-3 | unit | `test_domain_cost.py::test_consumed_and_single_package_cost_are_distinct` | Confirm existing behavior; assert P×Q/S versus P for Q<S. |
| AC-4 | unit | `test_domain_cost.py::test_multi_package_purchase_cost_is_whole_package_total` | Confirm existing behavior; assert ceil(Q/S)×P. |
| AC-5 | unit/contract | `test_domain_cost.py::test_incompatible_basis_is_excluded_and_required_cost_drops` | Budget-present: drop with evidence-absent cause. |
| AC-5 | unit/contract (negative) | `test_domain_cost.py::test_no_compatible_product_without_budget_retains_ingredient` | Budget-absent: ingredient retained, cost fields absent, calculation succeeds. |
| AC-6 | unit | `test_domain_nutrition.py::test_branded_value_precedes_generic_value` | Branded wins; generic-only remains usable. |
| AC-7 | unit | `test_domain_nutrition.py::test_branded_timestamp_then_product_id_tiebreak` | Newest timestamp, then lexicographic product ID. |
| AC-8 | repeatability | `test_domain_nutrition.py::test_conflict_selection_is_repeatable` | Identical evidence more than once, including equal timestamps. |
| AC-9 | unit | `test_domain_cost.py::test_zero_confidence_candidate_is_accepted` | Confidence 0 selectable and traceable. |
| AC-10 | unit | `test_domain_cost.py::test_best_score_beats_confidence_and_is_traceable` | Score ordering controls selection. |
| AC-11 | unit/validation | `test_domain_cost.py::test_confidence_closed_interval_validation` | 0 and 1 pass; outside fails without clamping. |
| AC-12 | unit/API boundary | `test_domain_conversion.py::test_assumed_unit_warning_and_invalid_quantity_errors` | Warning and conversion/validation failures. |
| AC-13 | service contract | `test_service_integration.py::test_unresolved_ingredient_is_rejected_without_zero_result` | Real service, empty producer result, reject. |
| AC-6, AC-7 (per-nutrient independence) | unit | `test_domain_nutrition.py::test_precedence_is_per_nutrient_independent` | One candidate where nutrient A resolves branded, nutrient B generic-only. |
| Edge case (invalid request) | service/schema validation | `test_service_integration.py::test_invalid_request_rejected_before_calculation` | Already Pydantic-enforced; test confirms rejection behavior. |
| Edge case (unusable price evidence) | unit | `test_domain_cost.py::test_unusable_price_evidence_excluded` | Missing, non-positive, non-SGD, stale (> 24h). |

## Integration per interface

| Interface (producer → consumer) | Test type | Test location / name | Notes |
|---|---|---|---|
| Canonical graph evidence rows → `CostNutritionRepository.fetch_food_facts` | repository integration | `test_repository_integration.py::test_canonical_rows_project_to_calculator_facts` | Real repository query/projection runs against the fake-driver producer fixture. Real-mart execution deferred per `docs/findings/data-prep-price-path.md`. |
| `CostNutritionRepository` facts → `CostNutritionService.calculate` → `CostNutritionResponse` | service integration | `test_service_integration.py::test_repository_facts_flow_to_public_cost_nutrition_response` | Real repository fixture, real service; mock only the Neo4j dependency if needed. Assert consumed/package costs, nutrients, warnings, and absence of audit-only fields. |
| Calculator result contract → p2-003 planning consumer | deferred integration | (no test file in this loop) | p2-003 not implemented. Deferral recorded in Revision notes and `decisions.md`; p2-003's plan writes the consuming integration test. |

## Risks & mitigations

- **Model shape change is broader than a field add.** `FoodFacts.nutrients` is
  a single profile; per-candidate facts are required for R-12. Mitigation:
  Design §1 pins the shape (list of candidate facts per concept). If the
  service's callers rely on the current `dict[str, FoodFacts]` shape, the
  change is breaking and the plan's scope grows; the implementer must stop and
  report if the shape change is larger than expected. Route to `plan` if so.
- **Current graph projection lacks conflict metadata.** `QUERY_B` omits
  `f.nutrition_source`, `ful.observed_at`, and `ful.listing_key`. Mitigation:
  add the three properties to the query. Confirmed present in the canonical
  mart schema (see Reference). If a property is absent from the deployed
  graph despite being in the schema, route to `spec`.
- **Current resolver score is not the graph mapping score.** The service
  re-resolves already returned canonical candidates and discards the returned
  confidence. Mitigation: preserve the repository candidate score and
  confidence through selection; test score and confidence separately.
- **Canonical real-data path is unavailable.** The data-preparation dbt project
  fails at parse on missing retail references. Mitigation: canonical-row
  fixtures and the existing fake-driver infrastructure; mark real-mart
  verification deferred; do not claim end-to-end data-pipeline evidence.
- **Tie behavior can become order-dependent.** Mitigation: explicit stable
  secondary keys and repeated-run tests, including identical timestamp cases.
- **Rounding can hide arithmetic defects.** Mitigation: assert raw domain
  arithmetic where possible; assert documented rounding only at the response
  boundary.

## Scope check

Fits one working context: yes. One calculator vertical slice — models,
repository query, domain helpers, service, and focused tests. The model shape
change is bounded (list-per-concept instead of dict-per-concept). The real
data-preparation repair and p2-003 consumer integration are external or
later-feature work and are explicitly deferred.

## Revision notes

- **Initial plan** derived from the approved specification and current
  brownfield code.
- **F-1 (round 1)** → Added an Edge case test row for invalid request rejection.
- **F-2 (round 1)** → Added an Edge case test row for unusable price evidence
  exclusion.
- **F-3 (round 1)** → Added a per-nutrient independence test row; Design §2
  names per-nutrient precedence explicitly.
- **F-4 (round 1)** → Cost is request-dependent; Design §4 states the
  condition and AC-5 has two test rows.
- **F-1 (round 2)** → Reframed test tasks for the prove-and-fix baseline;
  AC-1/AC-2/AC-3/AC-4 confirmed as existing.
- **F-2 (round 2)** → Split T-2: the model/schema/query field additions are a
  prerequisite task that precedes the tests that need them.
- **F-3 (round 2)** → Added Design §0 (Baseline inventory) and Design §1
  (Model shape: per-candidate food facts). Reordered tasks so the
  field-extension task precedes every test that depends on the fields. Reason:
  the plan assumed fields (`source_kind`, `observed_at`, `product_id`,
  `budget`) and a model shape (`FoodFacts.nutrients` holds two competing
  profiles) that the code does not have. Every test task that references those
  assumptions would have failed at its boundary exactly as T-2 did. The
  inventory is the plan's premise; the model shape is the spec's implicit
  contract, now made explicit.
- **F-4 (round 2)** → Added `## Reference` citing `models/mart/schema.yml` and
  `MART_CONTENT_COLUMNS` as the source of `nutrition_source`, `observed_at`,
  and `listing_key`, rather than implying p1-002's edge contract supplies them.
  Verified present in both files by grep, 2026-10-06. p1-002 governs
  linking-record provenance; the three fields are the marts' payload content,
  governed by the mart schema contract.

## Tasks

- [x] **T-1** Confirm existing nutrition scaling and aggregation tests (AC-1, AC-2)
  - Type: test
  - Covers: AC-1, AC-2
  - Files: `SystemCode/remy/api/tests/features/calculator/test_domain_nutrition.py`
  - Done when: existing tests for AC-1/AC-2 confirmed passing; no new test needed.

- [x] **T-2** Extend models, query, and schemas with the fields the tests need
  - Type: impl
  - Covers: prerequisite for AC-5, AC-6, AC-7, AC-8, AC-11, and the unusable-price-evidence edge case
  - Files: `models.py`, `repository.py`, `schemas.py`
  - Done when:
    * `FoodFacts` gains `source_kind`, `candidate_key`, `observed_at`,
      `product_id`.
    * `RetailSKU` gains `__post_init__` rejecting confidence outside [0, 1].
    * `QUERY_B` projects `f.nutrition_source`, `ful.observed_at`,
      `ful.listing_key`.
    * `CostNutritionRequest` gains `budget: float | None = None`.
    * `fetch_food_facts` returns `dict[str, list[FoodFacts]]` — one
      candidate per accepted `FULFILLS` edge.
    * Existing tests still pass; no behavior change implemented yet.
    * If a projected property is absent from the deployed graph despite
      being declared in `models/mart/schema.yml`, stop and route to `spec`.

- [ ] **T-3** Write failing tests for cost separation, eligibility, and the request-dependent condition (AC-3, AC-4, AC-5, edge case: unusable price evidence)
  - Type: test
  - Covers: AC-3, AC-4, AC-5 (both rows), unusable-price-evidence edge case
  - Files: `SystemCode/remy/api/tests/features/calculator/test_domain_cost.py`
  - Done when: tests exist and fail on the missing behavior. AC-3/AC-4 confirm the baseline; AC-5's two rows and the edge case are new.

- [ ] **T-4** Write failing tests for source precedence and per-nutrient independence (AC-6, AC-7, AC-8)
  - Type: test
  - Covers: AC-6, AC-7, AC-8, per-nutrient independence
  - Files: `SystemCode/remy/api/tests/features/calculator/test_domain_nutrition.py`
  - Done when: tests exist and fail because the deterministic per-nutrient precedence is not implemented.

- [ ] **T-5** Write failing tests for confidence-interval selection (AC-9, AC-10, AC-11)
  - Type: test
  - Covers: AC-9, AC-10, AC-11
  - Files: `SystemCode/remy/api/tests/features/calculator/test_domain_cost.py`
  - Done when: tests exist and fail on missing behavior. AC-9/AC-10 confirm the baseline; AC-11 is new.

- [ ] **T-6** Write failing tests for conversion warnings and unit errors (AC-12)
  - Type: test
  - Covers: AC-12
  - Files: `SystemCode/remy/api/tests/features/calculator/test_domain_conversion.py`
  - Done when: tests exist and fail on missing behavior.

- [ ] **T-7** Write failing tests for unresolved-ingredient and invalid-request rejection (AC-13, edge case: invalid request)
  - Type: test
  - Covers: AC-13, the invalid-request edge case
  - Files: `SystemCode/remy/api/tests/features/calculator/test_service_integration.py`
  - Done when: tests exist and fail on missing behavior.

- [ ] **T-8** Write failing integration tests for the two interfaces (repository → service, service → response)
  - Type: test
  - Covers: the two `## Integration per interface` rows
  - Files: `test_repository_integration.py`, `test_service_integration.py`
  - Done when: each integration test runs the real repository/service against a fixture producer and fails on the missing interface. The p2-003 row is not written (deferred).

- [ ] **T-9** Implement per-nutrient source precedence and aggregation (AC-6, AC-7, AC-8)
  - Type: impl
  - Covers: AC-6, AC-7, AC-8, per-nutrient independence
  - Files: `domain/nutrition.py`
  - Done when: T-4 passes; per-nutrient deterministic precedence across candidate facts implemented and repeatable.

- [ ] **T-10** Implement cost eligibility, selection, and the request-dependent condition (AC-3, AC-4, AC-5, AC-9, AC-10, AC-11, edge case: unusable price evidence)
  - Type: impl
  - Covers: AC-3, AC-4, AC-5, AC-9, AC-10, AC-11, the unusable-price-evidence edge case
  - Files: `domain/cost.py`, `models.py` (if validation moves there)
  - Done when: T-3 and T-5 pass; unusable-evidence exclusion, consumed/package separation, closed-interval validation, best-score selection, and the request-dependent cost-required outcome are implemented.

- [ ] **T-11** Implement conversion warnings and unit validation (AC-12)
  - Type: impl
  - Covers: AC-12
  - Files: conversion helper under `domain/`
  - Done when: T-6 passes.

- [ ] **T-12** Implement request validation and unresolved-ingredient rejection (AC-13, edge case: invalid request)
  - Type: impl
  - Covers: AC-13, the invalid-request edge case
  - Files: `schemas.py`, `service.py`
  - Done when: T-7 passes.

- [ ] **T-13** Wire repository projection and service orchestration (integration interfaces)
  - Type: impl
  - Covers: the two `## Integration per interface` rows
  - Files: `repository.py`, `service.py`, `models.py`
  - Done when: T-8 passes; repository facts flow to the response with the R-16 boundary intact and audit provenance retained in the trace.

- [ ] **T-14** Run the full focused test suite and `sdd.py ci`; record deferrals
  - Type: verification
  - Covers: AC-1 through AC-13, all edge cases, both integration interfaces
  - Files: (all above)
  - Done when: `sdd.py ci p2-002-cost-nutrition-calculation` reports PASS; the deferred p2-003 interface test and real-mart execution are recorded in `decisions.md` with named follow-ups. No skipped placeholder test for the p2-003 interface.
