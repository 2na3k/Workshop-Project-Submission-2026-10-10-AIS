# Roadmap

## Goals map

| Goal | Delivered in |
|------|--------------|
| G-1  | p2           |
| G-2  | p3           |
| G-3  | p2           |
| G-4  | p1           |
| G-5  | p1           |
| G-6  | p3           |
| G-7  | p1           |

## Brownfield note

The pipeline, the graph, a nutrient-calculation API, and a meal-planning API
already exist. Their code is not evidence that the phase exit criteria are met:
the criteria require demonstrations (manifests, gates, tests, provenance
checks), and pre-existing systems built before the constitution was written
generally lack them. Features below marked `existing` or `partial` describe the
work required to make that code **provable** against the constitution, not to
rebuild it. Where existing code violates a constitutional rule, the feature
description says "fix and prove"; where it is silent, the feature is "prove by
test"; where nothing exists, it is "new".

## Feature order & shared contracts

| Feature                                    | Status  | Depends on                                                                                                      | Shares contract with                                                                                              | Contract                                                                                                                             |
|--------------------------------------------|---------|-----------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| p1-001-reproducible-source-pipeline        | done    | —                                                                                                               | p1-002-provenance-graph-model, p1-003-coverage-quality-reporting                                                  | Source snapshot manifest and quality-gate result                                                                                     |
| p1-001b-test-infrastructure                | done    | p1-001-reproducible-source-pipeline                                                                             | p1-002-provenance-graph-model                                                                                     | Fake driver fixture and cloud Neo4j integration fixture for graph tests                                                              |
| p1-002-provenance-graph-model              | done    | p1-001-reproducible-source-pipeline, p1-001b-test-infrastructure                                                | p1-001-reproducible-source-pipeline, p1-001b-test-infrastructure, p1-003-coverage-quality-reporting              | Canonical graph schema and `REQUIRES`/`FULFILLS` provenance contract                                                                 |
| p1-003-coverage-quality-reporting          | done    | p1-001-reproducible-source-pipeline, p1-002-provenance-graph-model                                              | p1-001-reproducible-source-pipeline, p1-002-provenance-graph-model                                                | Coverage dimensions and graph quality manifest                                                                                       |
| p2-001-constraint-evidence-filtering       | done    | p1-002-provenance-graph-model                                                                                   | p2-002-cost-nutrition-calculation, p2-003-feasible-meal-plan-solving                                              | Candidate evaluation outcome and distinct evidence-absent/present-exclusion causes                                                   |
| p2-002-cost-nutrition-calculation          | done    | p1-002-provenance-graph-model, p2-001-constraint-evidence-filtering                                             | p2-001-constraint-evidence-filtering, p2-003-feasible-meal-plan-solving                                           | Portion nutrient and consumed/package cost result contract; item-level evidence-absent signals (`MISSING_PACKAGE_DATA`, `PARTIAL_NUTRITION_DATA`) consumed by p2-003 as the recipe-level drop trigger (per-nutrient for partial nutrition) |
| p2-003-feasible-meal-plan-solving          | partial — impl complete | p2-001-constraint-evidence-filtering, p2-002-cost-nutrition-calculation                                         | p2-001-constraint-evidence-filtering, p2-002-cost-nutrition-calculation                                           | Plan feasibility result with named binding constraints (deterministic individually-binding set), reasoning structure sufficient for downstream explanation, and the recipe-level nutrition drop behavior consuming p2-002's item-level `PARTIAL_NUTRITION_DATA` signal (per-nutrient for tracked nutrients). Cost/budget out of scope; recipe-level cost drop deferred to p3-004. |
| p3-001-workflow-recommendation-service     | done    | p2-003-feasible-meal-plan-solving                                                                               | p3-002-explainable-response-contract, p3-003-web-planner-experience, p3-004-conversational-constraint-interface   | Recommendation execution result and trace boundary                                                                                   |
| p3-002-explainable-response-contract       | done    | p2-001-constraint-evidence-filtering, p2-002-cost-nutrition-calculation, p3-001-workflow-recommendation-service | p3-001-workflow-recommendation-service, p3-003-web-planner-experience, p3-004-conversational-constraint-interface | Three-level user explanation and audit-provenance separation                                                                         |
| p3-003-web-planner-experience              | out of scope | p3-001-workflow-recommendation-service, p3-002-explainable-response-contract                                    | p3-001-workflow-recommendation-service, p3-002-explainable-response-contract                                      | Web request/response contract for meal-plan recommendations. **Owned by a separate frontend effort, not this SDD effort.** |
| p3-004-conversational-constraint-interface | new     | p3-001-workflow-recommendation-service, p3-002-explainable-response-contract                                    | p3-001-workflow-recommendation-service, p3-002-explainable-response-contract, p3-003-web-planner-experience       | Conversational constraint extraction, turn-level recommendation delivery, safe re-expression of deterministic explanation causes, **and the recipe-level cost drop inherited from R-8/R-10 per A-006** |

## Phase p1 - reproducible data and graph foundation

Status: done (external dependency tracked)

### Outcome

A reproducible, quality-gated canonical data foundation is available for recipe
requirements, normalized food concepts, nutrition profiles, products, and dated
retail offers. Graph links retain the provenance needed by downstream reasoning
and the graph can be refreshed only from an accepted quality manifest.

Existing pipeline and graph code is present. This phase makes that code
**provable**: it adds the source snapshot manifest, the quality gate that blocks
refresh on a failed manifest, the schema-conformance test, the edge-provenance
test, and the coverage report. Where existing code violates a constitutional
rule (R-1, R-4, R-15), this phase fixes it.

### Goals served

- G-4
- G-5
- G-7

### Features

- **p1-001-reproducible-source-pipeline** *(done, 2026-10-03)* — Source snapshot
  manifest emitted; deterministic source and mart content checksums computed;
  reproducibility checker wired into the Makefile and CI. One loop-back (review
  findings F-1..F-11 resolved; F-3 deferred under override O-1). Follow-up:
  resolve `docs/findings/data-prep-price-path.md` and pin the real reference
  checksums (see
  `docs/sdd/features/p1-001-reproducible-source-pipeline/decisions.md` O-1).
  (serves G-7)
- **p1-001b-test-infrastructure** *(done, 2026-10-04)* — Graph test
  infrastructure: a fake driver/session/transaction fixture for orchestration
  tests that must not touch a live Neo4j, and a cloud Neo4j integration fixture
  (dedicated instance configured via `.env.test` or CI secrets) for real
  write/read tests. The integration fixture skips locally when unconfigured and
  fails under CI, so a skipped integration test in CI is a CI failure. CI
  workflow added. No production code changes. (enables G-4, G-7 for downstream
  features)
- **p1-002-provenance-graph-model** *(done, 2026-10-05)* — Provenance-preserving
  canonical graph model: canonical edge vocabulary on `REQUIRES` and `FULFILLS`
  (source, snapshot, mapping/normalization version, confidence, observation);
  fail-closed manifest admission in the serving model; canonical property
  allowlists enforced with legacy aliases rejected; reject-don't-repair for
  missing provenance; MERGE idempotence on identity keys. One loop-back (F-1, F-2,
  F-3 and the README nit resolved). dbt singular test execution deferred pending
  `docs/findings/data-prep-price-path.md` (documented in the feature's
  decisions.md D-4). (serves G-4, G-7)
