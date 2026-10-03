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

| Feature                                | Status   | Depends on                                                                                                      | Shares contract with                                                         | Contract                                                                           |
|----------------------------------------|----------|-----------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| p1-001-reproducible-source-pipeline    | partial  | —                                                                                                               | p1-002-provenance-graph-model, p1-003-coverage-quality-reporting             | Source snapshot manifest and quality-gate result                                   |
| p1-002-provenance-graph-model          | partial  | p1-001-reproducible-source-pipeline                                                                             | p1-001-reproducible-source-pipeline, p1-003-coverage-quality-reporting       | Canonical graph schema and `REQUIRES`/`FULFILLS` provenance contract               |
| p1-003-coverage-quality-reporting      | new      | p1-001-reproducible-source-pipeline, p1-002-provenance-graph-model                                              | p1-001-reproducible-source-pipeline, p1-002-provenance-graph-model           | Coverage dimensions and graph quality manifest                                     |
| p2-001-constraint-evidence-filtering   | partial  | p1-002-provenance-graph-model                                                                                   | p2-002-cost-nutrition-calculation, p2-003-feasible-meal-plan-solving         | Candidate evaluation outcome and distinct evidence-absent/present-exclusion causes |
| p2-002-cost-nutrition-calculation      | partial  | p1-002-provenance-graph-model                                                                                   | p2-001-constraint-evidence-filtering, p2-003-feasible-meal-plan-solving      | Portion nutrient and consumed/package cost result contract                         |
| p2-003-feasible-meal-plan-solving      | partial  | p2-001-constraint-evidence-filtering, p2-002-cost-nutrition-calculation                                         | p2-001-constraint-evidence-filtering, p2-002-cost-nutrition-calculation      | Plan feasibility result with named binding constraints, and reasoning structure sufficient for downstream explanation |
| p3-001-workflow-recommendation-service | partial  | p2-003-feasible-meal-plan-solving                                                                               | p3-002-explainable-response-contract, p3-003-web-planner-experience, p3-004-conversational-constraint-interface | Recommendation execution result and trace boundary                                 |
| p3-002-explainable-response-contract   | partial  | p2-001-constraint-evidence-filtering, p2-002-cost-nutrition-calculation, p3-001-workflow-recommendation-service | p3-001-workflow-recommendation-service, p3-003-web-planner-experience, p3-004-conversational-constraint-interface | Three-level user explanation and audit-provenance separation                       |
| p3-003-web-planner-experience          | partial  | p3-001-workflow-recommendation-service, p3-002-explainable-response-contract                                    | p3-001-workflow-recommendation-service, p3-002-explainable-response-contract | Web request/response contract for meal-plan recommendations                        |
| p3-004-conversational-constraint-interface | new  | p3-001-workflow-recommendation-service, p3-002-explainable-response-contract                                   | p3-001-workflow-recommendation-service, p3-002-explainable-response-contract, p3-003-web-planner-experience | Conversational constraint extraction, turn-level recommendation delivery, and safe re-expression of deterministic explanation causes |

## Phase p1 - reproducible data and graph foundation

Status: active

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

- **p1-001-reproducible-source-pipeline** *(partial)* — Existing build from raw
  sources to canonical marts. Remaining work: emit a source snapshot manifest
  (source, snapshot id, checksum, timestamp); make entity and relationship
  counts deterministic across rebuilds; add the reproducibility test to CI.
  (serves G-7)
- **p1-002-provenance-graph-model** *(partial)* — Existing graph load. Remaining
  work: ensure every populated `REQUIRES` and `FULFILLS` edge carries the
  properties R-4 requires; add the schema-conformance test (R-1: single canonical
  property names) and the edge-provenance test; wire the loader so it refuses to
  run unless the manifest passed. (serves G-4, G-7)
- **p1-003-coverage-quality-reporting** *(new)* — Publish separate nutrition,
  price, unit-conversion, dietary-evidence, and whole-recipe completeness
  measures, regenerated on every build. (serves G-5)

### Exit criteria

- A clean rebuild from the declared source snapshots produces the canonical marts
  and a quality manifest with deterministic entity and relationship counts.
  *Demonstrated by a CI reproducibility test, not asserted.*
