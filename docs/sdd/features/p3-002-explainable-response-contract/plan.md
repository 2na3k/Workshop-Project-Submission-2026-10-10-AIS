---
feature: p3-002-explainable-response-contract
---

# Plan - Explainable response contract

## Approach

- **Chosen:** Define the contract as a set of concrete, framework-free Python
  types (Pydantic models) in a single new module `app/chat_contract.py` in the
  `remy-app` composition-root package — `ChatRequest`, the five SSE event models
  (`MetadataEvent`, `TokenEvent`, `PlanUpdatedEvent`, `ErrorEvent`, `DoneEvent`),
  the three-level explanation models (plan / recipe / constraint), and a thin
  mapper from p3-001's `TraceEnvelope` to the explanation payload — plus the two
  constitution-named conformance fixtures. `remy-app` is the only package that
  may import both `api` and `workflows` under the `.importlinter` contracts, so
  it is the only place the contract can read p3-001's `TraceEnvelope` **and** be
  imported by the fixtures without breaking an import contract.
- **Rejected:** Put the contract types in `remy-api` (e.g.
  `api/features/chat/schemas.py`). Rejected because the contract must consume
  p3-001's `TraceEnvelope` (a `workflows` type) and `.importlinter`'s
  `api does not depend on workflows` forbids `api` source from importing
  `workflows`; the mapper could not live in `api`.

## Design

### §0 Pre-write confirmations (read before writing)

- **The two constitution-named fixtures are absent.** Verified: `remy/api/tests`
  contains only `features/{plan,dietary,calculator}`; there is **no**
  `remy/api/tests/api/` directory and no `test_response_schema.py` or
  `test_explanation_shape.py` anywhere under a `tests/api/` path. The
  calculator's `remy/api/tests/features/calculator/test_response_schema.py` is a
  **different** file (p2-002's feature-local regression) and is **not** R-16's
  fixture (spec "Fixtures"; p2-002 F-D / p3-001 BD-2a). p3-002 creates both
  named fixtures fresh, at `remy/app/tests/api/<name>` (see §1).
- **`TraceEnvelope` input shape.** Verified in
  `remy/workflows/src/workflows/models.py`: `TraceEnvelope(schema_version,
  outcome: Outcome, raw_message, parsed_constraints: ConstraintSet | None,
  unapplied_constraints, node_runs, llm_invocations, plan_trace: PlanTraceView
  | None)`; `Outcome(kind: "plan"|"infeasible"|"failure", plan: PlanResult |
  None, reason, node, unapplied_constraints, text)`; `PlanTraceView(
  feasibility_outcome, reason, binding_constraints: NamedConstraintView[],
  applied_tolerance_pct, recipes: RecipeOutcomeView[], requirements:
  RequirementOutcomeView[])`. `RecipeOutcomeView(recipe_id, outcome, cause,
  causes)`; `RequirementOutcomeView(recipe_id, requirement_id, constraint,
  state, requirement_text, resolved_concept, selected_offer, warnings)`.
- **Audit provenance is already stripped at the API→workflow boundary (F-P3-1
  root).** Verified in `app/plan_adapter.py` + `api/features/plan/schemas.py`:
  `ConstraintOutcomeResponse.selected_offer` is `SelectedOfferResponse{
  listing_name, retailer}` only. The adapter's `_requirement` copies that offer
  into `RequirementOutcomeView.selected_offer`, so `confidence` /
  `source_snapshot_id` / `mapping_version` / `food_key` never reach
  `PlanTraceView`. This is why R-16's **user-payload** clause is satisfiable
  (the fields are already absent) and its **trace-side** clause is **not**
  (the fields never arrived) — Finding F-P3-1, owned by p2-003.
- **Import-linter contracts** (`SystemCode/.importlinter`): root packages
  `domain, workflows, api, app`; forbidden edges include `api → workflows`,
  `api → app`, `workflows → api`, `workflows → app`. `app` may import `api` and
  `workflows` (composition root). This is the binding constraint on module and
  fixture placement.
- **Current check set** (`sdd.json`) runs `remy/api/tests/features/plan`,
  `remy/workflows/tests`, `remy/app/tests`. It does **not** explicitly cover
  the new contract module or the new fixtures; this plan updates it (see Files
  to touch).

### §1 Fixture location — amendment A-007 (confirmed)

The constitution names the fixture paths `tests/api/test_response_schema.py`
and `tests/api/test_explanation_shape.py`. Those paths are package-relative;
the owning package is bounded by the import contracts:

- The fixtures must import the **contract types** (to serialize a representative
  response and assert the key set) and p3-001's **`TraceEnvelope`** (to build
  the input). The contract types live in `app` (Approach). A fixture that
  imports `app` must therefore run where `remy-app` is importable.