- **p1-003-coverage-quality-reporting** *(done, 2026-10-05)* — Coverage and
  quality reporting: a five-dimension report (`nutrition_coverage`,
  `price_availability`, `package_unit_conversion_coverage`,
  `dietary_evidence_coverage`, `whole_recipe_completeness`) derived from the
  canonical marts, with deterministic counts and bounded percentages; a
  `association` block in the reproducibility manifest (source snapshot id,
  input-mart content checksum, deterministic build id); a runtime
  fail-closed guard refusing the report when the association is unset; the
  model gated behind `enabled=var('enable_coverage_report')` so the general
  build doesn't require its prerequisites. Three loop-backs (round-1: tests
  were SQL-text greps; round-2: association producer missing and unverified;
  round-3: runtime guard, manifest-comparison test, Makefile ordering). The
  dbt singular test and the real-mart demonstration are deferred pending
  `docs/findings/data-prep-price-path.md` (recorded in the feature's
  decisions.md D-1). (serves G-5)

### Exit criteria

- A clean rebuild from the declared source snapshots produces the canonical
  marts and a quality manifest with deterministic entity and relationship
  counts. *Deferred pending `docs/findings/data-prep-price-path.md`: the
  project cannot parse because `stg_retail_listing.sql` references nodes that
  no producer creates. The deterministic content checksums and the
  reproducibility checker are verified against fixtures; the real-build
  demonstration is a tracked follow-up owned by the data-preparation
  package.*
- The quality gate rejects dangling `REQUIRES` or `FULFILLS` references and
  prevents graph refresh when the manifest is not accepted. *Satisfied by
  p1-002's `test_dangling_endpoint_blocks_load` and the failing-manifest
  fixtures.*
- Schema-conformance and edge-provenance checks pass for the canonical property
  names and for every populated `REQUIRES` and `FULFILLS` linking record.
  *Satisfied by p1-002's `test_schema_conformance.py` and
  `test_edge_provenance.py`.*
- The coverage report exposes separate measurements for nutrition, price
  availability, package-unit conversion, dietary evidence, and overall recipe
  completeness. *Satisfied by p1-003's `test_coverage_quality_report.py`
  (18 tests).*
- **Conformance clause:** every p1 feature that touches pre-existing code has a
  passing test or CI command demonstrating that the code satisfies its exit
  criteria. "The code exists" is not evidence. Graph test infrastructure
  (p1-001b) is a prerequisite for the graph conformance demonstrations in
  p1-002 and p1-003; those features cannot close without it. *Satisfied: p1-001b
  closed 2026-10-04.*
- No unresolved blocking findings. *p1-001's F-3, p1-002's T-5/T-12, and
  p1-003's T-15 and real-mart demonstration are deferred pending
  `docs/findings/data-prep-price-path.md`. The phase exits with these deferrals
  tracked; the phase review decides whether the finding must resolve before p2
  begins.*

### Risks & unknowns

- The existing pipeline may not preserve source provenance in a form that can be
  turned into a manifest without rework. If so, the rework is in scope for
  p1-001 and the effort is larger than the "partial" status implies.
  *Realized: p1-001 surfaced that the pipeline had never been built end to end
  in this repo state; the price-path finding blocks the reproducible build.*
- The existing graph may accept more than one property name for a concept
  (legacy naming from before the constitution). R-1 makes this a violation and
  the fix is part of p1-002 — this may affect the deployed schema and require a
  migration. *Realized: p1-002 enforced the canonical allowlist; legacy aliases
  are rejected at load. No migration was required because the deployed graph
  already used the canonical names.*
- Coverage measurement may reveal gaps that were previously invisible. Gaps are
  reported, not hidden; closing them is not p1's job.
- Retail crawling is constrained by the absence of a public API and price
  snapshots become stale; the accepted snapshot policy and freshness metadata
  must remain explicit.
