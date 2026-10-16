---
feature: p3-001-workflow-recommendation-service
---

# Plan - Workflow recommendation service

## Approach

**Chosen:** A three-node LangGraph workflow (`Extract Constraints` -> `Plan` ->
`Generate Response`) in `remy/workflows`, depending only on a **workflow-owned
plan interface (a port)** expressed in workflow-owned models; the port is
implemented by an **adapter in `remy/app`** (the composition root) that calls
`PlanService.generate` and maps `PlanRequest`/`PlanResponse`/`PlanTrace` to and
from the workflow models. This satisfies R-2 (workflows never imports `api`;
`app` imports both) and keeps the workflow testable with a fake port.

**Main rejected alternative:** Have the workflow call the plan over HTTP
(`POST /plan`) or through a new shared contract package. Rejected because HTTP
adds a network hop and duplicates request validation, and a shared contract
package reopens the closed p2-003 feature more than the minimal return-shape
fix requires; dependency inversion through a workflow-owned port is lighter and
already permitted by `.importlinter`.

## Prerequisites

**P-1 — p2-003's C-7 reopen has landed.**

The reopen (committed 2026-10-15) made the two additive changes:
1. `plan/schemas.py` — `recipe_outcomes` and `constraint_outcomes` are
   re-enabled on `PlanResponse`.
2. `plan/service.py` — `PlanService.generate` returns
   `tuple[PlanResponse, PlanTrace]`; the router unpacks and serializes only
   the response.

The adapter is written against this shape; there is no fallback, no stateful
side channel, and no deferred integration edge.

**P-2 — `langchain` and `langchain-ollama` are added to
`remy/workflows/pyproject.toml`.** These are currently missing from the
environment. The plan adds them as a task (Files to touch). Tests use a fake
LLM client; the real provider is only needed at runtime.

## Design

### section 0 Baseline inventory (read before writing; this is p2 code, not p3)

p3-001 is greenfield; the code read is p2's. Verified by reading the files named.

- **`PlanService.generate` (remy/api/src/api/features/plan/service.py).**
  Current signature `generate(self, request) -> PlanResponse`. It stores the
  trace as a side effect on `self.last_trace: PlanTrace | None`. **The C-7
  reopen (Prerequisite P-1) changes this to
  `generate(self, request) -> tuple[PlanResponse, PlanTrace]` before this
  feature's implementation begins.** `generate_v2` exists (skeleton/post-solve
  variant); the spec says it is not used. The plan reads the pre-reopen code as
  the baseline and the post-reopen shape as the target.

- **`PlanResponse` (plan/schemas.py).** Fields post-P-1: `plan_id`, `status`
  (`complete|partial`), `message`, `validation_summary`, `feasibility_outcome`,
  `relaxed`, `applied_tolerance_pct`,
  `binding_constraints: list[NamedConstraintResponse] | None`, `relaxations`,
  `horizon_totals`, `days: list[DayResponse]`, **and (re-enabled by P-1)
  `recipe_outcomes: list[RecipeOutcomeResponse]` and
  `constraint_outcomes: list[ConstraintOutcomeResponse]`.** The three-level
  recipe/constraint reasoning is thus available in both `PlanResponse` and
  `PlanTrace`.