- `remy-app` depends on `remy-api` **and** `remy-workflows`; the reverse is
  forbidden. `remy/app/tests/` already imports `api`, `app`, and `workflows`
  together (`test_integration_adapter_plan.py`). So the fixtures land under
  **`remy/app/tests/api/`** — `remy/app/tests/api/test_response_schema.py` and
  `remy/app/tests/api/test_explanation_shape.py`, satisfying the
  constitution's `tests/api/<name>` leaf within the only package that can host
  them.
- **Amendment A-007 (approved).** The constitution's R-16 and R-17 named check
  paths are corrected from `tests/api/<name>` to
  `SystemCode/remy/app/tests/api/<name>`, matching the deployed placement this
  feature establishes and formalizing the divergence already recorded as
  p2-002 F-D and p3-001 BD-2a. The `tests/api/<name>` leaf is preserved; the
  package prefix is made explicit. A-007 lands alongside this plan (the
  amendment file is committed before the plan is approved). The plan does not
  initiate the amendment; it consumes the approved A-007 as the binding path.

### §2 Contract module `app/chat_contract.py`

Concrete Pydantic v2 models (p3-004 imports this module; the field *names* below
are the contract and are fixed here, since a contract whose field names are
undecided is not a contract p3-004 can implement):

- **`ChatRequest`** — `session_id: str` (required), `message: str` (required),
  `user_context: dict | None = None` (optional). `extra="forbid"`. (AC-1)
- **Three-level explanation models** (the payload the SSE events carry):
  - `OfferView` — `listing_name: str`, `retailer: str`. No audit fields.
  - `ConstraintExplanation` — `requirement_id: str | None`, `constraint: str`,
    `state: str`, `resolved_concept: str | None`, `selected_offer:
    OfferView | None`, `warnings: list[str]`. (AC-9)
  - `RecipeExplanation` — `recipe_id: str`, `outcome: str`, `drop_causes:
    list[DropCause]` (ordered), `constraints: list[ConstraintExplanation]`.
    (AC-4, AC-5, AC-6)
  - `PlanExplanation` — `feasibility_outcome: str`, `reason: str | None`,
    `binding_constraints: list[NamedConstraintView]` (reuses the
    `workflows.models.NamedConstraintView` type; `app` may import `workflows`),
    `relaxed: bool`, `applied_tolerance_pct: int`, `recipes:
    list[RecipeExplanation]`. (AC-3, AC-13, AC-14)
  - `DropCause` — a closed enum `{"evidence-absent",
    "present-evidence-excludes", "unmapped"}`. (AC-4, AC-5, AC-6)
- **Five SSE event models**, each with a literal `event` discriminator so the
  type is exactly one of five (AC-2):
  - `MetadataEvent` — `event="metadata"`, `session_id: str`, `workflow_node:
    str`, `trace_id: str`. (AC-10)
  - `TokenEvent` — `event="token"`, `delta: str`.
  - `PlanUpdatedEvent` — `event="plan_updated"`, `delta: MealDelta`
    (`day: int`, `slot: str`, `recipe_id: str`) **and** `explanation:
    MealScopedExplanation` (`recipe: RecipeExplanation`, `constraints:
    list[ConstraintExplanation]`). (AC-2b, C-2)
  - `ErrorEvent` — `event="error"`, `code: str`, `message: str`,
    `trace_id: str | None`. `code`/`message` mirror the API's standard error
    envelope (`api/core/errors.py` `ErrorBody`); the contract does **not**
    carry `ErrorBody.timestamp` or `details` in the SSE event — those are
    request-lifecycle fields, not stream-event fields. (AC-12)
  - `DoneEvent` — `event="done"`, `status: str`, `trace_id: str`. (AC-10)
- **`ChatResponseEnvelope`** (the non-streaming projection a serializer/judge
  reads) — `trace_id: str`, `plan: PlanExplanation | None`, `error:
  ErrorView | None` (contract-local shape: `code: str`, `message: str`; no
  `timestamp`/`details`). The trace is **not** a field (referenced by
  `trace_id` only, C-1). The **streaming path** (SSE events) and the
  **non-streaming path** (`ChatResponseEnvelope`) are both produced from the
  same mapper output; p3-004 chooses which to serve for a given request. The
  contract defines both. (AC-10)
- **Audit-provenance floor (SF-1, Shape A).** A module-level
  `R16_FORBIDDEN_FIELDS: tuple[str, ...]` naming **specific field names** — the
  R-16 floor is:

  ```python
  R16_FORBIDDEN_FIELDS = (
      "confidence",
      "normalization_version",
      "source",
      "source_snapshot_id",
      "source_id",
      "mapping_version",
      "food_key",
      "fdc_id",
  )
  ```

