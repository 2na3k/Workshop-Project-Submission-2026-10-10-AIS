# Decisions - Conversational constraint interface

## Decisions

### D-1 A-006 recipe-level cost drop enforced in API plan service layer
- Date: 2026-10-18
- Context: Amendment A-006 deferred the recipe-level cost drop for uncosted requirements (when no cost-eligible fresh package exists per R-8/R-10) from p2 to p3-004. The enforcement point needed to be located where candidate pools are filtered.
- Decision: Enforce the recipe-level cost drop in `PlanService.generate` inside `remy/api/src/api/features/plan/service.py`, using the calculator's `selected_offer is None` signal (the recipe-inspection equivalent of `MISSING_PACKAGE_DATA`) to drop recipes with an `evidence-absent` cause. The drop is gated via `drop_uncosted: bool = False`, preserving p2's retain behavior for cost-agnostic callers while firing when budget is requested.
- Alternatives: Enforce in the constraint filtering layer `filtering.py` (rejected: lacks package inspection context); enforce in the workflow node (rejected: separates candidate filtering from the plan service).
- Affects: AC-8, AC-9, AC-10, R-8, R-10.
- Source: Spec Clarification C-1, Plan §5, Tasks T-4, T-5, T-13.

### D-2 Stateless per-turn conversational interface without server session storage
- Date: 2026-10-18
- Context: A conversational interface can either manage stateful server sessions with persistence or evaluate turns statelessly from request message and client-provided user context.
- Decision: Implement `POST /chat` as a stateless per-turn endpoint. Each request is evaluated solely from its `session_id`, `message`, and optional `user_context`. Multi-turn continuity (such as meal modification deltas) is carried by the client via `user_context`. No server-side session memory or persistence is introduced.
- Alternatives: Introduce Redis/database session persistence (rejected: adds state management and storage infrastructure out of scope for this phase).
- Affects: AC-1, AC-19, Clarification C-2.
- Source: Spec Clarification C-2, Plan §1, Tasks T-9, T-10.

### D-3 Reuse p3-001 Generate Response node for deterministic safe re-expression
- Date: 2026-10-18
- Context: Recommendation outcomes and drop causes delivered in user text must not restate `evidence-absent` drops as permissive and must not invent recipe or requirement IDs not produced by the plan.
- Decision: Reuse the existing p3-001 `Generate Response` node and its deterministic structured check in `workflows/nodes.py`, verifying that referenced recipe IDs, requirement IDs, and drop causes are subsets of the plan result, and raising an error if evidence-absent candidates are claimed as selected.
- Alternatives: Build a new response generation node in `remy-app` (rejected: duplicates validation logic and risks divergence from frozen workflow behavior).
- Affects: AC-11, AC-12, Clarification C-3.
- Source: Spec Clarification C-3, Plan §8, Task T-16.

### D-4 Acceptance of Phase p2 data-quality findings (DQ-1..DQ-7) as tracked follow-ups
- Date: 2026-10-18
- Context: Phase p2 closed with tracked data-quality findings (DQ-1..DQ-7) noting partial coverage and candidate mapping anomalies in the underlying graph.
- Decision: Build against whatever the plan produces without masking or compensating for data coverage gaps in the conversational interface layer.
- Alternatives: Synthesize missing prices or fallback mappings in the application layer (rejected: violates constitutional honesty and masks data preparation flaws).
- Affects: Clarification C-4, Spec §Summary.
- Source: Spec Clarification C-4, Phase p2 Review.

### D-5 On-demand cost projection folded into existing `/chat` response and SSE stream
- Date: 2026-10-18
- Context: When callers express a budget or cost intent ("cheapest", "under $5", "how much does it cost"), cost figures must be surfaced without creating a parallel endpoint or altering the frozen p3-002 SSE event vocabulary.
- Decision: Fold on-demand cost calculations into the existing `/chat` turn: `chat_router.py` calls `CostNutritionService.calculate` for scoped ingredients, exposes consumed vs. retail cost separately (R-11), surfaces `MISSING_PACKAGE_DATA` without fabricating prices, and streams the cost details within `token` events and `ChatResponseEnvelope`. When no cost intent is present, the calculator is not invoked.
- Alternatives: Create a separate `POST /chat/cost` endpoint (rejected: fragments the conversational interface); introduce a new `cost_updated` SSE event (rejected: violates frozen p3-002 event vocabulary).
- Affects: AC-4, AC-5, AC-6, AC-7, R-11, Clarification C-5.
- Source: Spec Clarification C-5, Plan §4, Tasks T-11, T-12.

### D-6 Cost/budget intent detection extends Extract Constraints with additive `cost_query`
- Date: 2026-10-18
- Context: Natural language requests must be checked for cost/budget intent to determine whether to surface cost figures and trigger the recipe-level cost drop.
- Decision: Add an optional field `cost_query: bool | None = None` to `ConstraintSet` in `workflows/models.py` and `PlanInput.cost_query: bool = False`. In `workflows/nodes.py`, extract intent via LLM when present, falling back to a deterministic regex pattern on affordability keywords (`cost`, `price`, `budget`, `cheap`, `$`, `under $`).
- Alternatives: Dedicated classifier workflow node (rejected: adds unnecessary latency and node overhead to the LangGraph flow).
- Affects: AC-3, AC-4, AC-5, Clarification C-6.
- Source: Spec Clarification C-6, Plan §3, Tasks T-2, T-3, T-6, T-7.