- The integration tests depend on a configured cloud Neo4j instance
  (`NEO4J_TEST_URI`). If the instance is idle-paused, unreachable, or the
  credentials are wrong, CI fails (per p1-001b's D-2). The instance must remain
  available for the phase to keep passing.
- **Deferred dbt execution consolidates into the data-preparation price-path
  finding.** p1-001's F-3, p1-002's T-5/T-12, and p1-003's T-15 and real-mart
  demonstration all block on the same upstream defect:
  `models/staging/stg_retail_listing.sql` references `retail_aisle_listing`
  and `retail_search_listing`, which no model, seed, or source produces. The
  seeds themselves are present and used by the other staging models. Every
  `dbt` command fails at parse. **The data-preparation package is not owned by
  this effort; the fix is the package owner's.** The phase review must decide
  whether this external dependency blocks the phase exit or becomes a p2
  prerequisite. p2's features read the canonical marts; without a working
  pipeline those reads are fixture-based. See
  `docs/findings/data-prep-price-path.md`.

### Phase p1 progress

- p1-001: closed 2026-10-03, 1 implementation loop. Follow-up: the price-path
  finding.
- p1-001b: closed 2026-10-04, 0 loops.
- p1-002: closed 2026-10-05, 1 implementation loop. dbt singular test execution
  deferred pending the price-path finding.
- p1-003: closed 2026-10-05, 3 implementation loops. dbt singular test
  execution and real-mart demonstration deferred pending the price-path
  finding.

**Phase p1 totals:** 4 features closed; 5 loops (p1-001: 1, p1-001b: 0,
p1-002: 1, p1-003: 3). Every loop was verification or plumbing, none was a
design failure. Phase exit is pending the phase review's decision on the
data-preparation price-path finding.

## Phase p2 - deterministic constraint evaluation and plan solving

Status: done

### Outcome

The reasoning core evaluates explicit nutrition, allergen, dietary, freshness,
unit, and budget constraints conservatively, computes distinct consumed and
package costs, and returns a feasible meal plan only when the requested horizon
can be satisfied.

A nutrient-calculation API and a meal-planning API already exist. This phase
makes them **provable against the constitution**: it adds the fixtures that
demonstrate R-5 through R-14, fixes any behavior those fixtures reveal to be
non-conformant, and ensures the solver's output carries the reasoning structure
p3 needs.

**Prerequisite:** `docs/findings/data-prep-price-path.md` must resolve before
p2's features can read the canonical marts against real data. Until then, the
project cannot parse, `dbt` cannot run, and p2's reasoning is verified with
fixtures only. The phase review set the p2 posture to "proceed with fixtures,"
tracking the finding as a p2 risk.

### Goals served

- G-1
- G-3

### Features

- **p2-001-constraint-evidence-filtering** *(done, 2026-10-05)* — Constraint
  evidence filtering: explicit per-constraint evaluation (allergen, dietary,
  nutrient, freshness, unit-basis) producing retained, warned,
  present-evidence-excludes, or evidence-absent outcomes; distinct drop causes
  with fixed precedence (present-evidence-excludes before evidence-absent);
  ingredient-scoped warnings for mild allergens; input-error rejection for
  unsupported codes; conservative defaults (unspecified allergen severity →
  severe; offer freshness threshold 24h inclusive). Internal outcome models
  (`CandidateOutcome`, `ConstraintEvaluation`, `IngredientWarning`,
  `FilterResult`) carry cause history without widening the user response
  boundary. Zero loops. Pre-existing API baseline failures excluded from the
  feature's CI and recorded in the feature's decisions.md D-1. (serves G-1)
- **p2-002-cost-nutrition-calculation** *(done, 2026-10-08)* — Cost and
  nutrition calculation: prove-and-fix against the amended constitution
  (R-1, R-5, R-8, R-9, R-10, R-11, R-12, R-13, R-16). The repository now
  reads the deployed canonical property names (`confidence`, not the stale
  `mapping_confidence`) and projects the full evidence contract (nine
  canonical nutrients, `food_key`, `price_status`, `price_match_status`,
  `freshness_status`, `price_basis`, `package_volume_ml`, `nutrition_rank`,
  `selection_priority`). Cost eligibility is enforced in `domain/cost.py` per
  amended R-10: `price_status == "estimated"`, `price_match_status ==
  "accepted"`, `freshness_status == "fresh"`, `price_basis in {package_mass,
  package_volume}`, SGD, positive price, positive amount;
  `cost_basis_compatible` is informational and does not gate selection.
  `package_volume` is converted to grams silently via `domain.units.to_grams`.
  Per-nutrient conflict precedence is implemented in
  `domain/nutrition_select.py` per amended R-12 (branded over generic;
  smallest `(nutrition_rank, selection_priority, food_key)` tuple, nulls
  last) and applied per nutrient. Nutrient totals are null-when-any per
  amended R-9. Item-level evidence-absent signals (`MISSING_PACKAGE_DATA`,
  `PARTIAL_NUTRITION_DATA` with the missing nutrient names) are emitted;
  recipe-level drops are p2-003's. Best-score cost selection with no
  confidence floor, in the R-13 ordering. Audit-only provenance is retained
  in a new `CalculationTrace`; the router returns only the public response
  (R-16). `MAX_REQUEST_INGREDIENTS = 100` is a named constant. Two
  loop-backs: one to the plan (T-20's file scope omitted `router.py`; F-E),
  one to the spec (the initial spec's freshness and eligibility rules did not
  match the deployed schema, resolved by amendments A-001..A-004). (serves
  G-1, G-3)
- **p2-003-feasible-meal-plan-solving** *(partial — implementation complete,
  pending phase review of data findings)* — Existing planning API. The plan
  path is implemented: satisfiable requests return a plan; unsatisfiable
  requests return no plan with a deterministic set of individually-binding
  constraints (R-14, per A-005); the plan result carries three-level reasoning
  (plan / recipe / constraint) with distinct drop causes and precedence
  `present-evidence-excludes` → `evidence-absent` → `unmapped`; the
  user-facing response excludes audit provenance; the trace is separate from
  p2-002's `CalculationTrace`. p2-003 consumes p2-002's item-level
  `PARTIAL_NUTRITION_DATA` signal per tracked nutrient. Cost and budget are
  out of scope (A-006); the recipe-level cost drop is deferred to p3-004.
  Solver-unavailable is a hard failure.

  **Implementation surfaced a systemic data-coverage problem** that limits the
  plan's usable candidate pool. Every filter the plan correctly applies removes
  most of the recipe graph:

  | Filter | Recipes removed | Source |
    |---|---:|---|
  | `REQUIRES` edges with null/zero `quantity` or `unit` | ~12,892 of ~15,000 (86%) | Recipe parser |
  | No `BEST_FULFILLMENT` for a required `FoodConcept` | ~13,197 (88%) | `FULFILLS` coverage: 2,532 of 31,630 concepts have products |
  | `Food` node missing one or more canonical nutrients | 1,643 of 8,966 Foods (18%) | Nutrition pipeline |
  | Sparse dietary/allergen evidence | 5,408 of 9,700 `FULFILLS` edges (56%) have `unknown` allergen status; halal/vegetarian non-`unknown` on <2% of edges | Screening pipeline |
  | No recipe yield (`servings`/`yield`) | ~all | Recipe dataset |

  The intersection is a small fraction of the graph. Recipes that survive all
  filters are dominated by a subset with complete coverage on every dimension,
  which is why the plan's output looks nutritionally odd (sauces and
  condiments as "meals", whole-batch nutrient totals reported as one serving).

  **The plan's behavior is correct given the data.** The findings are
  data-preparation problems, not p2-003 bugs. See "Phase p2 data-quality
  findings" below for the full list. (serves G-1)

### Exit criteria

- A request whose `horizon_days × meals_per_day` can be satisfied by the
  eligible recipes returns a plan that fills every `(day, meal)` slot
  (R-14's producible direction). *To be satisfied by p2-003's
  `test_domain_solver.py` fixture.*
- A request that cannot be satisfied after filtering, dropping, and the
  permitted nutrient-tolerance relaxation returns no plan and names a
  deterministic minimal set of binding constraints (R-14's infeasibility
  direction). *To be satisfied by p2-003's `test_domain_solver.py` fixture.*
- A recipe that is evidence-absent for any tracked nutrient is dropped from the
  plan pool with an `evidence-absent` cause categorized under the affected
  nutrient's constraint (R-9's recipe-level drop). *To be satisfied by p2-003's
  fixture, consuming p2-002's `PARTIAL_NUTRITION_DATA`.*
- The plan result exposes three-level reasoning (plan / recipe / constraint)
  with distinct drop causes (`evidence-absent`, `present-evidence-excludes`,
  `unmapped`) and their precedence. *To be satisfied by p2-003's fixture,
  consuming p2-001's outcomes.*
- The user-facing plan response excludes audit-only provenance; the plan-level
  trace (separate from p2-002's `CalculationTrace`) carries it. *To be
  satisfied by p2-003's response-schema fixture.*
- Cost and budget evaluation is out of scope for p2; the recipe-level cost
  drop is deferred to p3-004-conversational-constraint-interface. *Recorded
  per A-006. The deferral crosses the p2→p3 phase boundary; p3-004's entry
  names the inherited obligation, and the phase p2 review acknowledges that
  R-8's and R-10's recipe-level check fixtures are owned by p3-004, not by any
  p2 feature.*
- No unresolved blocking findings. *p2-002's F-A (p2-001 freshness predicate:
  timestamp branch retained as latent), F-B (p2-001 cost-basis predicate:
  behavioral, open), F-C (data-prep real-mart deferral), F-D (R-16 test-path
  divergence), and N-1 (cross-feature test imports) are tracked for phase
  review. p2-003's A-005 and A-006 are new amendments; their impact is tracked
  above.*
- **Data-coverage acknowledgment.** The phase exits with the DQ-1..DQ-7
  findings tracked (see "Phase p2 data-quality findings"). The plan's
  candidate pool is limited by the deployed graph's coverage; the plan's
  behavior is correct given the data. The phase review decides whether the
  findings block the p2→p3 transition or are tracked as data-preparation
  follow-ups.

### Risks & unknowns

- **p2-001 freshness predicate verification (carried).** The amended R-8 makes
  freshness enforcement dual-layer. p2-001's `_evaluate_freshness` still
  contains a timestamp branch (`now - offer_observed_at <= 24h`) that predates
  the amendment. Confirm where `offer_observed_at` is populated: if from a
  non-existent `FULFILLS` property, the branch is dead and the effective rule
  is already status-based (cleanup, not behavior); if from
  `BEST_FULFILLMENT.selected_at` or another source, the branch fires and
  measures the wrong thing (behavioral). Either way the code should express
  only the status rule.
- **p2-001 `cost_basis_compatible` check.** If p2-001's filtering treats
  `cost_basis_compatible = FALSE` as ineligible, it is non-conformant with the
  amended R-10 (which uses `price_status`/`price_match_status`/`price_basis`,
  not the flag). A p2-001 finding.
- **`Nutrients` DTO `calcium_mg`/`iron_mg` population state.** The p2-002 spec
  keeps the DTO's two extras and documents them as always null. If they are
  currently populated from a source, the spec would regress them, and either
  the spec or the DTO needs a different treatment. Verify the live response
  before freezing the p2-002 spec.
- **`data-prep-price-path` finding** (carried from p1): real marts cannot be
  built; p2's features are verified with fixtures only.
- **p2-003's R-14 relaxation set depends on A-005.** Until A-005 is approved,
  p2-003's spec asserts a reading of R-14 that the constitution does not yet
  express. A-005 names the permitted relaxation set (nutrient-bound widening
  only) and prohibits structural relaxations. If A-005 is rejected, the
  existing solver's relaxation ladder (repeats, no-consecutive) remains
  constitutionally unclassified and p2-003's spec must be revised.
- **The recipe-level cost drop is deferred to p3-004 (A-006)**. R-8 and R-10
  name a recipe-level cost drop that p2-003 does not implement (cost out of
  scope). A-006 amends R-8/R-10 so the calculator's item-level
  `MISSING_PACKAGE_DATA` signal is the sole cost enforcement point in p2.
  p3-004-conversational-constraint-interface owns the recipe-level cost drop
  and, when it ships, asserts R-8's and R-10's recipe-level fixtures. The
  deferral crosses the p2→p3 phase boundary; if p3-004's scope changes (for
  example, if budget evaluation moves to a different feature), the owner
  named in A-006 must be re-amended.
