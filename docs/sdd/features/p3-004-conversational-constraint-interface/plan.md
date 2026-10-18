---
feature: p3-004-conversational-constraint-interface
---

# Plan - Conversational constraint interface

## Approach

**Chosen.** Implement `POST /chat` as a new FastAPI router in `remy/app` that
runs the existing p3-001 LangGraph workflow, maps the resulting `TraceEnvelope`
through p3-002's `from_trace_envelope`, and streams p3-002's five SSE events via
a new small SSE serializer; detect cost intent by extending the Extract
Constraints output with an additive `cost_query` field (C-6) plus a
deterministic keyword predicate, fold on-demand cost into the existing
`ChatResponseEnvelope`/event payloads via the existing calculator service (C-5),
and land the A-006 recipe-level cost drop inside `PlanService.generate` by
mirroring the existing `nutrition_dropped` loop, gated behind an opt-in flag so
p2's "retain uncosted recipe" behavior is unchanged unless budget is requested.

**Rejected.** A standalone cost endpoint plus a new cost response type — rejected
because C-5 fixes cost into the one conversational surface and p3-002's contract
is frozen; a parallel surface would duplicate the R-16 boundary and the event
vocabulary.

## Design

### 1. `/chat` endpoint + SSE transport (`remy/app`) — AC-1, AC-2, AC-16, AC-17, AC-19