No `*_id` glob is used. The permitted structural id fields (`recipe_id`,
`requirement_id`, `trace_id`, `plan_id`, `session_id`) are not in this list;
they are legitimately surfaced. The R-16 fixture imports this constant. The
calculator's fixture's broader list (`nutrition_rank`,
`selection_priority`, `approval_status`) is **not** part of R-16's floor;
those are p2-002's endpoint-specific exclusions (C-3). **The SSE contract
declares no endpoint-specific exclusions of its own** (SF-2): prices,
`listing_name`, `retailer`, `recipe_id`, `requirement_id`, `trace_id` are
permitted in the user payload.

### §3 Mapper `app/chat_contract.py::from_trace_envelope`

A pure function `from_trace_envelope(env: TraceEnvelope, trace_id: str) ->
ChatResponseEnvelope` in the same module (the app↔workflows boundary is already
app's job). **`trace_id` is accepted from the caller (SF-3);** the mapper has no
opinion on how the id is minted or stored. The trace store / id-minting
mechanism is p3-004's; the contract only requires the field.

- Reads `env.plan_trace` (a `PlanTraceView`) and `env.outcome`.
- Maps `PlanTraceView.recipes` → `RecipeExplanation` (carrying `cause`/`causes`
  into `drop_causes`, preserving p2 precedence order
  `present-evidence-excludes → evidence-absent → unmapped`, AC-6), and
  `PlanTraceView.requirements` → `ConstraintExplanation` grouped under their
  `recipe_id` (AC-3, AC-4, AC-5, AC-9).
- `env.outcome.kind == "failure"` → `ChatResponseEnvelope.error` populated, no
  `plan` (AC-12); `"infeasible"` → `PlanExplanation` with binding constraints
  (AC-13); relaxed plan → `relaxed`/`applied_tolerance_pct` carried (AC-14).
- The mapper never emits an `R16_FORBIDDEN_FIELDS` field into the explanation
  models (the source `OfferView` has no such fields; the mapper asserts none
  are copied — a defensive `assert` that the constructed models don't contain
  any forbidden field name).

### §4 Fixtures

- **`remy/app/tests/api/test_response_schema.py` (R-16)** — two independent
  test functions so the two clauses' verdicts are visible separately (AC-11b):
  - `test_user_payload_excludes_audit_provenance` (**passes**): builds a
    representative `ChatResponseEnvelope` via `from_trace_envelope`, dumps it,
    and asserts no key / substring matches `R16_FORBIDDEN_FIELDS` (AC-7).
    Mirrors the assertion style of the calculator's
    `test_response_schema.py` but asserts **R-16's floor only** (C-3, SF-1).
  - `test_trace_retains_audit_provenance` (**`xfail`**): asserts the trace
    object carries `confidence` / `normalization_version` / source id; `xfail`
    because `PlanTraceView` does not carry them yet (AC-8, AC-11b).
    `@pytest.mark.xfail(strict=True, reason="F-P3-1: PlanTraceView carries no
    R-16 audit provenance; owned by p2-003")`. **When F-P3-1 resolves, remove
    the `xfail` in the same change** — `strict=True` will fail on an
    unexpectedly passing test until it is removed.
- **`remy/app/tests/api/test_explanation_shape.py` (R-17)** — builds two
  `TraceEnvelope`s, one with a recipe dropped `evidence-absent`, one dropped
  `present-evidence-excludes`, maps each, and asserts (a) all three levels
  (plan/recipe/constraint) present in both (AC-3) and (b) the two drop causes
  are distinct and each is distinct from `unmapped` (AC-4, AC-5). A third case
  with multiple causes asserts precedence order and no collapse (AC-6).

### §5 What this feature does NOT build

Per spec Non-goals: no `/chat` endpoint, no SSE transport, no trace-retrieval
endpoint, no workflow node, no judge/eval surface, no cost/budget. The contract
is types + mapper + fixtures only.

## Files to touch

| File | Action | Why |
|---|---|---|
| `SystemCode/remy/app/src/app/chat_contract.py` | **create** | the contract types (`ChatRequest`, 5 SSE events, 3-level explanation), the `R16_FORBIDDEN_FIELDS` floor constant, and `from_trace_envelope` mapper (§2, §3) |
| `SystemCode/remy/app/tests/api/__init__.py` | **create** | make `tests/api/` a package under `remy-app` |
| `SystemCode/remy/app/tests/api/test_response_schema.py` | **create** | R-16 named fixture, both clauses (§4; AC-7, AC-8, AC-11a, AC-11b) |
| `SystemCode/remy/app/tests/api/test_explanation_shape.py` | **create** | R-17 named fixture, two-response + multi-cause (§4; AC-3–AC-6, AC-11a) |
| `SystemCode/remy/app/tests/test_chat_contract.py` | **create** | unit/integration tests for `ChatRequest`, SSE event discrimination, `plan_updated` shape, mapper, trace-id boundary (AC-1, AC-2, AC-2b, AC-9, AC-10, AC-12, AC-13, AC-14) |
| `SystemCode/docs/sdd/constitution.md` | **edit** | apply Amendment A-007: correct R-16's and R-17's named check paths from `tests/api/<name>` to `SystemCode/remy/app/tests/api/<name>`. The amendment file is `SystemCode/docs/amendments/A-007-fixture-path.md` (created separately). |
| `SystemCode/docs/amendments/A-007-fixture-path.md` | **create** | amendment proposal (status `approved`): R-16/R-17 named check paths reflect the deployed placement; formalizes the divergence recorded as p2-002 F-D and p3-001 BD-2a. |
| `sdd.json` | **edit** | extend the `test` check to explicitly include `remy/app/tests/api` (the new fixture directory) in addition to the existing `remy/app/tests` glob; confirm `lint`/`typecheck` already cover `remy/app/src` and `remy/app/tests` (they do via existing globs). The check set must cover the feature's new source and test paths. |

## Constitution alignment

- **R-2** (inward deps; `api`↛`workflows`, `api`↛`app`, `workflows`↛`api`/`app`)
  — the contract + mapper live in `app`, the only package permitted to import
  both `api` and `workflows`; `lint-imports` must stay green (4 kept, 0 broken).
- **R-16** (user response excludes audit-only provenance, amended by A-007) —
  the contract's user payload exposes only resolved concept / chosen offer /
  constraint outcome / warnings; `R16_FORBIDDEN_FIELDS` floor asserted by
  `remy/app/tests/api/test_response_schema.py` user-payload clause (passes);
  trace-side clause `xfail` under F-P3-1. A-007 makes the fixture path the
  constitution's named path.
- **R-17** (three-level explanations, distinct drop causes, amended by A-007) —
  the explanation models carry plan/recipe/constraint with a closed `DropCause`
  enum; `remy/app/tests/api/test_explanation_shape.py` asserts all three levels
  and the `evidence-absent` vs `present-evidence-excludes` vs `unmapped`
  distinction. A-007 makes the fixture path the constitution's named path.
- **R-14** (feasibility floor names binding constraint; via A-005) — surfaced
  unchanged: `PlanExplanation` carries `binding_constraints`, `relaxed`,
  `applied_tolerance_pct` from `PlanTraceView`; the contract re-decides nothing
  (AC-13, AC-14).
- **R-1** (single schema / docs corrected in same change) — `API_doc.md` §3's
  `/chat` shape is the deployed reference; the spec is the source of truth. The
  contract's field names align with §3 where it already specifies them; the
  `plan_updated` payload is extended (delta + scoped explanation) per C-2.
  API_doc is **not** edited by this feature (p3-004 implements the endpoint and
  owns the doc update); the divergence is noted for p3-004, not carried as a
  dual schema.

## Test strategy

| AC | Test type | Test location / name | Notes |
|---|---|---|---|
| AC-1 | unit | `remy/app/tests/test_chat_contract.py::test_chat_request_requires_session_and_message` | conforming request serializes; missing `session_id` or `message` rejected; omitted `user_context` valid |
| AC-2 | unit | `remy/app/tests/test_chat_contract.py::test_sse_event_type_is_one_of_five` | each of the 5 events validates; an unknown `event` value is rejected; missing a required field per type is rejected |
| AC-2b | unit | `remy/app/tests/test_chat_contract.py::test_plan_updated_carries_delta_and_scoped_explanation` | `plan_updated` with delta+scoped-explanation valid; delta-only and full-plan-explanation variants rejected |
| AC-3 | conformance | `remy/app/tests/api/test_explanation_shape.py::test_all_three_levels_present` | plan/recipe/constraint present in both built responses; missing a level is non-conforming |
| AC-4 | conformance | `remy/app/tests/api/test_explanation_shape.py::test_evidence_absent_distinct` | evidence-absent drop reported distinctly from present-evidence-excludes and unmapped |
| AC-5 | conformance | `remy/app/tests/api/test_explanation_shape.py::test_present_evidence_excludes_distinct` | present-evidence-excludes drop reported distinctly |
| AC-6 | conformance | `remy/app/tests/api/test_explanation_shape.py::test_multi_cause_precedence_preserved` | all causes kept, ordered present-evidence-excludes → evidence-absent → unmapped |
| AC-7 | conformance | `remy/app/tests/api/test_response_schema.py::test_user_payload_excludes_audit_provenance` | no field from `R16_FORBIDDEN_FIELDS`; passes |
| AC-7b | unit | `remy/app/tests/test_chat_contract.py::test_r16_floor_is_the_named_field_list` | `R16_FORBIDDEN_FIELDS` is exactly the named list; the SSE contract adds no endpoint-specific exclusions (SF-2) |
| AC-8 | conformance (xfail) | `remy/app/tests/api/test_response_schema.py::test_trace_retains_audit_provenance` | `xfail(strict=True)` reason F-P3-1; trace carries provenance — fails until F-P3-1 resolves; remove `xfail` when it does |
| AC-9 | unit | `remy/app/tests/test_chat_contract.py::test_constraint_explanation_fields` | resolved concept / offer / outcome / warnings only; offer may be null without error or drop |
| AC-10 | unit | `remy/app/tests/test_chat_contract.py::test_trace_referenced_not_embedded` | stable `trace_id` present on metadata/done/envelope; no event carries the trace body; `from_trace_envelope(env, trace_id)` accepts the id |
| AC-11a | conformance | `remy/app/tests/api/test_response_schema.py` + `test_explanation_shape.py` exist and collect | both named fixtures present at `remy/app/tests/api/<name>` (A-007) and asserting AC-3..AC-10 |
| AC-11b | conformance | `remy/app/tests/api/test_response_schema.py` (two functions) | user-payload clause passes (not xfail); trace-side clause xfail with F-P3-1 reason |
| AC-12 | unit | `remy/app/tests/test_chat_contract.py::test_failure_outcome_maps_to_error_event` | failure `Outcome` → `ErrorEvent`/envelope error, no plan payload; trace_id still correlates; `ErrorEvent` carries `code`+`message` only |
| AC-13 | integration | `remy/app/tests/test_chat_contract.py::test_infeasible_envelope_from_trace` | infeasible `TraceEnvelope` → PlanExplanation names binding constraints; recipe/constraint levels intact |
| AC-14 | integration | `remy/app/tests/test_chat_contract.py::test_relaxed_plan_carries_tolerance` | relaxed `TraceEnvelope` → `relaxed=True`, `applied_tolerance_pct` unchanged |

## Integration per interface

| Interface (producer → consumer) | Test type | Test location / name | Notes |
|---|---|---|---|
| p3-001 `TraceEnvelope` (producer) → `from_trace_envelope` contract input (consumer) | integration | `remy/app/tests/test_chat_contract.py::test_maps_real_trace_envelope_to_explanation` | builds a real `TraceEnvelope` via `workflows.trace.assemble_trace` with a real `PlanTraceView`; runs the **real** mapper; asserts the three-level explanation. Mapper (code under test) runs for real; the envelope is the real producer type. |
| `from_trace_envelope` output + SSE event models (producer) → payload serialization (consumer) | integration | `remy/app/tests/test_chat_contract.py::test_events_serialize_to_wire_payloads` | wraps the mapped explanation in `MetadataEvent`/`PlanUpdatedEvent`/`DoneEvent`/`ErrorEvent`, calls the **real** `model_dump()` serialization, asserts the wire payload shape (discriminator + fields) and that no `R16_FORBIDDEN_FIELDS` field appears. Serializer (pydantic dump via the real models) runs for real. |
| contract types (producer) → R-16 & R-17 named fixtures (consumer) | conformance | `remy/app/tests/api/test_response_schema.py`, `remy/app/tests/api/test_explanation_shape.py` | the fixtures import the **real** contract types and `from_trace_envelope`, build representative responses, and assert R-16 (both clauses) and R-17. No re-implementation of the contract in the test. |
| full chat workflow (producer: `workflows.graph.build` via adapter) → `from_trace_envelope` (consumer) | integration | `remy/app/tests/test_chat_contract.py::test_compiled_workflow_outcome_maps_through_contract` | runs the **real** compiled workflow with a fake LLM + fake `PlanPort` (dependencies mocked, code under test — graph + mapper — real), takes the emitted `TraceEnvelope`, and maps it through the real contract mapper end to end. |

## Risks & mitigations

- **Fixture-path amendment A-007** lands before the plan is approved. *Mitigation:*
  the amendment file and the constitution edit are in Files to touch; the plan
  consumes A-007 as the binding path. If A-007 is rejected, the plan reverts to
  `remy/api/tests/api/<name>` and the contract types must move out of `app` to
  a package `api` tests can import; that is a larger change and a spec-level
  finding.
- **F-P3-1 keeps the trace-side R-16 clause red.** *Mitigation:* the trace-side
  assertion is `xfail(strict=True)` with an F-P3-1 reason; CI stays green while
  the gap is visible; resolution is owned by p2-003 (not this feature). When
  F-P3-1 resolves, remove the `xfail` in the same change (`strict=True` forces
  this).
- **`plan_updated` shape diverges from the deployed API_doc example** (which
  shows delta only). *Mitigation:* C-2 is the source of truth; API_doc is the
  deployed reference and is p3-004's to update when it implements the endpoint;
  the plan records the divergence rather than editing another feature's doc.
- **Contract field names become a de-facto API p3-003/p3-004 depend on.**
  *Mitigation:* names align with API_doc §3 where it already specifies them;
  new fields (`trace_id`, `plan_updated.explanation`) are additive and
  documented in §2.
- **R-16 floor could be mis-asserted as the calculator's broader list.**
  *Mitigation:* `R16_FORBIDDEN_FIELDS` is the named eight (SF-1); AC-7b asserts
  the floor is exactly the named list; the calculator's list remains its own
  (C-3).

## Scope check

Fits one working context: **yes.** One new contract module + mapper in `app`,
two named fixtures, one unit/integration test file, one amendment (A-007), and
one `sdd.json` check-set edit. No endpoint, transport, workflow node, or
upstream reopen. All tests run under `remy-app` with a fake LLM and fake port;
no live model, no Neo4j, no network. F-P3-1 is tracked, not resolved here.

## Revision notes
<!-- F-n -> what changed -->

- **BD-3 resolved by amendment A-007.** The two constitution-named fixtures are
  placed at `remy/app/tests/api/<name>` and the constitution's R-16/R-17 named
  check paths are corrected to `SystemCode/remy/app/tests/api/<name>`. The
  amendment formalizes the divergence already recorded as p2-002 F-D and p3-001
  BD-2a; it lands alongside this plan (the amendment file and the constitution
  edit are in Files to touch). The `tests/api/<name>` leaf the constitution
  named is preserved.
- **SF-1 (R-16 floor, Shape A).** `R16_FORBIDDEN_FIELDS` is a tuple of specific
  field names (`confidence`, `normalization_version`, `source`,
  `source_snapshot_id`, `source_id`, `mapping_version`, `food_key`, `fdc_id`);
  no `*_id` glob. The structural id fields (`recipe_id`, `requirement_id`,
  `trace_id`, `plan_id`, `session_id`) are permitted and not in the floor.
- **SF-2 (no endpoint-specific exclusions).** p3-002's SSE contract declares
  no endpoint-specific exclusions beyond R-16's floor. The calculator's
  stricter list (`nutrition_rank`, `selection_priority`, `approval_status`)
  remains its own. Prices, `listing_name`, `retailer`, structural ids are
  permitted in the user payload.
- **SF-3 (trace_id accepted).** `from_trace_envelope(env: TraceEnvelope,
  trace_id: str) -> ChatResponseEnvelope`. The mapper has no opinion on how
  the id is minted or stored; the trace store / id-minting mechanism is
  p3-004's.
- **Smaller clarifications applied.** (a) `ChatResponseEnvelope` is the
  non-streaming projection; SSE events are the streaming path; both produced
  from the same mapper output; p3-004 chooses which to serve. (b)
  `PlanExplanation.binding_constraints` reuses `workflows.models.NamedConstraintView`
  (app may import workflows); no contract-local duplicate. (c) `ErrorEvent`
  carries `code` + `message` only; not `ErrorBody.timestamp` or `details`.

## Tasks

### Group 0 — pre-task admin

- [ ] **T-1** Confirm the contract module and amendment prerequisites
  - Type: admin
  - Covers: plan §0; A-007 prerequisite (already landed at constitution v1.7)
  - Files: none (verification only)
  - Done when:
    - `grep -n 'remy/app/tests/api' docs/sdd/constitution.md` shows R-16's and R-17's check paths point to `SystemCode/remy/app/tests/api/<name>` and the version line reads `Version: 1.7`.
    - `find SystemCode/remy/app/tests -name 'test_response_schema.py' -o -name 'test_explanation_shape.py'` returns nothing (fixtures absent; T-4..T-6 create them).
    - `find SystemCode/remy/api/tests/api -type d` returns nothing (the `tests/api/` directory is created under `remy-app`, not `remy-api`).
    - `uv run lint-imports` reports 4 kept, 0 broken.

### Group 1 — contract types

- [ ] **T-2** Write failing tests: `ChatRequest` validation
  - Type: test
  - Covers: AC-1
  - Files: `SystemCode/remy/app/tests/test_chat_contract.py` (create)
  - Done when: `test_chat_request_requires_session_and_message` fails because `app.chat_contract` does not exist; the test asserts a conforming request serializes, a request missing `session_id` or `message` is rejected, and a request omitting `user_context` is valid.

- [ ] **T-3** Write failing tests: SSE event discrimination and `plan_updated` shape
  - Type: test
  - Covers: AC-2, AC-2b
  - Files: `SystemCode/remy/app/tests/test_chat_contract.py` (append)
  - Done when: `test_sse_event_type_is_one_of_five` and `test_plan_updated_carries_delta_and_scoped_explanation` fail because the event models do not exist; the tests assert (a) each of the five events validates, an unknown `event` value is rejected, missing a required field per type is rejected; (b) `plan_updated` with delta+scoped-explanation is valid, delta-only and full-plan-explanation variants are rejected.

- [ ] **T-4** Write failing tests: constraint, recipe, and plan explanation models; `DropCause` closed enum
  - Type: test
  - Covers: AC-9, AC-4/AC-5/AC-6 vocabulary (via the `DropCause` enum)
  - Files: `SystemCode/remy/app/tests/test_chat_contract.py` (append)
  - Done when: `test_constraint_explanation_fields` and `test_drop_cause_enum_is_closed` fail; the tests assert (a) `ConstraintExplanation` carries `requirement_id`, `constraint`, `state`, `resolved_concept`, `selected_offer`, `warnings`; `selected_offer` may be null; (b) `DropCause` accepts only `"evidence-absent"`, `"present-evidence-excludes"`, `"unmapped"` and rejects an unknown cause string (review nit 2).

- [ ] **T-5** Create `app/chat_contract.py` with the request, event, and explanation models
  - Type: impl
  - Covers: AC-1, AC-2, AC-2b, AC-4, AC-5, AC-6, AC-9
  - Files: `SystemCode/remy/app/src/app/chat_contract.py` (create)
  - Done when: T-2, T-3, T-4 pass; the module defines `ChatRequest`, the five SSE event models, `OfferView`, `ConstraintExplanation`, `RecipeExplanation`, `PlanExplanation`, `DropCause` (closed enum), `MealDelta`, `MealScopedExplanation`. `ChatRequest` uses `extra="forbid"`. Field names match plan §2 exactly.

### Group 2 — audit floor and mapper

- [ ] **T-6** Write failing tests: floor constant definition and R-16 floor exactly-as-named
  - Type: test
  - Covers: AC-7b
  - Files: `SystemCode/remy/app/tests/test_chat_contract.py` (append)
  - Done when: `test_r16_floor_is_the_named_field_list` fails; the test asserts the floor constant (name per F-2 resolution below) is exactly the eight named fields (`confidence`, `normalization_version`, `source`, `source_snapshot_id`, `source_id`, `mapping_version`, `food_key`, `fdc_id`), no `*_id` glob, and that the permitted structural ids (`recipe_id`, `requirement_id`, `trace_id`, `plan_id`, `session_id`) are not in the floor.

- [ ] **T-7** Write failing tests: `from_trace_envelope` maps a real `TraceEnvelope` to the explanation
  - Type: integration
  - Covers: AC-3, AC-4, AC-5, AC-6, AC-13, AC-14 (mapper behavior); AC-10 (trace_id accept-signature)
  - Files: `SystemCode/remy/app/tests/test_chat_contract.py` (append)
  - Done when: `test_maps_real_trace_envelope_to_explanation` fails; the test builds a real `TraceEnvelope` via `workflows.trace.assemble_trace` with a real `PlanTraceView` (feasible, infeasible, relaxed, multi-cause cases), calls the real `from_trace_envelope(env, trace_id="trace-abc")`, and asserts (a) three levels present; (b) drop causes distinct and ordered per p2 precedence; (c) infeasible names binding constraints; (d) relaxed carries label and tolerance; (e) returned `trace_id` equals the accepted input.

- [ ] **T-8** Implement the floor constant and `from_trace_envelope` mapper
  - Type: impl
  - Covers: AC-3, AC-4, AC-5, AC-6, AC-7b, AC-10, AC-13, AC-14
  - Files: `SystemCode/remy/app/src/app/chat_contract.py` (append)
  - Done when: T-6, T-7 pass; the mapper signature is `from_trace_envelope(env: TraceEnvelope, trace_id: str) -> ChatResponseEnvelope`; the mapper reads `env.plan_trace` and `env.outcome`, maps recipes and requirements, groups constraints under their `recipe_id`, preserves cause precedence, and handles failure / infeasible / relaxed outcomes. **F-2 resolution:** the floor constant is named `CHAT_FORBIDDEN_FIELDS` (not `R16_FORBIDDEN_FIELDS`), with a comment that the first four are R-16's floor and the remaining four (`source`, `source_snapshot_id`, `mapping_version`, `food_key`, `fdc_id` — note this list is the full constant; the comment splits them as "R-16 named categories" vs. "additional exclusions this contract's chat payload applies") so the name and the assertion in AC-7b agree that R-16's floor is the *named categories*, not this constant's full set.

### Group 3 — R-16 and R-17 named fixtures

- [ ] **T-9** Write failing R-16 fixture: user-payload exclusion (passing) and trace retention (`xfail`)
  - Type: conformance
  - Covers: AC-7, AC-8, AC-11a, AC-11b
  - Files: `SystemCode/remy/app/tests/api/__init__.py` (create), `SystemCode/remy/app/tests/api/test_response_schema.py` (create)
  - Done when: two test functions exist: (a) `test_user_payload_excludes_audit_provenance` builds a representative `ChatResponseEnvelope` via `from_trace_envelope`, dumps it, and asserts no key / substring matches `CHAT_FORBIDDEN_FIELDS` (passes); (b) `test_trace_retains_audit_provenance` asserts the trace object carries provenance and is marked `@pytest.mark.xfail(strict=True, reason="F-P3-1: ...")`; both run at `remy/app/tests/api/test_response_schema.py`.

- [ ] **T-10** Write R-17 fixture: three levels + distinct drop causes + multi-cause precedence
  - Type: conformance
  - Covers: AC-3, AC-4, AC-5, AC-6, AC-11a
  - Files: `SystemCode/remy/app/tests/api/test_explanation_shape.py` (create)
  - Done when: the fixture builds two `TraceEnvelope`s (one dropped `evidence-absent`, one dropped `present-evidence-excludes`), maps each, and asserts (a) all three levels present; (b) the two drop causes are distinct and each distinct from `unmapped`; (c) a third multi-cause case preserves order and no collapse.

- [ ] **T-11** Write failing test: events serialize to wire payloads with no floor field
  - Type: integration
  - Covers: AC-10 (no trace embedded); AC-7 (no floor field in payloads)
  - Files: `SystemCode/remy/app/tests/test_chat_contract.py` (append)
  - Done when: `test_events_serialize_to_wire_payloads` fails; wraps the mapped explanation in `MetadataEvent` / `PlanUpdatedEvent` / `DoneEvent` / `ErrorEvent`, calls `model_dump()`, asserts the wire shape and that no `CHAT_FORBIDDEN_FIELDS` field appears.

- [ ] **T-12** Write failing test: failure outcome maps to `ErrorEvent` / envelope error
  - Type: unit
  - Covers: AC-12
  - Files: `SystemCode/remy/app/tests/test_chat_contract.py` (append)
  - Done when: `test_failure_outcome_maps_to_error_event` fails; asserts a `TraceEnvelope` with `outcome.kind == "failure"` maps to a `ChatResponseEnvelope` with `error` populated, `plan` null, `trace_id` still correlating, and that `ErrorEvent` carries `code` and `message` only (not `timestamp` / `details`).

- [ ] **T-13** Write integration test: compiled workflow → contract mapper end-to-end
  - Type: integration
  - Covers: p3-001's workflow as producer, contract as consumer
  - Files: `SystemCode/remy/app/tests/test_chat_contract.py` (append)
  - Done when: `test_compiled_workflow_outcome_maps_through_contract` runs the real `workflows.graph.build` with a fake LLM and fake `PlanPort`, captures the emitted `TraceEnvelope`, maps through the real `from_trace_envelope`, and asserts the three-level explanation.

### Group 4 — CI config

- [ ] **T-14** Update `sdd.json` check set to name the fixture directory
  - Type: impl
  - Covers: check-set coverage of the feature's paths
  - Files: `sdd.json`
  - Done when: the `test` check explicitly includes `remy/app/tests/api` (either by naming the directory in addition to `remy/app/tests`, or by confirming the existing glob collects it and documenting the confirmation in the commit message — the reviewer's nit 3 asks for the double-collection check); `lint`/`typecheck` confirm `remy/app/src` and `remy/app/tests` cover the new module and fixtures. Run `cd SystemCode && uv run --package remy-app pytest -q remy/app/tests` and confirm both `test_chat_contract.py` and `tests/api/*` collect.

### Group 5 — closing admin

- [ ] **T-15** Record decisions
  - Type: admin
  - Covers: C-1, C-2, C-3, BD-3/A-007, F-1, F-2
  - Files: `docs/sdd/features/p3-002-explainable-response-contract/decisions.md`
  - Done when: the decisions file records (a) C-1 trace referenced by `trace_id`; (b) C-2 `plan_updated` delta + meal-scoped explanation; (c) C-3 layered R-16 floor, SSE contract declares no endpoint-specific exclusions; (d) A-007 approved and the fixture path; (e) **F-1**: the contract module lives in `app`; p3-004's endpoint code must live in `app` or the contract must move — pin this for p3-004's plan; (f) **F-2**: the floor constant is named `CHAT_FORBIDDEN_FIELDS` with the R-16-floor-vs-endpoint-extras split documented in a comment; AC-7b asserts the R-16 floor is the named *categories*, not the constant's full set.

- [ ] **T-16** Run the full suite and CI
  - Type: verification
  - Covers: all ACs and interfaces
  - Files: (all above)
  - Done when:
    - `cd SystemCode/remy/app && uv run --package remy-app pytest -q tests` passes with `test_chat_contract.py` and `tests/api/*` collected.
    - The R-16 trace-side test is `xfail` (not `fail`, not `pass`); the user-payload test is `pass`.
    - `cd SystemCode && uv run lint-imports` reports 4 kept, 0 broken.
    - `cd SystemCode/remy/app && uv run --package remy-app mypy src/app/chat_contract.py --ignore-missing-imports` passes.
    - `sdd.py ci p3-002-explainable-response-contract` reports `OVERALL: PASS`.
