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
| p2-003-feasible-meal-plan-solving          | partial | p2-001-constraint-evidence-filtering, p2-002-cost-nutrition-calculation                                         | p2-001-constraint-evidence-filtering, p2-002-cost-nutrition-calculation                                           | Plan feasibility result with named binding constraints (deterministic minimal set), reasoning structure sufficient for downstream explanation, and the recipe-level nutrition drop behavior consuming p2-002's item-level `PARTIAL_NUTRITION_DATA` signal (per-nutrient for tracked nutrients). Cost/budget out of scope; recipe-level cost drop deferred. |
| p3-001-workflow-recommendation-service     | partial | p2-003-feasible-meal-plan-solving                                                                               | p3-002-explainable-response-contract, p3-003-web-planner-experience, p3-004-conversational-constraint-interface   | Recommendation execution result and trace boundary                                                                                   |
| p3-002-explainable-response-contract       | partial | p2-001-constraint-evidence-filtering, p2-002-cost-nutrition-calculation, p3-001-workflow-recommendation-service | p3-001-workflow-recommendation-service, p3-003-web-planner-experience, p3-004-conversational-constraint-interface | Three-level user explanation and audit-provenance separation                                                                         |
| p3-003-web-planner-experience              | partial | p3-001-workflow-recommendation-service, p3-002-explainable-response-contract                                    | p3-001-workflow-recommendation-service, p3-002-explainable-response-contract                                      | Web request/response contract for meal-plan recommendations                                                                          |
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

Status: active

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
- **p2-003-feasible-meal-plan-solving** *(partial)* — Existing planning API.
  Remaining work: verify satisfiable returns a plan and unsatisfiable returns no
  plan with a deterministic minimal set of named binding constraints (R-14, as
  amended by A-005); confirm the plan result carries per-requirement outcomes,
  drop causes, selected offers, and resolved concepts so that p3 can explain
  without re-deriving. p2-003 consumes p2-002's item-level
  `PARTIAL_NUTRITION_DATA` signal as the recipe-level nutrition drop trigger
  (per tracked nutrient; a nutrient is tracked when the request supplies a
  `limit` or a `goal`), and p2-001's per-constraint outcomes and unmapped-
  requirement tracking. `unmapped` is a top-level drop cause distinct from
  `evidence-absent` and `present-evidence-excludes`; precedence is
  `present-evidence-excludes` → `evidence-absent` → `unmapped`. The relaxation
  set is nutrient-bound widening only (`nutrient_tolerance_pct`, integer
  `[0, 25]`, default 0); structural relaxations are prohibited; a request
  satisfiable only under a structural relaxation returns a hard infeasibility
  failure. Cost and budget are out of scope for this feature (per A-006); the
  calculator's `MISSING_PACKAGE_DATA` signal is not consumed here, and the
  recipe-level cost drop is **deferred to p3-004-conversational-constraint-
  interface**. The solver-unavailable case is a hard failure (no degraded plan).
  (serves G-1)

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
- p2-003: not started. Will consume p2-002's item-level evidence-absent
  signals as the recipe-level drop trigger.

## Phase p3 - explainable recommendation delivery

Status: planned

### Features

- **p3-004-conversational-constraint-interface** *(new)* — Conversational
  constraint extraction, turn-level recommendation delivery, and safe
  re-expression of deterministic explanation causes. **Additionally, p3-004
  inherits the recipe-level cost drop from A-006**: when a requirement has no
  cost-eligible package (the calculator's `MISSING_PACKAGE_DATA` signal, per
  amended R-8/R-10), p3-004 drops the recipe from the eligible pool with an
  evidence-absent cause, asserting R-8's and R-10's recipe-level fixtures.
  Until p3-004 ships, the calculator's item-level signal is the sole cost
  enforcement point. (serves G-1, and closes the R-8/R-10 check obligation
  deferred from p2)

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