- **p2-001 F-B (cost-basis predicate) affects the pool p2-003 sees.** If
  p2-001's `_evaluate_cost_basis` continues to gate on
  `cost_basis_compatible`, the candidate pool p2-003 receives is smaller than
  amended R-10 permits (~63 eligible `package_mass` rows filtered out). Cost is
  out of scope for p2-003, so this does not change p2-003's behavior directly;
  but the shared contract with the future budget feature is affected. Triage
  F-B before the budget feature's plan.
- **Systemic data-coverage gap in the deployed recipe graph (surfaced by
  p2-003).** Seven findings (DQ-1..DQ-7, see "Phase p2 data-quality findings")
  describe coverage gaps that together reduce the plan's usable candidate
  pool to a small fraction of the recipe graph. The plan's behavior is correct
  at each filter; the graph's coverage is the limiting factor. The phase
  review must decide the posture: proceed with the current coverage, or
  block phase p2 exit pending data-preparation fixes. Findings DQ-2 and DQ-3
  are the largest (86% and 88% of recipes removed respectively); their
  intersection with the other filters leaves a very small usable set. **Owner:**
  data-preparation. Tracked for phase review.

### Phase p2 progress

- p2-001: closed 2026-10-05, 0 loops. Pre-existing API baseline failures
  excluded from the feature's CI (see the feature's decisions.md D-1).
- p2-002: closed 2026-10-08, 2 loops (plan: T-20's router file scope; spec:
  freshness/eligibility rule alignment). Five follow-ups carried to phase
  review: F-A and F-B (p2-001 freshness and cost-basis predicates), F-C
  (data-prep real-mart deferral, shared with p1), F-D (R-16 named check path
  divergence from the constitution), N-1 (cross-feature test imports). CI
  PASS on the corrected check set (`tests/features/calculator`,
  `src/api/features/calculator`).
- p2-003: implementation complete (pending phase review of data findings).
  The plan path is implemented; all acceptance criteria are covered by
  fixtures. CI PASS on `tests/features/plan` and the extended
  `tests/features/calculator` check set. Seven data-quality findings
  (DQ-1..DQ-7) surfaced during implementation; all are upstream of p2-003
  in the data-preparation package. The plan's output quality is limited by
  the graph's coverage, not by the plan's logic. See "Phase p2 data-quality
  findings."

### Phase p2 data-quality findings

The p2-003 implementation surfaced the following data problems in the deployed
recipe graph. They are owned by the data-preparation package, not by any p2
feature. The phase review must decide whether to track them as p3 blockers or
accept the current coverage for the phase p2 exit.

**Finding DQ-1 — no recipe yield.** `Recipe` nodes carry
`[recipe_id, source, source_license, Title, Instructions, Image_Name,
projection_owner]` — no `servings`, `yield`, or `portions` field. The plan
reports whole-recipe nutrient totals as one meal. A "Big-Batch Parmesan
Polenta" (yields ~8-10 servings) is reported as 1900 kcal and 14,655mg sodium
for one meal; the arithmetic is correct for the whole recipe, but the
semantics (recipe vs. serving) are unsupported. **Owner:** data-preparation.
Add a `servings`/`yield` property from the raw recipe dataset.

**Finding DQ-2 — `REQUIRES` edges with null/zero quantity or unit.**
12,892 of ~15,000 recipes (86%) have at least one `REQUIRES` edge whose
`unit` is null, empty, or the string `"null"`, or whose `quantity` is null or
zero. The plan filters those recipes out at the query level rather than
guessing a unit (guessing would silently zero the ingredient). **Owner:**
data-preparation. The recipe parser that emits `REQUIRES` edges produces
null `unit` or `quantity` for most recipes; that is a parsing gap.

**Finding DQ-3 — `FoodConcept` vocabulary has thin `FULFILLS` coverage.**
31,630 concepts total; 2,532 have any `FULFILLS` edge (8%); 29,098 have none.
`BEST_FULFILLMENT` is correctly built for the 2,532 that have `FULFILLS`
(one-to-one match verified). 60,341 `REQUIRES` edges across 13,197 recipes
(~88% of the graph) point at concepts with no `BEST_FULFILLMENT`, so those
recipes are dropped for `unmapped`. **Owner:** data-preparation. Either the
product→concept matching is too strict, or the product set is too small
relative to the concept vocabulary.

**Finding DQ-4 — sparse dietary and allergen evidence.** `FULFILLS` edges:
9,700 total. `halal_status`: 160 non-`unknown` (1.6%). `vegetarian_status`:
1,241 non-`unknown` (12.8%). `allergen_screening_status`: 5,408 `unknown`
(56%). `may_allergic`: 4,292 `TRUE`, 5,408 `FALSE`. Dietary-filtered and
allergen-filtered requests operate on a small non-`unknown` slice; recipes
with `unknown` status on a declared constraint are dropped. **Owner:**
data-preparation. Broaden the dietary/allergen screening coverage.

**Finding DQ-5 — `REQUIRES` unit vocabulary is inconsistent.** The
`_UNIT_TO_GRAMS` table covers ~40 units. The recipe dataset uses arbitrary
strings, some outside the table (`"tbsp."`, `"T"`, `"c"`, `"large"`,
`"small"`). Unrecognized units raise `UnitConversionError`, and the caller
skips the ingredient — a second silent-zero path distinct from DQ-2.
**Owner:** data-preparation (normalize the unit field) or the domain layer
(extend the table and use the error signal to surface the gap rather than
swallow it).