- The quality gate rejects dangling `REQUIRES` or `FULFILLS` references and
  prevents graph refresh when the manifest is not accepted. *Demonstrated by a
  failing-manifest fixture that shows the loader exiting non-zero.*
- Schema-conformance and edge-provenance checks pass for the canonical property
  names and for every populated `REQUIRES` and `FULFILLS` linking record.
  *Demonstrated by the two named tests; for any rule the existing code violates,
  the test fails first and the fix lands with the test.*
- The coverage report exposes separate measurements for nutrition, price
  availability, package-unit conversion, dietary evidence, and overall recipe
  completeness.
- **Conformance clause:** every p1 feature that touches pre-existing code has a
  passing test or CI command demonstrating that the code satisfies its exit
  criteria. "The code exists" is not evidence.
- No unresolved blocking findings.

### Risks & unknowns

- The existing pipeline may not preserve source provenance in a form that can be
  turned into a manifest without rework. If so, the rework is in scope for
  p1-001 and the effort is larger than the "partial" status implies.
- The existing graph may accept more than one property name for a concept
  (legacy naming from before the constitution). R-1 makes this a violation and
  the fix is part of p1-002 — this may affect the deployed schema and require a
  migration.
- Coverage measurement may reveal gaps that were previously invisible. Gaps are
  reported, not hidden; closing them is not p1's job.
- Retail crawling is constrained by the absence of a public API and price
  snapshots become stale; the accepted snapshot policy and freshness metadata
  must remain explicit.

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

### Goals served

- G-1
- G-3

### Features

- **p2-001-constraint-evidence-filtering** *(partial)* — Existing filtering logic
  in the calculator API. Remaining work: write a fixture for each of R-5 through
  R-10 (severe vs. mild vs. absent allergen; explicit vs. unknown dietary; stale
  offer; missing profile; incompatible unit basis) and either the fixtures pass
  or the code is fixed. The evidence-absent vs. present-exclusion distinction
  (R-5, R-17) must be visible in the output, not just in the drop outcome.
  (serves G-1)
- **p2-002-cost-nutrition-calculation** *(partial)* — Existing nutrient
  computation. Remaining work: verify separate cost fields (R-11); verify
  deterministic conflict precedence across runs (R-12); verify the closed-interval
  confidence and no-floor selection (R-13); verify unit-basis enforcement
  (R-10). Any rule the existing code violates is fixed and re-tested.
  (serves G-1, G-3)
- **p2-003-feasible-meal-plan-solving** *(partial)* — Existing planning API.
  Remaining work: verify satisfiable returns a plan and unsatisfiable returns no
  plan with named binding constraints (R-14); confirm the plan result carries
  per-requirement outcomes, drop causes, selected offers, and resolved concepts
  so that p3 can explain without re-deriving. (serves G-1)

### Exit criteria

- Domain-rule tests pass for severe versus mild versus absent allergen evidence,
  explicit versus unknown dietary compliance, stale offers, missing nutrition
  profiles, and incompatible unit bases. *For pre-existing code: fixture fails
  first, fix lands with the fixture.*
- Calculator tests pass for deterministic nutrient precedence, closed-interval
  mapping confidence, separate consumed/package cost fields, and the declared
  24-hour offer freshness threshold.
- Solver tests pass for both a satisfiable request that returns a plan and an
  unsatisfiable request that returns no plan with named binding constraint(s).
- Solver output carries sufficient reasoning structure (per-requirement outcomes,
  drop causes, selected offers, resolved concepts) that p3 can explain every
  recommendation and every drop without re-deriving the reasoning.
- The reasoning core never treats absent evidence as compliance, zero nutrition,
  or an available price, and no plan is returned when a feasible plan exists but
  was incorrectly classified as infeasible.
- **Conformance clause:** every p2 feature that touches pre-existing code has a
  passing fixture demonstrating conformance with the constitutional rules it is
  subject to, or the code has been fixed and the fixture passes.
- No unresolved blocking findings.

### Risks & unknowns

- The existing APIs may satisfy a rule by accident rather than by design — for
  example, treating missing allergen evidence as `fail` because there is no
  `unknown` path. Fixtures will distinguish the two, and where the distinction is
  missing the code needs to be extended, not just tested.