- New module `app/src/app/chat_router.py` exposes an `APIRouter` with
  `POST /chat` (mounted under the app's `/api/v1` prefix to match API_doc §3).
  The handler validates the body against the existing
  `app.chat_contract.ChatRequest` (session_id + message required, user_context
  optional — AC-1) and returns a `fastapi.responses.StreamingResponse` with
  `media_type="text/event-stream"` (AC-1).
- The handler builds/uses the compiled workflow via the existing
  `app.composition.create_workflow(plan_service, ...)` and calls
  `workflow.invoke({"raw_message": request.message, ...})`. The resulting
  `TraceEnvelope` is mapped by `from_trace_envelope(env, trace_id)` (p3-002) into
  a `ChatResponseEnvelope`. A fresh `trace_id` (e.g. `secrets.token_hex`) is
  minted per turn and placed on every event that carries it; the trace object is
  never embedded (AC-16).
- Event emission order per turn: one `metadata` event (session_id,
  workflow_node, trace_id), zero or more `token` events (the generation text,
  chunked), a `plan_updated` event when the turn changes a meal (AC-18), and a
  terminal `done` event. A workflow `failure` outcome (or any raised exception)
  emits a single `error` event with a stable `code` and human-readable `message`
  then closes the stream (AC-17); no partial recommendation is presented as
  complete. Only the five p3-002 event types are emitted (AC-2).
- **Statelessness (AC-19):** the handler holds no module-level/session state; each
  call is a pure function of its request body. Continuity, if any, is carried by
  the client via `user_context`. The router is wired in a composition entrypoint
  (`app/src/app/main.py`, new) that constructs the FastAPI app and injects the
  `PlanService`; this keeps `api` free of any `app` import (R-2).

### 2. SSE serializer (`remy/app`) — AC-2, AC-16

- New module `app/src/app/sse.py` with a pure function
  `serialize_event(event: BaseModel) -> str` that renders a p3-002 event model to
  a `event: <type>\ndata: <json>\n\n` frame. It serializes via
  `model_dump(mode="json")`, so the frame carries exactly the contract fields and
  never the trace object (AC-16). A non-contract object is a programming error
  (the serializer only accepts the five event models). This is a pure
  producer→consumer boundary (handler emits event objects; serializer frames
  them) and is tested in isolation and end-to-end.

### 3. Cost-intent detection — additive `cost_query` (`remy/workflows`) — AC-4, AC-5

- Add an optional field `cost_query: bool | None = None` to the end of the frozen
  `ConstraintSet` dataclass in `workflows/models.py` (after
  `nutrient_tolerance_pct`). **Additive and backward-compatible:** every existing
  `test_extract.py` assertion checks specific fields (`horizon_days`,
  `allergies`, `dietary`, `nutrient_tolerance_pct`, `unapplied`); none asserts the
  absence of `cost_query`, and the default `None` leaves `ConstraintSet(...)`
  equality in `test_structured_constraints_are_passed_through_without_calling_llm`
  intact (that test constructs `ConstraintSet(horizon_days=2, meals_per_day=3)`,
  whose `cost_query` defaults to `None` on both sides).
- **[F-1] Scope of `PlanInput` changes.** `PlanInput` is unchanged by the
  *extraction* change — the Plan node still maps only the fields it forwarded
  before. §5 below **separately** adds an additive `PlanInput.cost_query: bool =
  False` flag solely to thread the budget signal to the adapter for the cost-drop
  gate. Both statements are true and non-contradictory: the extraction change
  leaves `PlanInput` alone; the gate change adds one optional field to it.
- In `workflows/nodes.py` `_constraint_set`, set `cost_query` from the LLM output
  when present (`value.get("cost_query")`), else from a deterministic predicate on
  the raw message. **Cost-intent predicate (names the AC-4/AC-5 boundary):** the
  turn carries cost intent iff the message matches, case-insensitively, the regex
  `\b(cost|costs|price|prices|priced|cheap|cheaper|cheapest|budget|afford|
  affordable|dollar|dollars|sgd)\b` **or** contains a currency-amount pattern
  `\$\s?\d` / `\bunder\s+\$?\d`. **Fallback when ambiguous is conservative:** no
  match and no LLM `cost_query` ⇒ `cost_query` is falsy ⇒ no cost surfaced
  (AC-5). The LLM field, when explicitly set, takes precedence over the keyword
  fallback (so a model that recognizes a paraphrase like "won't break the bank"
  can set it even without a keyword).

### 4. On-demand cost projection folded into `/chat` (`remy/app`) — AC-4, AC-6, AC-7

- When `parsed_constraints.cost_query` is truthy, the handler calls the existing
  `CostNutritionService.calculate(CostNutritionRequest(...))` for the recipe /
  ingredient names in scope (the selected meal's ingredients, or the
  `user_context` plan's). It reuses the calculator's existing consumed-vs-retail
  separation (R-11) — it does **not** recompute cost (AC-6).
- The computed cost is **folded into the existing payload** (C-5): consumed and
  retail cost per item, and the calculator's `MISSING_PACKAGE_DATA` warning when a
  requirement has no cost-eligible fresh package (surfaced as the warning string,
  not a fabricated/zero price — AC-7). Cost values ride in the already-permitted
  fields (prices are **not** in `CHAT_FORBIDDEN_FIELDS`); no new response type and
  no new SSE event are introduced (Non-goal). When `cost_query` is falsy, the
  calculator is not called and no cost figure appears (AC-5).
- **Cost-intent but no scoped names** (edge case): the calculator is not called;
  the explanation proceeds without cost and the turn is not an error.

### 5. A-006 recipe-level cost drop in the api plan service — AC-8, AC-9, AC-10

- The drop lands in `PlanService.generate` (the path the adapter calls), **not**
  `generate_v2`. It mirrors the existing `nutrition_dropped` loop exactly, using
  the calculator signal the service already fetches:
  `signals = self.calculator_service.inspect_candidates(...)` returns
  `dict[recipe_id -> RecipeNutritionSignal]`, and each `RecipeNutritionSignal`
  already carries `selected_offers: list[RequirementOffer]` where
  `selected_offer is None` **iff** `select_package` found no cost-eligible fresh
  package. **`selected_offer is None` is the recipe-inspection analogue of the
  calculator's item-level `MISSING_PACKAGE_DATA`** — the signal A-006 names. (See
  F-5 verify-on-touch: the equivalence is asserted in the fixture by the warning
  string, so the claim is testable, not assumed.)
- `select_package` (`calculator/domain/cost.py`) already enforces R-8/R-10
  correctly: `price_status == estimated`, `price_match_status == accepted`,
  `freshness_status == fresh`, `price_basis in {package_mass, package_volume}`
  (via `_package_grams`), SGD, positive price, positive grams. The drop therefore
  **consumes** that enforcement; it does not reimplement eligibility. (Note: the
  `_evaluate_cost_basis` helper in `filtering.py` is a separate, unused-by-default
  path that still lists `PACKAGE_UNRESOLVED`; the A-006 drop does not use it and
  this plan does not touch it — flagged as a risk below.)
- **Gating (opt-in):** the drop is **off by default** and fires only when cost /
  budget is requested, preserving A-006's "retain the uncosted recipe until
  p3-004 ships the drop" for all cost-agnostic callers (so
  `test_untracked_partial_nutrition_retained`, `test_service_integration`, and the
  other existing plan tests stay green). Concrete mechanism:
  `PlanService.generate(request, *, drop_uncosted: bool = False)`. When
  `drop_uncosted` is True, after the `nutrition_dropped` block the service adds a
  `cost_dropped` set: for each `recipe` in `filtered`, if any
  `requirement_offer.selected_offer is None` in that recipe's signal, it appends
  `"evidence-absent"` to `causes[recipe_id]`, adds the recipe to `cost_dropped`,
  and appends a `RequirementOutcome(recipe_id, requirement_id=occurrence_id,
  constraint="budget", state="evidence-absent")`. `eligible` then excludes
  `cost_dropped` alongside `nutrition_dropped` and `unmapped`. The adapter
  (`PlanServiceAdapter.generate`) passes `drop_uncosted=request.cost_query`
  **[F-3]** — `PlanInput.cost_query` is the sole budget signal threaded to the
  adapter (a minimal additive `PlanInput.cost_query: bool = False`, mapped in
  `plan_adapter` to the `drop_uncosted` kwarg). The existing `evidence-absent`
  cause is already in `CAUSE_PRECEDENCE`, so `resolve_recipe_causes` orders/dedups
  it with no change. **[F-3] Reconciliation with AC-8:** the A-006 drop is
  exercised on cost-intent turns; default-off preserves p2's retain behavior for
  cost-agnostic callers, which is consistent with AC-9/AC-10's own "when the
  recipe-level cost drop is evaluated" conditioning and with risk #1's
  mitigation. (Optional: sync AC-8's phrasing the next time the spec is touched.)
- The drop is reported at the recipe level (`RecipeOutcome` cause/causes) and the
  constraint level (`RequirementOutcome` state `evidence-absent`), so it flows
  through the existing `recipe_outcomes` / `constraint_outcomes` into the trace
  and p3-002's explanation unchanged (R-17 holds via existing projection).

### 6. R-8/R-10 recipe-level fixture modules (`SystemCode/remy/api/tests/features/plan/`) — AC-8, AC-9, AC-10

- **New module `test_service_cost_drop.py`**, structured like
  `test_service_nutrition_drop.py` (reusing the `Driver`/`Session`/
  `SignalInspector` fakes and a `_row` builder; `PlanService(PlanRepository(
  Driver(rows)))` with `service.calculator_service = SignalInspector(signals)`).
  The `SignalInspector` returns, for the uncosted recipe, a `RecipeNutritionSignal`
  whose `selected_offers=[RequirementOffer(occurrence_id, canonical_key,
  selected_offer=None)]`, and for the costed recipe a real `OfferRef`.
  - `test_uncosted_recipe_dropped_evidence_absent` — AC-8: `drop_uncosted=True`,
    uncosted recipe → `outcome == "dropped"`, `cause == "evidence-absent"`; costed
    recipe retained.
  - `test_uncosted_recipe_retained_when_cost_not_requested` — the gate: default
    `drop_uncosted=False` → uncosted recipe retained (guards A-006's default and
    the existing plan tests).
- **New module `test_cost_drop_eligibility.py`** asserting the R-8/R-10
  recipe-level predicate through `select_package` at the unit level (reusing the
  `_package` builder from `test_domain_cost.py`) **and** confirming the service
  drops the recipe when the only package is ineligible:
  - AC-9 (R-8): a package with `freshness_status` not `fresh` →
    `select_package(...) is None` → signal `selected_offer is None` → recipe
    dropped `evidence-absent`.
  - AC-10 (R-10): a package with `price_status != estimated`,
    `price_match_status != accepted`, or `price_basis` outside
    `{package_mass, package_volume}` → `select_package(...) is None` → recipe
    dropped `evidence-absent`.

### 7. R-16 / R-17 named fixtures at the A-007 paths (`remy/app/tests/api/`) — AC-11..AC-16, AC-20

- The named fixtures already exist (p3-002):
  `app/tests/api/test_response_schema.py` (R-16, both clauses now passing —
  F-P3-1 resolved) and `app/tests/api/test_explanation_shape.py` (R-17). p3-004
  **keeps them green** and **extends** R-16 coverage to the **served** surface.
- **R-16 asserts the full `CHAT_FORBIDDEN_FIELDS` set**, not only
  `confidence`/`normalization_version`/`source_*`: the existing
  `test_user_payload_excludes_audit_provenance` already iterates
  `CHAT_FORBIDDEN_FIELDS` (all eight: `confidence`, `normalization_version`,
  `source`, `source_snapshot_id`, `source_id`, `mapping_version`, `food_key`,
  `fdc_id`) via `any(field in key ...)`. p3-004 adds an endpoint-level assertion
  (below) that the **streamed** `/chat` payload likewise excludes the full set.
- **New endpoint-level test module `app/tests/api/test_chat_endpoint.py`** drives
  the real FastAPI app with `fastapi.testclient.TestClient`, asserting the served
  surface for AC-1, AC-2, AC-13 (three levels present in the stream), AC-14
  (distinct causes in the stream), AC-15 (full `CHAT_FORBIDDEN_FIELDS` absent from
  every event payload), AC-16 (`trace_id` present, trace object absent), AC-17
  (failure → single `error` event), AC-18 (`plan_updated` delta + meal-scoped
  explanation), AC-19 (two independent calls, no shared state), AC-20 (the named
  R-16/R-17 fixtures pass for the endpoint's mapped response). The workflow's LLM
  and plan port are faked (dependencies may be mocked); the endpoint, serializer,
  mapper, and contract models run for real.
- **[F-2] End-to-end gated-drop coverage.** `test_chat_endpoint.py` also carries
  `test_cost_intent_turn_drops_uncosted_recipe_end_to_end`: a cost-intent `/chat`
  turn whose plan contains an uncosted recipe drives the real handler → real
  `PlanService.generate(drop_uncosted=True)` → real projection, asserting the
  recipe appears in the streamed explanation as `evidence-absent` (not
  `selected`), so the plan's top risk ("gating could silently no-op R-8/R-10") is
  covered end to end, not only at the service. Optional cheap add in the same
  test: the cost drop empties the pool → infeasible outcome with named binding
  constraints (reuses the existing empty-pool path).

### 8. Safe re-expression — reuse p3-001 Generate Response — AC-11, AC-12

- No new generation path. The handler consumes the workflow's existing Generate
  Response node output, which already enforces the deterministic check (referenced
  recipe IDs / requirement IDs / drop causes ⊆ the plan's; `evidence-absent`
  recipes cannot be selected). The cost-drop recipes carry `evidence-absent`, so
  the existing check covers AC-12 for them with no change. Tests assert the node
  rejects an out-of-set reference (AC-11) and never restates an evidence-absent
  drop as permissive (AC-12), driving the real node with a fake LLM.

### 9. API_doc §3 update — AC-21

- Edit `SystemCode/remy/api/docs/API_doc.md` §3 so the `plan_updated` SSE example
  carries the delta **and** the meal-scoped three-level explanation (p3-002 C-2),
  replacing the legacy delta-only example. Because CI does not execute docs, AC-21
  is verified by a cheap test (`app/tests/api/test_api_doc_plan_updated.py`) that
  reads the doc and asserts the `plan_updated` example contains an `explanation`
  with `recipe` and `constraints` (not delta-only).

## Files to touch

| Path | Change |
|---|---|
| `SystemCode/remy/app/src/app/chat_router.py` | **new** — `POST /chat` router, workflow run, event emission, error handling |
| `SystemCode/remy/app/src/app/sse.py` | **new** — SSE frame serializer for the five event models |
| `SystemCode/remy/app/src/app/main.py` | **new** — FastAPI app composition; wires router + `PlanService` (keeps `api` free of `app`) |
| `SystemCode/remy/app/src/app/composition.py` | extend — expose cost-intent wiring / pass-through used by the handler |
| `SystemCode/remy/app/src/app/plan_adapter.py` | edit — thread `cost_query`→`drop_uncosted` through `PlanInput` into `PlanService.generate` |
| `SystemCode/remy/workflows/src/workflows/models.py` | edit — add `ConstraintSet.cost_query: bool \| None = None`; add `PlanInput.cost_query: bool = False` |
| `SystemCode/remy/workflows/src/workflows/nodes.py` | edit — set `cost_query` from LLM field or keyword predicate in `_constraint_set`; map `cost_query`→`PlanInput` in `plan` |
| `SystemCode/remy/api/src/api/features/plan/service.py` | edit — add `drop_uncosted` kwarg + `cost_dropped` loop consuming `selected_offer is None` |
| `SystemCode/remy/api/docs/API_doc.md` | edit — §3 `plan_updated` example → delta + meal-scoped explanation (AC-21) |
| `SystemCode/remy/app/tests/api/test_chat_endpoint.py` | **new** — served-surface tests (AC-1,2,13,14,15,16,17,18,19,20; **[F-2]** end-to-end gated drop) |
| `SystemCode/remy/app/tests/api/test_sse.py` | **[F-4] new** — `test_frame_shape` (serializer unit + framing; Integration edge 2) |
| `SystemCode/remy/app/tests/api/test_api_doc_plan_updated.py` | **new** — AC-21 doc assertion |
| `SystemCode/remy/app/tests/api/test_cost_projection.py` | **new** — cost folded into `/chat` (AC-4,6,7) |
| `SystemCode/remy/app/tests/api/test_response_schema.py` | keep green; extend R-16 to served payload if needed (AC-15,20) |
| `SystemCode/remy/app/tests/api/test_explanation_shape.py` | keep green (AC-13,14,20) |
| `SystemCode/remy/workflows/tests/test_extract.py` | extend — `cost_query` set/absent cases (AC-4,5); existing cases stay green |
| `SystemCode/remy/workflows/tests/test_generate.py` | **[F-4] extend** — `test_unknown_reference_rejected` (AC-11), `test_evidence_absent_not_restated_permissive` (AC-12) |
| `SystemCode/remy/api/tests/features/plan/test_service_cost_drop.py` | **new** — AC-8 service-level drop + gate |
| `SystemCode/remy/api/tests/features/plan/test_cost_drop_eligibility.py` | **new** — AC-9,10 R-8/R-10 recipe-level |
| `sdd.json` | **edited in this change** — lint/typecheck now cover `remy/api/src/api/features/plan` + `remy/api/tests/features/plan`; test set already covers the feature's test dirs |

**[F-4]** The `api/.../plan/schemas.py` "edit (if needed)" row is deleted — §5
commits to the kwarg mechanism (`PlanService.generate(request, *,
drop_uncosted=...)`), so `PlanRequest` is not touched; no conditional row.

## Constitution alignment

- **R-2** — the `/chat` endpoint and its wiring live in `remy/app`; nothing in
  `api` imports `app`; `lint-imports` stays green (check retained in sdd.json).
- **R-8** — the recipe-level cost drop consumes `select_package`'s
  `freshness_status == fresh` enforcement; a non-fresh-only requirement yields
  `selected_offer is None` → recipe dropped `evidence-absent` (AC-9 fixture).
- **R-10** — the drop consumes `select_package`'s price-status / match-status /
  price-basis enforcement; an ineligible-only requirement drops the recipe
  `evidence-absent` (AC-10 fixture); `cost_basis_compatible` is not used.
- **R-11** — cost surfacing reuses the calculator's consumed-vs-retail split; the
  handler does not conflate them (AC-6).
- **R-13** — p3-004 re-decides no selection; it surfaces the plan's outcomes and
  the trace's confidence unchanged.
- **R-16** — the served `/chat` payload excludes the full `CHAT_FORBIDDEN_FIELDS`
  set; prices are permitted; the trace is referenced by `trace_id`, never embedded
  (AC-15, AC-16).
- **R-17** — the stream exposes plan/recipe/constraint levels with distinct drop
  causes via the unchanged p3-002 projection (AC-13, AC-14).

## Test strategy

| AC | Test type | Test location / name | Notes |
|---|---|---|---|
| AC-1 | endpoint | `app/tests/api/test_chat_endpoint.py::test_valid_request_starts_event_stream` + `::test_missing_field_rejected` | TestClient; `text/event-stream`; 422 on missing session_id/message |
| AC-2 | endpoint | `test_chat_endpoint.py::test_only_five_event_types_emitted` | assert every emitted `event:` ∈ the five |
| AC-3 | unit | `workflows/tests/test_extract.py::test_natural_language_extracts_constraints*` (existing, extended) | constraints applied; none fabricated |
| AC-4 | unit+endpoint | `test_extract.py::test_cost_query_set_on_cost_message`; `app/tests/api/test_cost_projection.py::test_cost_surfaced_on_cost_intent` | predicate sets `cost_query`; cost appears |
| AC-5 | unit+endpoint | `test_extract.py::test_cost_query_absent_without_cost_reference`; `test_cost_projection.py::test_no_cost_without_intent` | conservative fallback; no cost figure |
| AC-6 | integration | `test_cost_projection.py::test_consumed_and_retail_distinct_via_calculator` | real `CostNutritionService.calculate` (mocked repo) |
| AC-7 | integration | `test_cost_projection.py::test_missing_package_reported_not_fabricated` | `MISSING_PACKAGE_DATA` surfaced; no zero price |
| AC-8 | service + **[F-2] endpoint** | `api/tests/features/plan/test_service_cost_drop.py::test_uncosted_recipe_dropped_evidence_absent`; `app/tests/api/test_chat_endpoint.py::test_cost_intent_turn_drops_uncosted_recipe_end_to_end` | service-level drop + end-to-end through handler (top-risk mitigation) |
| AC-9 | unit+service | `test_cost_drop_eligibility.py::test_non_fresh_package_drops_recipe` | `select_package` None → drop (R-8) |
| AC-10 | unit+service | `test_cost_drop_eligibility.py::test_ineligible_price_basis_drops_recipe` | `select_package` None → drop (R-10) |
| AC-11 | unit | `workflows/tests/test_generate.py::test_unknown_reference_rejected` (existing/extended) | real Generate Response node |
| AC-12 | unit | `workflows/tests/test_generate.py::test_evidence_absent_not_restated_permissive` | includes cost-drop recipes |
| AC-13 | endpoint | `test_chat_endpoint.py::test_three_levels_present_in_stream` | plan/recipe/constraint all present |
| AC-14 | fixture+endpoint | `app/tests/api/test_explanation_shape.py` (existing); `test_chat_endpoint.py::test_distinct_causes_in_stream` | evidence-absent vs present-evidence-excludes vs unmapped |
| AC-15 | fixture+endpoint | `app/tests/api/test_response_schema.py::test_user_payload_excludes_audit_provenance` (existing, full set); `test_chat_endpoint.py::test_stream_excludes_forbidden_fields` | full `CHAT_FORBIDDEN_FIELDS` |
| AC-16 | endpoint | `test_chat_endpoint.py::test_trace_id_present_trace_not_embedded` | `trace_id` present; no trace object |
| AC-17 | endpoint | `test_chat_endpoint.py::test_failure_emits_single_error_event` | fake failing node → one `error` event, stream closes |
| AC-18 | endpoint | `test_chat_endpoint.py::test_plan_updated_has_delta_and_scoped_explanation` | delta + meal-scoped explanation |
| AC-19 | endpoint | `test_chat_endpoint.py::test_two_independent_requests_no_shared_state` | second call independent of first |
| AC-20 | fixture | `app/tests/api/test_response_schema.py` + `test_explanation_shape.py` (both clauses pass) | A-007 paths; F-P3-1 resolved |
| AC-21 | doc test | `app/tests/api/test_api_doc_plan_updated.py::test_plan_updated_example_has_explanation` | reads API_doc §3 |

## Integration per interface

| Interface (producer → consumer) | Test type | Test location / name | Notes |
|---|---|---|---|
| p3-001 `TraceEnvelope` → `/chat` handler | integration | `app/tests/api/test_chat_endpoint.py::test_workflow_envelope_streams_events` | real `workflows.graph.build` (fake LLM/port) → real handler → events; asserts metadata/token/done |
| `/chat` handler → SSE serializer | integration | `app/tests/api/test_chat_endpoint.py::test_events_framed_as_sse` + `app/tests/api/test_sse.py::test_frame_shape` **[F-4]** | real `app.sse.serialize_event`; assert `event:`/`data:` framing, trace absent |
| api plan service `MISSING_PACKAGE_DATA` → plan candidate pool (A-006 drop) | integration | `api/tests/features/plan/test_service_cost_drop.py::test_uncosted_recipe_dropped_evidence_absent` | real `PlanService.generate` consuming `inspect_candidates` signal (`selected_offer is None`) |
| calculator service → `/chat` on-demand cost projection | integration | `app/tests/api/test_cost_projection.py::test_consumed_and_retail_distinct_via_calculator` | real `CostNutritionService.calculate` (mocked repo) → cost folded into `/chat` payload |
| p3-002 contract types → R-16/R-17 fixtures | integration | `app/tests/api/test_response_schema.py` + `app/tests/api/test_explanation_shape.py` | real `from_trace_envelope` → fixtures assert exclusion/retention + three levels/causes |
| `cost_query` field (workflows) → `/chat` intent branch | integration | `app/tests/api/test_cost_projection.py::test_cost_query_branches_handler` | real `extract_constraints` sets `cost_query` → handler takes the cost path |

All six edges run the code under test for real; only external dependencies (LLM,
Neo4j driver/repository) are faked. No edge is deferred.

## Risks & mitigations

- **Gating the cost drop could silently no-op R-8/R-10.** If `drop_uncosted` is
  never passed True in production wiring, the recipe-level fixtures would pass but
  the feature would be inert. *Mitigation:* the adapter sets `drop_uncosted` from
  the turn's cost/budget intent, and **[F-2]** the endpoint test
  `test_cost_intent_turn_drops_uncosted_recipe_end_to_end` asserts a cost-intent
  turn with an uncosted recipe drops it end to end (AC-8 path exercised through
  the handler, not only the service).
- **`filtering.py::_evaluate_cost_basis` still lists `PACKAGE_UNRESOLVED`** (an
  R-10 violation) but is only reachable via `require_cost=True`, which
  `generate`/`generate_v2` never pass. *Mitigation:* the A-006 drop deliberately
  uses `select_package` (correct R-10 enforcement) via `inspect_candidates`, not
  `_evaluate_cost_basis`. The dead path is out of this feature's scope; recorded
  as a note for review rather than changed here to avoid scope creep.
- **`ConstraintSet` is frozen; adding a field could break positional
  construction.** *Mitigation:* append `cost_query` last with a default; all known
  constructors use keywords or the documented positional order, and `test_extract`
  stays green.
- **SSE streaming under `TestClient`.** Streaming responses must be read to
  completion in tests. *Mitigation:* tests read the full body and parse frames;
  the serializer is also unit-tested in isolation.
- **LangGraph pending-deprecation warning** (carried from p3-001/p3-002). *Not a
  p3-004 defect;* monitored, not fixed here.
- **[F-5] Verify-on-touch (no redesign).** (a) The
  `selected_offer is None` ⇔ `MISSING_PACKAGE_DATA` equivalence is asserted in
  `test_service_cost_drop.py` by asserting the warning string, not assumed.
  (b) The `RequirementOutcome(recipe_id, requirement_id=occurrence_id,
  constraint="budget", state="evidence-absent")` constructor shape and `"budget"`
  label are verified against the real p2 signature on touch. (c) The additive
  `ConstraintSet` field is confirmed not to break any existing `test_extract`
  assertion (defaults on both sides). (d) `evidence-absent` is confirmed already in
  `CAUSE_PRECEDENCE`.

## Scope check

Fits one working context: yes. One feature, three packages touched along a single
thread (extract `cost_query` → plan drop → serve/stream), with the contract and
workflow already built. The cost drop, the endpoint, and the intent field are
cohesive parts of the one conversational turn; splitting them would separate a
producer from its consumer.

## Revision notes

- **r1 → r2 [F-1]**: §3's "`PlanInput` is unchanged" scoped to the *extraction*
  change; §5 separately adds the additive `PlanInput.cost_query` flag for the
  gate. No contradiction.
- **r1 → r2 [F-2]**: added
  `test_chat_endpoint.py::test_cost_intent_turn_drops_uncosted_recipe_end_to_end`
  to the Test strategy AC-8 row, the Risks mitigation, and the Files-to-touch
  row (`test_chat_endpoint.py`), closing the unscheduled end-to-end gated-drop
  test.
- **r1 → r2 [F-3]**: replaced the `<budget-present>` placeholder with
  `drop_uncosted=request.cost_query`; added the AC-8 reconciliation line in §5
  (drop exercised on cost-intent turns; default-off preserves p2's retain
  behavior, consistent with AC-9/AC-10's conditioning).
- **r1 → r2 [F-4]**: added `app/tests/api/test_sse.py` and
  `workflows/tests/test_generate.py` to Files-to-touch; deleted the hedged
  `api/.../plan/schemas.py | edit (if needed)` row (§5 commits to the kwarg).
- **r1 → r2 [F-5]**: recorded as a verify-on-touch note under Risks; no design
  change.

## Tasks

### Group 0 — pre-task admin

- [x] **T-1** Verify prerequisites and confirm the frozen plan is in force
  - Type: admin
  - Covers: plan r2 (frozen); C-1..C-7 (all logged in spec `## Clarifications`); F-5 verify-on-touch surfaces
  - Files: none (verification only)
  - Done when:
    - `sdd.py gate implement p3-004-conversational-constraint-interface` passes.
    - `docs/sdd/features/p3-004-conversational-constraint-interface/spec.md` `## Clarifications` contains C-1..C-7 with the seven confirmed decisions (A-006 layer=api plan service; stateless; reuse Generate Response; DQ-1..DQ-7 accepted; D-a cost folded into `/chat`; D-b `cost_query` field; A-007 fixture paths).
    - `docs/amendments/` contains A-006 and A-007.
    - `find SystemCode/remy/app/tests/api -name 'test_response_schema.py' -o -name 'test_explanation_shape.py'` returns both (p3-002 landed) — the A-007 fixtures exist and are green.
    - `grep -n 'def generate' SystemCode/remy/api/src/api/features/plan/service.py` shows `PlanService.generate` (the p2-003 tuple-return shape) and `inspect_candidates` on the calculator service.
    - `uv run lint-imports` reports 4 kept, 0 broken.

### Group 1 — workflow: cost-query extraction (p3-001 extension, additive)

- [x] **T-2** Write failing tests: `cost_query` extraction and keyword predicate
  - Type: test
  - Covers: AC-4, AC-5
  - Files: `SystemCode/remy/workflows/tests/test_extract.py` (extend)
  - Done when: `test_cost_query_set_on_cost_message` and `test_cost_query_absent_without_cost_reference` fail because `ConstraintSet.cost_query` does not exist; existing extract tests still pass (additive field, default `None`). Cases: cost keywords ("cheapest", "under $5", "what's the price", "budget") set truthy; no-cost messages falsy; LLM-provided `cost_query` takes precedence over the keyword fallback.

- [x] **T-3** Add `ConstraintSet.cost_query` and set it in the Extract Constraints node
  - Type: impl
  - Covers: AC-4, AC-5
  - Files: `SystemCode/remy/workflows/src/workflows/models.py` (append `cost_query: bool | None = None` after `nutrient_tolerance_pct`); `SystemCode/remy/workflows/src/workflows/nodes.py` (set from LLM output when present, else keyword regex in `_constraint_set`)
  - Done when: T-2 passes. Field appended last with default (frozen-dataclass safe); `test_extract` suite green; regex per plan §3.

### Group 2 — api plan service: A-006 recipe-level cost drop

- [x] **T-4** Write failing tests: R-8/R-10 recipe-level cost drop + default-off gate
  - Type: test
  - Covers: AC-8, AC-9, AC-10; F-5(a) warning-string assertion
  - Files: `SystemCode/remy/api/tests/features/plan/test_service_cost_drop.py` (create); `SystemCode/remy/api/tests/features/plan/test_cost_drop_eligibility.py` (create)
  - Done when:
    - `test_service_cost_drop.py::test_uncosted_recipe_dropped_evidence_absent` fails because `PlanService.generate` has no `drop_uncosted` kwarg. Fixture uses the `Driver`/`Session`/`SignalInspector` pattern from `test_service_nutrition_drop.py`; asserts recipe outcome `dropped` with cause `evidence-absent`, costed recipe retained.
    - `test_service_cost_drop.py::test_uncosted_recipe_retained_when_cost_not_requested` fails: default `drop_uncosted=False` retains the uncosted recipe (guards A-006 default + existing plan tests).
    - `test_cost_drop_eligibility.py::test_non_fresh_package_drops_recipe` (R-8) and `::test_ineligible_price_basis_drops_recipe` (R-10) fail: `select_package` returns `None` for the sole package (non-fresh; or `price_status != estimated` / `price_match_status != accepted` / `price_basis ∉ {package_mass,package_volume}`) → `SignalInspector` returns `selected_offer is None` → recipe dropped `evidence-absent`. **F-5(a):** each drop fixture asserts the calculator's `MISSING_PACKAGE_DATA` warning string is the item-level analogue of `selected_offer is None`.

- [x] **T-5** Add `drop_uncosted` kwarg and the `cost_dropped` loop
  - Type: impl
  - Covers: AC-8, AC-9, AC-10; plan §5 gating
  - Files: `SystemCode/remy/api/src/api/features/plan/service.py` (edit)
  - Done when: T-4 passes. Signature `PlanService.generate(request, *, drop_uncosted: bool = False)`. When True, after the `nutrition_dropped` block: for each recipe with any `requirement_offer.selected_offer is None` in its `inspect_candidates` signal, append `"evidence-absent"` to `causes[recipe_id]`, add to `cost_dropped`, append `RequirementOutcome(recipe_id, requirement_id=occurrence_id, constraint="budget", state="evidence-absent")`. `eligible` excludes `cost_dropped` alongside `nutrition_dropped` / `unmapped`. **F-5(b):** verify `RequirementOutcome`'s real signature/labels on touch and adjust names if they differ. **F-5(d):** confirm `evidence-absent` already in `CAUSE_PRECEDENCE` (no change to `resolve_recipe_causes`). Existing plan tests stay green (default-off).

### Group 3 — workflow: thread budget signal to the adapter

- [x] **T-6** Write failing test: `PlanInput.cost_query` threads to `drop_uncosted`
  - Type: test
  - Covers: AC-8 (via plan §5 F-1 additive path)
  - Files: `SystemCode/remy/workflows/tests/test_plan_node.py` (create if absent; append if present)
  - Done when: `test_plan_node_maps_cost_query_to_plan_input` fails because `PlanInput.cost_query` does not exist; the test drives the real Plan node with a fake port and asserts `PlanInput.cost_query` mirrors `ConstraintSet.cost_query` (truthy source → True; falsy/None → False).

- [x] **T-7** Add `PlanInput.cost_query` and map it in the Plan node
  - Type: impl
  - Covers: plan §5 (F-1 additive field)
  - Files: `SystemCode/remy/workflows/src/workflows/models.py` (append `PlanInput.cost_query: bool = False`); `SystemCode/remy/workflows/src/workflows/nodes.py` (`plan` node maps `bool(constraint_set.cost_query)` onto `PlanInput.cost_query`)
  - Done when: T-6 passes; `bool(None)` coercion is the only behavior for the falsy case; existing Plan node tests stay green.

- [x] **T-8** Wire `cost_query` → `drop_uncosted` in `PlanServiceAdapter`
  - Type: impl
  - Covers: AC-8 (production wiring; risks #1 mitigation)
  - Files: `SystemCode/remy/app/src/app/plan_adapter.py` (edit)
  - Done when: `PlanServiceAdapter.generate` calls `plan_service.generate(request, drop_uncosted=plan_input.cost_query)` (no other budget signal). Existing adapter tests stay green; a small test in Group 5 (T-13 F-2) asserts the production path end to end.

### Group 4 — app: SSE serializer and `/chat` endpoint

- [x] **T-9** Write failing tests: SSE serializer and `/chat` endpoint surface
  - Type: test
  - Covers: AC-1, AC-2, AC-16, AC-17, AC-19
  - Files: `SystemCode/remy/app/tests/api/test_sse.py` (create); `SystemCode/remy/app/tests/api/test_chat_endpoint.py` (create)
  - Done when: tests fail because `app.sse` and `app.chat_router` do not exist. `test_sse.py::test_frame_shape` asserts `event: <type>\ndata: <json>\n\n` framing, JSON round-trips through the p3-002 event models, and no trace object leaks. `test_chat_endpoint.py` covers AC-1 (`text/event-stream`; 422 on missing session/message), AC-2 (only five event types), AC-16 (`trace_id` present, trace object absent), AC-17 (failure → single `error` event, stream closes), AC-19 (two independent calls).

- [x] **T-10** Implement SSE serializer and `/chat` router
  - Type: impl
  - Covers: AC-1, AC-2, AC-16, AC-17, AC-19
  - Files: `SystemCode/remy/app/src/app/sse.py` (create); `SystemCode/remy/app/src/app/chat_router.py` (create); `SystemCode/remy/app/src/app/main.py` (create); `SystemCode/remy/app/src/app/composition.py` (extend)
  - Done when: T-9 passes. `serialize_event` accepts only the five p3-002 event models and uses `model_dump(mode="json")`. Router: validates `ChatRequest`, runs `composition.create_workflow(plan_service).invoke(...)`, mints `trace_id` per turn, streams `metadata` → `token*` → `plan_updated?` → `done`; failure → single `error` event + close. `main.py` builds the FastAPI app and mounts the router under `/api/v1`; `api` stays free of `app` imports.

### Group 5 — app: cost projection and served-surface conformance

- [x] **T-11** Write failing tests: on-demand cost folded into `/chat`
  - Type: test
  - Covers: AC-4, AC-5, AC-6, AC-7
  - Files: `SystemCode/remy/app/tests/api/test_cost_projection.py` (create)
  - Done when: tests fail because the handler's cost branch does not exist. `test_cost_surfaced_on_cost_intent` (cost_query truthy → calculator called, cost in payload); `test_no_cost_without_intent` (cost_query falsy → calculator not called); `test_consumed_and_retail_distinct_via_calculator` (real `CostNutritionService.calculate` with mocked repo — consumed vs retail exposed separately, R-11); `test_missing_package_reported_not_fabricated` (`MISSING_PACKAGE_DATA` warning present; no fabricated/zero price); `test_cost_query_branches_handler` (real `extract_constraints` sets `cost_query` → handler takes the cost path).

- [x] **T-12** Implement on-demand cost projection in `/chat` handler
  - Type: impl
  - Covers: AC-4, AC-5, AC-6, AC-7
  - Files: `SystemCode/remy/app/src/app/chat_router.py` (edit — cost branch); `SystemCode/remy/app/src/app/composition.py` (extend — expose calculator wiring)
  - Done when: T-11 passes. When `cost_query` truthy: call `CostNutritionService.calculate(...)` for scoped names; fold consumed/retail cost + `MISSING_PACKAGE_DATA` warning into the existing event payloads; no new event type. When falsy: calculator not called. No scoped names → no calculator call, no error.

- [ ] **T-13** Write failing endpoint test: **[F-2]** cost-intent turn drops uncosted recipe end-to-end (production wiring)
  - Type: test
  - Covers: AC-8 end-to-end; risks #1 mitigation; T-8 production wiring
  - Files: `SystemCode/remy/app/tests/api/test_chat_endpoint.py` (append)
  - Done when: `test_cost_intent_turn_drops_uncosted_recipe_end_to_end` fails because the production wiring (T-8) or the handler cost branch is missing. **Fixture-wiring per verdict:** the test wires **real** `PlanServiceAdapter` + **real** `PlanService` (the `SignalInspector` pattern from `test_service_cost_drop.py` fakes repo/calculator; the LLM and port fake only at the workflow boundary is allowed only if the adapter and PlanService still run for real). Asserts: cost-intent `/chat` turn → streamed explanation shows the uncosted recipe as `evidence-absent` (not `selected`); a costed recipe remains selectable. **Optional-if-free:** pool-emptied-by-cost-drop → infeasible with named binding constraints.

- [ ] **T-14** Write failing endpoint tests: served-surface conformance
  - Type: test
  - Covers: AC-13, AC-14, AC-15, AC-18, AC-20
  - Files: `SystemCode/remy/app/tests/api/test_chat_endpoint.py` (append); `SystemCode/remy/app/tests/api/test_response_schema.py` (extend only if R-16 does not already exercise the streamed payload)
  - Done when: `test_three_levels_present_in_stream` (AC-13), `test_distinct_causes_in_stream` (AC-14; evidence-absent vs present-evidence-excludes vs unmapped), `test_stream_excludes_forbidden_fields` (AC-15; **full** `CHAT_FORBIDDEN_FIELDS` set — all eight, per F-5 note), `test_plan_updated_has_delta_and_scoped_explanation` (AC-18) fail against the current handler. AC-20: the A-007 fixtures (`test_response_schema.py`, `test_explanation_shape.py`) remain green against the mapped response.

- [ ] **T-15** Fix any served-surface defects surfaced by T-13/T-14
  - Type: impl
  - Covers: AC-13, AC-14, AC-15, AC-18, AC-20
  - Files: `SystemCode/remy/app/src/app/chat_router.py` (edit — payload construction only, if needed)
  - Done when: T-13, T-14 pass; no reimplementation of p3-002's projection (`from_trace_envelope` stays the source); the full `CHAT_FORBIDDEN_FIELDS` set is excluded from every event payload; prices remain permitted.

- [ ] **T-16** Extend Generate Response tests for the inherited cost-drop cause
  - Type: test
  - Covers: AC-11, AC-12
  - Files: `SystemCode/remy/workflows/tests/test_generate.py` (extend)
  - Done when: `test_unknown_reference_rejected` (AC-11) and `test_evidence_absent_not_restated_permissive` (AC-12) cover a cost-dropped recipe (state `evidence-absent` under `constraint="budget"`) driven through the real Generate Response node with a fake LLM. Existing generate tests stay green.

### Group 6 — docs

- [ ] **T-17** Write failing doc test: `plan_updated` example carries delta + scoped explanation
  - Type: test
  - Covers: AC-21
  - Files: `SystemCode/remy/app/tests/api/test_api_doc_plan_updated.py` (create)
  - Done when: `test_plan_updated_example_has_explanation` fails because API_doc §3 still carries the legacy delta-only example. Reads `SystemCode/remy/api/docs/API_doc.md` §3, asserts the `plan_updated` example contains an `explanation` with `recipe` and `constraints`.

- [ ] **T-18** Update API_doc §3 `plan_updated` example
  - Type: impl
  - Covers: AC-21; p3-002 C-2 / N-2
  - Files: `SystemCode/remy/api/docs/API_doc.md` (edit §3)
  - Done when: T-17 passes; the `plan_updated` example shows the delta (`day`, `slot`, `recipe_id`) **and** the meal-scoped three-level explanation, replacing the delta-only example.

### Group 7 — CI check set

- [ ] **T-19** Update `sdd.json` to cover p3-004's source and test paths
  - Type: impl
  - Covers: plan Output §sdd.json
  - Files: `sdd.json` (edit)
  - Done when:
    - The check set includes `remy/api/src/api/features/plan`, `remy/api/tests/features/plan/`, `remy/app/src/app/`, `remy/app/tests/api/`, `remy/workflows/src/workflows/`, and `remy/api/docs/API_doc.md` (doc presence for AC-21).
    - `uv run lint-imports` remains 4 kept, 0 broken (`api does not depend on app` contract holds).
    - `sdd.py check p3-004-conversational-constraint-interface` passes.

### Group 8 — final conformance sweep

- [ ] **T-20** Full-feature CI run and cross-check
  - Type: impl (CI gate)
  - Covers: all ACs; all six integration edges
  - Files: none
  - Done when:
    - `sdd.py ci p3-004-conversational-constraint-interface` returns `PASS` (or `INCONCLUSIVE` retried to `PASS`).
    - The six integration edges each have a green test: `TraceEnvelope→handler` (`test_workflow_envelope_streams_events`), `handler→serializer` (`test_events_framed_as_sse` + `test_sse.py::test_frame_shape`), `plan-service MISSING_PACKAGE_DATA→pool` (`test_service_cost_drop.py::test_uncosted_recipe_dropped_evidence_absent`), `calculator→/chat cost` (`test_consumed_and_retail_distinct_via_calculator`), `contract types→fixtures` (A-007 fixtures green), `cost_query→/chat intent branch` (`test_cost_query_branches_handler`).
    - Every AC-1..AC-21 is mapped to at least one green test (see plan Test strategy).
    - `test_cost_intent_turn_drops_uncosted_recipe_end_to_end` is green and its fixture wires the real `PlanServiceAdapter` + real `PlanService` (verdict fold-forward).