**Finding DQ-6 — 18% of `Food` nodes have a missing canonical nutrient.**
1,643 of 8,966 `Food` nodes (18%) have at least one of the nine canonical
nutrients missing. Per-nutrient: energy 567, protein 552, fat 576, saturated
fat 1,218, carbohydrates 558, fiber 1,387, sugars 1,057, sodium 565,
cholesterol 1,331. A request tracking a nutrient from the high-gap cluster
(saturated fat, fiber, sugars, cholesterol) drops 12-15% of recipes for that
nutrient alone; tracking multiple nutrients compounds the loss. **Owner:**
data-preparation. Fill missing nutrient values, or distinguish "USDA
genuinely lacks this field" from "the pipeline dropped it."

**Finding DQ-7 (resolved, no issue) — `nutrition_basis` is uniformly
`per_100g`.** All 8,966 `Food` nodes are `per_100g`. No `per_serving` or
other-basis values exist. The `per_serving` code path in
`_normalise_food_nutrients` is dead code against the deployed graph; no
silent-zero path here.

**Cumulative effect.** Each finding removes recipes. The intersection of
recipes surviving every filter is a small fraction of the graph. The plan's
output quality is limited entirely by the graph's coverage, not by the plan's
logic. **The phase review must decide** whether these findings block the
phase p2 exit (and become p3 prerequisites), or whether the phase exits on
the current fixture-verified posture with the findings tracked as
data-preparation follow-ups.

## Phase p3 - explainable recommendation delivery

Status: planned (greenfield)

### Outcome

The backend recommendation surface is built end-to-end: a LangGraph workflow orchestrates constraint extraction, plan generation (via p2-003), and explanation assembly; a response contract exposes three-level reasoning (plan / recipe / constraint) with the drop-cause distinctions p2 established; a conversational interface accepts natural-language requests, preserves the deterministic explanation causes, and surfaces cost on follow-up turns. The frontend (web planner UI) is owned by a separate effort and is out of scope for this SDD effort.

### Goals served

- G-2
- G-6

### Features

- **p3-001-workflow-recommendation-service** *(done, 2026-10-16)* — LangGraph
  recommendation workflow orchestrating three nodes: Extract Constraints
  (LLM-driven constraint extraction and validation), Plan (deterministic
  delegation to p2-003 via a workflow-owned port), Generate Response
  (structured-verified text generation). The workflow depends only on a
  workflow-owned port; the adapter in `remy/app` calls
  `PlanService.generate` and maps the real `(PlanResponse, PlanTrace)` tuple
  to workflow-owned models (`PlanInput`, `PlanResult`, `PlanTraceView`),
  preserving R-2's inward dependency direction (`lint-imports` 4 kept, 0
  broken). The versioned `TraceEnvelope` captures the raw message, parsed
  constraints, unapplied constraints, one entry per node run, one entry per
  LLM invocation, and the embedded `PlanTraceView`; it is never part of the
  user-displayable payload. Generate Response runs a deterministic check on
  its structured output (referenced IDs/causes are a subset of the plan's;
  evidence-absent drops never restated as permissive). Extraction is
  faithful: stated allergens/dietary flags preserved, severity never
  downgraded, tolerance 0 unless explicitly requested, unapplied constraints
  reported. All workflow tests use a fake LLM and fake port. Zero loops
  beyond the planned reopens. **Three p2-003 reopens were required and
  landed** (tuple return; `requirement_id` on `ConstraintOutcomeResponse`;
  infeasibility returned as a shaped response rather than raised) — each
  recorded in p2-003's `decisions.md` and `CHANGELOG.md`. **One p2-001
  reopen** moved `workflows/rules/` to `domain/` to satisfy the new
  `api does not depend on workflows` `.importlinter` contract. Two
  workflow-side R-16/R-17 conformance tests pass; the trace-side R-16
  assertion is `xfail` under tracked **Finding F-P3-1** (p2-003: `PlanTrace`
  carries no R-16 audit provenance). Two constitution-path findings route to
  phase review: **BD-2a** (R-16's named path divergence — same as p2-002's
  F-D) and **BD-2b** (R-17's named fixture `tests/api/test_explanation_shape.py`
  is absent; owner likely p3-002). (serves G-2, G-6)
- **p3-002-explainable-response-contract** *(done, 2026-10-17)* — The
  user-facing response contract for Remy's conversational surface, defined as
  concrete Pydantic v2 types in `SystemCode/remy/app/src/app/chat_contract.py`:
  the `/chat` request schema (`ChatRequest`), the five SSE event payloads
  (`MetadataEvent`, `TokenEvent`, `PlanUpdatedEvent`, `ErrorEvent`,
  `DoneEvent`), the three-level explanation models (`PlanExplanation` /
  `RecipeExplanation` / `ConstraintExplanation`, `OfferView`, `DropCause`
  closed enum), `MealDelta` + `MealScopedExplanation` (the delta + meal-scoped
  explanation for `plan_updated`), and `ChatResponseEnvelope` (the
  non-streaming projection; trace referenced by `trace_id`, never embedded).
  The pure mapper `from_trace_envelope(env: TraceEnvelope, trace_id: str) ->
  ChatResponseEnvelope` projects p3-001's trace into the explanation,
  preserving p2's drop-cause precedence (`present-evidence-excludes` →
  `evidence-absent` → `unmapped`), failure-to-`ErrorEvent` mapping, and
  infeasible binding constraints. The audit-provenance floor is the named
  `CHAT_FORBIDDEN_FIELDS` constant (`confidence`, `normalization_version`,
  `source`, `source_snapshot_id`, `source_id`, `mapping_version`, `food_key`,
  `fdc_id`); prices and structural ids are permitted in the user payload, and
  the SSE contract declares no endpoint-specific exclusions beyond R-16's
  floor (C-3). Both constitution-named fixtures are created at
  `SystemCode/remy/app/tests/api/<name>` per **Amendment A-007** (constitution
  v1.6 → v1.7). The R-16 fixture has two independently-visible clauses: the
  user-payload exclusion passes; the trace-side retention is
  `xfail(strict=True)` under **Finding F-P3-1** (owned by p2-003). The R-17
  fixture asserts three-level presence, distinct drop causes, and multi-cause
  precedence. Zero loops beyond the plan-review's two minor findings (F-1
  contract-module home for p3-004; F-2 floor constant naming). CI PASS: 81
  passed, 3 xfailed (all strict; all F-P3-1 or its p3-001 counterpart); 4
  `.importlinter` contracts kept, 0 broken. **Cross-feature: Amendment A-007**
  formalizes the R-16/R-17 fixture-path divergence previously tracked as
  p2-002 F-D and p3-001 BD-2a. (serves G-2, G-6)
- **p3-003-web-planner-experience** *(new)* — The web request/response
  contract for meal-plan recommendations: the client-facing API surface that
  delivers p3-002's response shape to the web planner UI. (serves G-6)
- **p3-004-conversational-constraint-interface** *(new)* — Conversational
  constraint extraction, turn-level recommendation delivery, and safe
  re-expression of deterministic explanation causes. **Additionally, p3-004
  inherits the recipe-level cost drop from A-006**: when a requirement has no
  cost-eligible package (the calculator's `MISSING_PACKAGE_DATA` signal, per
  amended R-8/R-10), p3-004 drops the recipe from the eligible pool with an
  evidence-absent cause, asserting R-8's and R-10's recipe-level fixtures.
  Until p3-004 ships, the calculator's item-level signal is the sole cost
  enforcement point. (serves G-1's budget aspect, closes the R-8/R-10 check
  obligation deferred from p2)