- **`PlanTrace` (plan/trace.py).** Plain dataclass:
  `feasibility_outcome: str`, `reason: str | None`,
  `binding_constraints: list[NamedConstraint]`, `applied_tolerance_pct: int`,
  `recipes: list[RecipeOutcome]`, `requirements: list[RequirementOutcome]`.
  **No `confidence`, no `normalization_version`, no `source_*`/`*_id`.** This
  confirms **Finding F-P3-1** (R-16 trace-side retention and R-13 "confidence
  in the trace" are not satisfiable through p3-001).

- **Reasoning models (plan/models.py).**
  `RecipeOutcome(recipe_id, outcome: selected|retained-unselected|dropped,
  cause: str|None, causes: tuple[str,...])`;
  `RequirementOutcome(recipe_id, requirement_id, constraint, state,
  requirement_text, resolved_concept, selected_offer: object|None,
  warnings: tuple)`;
  `NamedConstraint(scope: plan|recipe|requirement, code,
  kind: present-evidence-excludes|evidence-absent|unmapped|nutrient-bound|horizon)`;
  `IngredientWarning(code, ingredient_id, detail)`. None carry provenance.

- **`PlanRequest` (plan/schemas.py).** `horizon_days` (1-14), `meals_per_day`
  (1-6), `servings` (>=1, default 1), `nutrient_tolerance_pct`
  (int, `[0,25]`, strict, default 0), `allergies: list[AllergyRequest(code,
  severity: mild|severe|None)]`, `dietary: list[DietaryRequest(code)]`,
  `nutrients: list[NutrientRequest(code, unit, goal, limit{min,max})]`.
  Validates unique codes and `min <= max`. **This is what Extract Constraints
  must produce** (as workflow models the adapter maps into `PlanRequest`).

- **Router & wiring (plan/router.py, plan/dependencies.py).**
  `POST ""` -> `service.generate`; `POST "/v2"` -> `generate_v2`.
  `get_plan_service(repository)` builds `PlanService(repository)`; the
  repository is built from `request.app.state.neo4j_driver`. The adapter does
  not go through the router; it constructs/holds a `PlanService` and calls
  `generate` directly in-process. After P-1, the router unpacks the tuple and
  serializes only the `PlanResponse`.

- **`.importlinter` (SystemCode/.importlinter).** `root_packages = domain,
  workflows, api, app`. Contracts: *domain is a leaf*; *workflows does not
  depend on api* (workflows does-not-import api **and** app); *api does not
  depend on app*; *api does not depend on workflows*. **Q2 is already resolved
  in the codebase: `app` is a root package** (the spec's Q2 note is outdated).
  No contract forbids `app -> api` or `app -> workflows`. **`uv run
  lint-imports` currently passes: 4 kept, 0 broken.**

- **`workflows` package.** Greenfield: `src/workflows/__init__.py` only; **no
  `tests/` directory**. `pyproject.toml` deps: `langgraph>=0.2,<1`,
  `remy-domain`.

- **`app` package.** Composition root; `src/app/__init__.py` is empty.
  `pyproject.toml` deps: `remy-api`, `remy-workflows`. **This is the adapter's
  home.**

- **`sdd.json`.** Updated in this change (see Files to touch) from the p2
  calculator/plan check set to cover `remy/api/tests/features/plan` (regression
  guard for the C-7 reopen), `remy/workflows/tests`, `remy/app/tests`, plus a
  new `lint-imports` check for AC-4.

- **Dependency availability (uv env, WSL).** `langgraph` [OK],
  `langchain_core` 1.6.4 [OK]; **`langchain` [MISSING]**,
  **`langchain-ollama` [MISSING]**, `langchain-openai` [MISSING].
  `init_chat_model` lives in `langchain.chat_models`, so adding `langchain`
  and `langchain-ollama` to `remy/workflows/pyproject.toml` is a plan-stage
  task (Prerequisite P-2).

- **LLM client default.** Model-agnostic via LangChain's `init_chat_model`,
  default provider Ollama (local) reached through `langchain-ollama`; hosted
  providers (OpenAI/Anthropic/Google) selectable by `.env`. Provider is
  configuration, not runtime failover (spec Non-goals).

#### Per-AC baseline status

| AC | Status | Note |
|---|---|---|
| AC-1 | absent | workflow graph does not exist |
| AC-2 | absent | Extract Constraints node new |
| AC-3 | absent | structured pass-through new |
| AC-4 | absent | port + adapter new; lint-imports contract already KEPT and must stay |
| AC-5 | absent | plan outcome mapping new (available in both `PlanResponse` and `PlanTrace` post-P-1) |
| AC-6 | absent | infeasible outcome mapping new |
| AC-7 | absent | relaxed label pass-through new |
| AC-8 | absent | evidence-absent preservation in generation new |
| AC-9 | absent | user-payload R-16 field exclusion new |
| AC-10 | absent | trace envelope new |
| AC-11 | absent | deterministic generation check new |
| AC-12 | absent | LLM-unavailable failure new |
| AC-13 | absent | plan-unavailable failure new |
| AC-14 | absent | workflow constraint-model validation new |
| AC-15 | absent | empty-pool discrimination pass-through new |
| AC-16 | absent | adapter contract test new; runs against the real post-P-1 tuple |
| AC-17 | absent | unapplied-constraints reporting new |
| AC-18 | absent | severity/tolerance faithfulness new |
| AC-19 | absent | mild-allergen warning pass-through new |
| AC-20 | absent | horizon-only request new |
| AC-21 | absent (partial deferral) | user-payload portion of api R-16/R-17 tests runnable; trace-side R-16 expected to fail until F-P3-1 resolves |

### section 1 Node and component shape (no file names here; see Files to touch)

- **Three nodes.** `Extract Constraints` (LLM) -> `Plan` (delegates the three
  middle conceptual stages to the plan port as one call) -> `Generate Response`
  (LLM + deterministic verification). Early-exit edges: any node may terminate
  the graph with a `failure(node, reason)` outcome; later nodes do not run
  (AC-1, AC-12, AC-13, AC-14).

- **Workflow state.** A typed graph state carrying: raw user message; parsed
  constraint set (workflow model); list of unapplied constraints; the plan
  result + plan trace view (workflow models, filled by the Plan node via the
  port); the generation structured output + text; the accumulating trace
  envelope; and the terminal outcome discriminator
  (`plan | infeasible | failure`).

- **Workflow-owned plan port.** A `Protocol` (or ABC) defined in `workflows`,
  typed entirely in **workflow-owned models** — a workflow `PlanInput` (mapping
  to `PlanRequest`'s fields) in, and a workflow `PlanResult` + workflow
  `PlanTraceView` out. The port returns both the result and the trace view.

  **`PlanTraceView` shape (this plan's decision).** `PlanTraceView` is a
  workflow-owned dataclass carrying the same fields as `PlanTrace`:
  `feasibility_outcome`, `reason`, `binding_constraints` (workflow-owned
  `NamedConstraintView`), `applied_tolerance_pct`, `recipes` (workflow-owned
  `RecipeOutcomeView`), `requirements` (workflow-owned
  `RequirementOutcomeView`). The adapter maps `PlanTrace` → `PlanTraceView`
  field-by-field. `PlanTraceView` is a **complete mirror**, not a subset — the
  workflow may need any of the fields, and the trace boundary carries all of
  them (spec's Reach invariant).

- **Adapter (in `app`).** Implements the port by constructing/holding a
  `PlanService` and calling `generate`. After P-1, `generate` returns
  `(PlanResponse, PlanTrace)`; the adapter unpacks both. It maps workflow
  `PlanInput` -> `PlanRequest`, and `PlanResponse` + `PlanTrace` -> workflow
  `PlanResult` + `PlanTraceView`, losing nothing material (AC-16). The adapter
  is the **only** place that maps between workflow models and api models.

- **LLM client.** A thin workflow-owned wrapper over `init_chat_model`
  (default Ollama via `langchain-ollama`), with provider/model from `.env`.
  Both LLM nodes accept an injected client so tests use a fake; no test needs a
  live model (AC-21).

- **Extract Constraints.** Produces the workflow constraint model from the raw
  message (LLM) or passes a structured set through unaltered (AC-3). Faithful
  extraction: every stated allergen/dietary flag present (AC-17); severity only
  when explicit, never downgraded; tolerance 0 unless explicitly requested
  (AC-18); anything the contract cannot express listed as **unapplied**
  (AC-17). Validates against the workflow constraint model (horizon presence,
  `[0,25]` tolerance, known nutrient codes, well-formed `min/max`) and fails
  early (AC-14). Bounded re-prompts on malformed LLM output; then failure
  (AC-12).

- **Plan node.** Builds the port input from the constraint set, calls the port,
  and records the result + trace view into the state and the trace envelope.
  Maps the port's result to a `plan` or `infeasible` outcome, preserving
  binding constraints, the empty-pool-vs-no-assignment distinction (AC-15),
  relaxed label and applied tolerance (AC-7), three-level reasoning and the
  three drop causes with precedence (AC-5, AC-6, AC-16), and mild-allergen
  warnings (AC-19). Port unavailable -> `failure(Plan, ...)` (AC-13).

- **Generate Response.** Produces structured output (referenced recipe IDs,
  requirement IDs, drop causes) **alongside** the text; a deterministic check
  asserts referenced IDs/causes are a subset of the plan result's and that no
  evidence-absent drop is phrased as permissive (AC-8, AC-11). Its input
  excludes R-16 provenance fields so none can leak into text (AC-9). Check
  failure -> `failure(GenerateResponse, ...)` (AC-11); all-or-nothing (C-4).

- **Trace envelope.** A versioned, self-contained workflow trace: schema
  version; outcome discriminator (+ failing node/reason); input (raw message,
  parsed set, unapplied constraints); one entry per node run (Plan = one
  entry); one entry per LLM invocation (node, provider, model, prompt, raw &
  parsed response, duration); and the embedded `PlanTraceView` unchanged. Never
  part of the user-displayable payload (AC-9, AC-10). Carries only what
  `PlanTrace` carries — provenance absence is F-P3-1, not fabricated.

### section 2 R-16 / R-17 conformance against the constitution's named test paths

AC-21 names `tests/api/test_response_schema.py` (R-16) and
`tests/api/test_explanation_shape.py` (R-17). These are **api-package** paths
(the constitution's named fixtures). p3-001's obligation is that the workflow's
**user-displayable output** passes the user-payload portion of R-16 (no
`confidence`, `normalization_version`, `source_*`/`*_id`) and that its outcome
exposes R-17's three levels with distinct causes.

**Alignment with the api fixtures.** The workflow-side tests
(`remy/workflows/tests/test_response_schema_workflow.py` and
`test_explanation_shape_workflow.py`) import the same allowed-key set and the
same distinct-cause assertion contract that the api fixtures use. The
permitted-key list and the three-drop-cause names are defined in one place
(either a small shared test helper under `remy/workflows/tests/` that mirrors
the api test's list, or a comment in each pointing to the api test as the
authority). If the api fixtures change (new field, new cause code), the
workflow-side tests break, surfacing the drift.

The **trace-side** R-16 assertion operates on the trace object, which carries
no provenance (F-P3-1); that assertion is expected to fail until F-P3-1
resolves and is recorded as a deferral (F-2). p3-001 does not edit the api
fixtures.

## Files to touch

| Path | Change | Why |
|---|---|---|
| **`SystemCode/remy/api/src/api/features/plan/schemas.py`** | **uncomment `recipe_outcomes`, `constraint_outcomes` on `PlanResponse`** | **Prerequisite P-1 (C-7 reopen).** Owned by p2-003. Committed before p3-001's implementation. |
| **`SystemCode/remy/api/src/api/features/plan/service.py`** | **change `generate` return to `tuple[PlanResponse, PlanTrace]`** | **Prerequisite P-1.** Owned by p2-003. |
| **`SystemCode/remy/api/src/api/features/plan/router.py`** | **unpack the tuple; serialize only the response** | **Prerequisite P-1.** Owned by p2-003. |
| **`SystemCode/remy/api/tests/features/plan/`** | **regression tests for the tuple return and the re-enabled response fields** | **Prerequisite P-1.** Owned by p2-003. |
| `SystemCode/remy/workflows/pyproject.toml` | add `langchain` and `langchain-ollama` deps | `init_chat_model` + local Ollama default; both currently MISSING (section 0) |
| `SystemCode/remy/workflows/src/workflows/__init__.py` | export the public workflow entry point | package surface |
| `SystemCode/remy/workflows/src/workflows/state.py` | workflow graph state (TypedDict) | AC-1, AC-10 |
| `SystemCode/remy/workflows/src/workflows/models.py` | workflow-owned constraint, plan-input, plan-result, `PlanTraceView` + sub-views, outcome, trace-envelope models | AC-2, AC-5, AC-6, AC-10, AC-16; keeps `api` types out of `workflows` (R-2) |
| `SystemCode/remy/workflows/src/workflows/plan_port.py` | workflow-owned plan port (Protocol) | AC-4; dependency inversion for R-2 |
| `SystemCode/remy/workflows/src/workflows/llm.py` | LLM client wrapper over `init_chat_model` (default Ollama) | AC-2, AC-11, AC-12 |
| `SystemCode/remy/workflows/src/workflows/nodes.py` | the three node functions | AC-2, AC-3, AC-5..AC-9, AC-11..AC-20 |
| `SystemCode/remy/workflows/src/workflows/graph.py` | assemble the `StateGraph`, edges, entry/terminal, early-exit | AC-1, AC-12, AC-13, AC-14 |
| `SystemCode/remy/workflows/src/workflows/trace.py` | versioned trace envelope assembly | AC-10 |
| `SystemCode/remy/workflows/tests/` (new dir) | unit + behavior tests with fake LLM and fake port | every AC's workflow-side rows |
| `SystemCode/remy/app/pyproject.toml` | add test deps if needed (pytest) | app test suite |
| `SystemCode/remy/app/src/app/plan_adapter.py` | adapter implementing the port by calling `PlanService.generate`, mapping to/from `PlanRequest`/`PlanResponse`/`PlanTrace` | AC-4, AC-16 |
| `SystemCode/remy/app/src/app/composition.py` | wire the adapter + LLM client into the workflow (composition root) | AC-4 |
| `SystemCode/remy/app/tests/` (new dir) | adapter contract test (AC-16) + composition/import-boundary test (AC-4) | AC-4, AC-16 |
| `sdd.json` | check set covers `remy/api/tests/features/plan`, `remy/workflows/tests`, `remy/app/tests`, lint/typecheck for workflows+app, and `lint-imports` | AC-4; CI must cover the feature's files |
| `docs/sdd/features/p2-003-feasible-meal-plan-solving/decisions.md` | record the C-7 reopen (return shape + re-enabled response fields) | p2-003 decisions; consequential change to a closed feature |
| `docs/sdd/features/p3-001-workflow-recommendation-service/decisions.md` | record F-P3-1 deferral, Q2 resolution, the P-1 prerequisite | consequential clarifications & deferrals |

The **Prerequisite P-1 files** (the p2-003 reopen) are listed in this table
because they must be committed before p3-001's implementation, but they are
**owned by p2-003**. This plan does not edit them; the tasks that perform the
reopen belong to a p2-003 reopen effort recorded separately.

## Constitution alignment

- **R-2 (inward deps; workflows does-not-import api):** workflow depends on a
  workflow-owned port; the adapter lives in `app`, which may import both;
  `uv run lint-imports` is a CI check (AC-4) and must stay 4-kept/0-broken.
- **R-3 (stack shape fixed):** LangGraph/LangChain + local LLM are libraries
  inside the existing Python backend; no new backend/store/solver shape.
  Confirmed same-shape by the constitution owner (spec C-5).
- **R-5 (absent evidence drops):** the workflow passes p2's evidence-absent
  drops through unchanged; the generation check forbids re-expressing them as
  permissive (AC-8, AC-11).
- **R-6 (severe drops / mild warns):** mild-allergen ingredient warnings are
  carried to the outcome and text; extraction never downgrades severity
  (AC-18, AC-19).
- **R-14 (feasibility floor; A-005 relaxation set):** infeasibility result,
  binding constraints, relaxed label, and applied tolerance pass through
  unchanged; the workflow never widens a relaxation (AC-6, AC-7).
- **R-16 (user response excludes audit provenance):** user-displayable output
  excludes `confidence`/`normalization_version`/`source_*`/`*_id`; the trace
  holds what it can; trace-side retention is F-P3-1 (AC-9, AC-21).
- **R-17 (three-level, distinct causes):** plan/recipe/constraint outcomes and
  the three distinct drop causes with precedence pass through for feasible and
  infeasible outcomes (AC-5, AC-6, AC-16).

## Test strategy

All workflow tests use a **fake LLM client** and a **fake plan port**; no test
requires a live model or a live Neo4j (AC-21). "api R-16/R-17" rows assert the
workflow's user-payload/outcome against the same conditions the constitution's
named api fixtures assert, in the workflow/app suites.

| AC | Test type | Test location / name | Notes |
|---|---|---|---|
| AC-1 | unit | `remy/workflows/tests/test_graph_order.py::test_node_order_and_single_outcome` | asserts node order, one outcome+trace, early-exit skips later nodes |
| AC-2 | unit | `remy/workflows/tests/test_extract.py::test_nl_extraction_records_raw_and_set` | fake LLM returns a constraint set; raw+parsed recorded in trace |
| AC-3 | unit | `remy/workflows/tests/test_extract.py::test_structured_passthrough_no_llm` | structured input used unaltered; LLM not called |
| AC-4 | integration/boundary | `remy/app/tests/test_import_boundary.py::test_lint_imports_kept` + `remy/workflows/tests/test_plan_port.py::test_workflow_uses_port_only` | runs `uv run lint-imports` (4 kept); workflow references port, not `api` |
| AC-5 | unit | `remy/workflows/tests/test_plan_node.py::test_feasible_outcome_carries_three_levels` | fake port returns feasible result+trace view; slots + 3-level reasoning preserved |
| AC-6 | unit | `remy/workflows/tests/test_plan_node.py::test_infeasible_carries_binding_and_reasoning` | binding constraints + 3-level reasoning intact; no fabricated plan |
| AC-7 | unit | `remy/workflows/tests/test_plan_node.py::test_relaxed_label_and_tolerance_passthrough` | relaxed + applied tolerance unchanged |
| AC-8 | unit | `remy/workflows/tests/test_generate.py::test_evidence_absent_not_permissive` | evidence-absent drop stays distinct; text not permissive |
| AC-9 | unit | `remy/workflows/tests/test_response_schema_workflow.py::test_user_payload_excludes_provenance` | user-displayable payload has no `confidence`/`normalization_version`/`source_*`/`*_id`; generation input also excludes them |
| AC-10 | unit | `remy/workflows/tests/test_trace_envelope.py::test_envelope_fields_and_embedded_plantrace` | envelope records nodes/raw extraction/constraint set/unapplied/model+provider/outcomes; embeds PlanTraceView; 3 levels reachable |
| AC-11 | unit | `remy/workflows/tests/test_generate.py::test_structured_check_subset_and_fail` | referenced IDs/causes subset passes; superset/permissive fails -> failure outcome |
| AC-12 | unit | `remy/workflows/tests/test_failure.py::test_llm_unavailable_or_timeout_fails_node` | fake LLM raises/times out after bounded re-prompts -> failure(node) |
| AC-13 | unit | `remy/workflows/tests/test_failure.py::test_plan_port_unavailable_fails` | fake port raises -> failure(Plan); no feasibility claim |
| AC-14 | unit | `remy/workflows/tests/test_extract.py::test_invalid_constraint_set_fails_before_plan` | missing horizon / tolerance out of range / unknown nutrient / bad min-max -> failure pre-plan; no coercion |
| AC-15 | unit | `remy/workflows/tests/test_plan_node.py::test_empty_pool_distinct_from_no_assignment` | fake port returns `no-recipes-survived` vs `no-assignment`; distinct |
| AC-16 | contract | `remy/app/tests/test_plan_adapter.py::test_adapter_maps_plan_response_and_trace` | adapter maps a real `(PlanResponse, PlanTrace)` (from a fake `PlanService`, but with real api schemas) losslessly; runs against the post-P-1 tuple |
| AC-17 | unit | `remy/workflows/tests/test_extract.py::test_unapplied_constraints_reported` | cost/dislike/cuisine -> listed unapplied in outcome and trace |
| AC-18 | unit | `remy/workflows/tests/test_extract.py::test_severity_and_tolerance_faithful` | ambiguous phrase != mild; tolerance 0 unless explicit; severity never downgraded |
| AC-19 | unit | `remy/workflows/tests/test_generate.py::test_mild_allergen_warning_in_outcome_and_text` | ingredient-scoped warning present in outcome and text |
| AC-20 | unit | `remy/workflows/tests/test_plan_node.py::test_horizon_only_request` | empty constraint set; plan decides on horizon coverage |
| AC-21 | conformance | `remy/workflows/tests/test_response_schema_workflow.py` + `remy/workflows/tests/test_explanation_shape_workflow.py` | user-payload R-16 + R-17 three-level/distinct-cause pass; **trace-side R-16 deferred to F-P3-1 (F-2)**; all with fake LLM/port; the api-path fixtures remain the constitution's named authority and are mirrored in these tests |

## Integration per interface

Four producer->consumer edges the plan names (the four required by the prompt).

| Interface (producer -> consumer) | Test type | Test location / name | Notes |
|---|---|---|---|
| **Extract Constraints output -> Plan node input** (parsed constraint set) | integration (real both nodes, fake LLM + fake port) | `remy/workflows/tests/test_integration_extract_to_plan.py::test_constraint_set_flows_to_plan_input` | runs the real Extract and Plan nodes in-graph; fake LLM yields a set, asserts the Plan node receives the mapped port input; code under test (nodes) is real |
| **Plan node -> p2-003 plan path (via workflow-owned port)** (`PlanInput` in, `(PlanResponse, PlanTrace)` out) | integration (real adapter, **real `PlanService`**) | `remy/app/tests/test_integration_adapter_plan.py::test_adapter_calls_real_generate_and_maps` | the adapter runs for real against a real `PlanService.generate` returning the post-P-1 tuple; the real repository is mocked at the Neo4j driver (per the phase posture; the data-prep-price-path finding blocks real marts). Asserts the mapped workflow `PlanResult` + `PlanTraceView` lose nothing from `PlanResponse` + `PlanTrace` |
| **Generate Response node -> workflow outcome** (structured refs + causes + text) | integration (real node, fake LLM) | `remy/workflows/tests/test_integration_generate_to_outcome.py::test_structured_output_drives_outcome_and_check` | real Generate node consumes a real plan result (from fake port) and the fake LLM's structured output; asserts the deterministic check and the assembled outcome |
| **Workflow -> caller (p3-004 / p3-002)** (outcome + trace envelope) | integration (real full graph, fakes at the edges) | `remy/workflows/tests/test_integration_workflow_envelope.py::test_end_to_end_outcome_and_trace_envelope` | real three-node graph end-to-end with fake LLM + fake port; asserts the single outcome + versioned trace envelope with embedded PlanTraceView; the consumer-side (p3-002/p3-004) asserts on the real envelope shape this feature produces |

## Risks & mitigations

- **R-1 -- The C-7 reopen has not landed yet.** This plan is written against
  the post-reopen shape; Prerequisite P-1 names the reopen as a hard
  prerequisite. If the reopen does not land before implementation begins,
  p3-001 cannot be implemented as specified; the sequencing is resolved at
  phase review. *Mitigation:* the reopen is a small, additive fix to closed
  p2-003 (uncomment two response fields; change `generate`'s return to a
  tuple; unpack in the router). Recorded as a prerequisite, not a risk that
  can be deferred indefinitely.
- **R-2 -- Finding F-P3-1: `PlanTrace` carries no R-16 provenance.** R-16's
  trace-side assertion and R-13's "confidence in the trace" cannot pass through
  p3-001. *Mitigation:* pass through what `PlanTrace` carries; never fabricate;
  record F-2 deferral for AC-21's trace-side assertion; owner is p2-003.
- **R-3 -- langchain / langchain-ollama missing from the env.** *Mitigation:*
  adding them to `remy/workflows/pyproject.toml` is a plan task; after `uv
  sync` the fake-LLM tests do not need the real provider, so CI does not
  require a running Ollama.
- **R-4 -- LLM nondeterminism could leak into eligibility/feasibility.**
  *Mitigation:* the LLM only extracts and phrases; all decisions come from the
  deterministic port; AC-11's structured check gates generation; AC-18 forbids
  severity/tolerance invention.
- **R-5 -- `sdd.json` is project-global; narrowing it could drop regression
  coverage of the reopen.** *Mitigation:* the new check set retains
  `remy/api/tests/features/plan` so the C-7 reopen is regression-guarded, and
  adds workflows+app+lint-imports.
- **R-6 -- Shared-plan collision with other p3 features.** p3-002 consumes this
  trace boundary. *Mitigation:* the trace envelope is versioned; the
  consumer-side edge test asserts the real shape; collisions surface at phase
  collision check.
- **R-7 -- `PlanTraceView` mirror could drift from `PlanTrace`.** If p2-003
  adds a field to `PlanTrace`, the adapter's mapping won't carry it, and the
  workflow trace boundary silently loses the field. *Mitigation:* AC-16's
  contract test asserts field-for-field mapping and fails when `PlanTrace`
  gains a field the adapter doesn't map. The test's `PlanTrace` fixture is
  constructed from the real api dataclass, not a hand-built dict, so a
  structural change to `PlanTrace` surfaces at test time.

## Scope check

Fits one working context: **yes.** One workflow package (`remy/workflows`), one
adapter in the composition root (`remy/app`), one config change (`sdd.json`),
and one decisions record. The prerequisite P-1 reopen is a separate effort
owned by p2-003 and committed before this feature's implementation begins; it
is not work this feature performs, but it is on the critical path.

## Revision notes
<!-- F-n -> what changed -->

- **F-1 (C-7 reopen is a prerequisite, not a deferral).** Baseline reading of
  `PlanService.generate` and `PlanResponse` confirmed the trace is on
  `self.last_trace` and `recipe_outcomes`/`constraint_outcomes` are commented
  out on `PlanResponse`. The plan's previous revision treated the reopen as a
  deferral with a deferred integration edge. The reviewer flagged that this
  leaves the plan unimplementable as written. **This revision makes C-7 a hard
  prerequisite (P-1):** the reopen lands before p3-001's implementation
  begins; the adapter calls the real `generate` returning
  `(PlanResponse, PlanTrace)`; there is no fallback, no `last_trace` read, and
  no deferred integration edge. Recorded in `## Prerequisites` and in
  decisions.md.
- **F-2 (F-P3-1 trace-side R-16 deferral).** `PlanTrace` carries no
  `confidence`/`normalization_version`/`source_*`/`*_id`, so AC-21's trace-side
  R-16 assertion and R-13's "confidence in the trace" cannot pass through
  p3-001. The user-payload portion is enforced; the trace-side assertion is
  deferred to F-P3-1 (owner p2-003). Recorded in decisions.md.
- **F-3 (Q2 resolved in codebase).** The spec's Open-question Q2 ("add `app` to
  `.importlinter` root packages") is already done: `.importlinter` lists `app`
  as a root package and `lint-imports` passes 4/0. The plan does not add `app`;
  it relies on the existing contracts and only keeps them green.
- **F-4 (sdd.json check set).** Updated the project check set to cover the
  feature's paths (`remy/workflows/tests`, `remy/app/tests`), retain
  `remy/api/tests/features/plan` as the reopen regression guard, and add a
  `lint-imports` check for AC-4.
- **F-5 (`PlanTraceView` is a full mirror).** The plan's previous revision left
  `PlanTraceView`'s shape unspecified. This revision names it as a
  workflow-owned dataclass carrying every field of `PlanTrace`. Rationale: the
  trace boundary (spec Reach invariant) requires all of them; a partial mirror
  would silently drop data. R-7 covers the drift risk with the contract test.
- **F-6 (integration edge against real `PlanService`).** The "Plan node ->
  p2-003 plan path" row now runs the adapter against a real
  `PlanService.generate` (with the Neo4j driver mocked per the phase posture),
  not a fake service. The real post-P-1 tuple is what gets mapped. This
  follows from F-1.
- **F-7 (AC-16 real tuple).** AC-16's contract test now constructs its
  `PlanTrace` fixture from the real api dataclass, so a structural change to
  `PlanTrace` surfaces at test time (R-7).
- **F-8 (R-16/R-17 alignment with api fixtures).** Section 2 now names how the
  workflow-side tests stay aligned with the constitution's named api fixtures:
  same allowed-key set, same distinct-cause contract, drift surfaces as a test
  failure.

## Tasks

### Group 0 — prerequisites & scaffolding

- [x] **T-1** Verify P-1 (C-7 reopen) landed; add langchain deps (P-2)
  - Type: admin
  - Covers: Prerequisites P-1, P-2
  - Files: `SystemCode/remy/workflows/pyproject.toml`
  - Done when:
    - `uv run --package remy-api python -c "import inspect; from api.features.plan.service import PlanService; print(inspect.signature(PlanService.generate).return_annotation)"` prints `tuple[PlanResponse, PlanTrace]` (or its typing equivalent); if not, **stop** and report — P-1 hasn't landed.
    - `uv run --package remy-api python -c "from api.features.plan.schemas import PlanResponse; print('recipe_outcomes' in PlanResponse.model_fields, 'constraint_outcomes' in PlanResponse.model_fields)"` prints `True True`.
    - `cd SystemCode/remy/api && uv run --package remy-api pytest -q tests/features/plan` passes.
    - `cd SystemCode && uv run lint-imports` reports 4 kept, 0 broken.
    - `langchain` and `langchain-ollama` are added to `remy/workflows/pyproject.toml`'s dependencies; `uv sync --all-packages` succeeds.

- [x] **T-2** Create the `workflows` package skeleton (models, state, port, trace envelope) — no nodes yet
  - Type: impl
  - Covers: AC-4, AC-10, AC-16 (structural prerequisites)
  - Files: `SystemCode/remy/workflows/src/workflows/__init__.py`, `state.py`, `models.py`, `plan_port.py`, `trace.py`
  - Done when:
    - `models.py` defines workflow-owned dataclasses: `ConstraintSet`, `PlanInput`, `PlanResult`, `PlanTraceView` (a full mirror of `PlanTrace` with workflow-owned sub-views: `NamedConstraintView`, `RecipeOutcomeView`, `RequirementOutcomeView`), `Outcome` (discriminated: `plan | infeasible | failure`), `TraceEnvelope`. No imports from `api`.
    - `plan_port.py` defines a `Protocol` (or ABC) with one method returning `(PlanResult, PlanTraceView)`, typed entirely in workflow models.
    - `trace.py` assembles the versioned envelope: schema version, outcome, input (raw message, parsed set, unapplied constraints), one entry per node run, one entry per LLM invocation.
    - `state.py` defines the graph state `TypedDict` carrying: raw message, parsed set, unapplied constraints, `PlanResult`, `PlanTraceView`, generation structured output, generation text, `TraceEnvelope`, `Outcome`.
    - `uv run --package remy-workflows mypy src/workflows` clean; `uv run lint-imports` still 4 kept.

### Group 1 — Extract Constraints (LLM node)

- [x] **T-3** Write failing tests: Extract Constraints behavior
  - Type: test
  - Covers: AC-2, AC-3, AC-14, AC-17, AC-18
  - Files: `SystemCode/remy/workflows/tests/__init__.py`, `tests/conftest.py` (fake LLM fixture), `tests/test_extract.py`
  - Done when: tests fail because `nodes.extract_constraints` does not exist; the tests drive the node directly with a fake LLM and assert:
    - AC-2: natural-language input yields a parsed constraint set; both the raw LLM response and the parsed set are recorded in the trace.
    - AC-3: a structured constraint set is used unaltered; the fake LLM is not called.
    - AC-14: missing horizon / `nutrient_tolerance_pct` out of `[0,25]` / unknown nutrient code / `min > max` each produce a `failure` outcome before the port is invoked; no field is silently coerced.
    - AC-17: a stated allergen or dietary flag appears in the set; a stated cost/dislike/cuisine is listed as `unapplied` in both the outcome and the trace.
    - AC-18: an ambiguous severity phrase does not produce `mild`; `nutrient_tolerance_pct` is 0 unless explicitly requested; a stated severity is never downgraded.

- [x] **T-4** Implement the LLM client wrapper and the Extract Constraints node
  - Type: impl
  - Covers: AC-2, AC-3, AC-14, AC-17, AC-18
  - Files: `SystemCode/remy/workflows/src/workflows/llm.py`, `nodes.py`, `graph.py` (partially — the extract node and its early-exit edge)
  - Done when: T-3 passes; the LLM wrapper is a thin layer over `init_chat_model`, default provider Ollama; provider and model are configuration (env), not failover; the node accepts an injected LLM client so tests use the fake.

### Group 2 — Plan node (port delegation)

- [x] **T-5** Write failing tests: Plan node maps the port's result to a workflow outcome, no fabrication
  - Type: test
  - Covers: AC-5, AC-6, AC-7, AC-13, AC-15, AC-19, AC-20
  - Files: `SystemCode/remy/workflows/tests/test_plan_node.py`, `tests/conftest.py` (fake port fixture)
  - Done when: tests fail because `nodes.plan` does not exist; the tests drive the node with a fake port and assert:
    - AC-5: feasible result carries slots and three-level reasoning (plan/recipe/constraint) unchanged.
    - AC-6: infeasible result carries the binding constraints and three-level reasoning, including dropped candidates; no fabricated plan.
    - AC-7: a relaxed plan carries the relaxed label and applied tolerance unchanged.
    - AC-13: the port raising yields `failure(Plan, ...)`; no trace claims feasibility.
    - AC-15: `no-recipes-survived` and `no-assignment` are distinct in the outcome.
    - AC-19: a mild-allergen ingredient warning is present in the outcome.
    - AC-20: a horizon-only request produces an empty constraint set and the port decides on horizon coverage.

- [x] **T-6** Implement the Plan node
  - Type: impl
  - Covers: AC-5, AC-6, AC-7, AC-13, AC-15, AC-19, AC-20
  - Files: `SystemCode/remy/workflows/src/workflows/nodes.py`, `graph.py` (Plan node + its early-exit edge)
  - Done when: T-5 passes; the node builds `PlanInput` from the constraint set, calls the port, records `PlanResult` and `PlanTraceView` into state and trace, and maps the result to a `plan | infeasible` outcome.

### Group 3 — Generate Response (LLM + deterministic check)

- [x] **T-7** Write failing tests: Generate Response's structured check and evidence-absent preservation
  - Type: test
  - Covers: AC-8, AC-9, AC-11, AC-12
  - Files: `SystemCode/remy/workflows/tests/test_generate.py`, `tests/conftest.py` (extend the fake LLM to return structured output)
  - Done when: tests fail because `nodes.generate_response` does not exist; the tests assert:
    - **AC-11's structured check (F-2 resolution):** the check is (a) every recipe ID / requirement ID referenced in the structured output is a subset of those in the plan result; (b) every drop-cause code in the structured output maps 1:1 to a plan cause; and (c) if a recipe appears as "selected" in the structured output but its cause code is `evidence-absent`, the check fails. The assertion is on the **structured output**, not on parsing the text; "permissive phrasing" is not asserted at the structured layer (the check ensures the structured output doesn't contradict the plan; the LLM is separately instructed not to phrase permissively, and that instruction is tested by one negative case where the structured output contradicts the plan).
    - AC-8: an evidence-absent drop stays distinct in the outcome; the text does not restate it as permissive (verified against the structured output's cause codes).
    - AC-9: the node's input excludes `confidence`, `normalization_version`, `source_*`, `*_id`; the user-displayable payload excludes them too.
    - AC-12: the fake LLM raising or timing out yields `failure(GenerateResponse, ...)`; no trace claims a recommendation.

- [x] **T-8** Implement the Generate Response node
  - Type: impl
  - Covers: AC-8, AC-9, AC-11, AC-12
  - Files: `SystemCode/remy/workflows/src/workflows/nodes.py`, `graph.py` (Generate Response node + its early-exit edge)
  - Done when: T-7 passes; the node produces structured output alongside the text; the check runs before user-facing serialization; the LLM input is filtered to exclude R-16 provenance fields.

### Group 4 — workflow assembly, trace envelope, end-to-end

- [x] **T-9** Write failing tests: graph order, single outcome+trace, early-exit, trace envelope
  - Type: test
  - Covers: AC-1, AC-10, AC-21
  - Files: `SystemCode/remy/workflows/tests/test_graph_order.py`, `tests/test_trace_envelope.py`, `tests/test_integration_workflow_envelope.py`
  - Done when: tests fail because `graph.build()` does not exist; the tests assert:
    - AC-1: the three nodes run in order; a single outcome and a single trace envelope are returned; early-exit skips later nodes; the Plan node appears as one entry in the trace.
    - AC-10: the envelope records schema version, outcome, input (raw message, parsed set, unapplied constraints), one entry per node run, one entry per LLM invocation (node, provider, model, prompt, raw response, parsed response, duration), and the embedded `PlanTraceView`; the three-level reasoning is reachable through the envelope.
    - AC-21 (user-payload portion): the user-displayable portion of the outcome excludes `confidence`, `normalization_version`, `source_*`, `*_id`. The workflow-side R-17 assertion (three levels, distinct causes) passes.
    - AC-21 (trace-side R-16): the trace-side assertion is expected to **xfail** with a reason referencing F-P3-1 (PlanTrace carries no provenance). The test exists, is marked `xfail`, and documents the gap.

- [x] **T-10** Assemble the graph and the trace envelope
  - Type: impl
  - Covers: AC-1, AC-10, AC-21
  - Files: `SystemCode/remy/workflows/src/workflows/graph.py`, `trace.py`
  - Done when: T-9 passes; the `StateGraph` is assembled with the three nodes, the early-exit edges, and the entry/terminal; the trace envelope assembles at every exit.

- [x] **T-11** Write failing tests: integration edges inside the workflow
  - Type: integration
  - Covers: four edges — Extract→Plan, Generate→outcome, workflow→caller
  - Files: `SystemCode/remy/workflows/tests/test_integration_extract_to_plan.py`, `tests/test_integration_generate_to_outcome.py`
  - Done when: the tests assert the parsed constraint set flows into the Plan node's `PlanInput`; the Generate Response's structured output drives the outcome and the check; the workflow→caller edge produces the envelope (covered end-to-end in T-9's integration test); code under test is real (nodes); fakes only at the LLM and port.

### Group 5 — adapter in `app`

- [x] **T-12** Write failing tests: adapter maps the real `(PlanResponse, PlanTrace)` losslessly; P-1 guard
  - Type: contract + integration
  - Covers: AC-4, AC-16; F-3
  - Files: `SystemCode/remy/app/tests/__init__.py`, `tests/conftest.py`, `tests/test_plan_adapter.py`, `tests/test_integration_adapter_plan.py`, `tests/test_import_boundary.py`
  - Done when: tests fail because `app.plan_adapter` does not exist; the tests assert:
    - **AC-16 (contract, F-3):** the adapter maps a real `(PlanResponse, PlanTrace)` — constructed from the real api dataclass, not a hand-built dict — to workflow `PlanResult` + `PlanTraceView` field-for-field. **The test constructs the tuple by calling a real `PlanService.generate` (with the Neo4j driver mocked) so that if P-1 hasn't landed, the failure message reads "generate did not return a tuple; P-1 prerequisite missing" — not a confusing mapping error.** R-7's drift risk is covered because the fixture uses the real api dataclass.
    - **AC-4 (import boundary):** `uv run lint-imports` passes 4 kept / 0 broken when run from `SystemCode/`; `workflows` does not import `api`; `app` may import both.

- [x] **T-13** Implement the adapter and composition root wiring
  - Type: impl
  - Covers: AC-4, AC-16
  - Files: `SystemCode/remy/app/src/app/plan_adapter.py`, `composition.py`, `pyproject.toml` (add pytest test-dep if missing)
  - Done when: T-12 passes; the adapter implements the workflow-owned port by calling `PlanService.generate` and unpacking the tuple; the adapter is the only place that maps between workflow and api models; the composition root wires the adapter and the LLM client into the workflow.

### Group 6 — CI config

- [x] **T-14** Update `sdd.json` check set
  - Type: impl
  - Covers: AC-4; CI scope
  - Files: `sdd.json`
  - Done when: `test` covers `remy/api/tests/features/plan` (regression guard for the C-7 reopen), `remy/workflows/tests`, `remy/app/tests`; `lint` and `typecheck` cover `src/workflows` and `src/app`; a new `lint-imports` check runs `uv run lint-imports` **from `SystemCode/`** (where `.importlinter` lives) so the working-directory is explicit (per the plan review's nit).

- [ ] **T-15** Add a workflow-side R-16/R-17 conformance test
  - Type: test
  - Covers: AC-21
  - Files: `SystemCode/remy/workflows/tests/test_response_schema_workflow.py`, `tests/test_explanation_shape_workflow.py`
  - Done when: the workflow-side tests import the same allowed-key set and the same distinct-cause contract as the constitution's named api fixtures (`tests/api/test_response_schema.py`, `tests/api/test_explanation_shape.py`); the user-payload portion passes; the trace-side R-16 assertion is `xfail` with a reason referencing F-P3-1. A comment in each file points to the api test as the authority so drift surfaces.

### Group 7 — closing admin

- [ ] **T-16** Record decisions
  - Type: admin
  - Covers: F-P3-1, F-2, Q2, P-1, P-2
  - Files: `docs/sdd/features/p3-001-workflow-recommendation-service/decisions.md`
  - Done when: the decisions file records (a) F-P3-1 as a tracked finding owned by p2-003 (R-16 trace-side retention + R-13 confidence-in-trace are not satisfiable through p3-001); (b) F-2's deferral of AC-21's trace-side assertion; (c) the Q2 resolution (already in codebase); (d) P-1 as a landed prerequisite; (e) P-2 (langchain deps); (f) F-1's spec-sync to-do (port returns workflow models; the adapter returns the real tuple — spec's C-1 wording to be corrected at next spec touch).

- [ ] **T-17** Run the full suite and CI
  - Type: verification
  - Covers: all ACs and interfaces
  - Files: (all above)
  - Done when:
    - `cd SystemCode/remy/api && uv run --package remy-api pytest -q tests/features/plan tests/features/calculator` passes.
    - `cd SystemCode/remy/workflows && uv run --package remy-workflows pytest -q` passes; the AC-21 trace-side test reports `xfail`, not `fail`.
    - `cd SystemCode/remy/app && uv run --package remy-app pytest -q` passes.
    - `cd SystemCode && uv run lint-imports` reports 4 kept, 0 broken.
    - `sdd.py ci p3-001-workflow-recommendation-service` reports `OVERALL: PASS`.
    - The `data-prep-price-path` finding remains the tracked deferral; the workflow→plan integration uses a real `PlanService` with a mocked Neo4j driver.