- The existing planner may not expose enough reasoning structure for p3 to
  explain without re-derivation. If it does not, p2-003 grows beyond "prove" into
  "extend the solver output."
- Unit conversion is incomplete outside supported compatible bases; unsupported
  quantities must remain evidence-absent rather than be approximated silently.
- Constraint interactions can reduce the retained recipe pool below the
  requested horizon; solver diagnostics must identify the binding constraint
  without weakening constitutional safety rules.

## Phase p3 - explainable recommendation delivery

Status: planned

### Outcome

The workflow and web application expose a usable meal-planning recommendation
experience — both form-driven and conversational — whose plan, recipe, and
constraint outcomes are explainable while audit-only provenance remains in the
execution trace.

### Goals served

- G-2
- G-6

### Features

- **p3-001-workflow-recommendation-service** *(partial)* — A planning API
  exists; the workflow's request extraction, graph retrieval, and orchestration
  may be partial. Remaining work: confirm the service preserves the deterministic
  domain result through response assembly, and defines the trace boundary.
  (supports G-1, G-2, G-6)
- **p3-002-explainable-response-contract** *(partial)* — Return resolved
  concepts, selected offers, per-requirement outcomes, warnings, and distinct
  drop causes at the permitted user scope. Remaining work: define the response
  schema, add the tests that assert user-facing keys exclude audit provenance and
  that evidence-absent vs. present-exclusion causes are distinct in the payload.
  (serves G-2, G-6)
- **p3-003-web-planner-experience** *(partial)* — Existing web surface, if any.
  Remaining work: verify the end-to-end form flow renders explanations,
  warnings, and drop causes; confirm no audit field leaks into the payload.
  (supports G-1, G-2, G-6)
- **p3-004-conversational-constraint-interface** *(new)* — Accept natural-
  language constraint input, extract a structured request, deliver
  recommendations conversationally across turns, and answer follow-up questions
  by reusing the deterministic reasoning output without paraphrase that alters
  safety or drop semantics. (serves G-1, G-2, G-6)

### Exit criteria

- API response-shape tests pass with plan-, recipe-, and constraint-level
  outcomes, including both evidence-absent and present-but-excluding drop causes.
- The user-facing payload contains only the approved explanation fields; mapping
  confidence, normalization version, source IDs, and other audit provenance are
  absent from the payload and present in the execution trace.
- A representative multi-turn conversation extracts structured constraints from
  prose, returns a recommendation, answers "why not X?" with the reasoning cause
  matching the underlying output, and distinguishes "dropped because evidence
  was absent" from "dropped because evidence ruled it out" in its reply.
- Conversational responses never introduce a recipe that the deterministic
  solver did not return, and never convert an evidence-absent drop into a softer
  or more permissive statement.
- When prose is insufficient to extract a required constraint, the conversational
  flow requests clarification rather than assuming compliance.
- An end-to-end smoke test submits a representative nutrition, allergen, dietary,
  and budget request through both the form flow and the conversational flow and
  shows a recommendation or a named feasibility explanation in the web
  application.
- The workflow preserves the deterministic domain result and does not allow
  response generation to convert a dropped or unknown candidate into a passing
  recommendation.
- **Conformance clause:** for any pre-existing p3 component, the conformance
  clause from p1 applies — the code is proven, not asserted.
- No unresolved blocking findings.

### Risks & unknowns

- Natural-language constraint extraction may be ambiguous; the workflow must
  preserve explicit structured constraints and handle insufficient input without
  inventing compliance.
- The language-model response layer may paraphrase or omit deterministic
  findings. The specific hazard to guard against is a paraphrase that softens or
  converts an evidence-absent drop into a permissive statement (e.g., "probably
  fine" or "not confirmed unsafe"); the response contract and its tests must
  reject any re-expression that alters the safety or drop semantics of the
  underlying result.
- The conversational layer adds session state and multi-turn context; it must
  not persist or reuse a constraint set across turns in a way that loses the
  explicit evidence-absent signaling of the current turn.
- The web client depends on stable backend contracts and may expose audit fields
  accidentally if serialization boundaries are not tested.

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