### Exit criteria

- A LangGraph workflow exists that accepts a request, invokes p2-003's plan
  path, and returns a result plus a trace. *New; no fixture exists.*
- The workflow's trace boundary is explicit: what the trace carries, where it
  stops, and which downstream feature reads it. *New.*
- The response contract exposes three-level explanations with the p2 drop
  causes and no audit provenance in the user payload. *New.*
- The web planner UI consumes the response contract end-to-end. *New.*
- The conversational interface extracts constraints from natural language,
  delivers turn-level recommendations, and re-expresses explanation causes
  without paraphrasing them into permissive statements. *New.*
- Cost and budget evaluation is in scope for p3-004 (per A-006); R-8's and
  R-10's recipe-level fixtures are satisfied by p3-004. *Owner: p3-004.*
- **Data-coverage acknowledgment (carried from p2).** p2-003's data-quality
  findings (DQ-1..DQ-7) limit the plan's candidate pool. Phase p3 builds the
  delivery surface against whatever the plan produces; the plan's output
  quality is upstream of p3. The phase review at p2 exit decides whether the
  findings must resolve before p3 begins or are tracked as data-preparation
  follow-ups. If they must resolve, p3 planning is blocked until then.
- No unresolved blocking findings.

### Risks & unknowns

- **Greenfield scope.** No p3 code exists. The phase builds the workflow,
  response contract, web surface, and chat interface from scratch. The effort
  is significantly larger than p1/p2's prove-and-fix features.
- **Dependency on p2-003's data quality.** The plan's output is limited by the
  deployed graph's coverage (DQ-1..DQ-7). If the plan's usable pool is a small
  biased slice, p3's explanations describe a small biased slice. The phase
  review at p2 exit decides whether this blocks p3.
- **Trace boundary is new.** p2's traces (`CalculationTrace`, plan-level
  trace) exist; p3-001 composes them or adds a workflow-level trace. The
  boundary's shape is a p3-001 design decision, not a spec decision. The spec
  names the contract; the plan designs it.
- **LangGraph dependency is new.** p1/p2 don't use LangGraph. p3-001 introduces
  it. The roadmap's `R-3` (stack shape fixed) permits it — LangGraph is the
  workflow orchestration layer the constitution's stack description names.
- **Streaming/SSE contract.** If p3-004's chat interface uses SSE (per the API
  doc), the event protocol is new and requires its own design. p3-001's
  workflow may need to support streaming, or the streaming layer may be
  p3-004's.
- **Web UI tech stack.** p3-003 assumes a web frontend. The stack
  (framework, build tooling) isn't specified in the constitution. Confirm
  during p3-003's spec.
- **F-P3-1 (trace-side R-16 provenance gap, owner: p2-003).** The user-payload
  exclusion clause of R-16 passes; the trace-side retention fails because
  `PlanTraceView` carries no `confidence`/`source_snapshot_id`/`mapping_version`.
  The R-16 trace-side fixture is `xfail(strict=True)` with a reason naming
  F-P3-1. **Resolution path (three small reopens):** p2-002 extends `OfferRef`
  with the three provenance fields and populates them in `inspect_candidates`;
  p2-003 carries them onto `RequirementOutcome` and projects
  `fc.normalization_version` from `FoodConcept`; p3-001 carries them onto
  `RequirementOutcomeView`; p3-002 removes the `xfail`. **Durable alternative:**
  extend `BEST_FULFILLMENT` to carry the winning `FULFILLS` edge's provenance
  (p1-002 reopen + graph rebuild). The phase review decides whether to action
  the three reopens before p3-004 ships or track as p2-003 follow-ups.
- **Kit defect (4th occurrence): Close artifacts in Implement task lists.**
  p2-002 (T-24), p2-003 (T-17), p3-001 (T-16), and p3-002 (old T-15) all
  placed `decisions.md` (a Close-stage artifact per `workflow.md`'s ownership
  table) in the Implement task list, contradicting "a stage may only write its
  own artifact." p3-002's implementer caught it and stopped; the task was
  removed. **Two one-line kit-prompt fixes prevent recurrence:** (a) the plan
  prompt should say "every task must be an Implement-stage artifact;
  Close-stage artifacts (`decisions.md`, `CHANGELOG.md`, `state.json`) are not
  tasks"; (b) the implement prompt should say "if a task asks you to write a
  Close-stage artifact, stop and route to `plan`." Both belong to a kit
  amendment at the phase review.

### Phase p3 progress

- p3-001: closed 2026-10-16, 0 loops. CI PASS on
  `remy/api/tests/features/plan`, `remy/workflows/tests`,
  `remy/app/tests`, and `lint-imports` (4 kept, 0 broken). Two workflow-side
  R-16/R-17 conformance tests pass; the trace-side R-16 assertion is `xfail`
  under F-P3-1 (owned by p2-003). Three p2-003 reopens and one p2-001 reopen
  landed as prerequisites (each recorded in their own features' decisions
  files). Carry-forward items for phase review: F-P3-1 (trace provenance),
  BD-2a (R-16 path divergence, same as p2-002's F-D), BD-2b (R-17 fixture
  absent; owner likely p3-002), and the langgraph pending-deprecation warning
  introduced by the new LangGraph dependency.
- p3-002: closed 2026-10-17, 0 loops. CI PASS: 81 passed, 3 xfailed (all
  strict; the R-16 trace-side clause under F-P3-1, and p3-001's two
  workflow-side F-P3-1 counterparts); `.importlinter` 4 kept, 0 broken.
  Amendment A-007 landed (constitution v1.7): R-16's and R-17's named check
  paths corrected to `SystemCode/remy/app/tests/api/<name>`. Two plan-review
  findings folded into the task pass: F-1 (contract module lives in `app`;
  p3-004's `/chat` endpoint must live there too) and F-2 (`CHAT_FORBIDDEN_FIELDS`
  names the chat payload's full exclusion set, with the R-16 floor asserted
  separately). Carry-forward items for phase review: F-P3-1 (trace-side
  provenance; owner p2-003; three-reopen resolution path named), the kit
  defect (Close artifacts in Implement task lists — 4th occurrence; two
  one-line prompt fixes named), and the API_doc §3 `plan_updated` divergence
  (p3-004 owns the doc update).
- F-P3-1 resolved 2026-10-17 (three small reopens: p2-002 `OfferRef`,
  p2-003 `RequirementOutcome`, p3-001 `RequirementOutcomeView`; p3-002's
  trace-side R-16 `xfail` removed). The trace now carries `confidence`,
  `source_snapshot_id`, and `mapping_version`. The durable alternative
  (extend `BEST_FULFILLMENT`) is not needed.
- p3-003: not started.
- p3-004: not started.

## Re-plan log

<!-- append-only. date, change, reason. -->

- 2026-10-02 — Replaced the scaffold with three dependency-ordered phases, mapped
  G-1 through G-7 exactly once, added feature order and shared contracts, and
  defined phase exits and risks — the approved proposal and constitution were
  available while the prior roadmap contained only a placeholder p1 and no usable
  project-state constraints.