### D-7 Adoption of Amendment A-007 canonical fixture paths
- Date: 2026-10-18
- Context: R-16 and R-17 conformance fixtures for the `/chat` response contract live in `SystemCode/remy/app/tests/api/` per Amendment A-007.
- Decision: Assert R-16 and R-17 conformance for the served `/chat` interface at the A-007 paths (`test_response_schema.py` and `test_explanation_shape.py`) in `remy-app`.
- Alternatives: Keep fixtures in `api` or `workflows` (rejected: fails architecture boundaries under R-2).
- Affects: AC-15, AC-20, R-16, R-17.
- Source: Spec Clarification C-7, Plan §7, Task T-14.

### D-8 Hybrid generation: LLM intro + deterministic meal text
- Date: 2026-10-18
- Context: Under local CPU inference (llama3.2:3b, no GPU), a full LLM-written
  meal plan (9 meals × ingredients × nutrients × instructions) exceeded both
  the latency budget (>90s) and the `num_predict` cap, causing truncation,
  JSON parse failure, and fallback. Reusing p3-001's `generate_response`
  unchanged was infeasible on this hardware.
- Decision: Split generation into two phases. The LLM writes only a short
  (2-sentence) encouraging introduction based on a slim fact sheet (titles,
  day/slot, nutrient status; no ingredients). The meal body — titles,
  ingredients, nutrients, instructions, plan-level outcome, and the `⚠️`
  nutrient disclosure — is generated deterministically from `PlanResult`
  via `_fallback_from_facts` and prepended with the LLM intro. Structured
  validation (AC-11, AC-12) still runs on the LLM's returned dict when
  present (test paths) and is skipped for the production `AIMessage` (fast
  path).
- Alternatives: (a) keep the LLM as sole generator with a larger
  `num_predict` and a smaller prompt — rejected: still 60–90s on CPU and
  truncation-prone; (b) drop the LLM entirely — rejected: removes the
  demonstrable LLM-generation component the spec and G-2 expect; (c) stream
  from `llm.stream()` with `astream_events` — deferred as a follow-up
  (real token-level streaming is a UX improvement, not a correctness fix).
- Affects: AC-11, AC-12, AC-13, AC-18, spec §User-facing behavior, tasks
  T-15, T-16. Introduces a documented case where the LLM intro may
  paraphrase the user's request ("170g protein") while the deterministic
  `⚠️` disclosure reflects the actual value (e.g., 158.4g); the disclosure
  line is authoritative.
- Source: BD-6 (final) in plan `## Revision notes`; review r1 F-3 accepted
  the dict-guarded validation; review r2 APPROVE accepted the hybrid
  approach.

## Consequential clarifications

- **C-1 (A-006 drop layer: api plan service, 2026-10-18, human).** The inherited recipe-level cost drop (A-006) is enforced in the **api plan service** layer (the plan feature's service/filtering), consuming the calculator's item-level `MISSING_PACKAGE_DATA` signal as the evidence-absent evidence; its fixtures live at `SystemCode/remy/api/tests/features/plan/`. Rationale: the plan service is the layer that forms the eligible pool and already applies the other recipe-level drops, so the cost drop is cohesive there.
- **C-2 (stateless per turn, 2026-10-18, human).** The `/chat` interface keeps no server-side session store; each turn is evaluated from its own message and optional `user_context`. Multi-turn continuity, if any, is carried by the client. Rationale: avoids introducing a session store and the associated persistence contract, which are out of scope for this phase.
- **C-3 (reuse p3-001 Generate Response for safe re-expression, 2026-10-18, human).** The safe re-expression of explanation causes reuses p3-001's Generate Response node and its deterministic structured-output check (referenced IDs/causes must be a subset of the plan's; evidence-absent never restated as permissive) rather than introducing a new generation path. Rationale: the node already enforces the safety invariant; re-implementing it would risk divergence.
- **C-4 (DQ-1..DQ-7 accepted, not compensated, 2026-10-18, human).** The phase p2 data-quality findings (DQ-1..DQ-7) are accepted as tracked data-preparation follow-ups; p3-004 builds against whatever the plan produces and does not compensate for coverage gaps. Rationale: coverage is upstream of this feature; compensating would mask the findings.
- **C-5 (D-a: cost folded into `/chat` using the existing response shape, 2026-10-18, human).** On-demand cost is surfaced by folding it into the existing p3-002 `/chat` response (the `ChatResponseEnvelope` projection and the SSE event payloads), not by adding a new response type or a parallel cost endpoint. Rationale: keeps the one conversational surface and reuses the frozen contract.
- **C-6 (D-b: intent detection extends the extraction node output with an optional cost-query field, 2026-10-18, human).** Cost/budget intent detection is realized by extending p3-001's Extract Constraints output with an optional cost-query field, rather than by a separate classifier stage. Rationale: intent is extracted from the same message the node already parses; a co-located field keeps the workflow's node count unchanged. The concrete field name and type are plan-stage decisions.
- **C-7 (A-007 fixture paths adopted, 2026-10-18, human).** p3-004 asserts R-16 and R-17 for the `/chat` surface at the A-007 paths (`SystemCode/remy/app/tests/api/test_response_schema.py`, `SystemCode/remy/app/tests/api/test_explanation_shape.py`), where `remy/app` is importable. Rationale: the contract types live in `remy/app` (the only package permitted to import both `api` and `workflows`), so the fixtures must run there.

## Overrides

None.

## Deviations from plan

No deviations from plan.

## Findings carried to phase review

- **Tracked upstream data-quality findings (DQ-1..DQ-7):** Inherited from phase p2; coverage gaps and catalog mapping limitations remain tracked as data-preparation improvements.
- **Defensive offer sanitization in `PlanUpdatedEvent`:** In `chat_router.py:336-340`, `selected_offer` on constraints in `PlanUpdatedEvent.explanation` is sanitized to `None` as a defensive mitigation against unverified graph mappings (e.g. water mapped to sugar product) until data-preparation fixes land in p2-002 follow-ups.
