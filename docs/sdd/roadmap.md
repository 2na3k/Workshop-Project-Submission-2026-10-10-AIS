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
| p2-001-constraint-evidence-filtering       | partial | p1-002-provenance-graph-model                                                                                   | p2-002-cost-nutrition-calculation, p2-003-feasible-meal-plan-solving                                              | Candidate evaluation outcome and distinct evidence-absent/present-exclusion causes                                                   |
| p2-002-cost-nutrition-calculation          | partial | p1-002-provenance-graph-model                                                                                   | p2-001-constraint-evidence-filtering, p2-003-feasible-meal-plan-solving                                           | Portion nutrient and consumed/package cost result contract                                                                           |
| p2-003-feasible-meal-plan-solving          | partial | p2-001-constraint-evidence-filtering, p2-002-cost-nutrition-calculation                                         | p2-001-constraint-evidence-filtering, p2-002-cost-nutrition-calculation                                           | Plan feasibility result with named binding constraints, and reasoning structure sufficient for downstream explanation                |
| p3-001-workflow-recommendation-service     | partial | p2-003-feasible-meal-plan-solving                                                                               | p3-002-explainable-response-contract, p3-003-web-planner-experience, p3-004-conversational-constraint-interface   | Recommendation execution result and trace boundary                                                                                   |
| p3-002-explainable-response-contract       | partial | p2-001-constraint-evidence-filtering, p2-002-cost-nutrition-calculation, p3-001-workflow-recommendation-service | p3-001-workflow-recommendation-service, p3-003-web-planner-experience, p3-004-conversational-constraint-interface | Three-level user explanation and audit-provenance separation                                                                         |
| p3-003-web-planner-experience              | partial | p3-001-workflow-recommendation-service, p3-002-explainable-response-contract                                    | p3-001-workflow-recommendation-service, p3-002-explainable-response-contract                                      | Web request/response contract for meal-plan recommendations                                                                          |
| p3-004-conversational-constraint-interface | new     | p3-001-workflow-recommendation-service, p3-002-explainable-response-contract                                    | p3-001-workflow-recommendation-service, p3-002-explainable-response-contract, p3-003-web-planner-experience       | Conversational constraint extraction, turn-level recommendation delivery, and safe re-expression of deterministic explanation causes |

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

Status: planned

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
fixtures only. The phase review decides whether this is a blocker.

### Goals served

- G-1
- G-3

### Features

- **p2-001-constraint-evidence-filtering** *(partial)* — Existing filtering logic
  in the calculator API. Remaining work: write a fixture for each of R-5 through
  R-10 and either the fixtures pass or the code is fixed. The evidence-absent vs.
  present-exclusion distinction must be visible in the output. (serves G-1)
- **p2-002-cost-nutrition-calculation** *(partial)* — Existing nutrient
  computation. Remaining work: verify separate cost fields (R-11); verify
  deterministic conflict precedence across runs (R-12); verify the closed-interval
  confidence and no-floor selection (R-13); verify unit-basis enforcement
  (R-10). (serves G-1, G-3)
- **p2-003-feasible-meal-plan-solving** *(partial)* — Existing planning API.
  Remaining work: verify satisfiable returns a plan and unsatisfiable returns no
  plan with named binding constraints (R-14); confirm the plan result carries
  per-requirement outcomes, drop causes, selected offers, and resolved concepts
  so that p3 can explain without re-deriving. (serves G-1)

### Exit criteria

*(unchanged)*

### Risks & unknowns

*(unchanged)*

## Phase p3 - explainable recommendation delivery

Status: planned

*(unchanged)*

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