- 2026-10-02 — Added p3-004-conversational-constraint-interface and extended the
  shared-contracts table, p2 exit criteria, and p3 risks — the application
  supports a chat feature where users talk to the system in natural language, and
  the roadmap did not previously represent that surface or its specific hazard of
  paraphrasing evidence-absent drops into permissive statements.

- 2026-10-02 — Re-scoped p1 and p2 features from "build" to "prove" against
  pre-existing code, and marked p3-001 through p3-003 as partial. Reason:
  brownfield adoption — the pipeline, graph, calculator API, and planner API
  already exist. Phase exit criteria now require demonstrations (manifests,
  gates, tests, provenance checks) rather than asserting completion. A
  conformance clause was added to p1, p2, and p3 exit criteria to make this
  explicit.

- 2026-10-03 — Marked p1-001 as done. Noted the O-1 follow-up (restore seeds,
  pin reference checksums) as a prerequisite for p1-002. Added a "Phase p1
  progress" subsection recording per-feature status and loop counts. Extended
  the phase p1 exit criteria with a clause that a deferred finding does not
  block phase exit provided its follow-up is tracked and lands before the
  phase's last feature closes. Reason: p1-001 closed with one loop-back and one
  deferred finding; the roadmap needs to reflect that status and the resulting
  dependency.

- 2026-10-04 — Inserted `p1-001b-test-infrastructure` as a prerequisite for
  p1-002. Reason: verification at p1-002's plan stage found that no fake-driver
  fixture, no `tests/graph/` directory, no Neo4j test infrastructure, and no
  `testcontainers` dependency exist. The plan assumed they did. Splitting the
  infrastructure into a small preceding feature keeps p1-002's scope to the
  provenance graph model and makes the dependency explicit.

- 2026-10-04 — Marked `p1-001b-test-infrastructure` as done, 0 loops. Updated
  the feature description to reflect the cloud Neo4j fixture (which replaced
  the originally planned testcontainers approach after the Docker-unavailable
  constraint surfaced). Added `p1-001b` as a dependency of p1-002 in the
  feature table. Marked the p1 exit criteria's conformance clause as satisfied.
  Added a risk about the integration tests' dependency on the configured cloud
  instance. Reason: p1-001b closed on 2026-10-04 with no loop-back; the roadmap
  needs to reflect that p1-002's test infrastructure is now in place.

- 2026-10-05 — Marked `p1-002-provenance-graph-model` as done, 1 loop. Updated
  the feature description to reflect what shipped (canonical edge vocabulary,
  fail-closed admission, canonical allowlists, reject-don't-repair, MERGE
  idempotence); recorded the F-1/F-2/F-3 + nit resolution. Marked the R-1
  legacy-naming risk as realized (canonical allowlist enforced; no migration
  required). Added a new phase risk naming the accumulating O-1 deferrals
  (p1-001 F-3, p1-002 T-5/T-12) and requiring the phase review to decide
  whether O-1 is a phase-exit blocker or a p2-or-later follow-up. Reason:
  p1-002 closed on 2026-10-05 after one loop-back; the roadmap reflects the
  phase progress and consolidates the O-1 deferrals so the phase review sees
  them as one issue rather than three.

- 2026-10-05 — Marked `p1-003-coverage-quality-reporting` as done, 3 loops.
  Updated the feature description to reflect what shipped (five-dimension
  report, manifest `association` block, runtime fail-closed guard, `enabled`
  var gating). Annotated the phase exit criteria with the deferred-vs-satisfied
  status of each. Set phase p1 status to `done (pending phase review)`. Added
  a p2 prerequisite note naming O-1 as the blocking issue for phase p2. Added
  a "Phase p1 totals" line to the progress subsection. Reason: p1-003 closed
  on 2026-10-05 after three loop-backs; phase p1's four features are all
  closed, and the roadmap needs to reflect the phase exit state and the O-1
  consolidation.

- 2026-10-05 — Corrected the O-1 framing throughout phase p1. The deferrals
  are not caused by missing seeds — the seeds are present and used by the
  staging models — but by a stale price-path model in the data-preparation
  package (`stg_retail_listing.sql` references two nodes that no producer
  creates). Added `docs/findings/data-prep-price-path.md` as the durable
  finding; updated the phase p1 status to `done (external dependency
  tracked)`; rewrote the O-1 risk bullet, the exit-criteria annotations, the
  feature follow-up notes, and the p2 prerequisite to cite the finding.
  Reason: the "missing seeds" framing was wrong and pointed at a fix that
  would not have resolved the parse failure; the actual cause is an
  out-of-scope defect owned by the data-preparation package.

- 2026-10-05 — Phase p1 closed. Phase review signed off with the p2 posture
  set to "proceed with fixtures"; `docs/findings/data-prep-price-path.md`
  tracked as a p2 risk. End-to-end demonstration deferred; the four p1
  features are verified at the fixture level. Reason: the phase's features
  are closed, the cross-team finding is tracked, and blocking p2 on an
  external fix stalls the project without adding verification value (p2's
  features are unit-level and don't require the real marts).

- 2026-10-05 — Marked `p2-001-constraint-evidence-filtering` as done, 0 loops.
  Set phase p2 status to `active`; added a "Phase p2 progress" subsection.
  Recorded what shipped (per-constraint evaluation with distinct drop causes,
  fixed cause precedence, ingredient-scoped warnings, conservative defaults,
  input-error rejection, internal outcome models) and the pre-existing API
  baseline failures excluded from the feature's CI. Reason: the first p2
  feature closed in a single cycle with no review findings; the roadmap
  reflects that p2 is now underway and that the API package has a recorded,
  excluded baseline of unrelated failures.

- 2026-10-07 — Amended the constitution's R-4, R-8, R-9, and R-10
  (amendments A-001..A-004) to match the deployed schema and to name the
  correct enforcement and drop layers. The deployed `FULFILLS` edge carries
  `freshness_status` (a status field), not a freshness timestamp; the
  calculator's cost-eligibility rule uses `price_status`, `price_match_status`,
  and `price_basis`, not `cost_basis_compatible`; the calculator emits
  item-level evidence-absent signals and p2-003 performs the recipe-level
  drop, per-nutrient for `PARTIAL_NUTRITION_DATA`. Rewrote p2-002's roadmap
  description from the four-rule first pass to the actual nine-rule scope
  (R-1, R-5, R-8, R-9, R-10, R-11, R-12, R-13, R-16). Added p2-001 as a
  p2-002 dependency. Named the p2-002 → p2-003 item-level signal contract in
  the feature table and in the p2-003 entry. Added three p2 risks (p2-001
  freshness predicate, p2-001 `cost_basis_compatible` check, `Nutrients` DTO
  population state). Reason: the p2-002 spec review surfaced that the
  constitution's freshness and cost-eligibility rules could not be satisfied
  by the deployed schema as written, and that the drop-layer responsibility
  was ambiguous; the roadmap now reflects the amended rules and the corrected
  scope.

- 2026-10-08 — Marked `p2-002-cost-nutrition-calculation` as done, 2 loops.
  Updated the feature description to reflect what shipped (canonical
  `QUERY_B`; cost eligibility per amended R-10; silent `package_volume`
  conversion; per-nutrient precedence per amended R-12; null-when-any
  nutrient totals per amended R-9; item-level evidence-absent signals;
  best-score package selection with no confidence floor in the R-13 ordering;
  internal `CalculationTrace`; `MAX_REQUEST_INGREDIENTS = 100`). Recorded the
  two loops (plan: T-20's file scope omitted `router.py`; spec: freshness and
  eligibility rules did not match the deployed schema, resolved by amendments
  A-001..A-004). Tightened the two p2-001 risk bullets with what p2-002's
  review established: the freshness predicate's timestamp branch may be dead
  code against the deployed schema (cleanup), while the cost-basis predicate
  has real behavioral impact on ~63 eligible packages (behavioral). Added the
  five follow-ups (F-A, F-B, F-C, F-D, N-1) to the phase p2 progress entry
  for phase review. Reason: the second p2 feature closed on 2026-10-08 after
  two loop-backs; the roadmap reflects the closure, the corrected p2-001
  findings' severities, and the carry-forward list.

- 2026-10-08 — Drafted amendments A-005 (R-14 relaxation set) and A-006 (R-8/R-10
  cost-drop deferral) in response to the p2-003 spec review. Updated the p2-003
  feature entry, phase p2 exit criteria, and phase p2 risks to reflect the
  amended rules: p2-003 consumes p2-002's `PARTIAL_NUTRITION_DATA` per tracked
  nutrient; `unmapped` is a top-level drop cause with precedence
  `present-evidence-excludes` → `evidence-absent` → `unmapped`; the relaxation
  set is nutrient-bound widening only, with `nutrient_tolerance_pct` in
  `[0, 25]` defaulting to 0; cost and budget are out of scope for p2, and the
  recipe-level cost drop is **deferred to p3-004-conversational-constraint-
  interface**, which now inherits the R-8/R-10 recipe-level check obligation.
  Reason: the p2-003 spec review surfaced that R-14's "permitted relaxations"
  was unclassified and that R-8/R-10 named a p2-003 cost-drop obligation the
  feature does not execute; both required amendments rather than spec-only
  readings, matching the A-001..A-004 precedent from p2-002. The owner of the
  deferred cost drop is p3-004, named in A-006 and in p3-004's entry.

- 2026-10-10 — p2-003 implementation complete; seven data-quality findings
  (DQ-1..DQ-7) surfaced during implementation and are recorded in a new
  "Phase p2 data-quality findings" subsection. Updated the p2-003 feature
  entry to distinguish implementation completion from phase-review pending;
  corrected the shared-contract column's R-14 wording from "minimal set" to
  "individually-binding set" per the amended AC-2. Added a phase p2 risk
  naming the systemic data-coverage gap, and a phase p2 exit-criteria clause
  requiring the phase review to decide whether the findings block p2 exit or
  are tracked as data-preparation follow-ups. Reason: the plan's logic is
  correct at every filter, but the graph's coverage gaps (86% loss from
  DQ-2, 88% from DQ-3, 18% from DQ-6, plus DQ-1, DQ-4, DQ-5) reduce the
  usable pool to a small fraction of the recipe graph. The phase review
  needs the full picture to decide the phase-exit posture.

- 2026-10-14 — Corrected phase p3's status from "planned" (implying partial
  code) to "planned (greenfield)". Marked p3-001, p3-002, and p3-003 as `new`
  in the feature table (previously `partial`). Rewrote the phase p3 section:
  added an Outcome describing the recommendation surface end-to-end, moved
  goals served to G-2/G-6, expanded the feature entries with descriptions for
  each, added exit criteria (new, not "prove"), and added greenfield-specific
  risks (new scope, p2 data-quality dependency, LangGraph introduction,
  streaming contract, web UI stack). Reason: verification found no p3
  implementation exists — the workflow, response contract, web planner, and
  chat interface are all to be built. The roadmap's `partial` status assumed
  pre-existing code; the brownfield posture does not apply to phase p3.

- 2026-10-16 — Marked `p3-001-workflow-recommendation-service` as done, 0
  loops. Recorded what shipped (three-node LangGraph workflow: Extract
  Constraints, Plan, Generate Response; workflow-owned plan port with the
  adapter in `app`; versioned `TraceEnvelope`; LLM client over
  `init_chat_model` defaulting to Ollama; deterministic structured-output
  check on Generate Response; faithful extraction with unapplied-constraint
  reporting) and the three p2-003 reopens plus one p2-001 reopen that landed
  as prerequisites. Flagged the phase-review carry-forwards: F-P3-1
  (`PlanTrace` carries no R-16 audit provenance; owner p2-003), BD-2a
  (R-16 named path divergence — same as p2-002's F-D), BD-2b (R-17 named
  fixture absent; owner likely p3-002), and the langgraph pending-deprecation
  warning. Reason: the first p3 feature closed with no blocking findings and
  three nits; the phase review needs the trace-provenance gap and the two
  constitution-path findings in view before p3-002 begins. Two prerequisites
  for p3-002 are recorded: it consumes p3-001's trace boundary, and it is the
  likely owner of R-17's named fixture.

- 2026-10-17 — Marked `p3-002-explainable-response-contract` as done, 0 loops.
  Recorded what shipped (concrete Pydantic contract models for `/chat` request,
  five SSE events, three-level explanation, `DropCause` enum, `MealDelta` +
  `MealScopedExplanation`; `from_trace_envelope` mapper; `CHAT_FORBIDDEN_FIELDS`
  audit floor; `trace_id`-referenced-not-embedded trace boundary per C-1;
  `plan_updated` delta + meal-scoped explanation per C-2; layered R-16 floor per
  C-3) and Amendment A-007 (R-16/R-17 fixture paths corrected to
  `SystemCode/remy/app/tests/api/<name>`; constitution v1.6 → v1.7). Recorded
  the two plan-review findings (F-1 contract-module home constrains p3-004;
  F-2 floor constant naming) folded into the task pass, and the implement-stage
  discovery BD-4 (T-15 mis-scoping — the 4th Close-artifact-in-Implement-list
  occurrence across p2-002/p2-003/p3-001/p3-002; two one-line kit-prompt fixes
  named). Flagged the phase-review carry-forwards: F-P3-1 (trace-side R-16
  provenance gap; owner p2-003; three-reopen resolution path named; durable
  `BEST_FULFILLMENT`-extension alternative recorded), the kit defect, the
  API_doc §3 `plan_updated` divergence (p3-004 owns the doc update), and the
  langgraph pending-deprecation warning. Reason: the second p3 feature closed
  with zero loops and two non-blocking nits; the phase review needs the
  provenance-gap resolution path and the recurring kit defect in view before
  p3-004 begins.

- 2026-10-17 — Resolved F-P3-1 via three additive reopens (p2-002
  `OfferRef`, p2-003 `RequirementOutcome`, p3-001 `RequirementOutcomeView`)
  and the removal of p3-002's trace-side R-16 `xfail`. The three fields
  (`confidence`, `source_snapshot_id`, `mapping_version`) live on the
  deployed `FULFILLS` edge; the calculator already projected them; the
  reopens carry them through the plan trace and the workflow view. The
  durable alternative (extend `BEST_FULFILLMENT` to carry the winning
  edge's provenance) is not needed. Phase p3 risks: F-P3-1 moved to
  resolved. Reason: p3-004 is the last p3 feature and is the layer that
  most needs the trace's provenance for conversational "why this offer?"
  answers; resolving it now avoids a fourth mid-loop discovery at p3-004.
