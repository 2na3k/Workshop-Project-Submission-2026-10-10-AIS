# Decisions - Explainable response contract

## Decisions

### D-1 Amendment A-007 establishes canonical fixture paths
- Date: 2026-10-17
- Context: Constitution R-16 and R-17 originally cited `tests/api/<name>` without specifying package prefix. Under `.importlinter` architecture contracts, the contract models live in `remy-app` (the only package permitted to import both `api` and `workflows`). Fixtures importing `remy-app` and `remy-workflows` must reside where `remy-app` is importable.
- Decision: Amendment A-007 (approved) updated constitution v1.6 to v1.7, establishing the canonical paths `SystemCode/remy/app/tests/api/test_response_schema.py` and `SystemCode/remy/app/tests/api/test_explanation_shape.py`.
- Alternatives: Move contract types into `api` (rejected: `api` cannot import `workflows` under R-2); leave path divergence undocumented (rejected: violates R-1 and constitutional integrity).
- Affects: AC-11a, AC-11b, R-16, R-17.
- Source: Plan §1, Amendment A-007, Task T-1.

### D-2 Specific R-16 exclusion floor without unbounded glob
- Date: 2026-10-17
- Context: R-16 defines four categories of audit provenance (`confidence`, `normalization_version`, `source_*`, `*_id`). An unconstrained `*_id` glob would strip legitimate user-facing identifiers such as `recipe_id`, `requirement_id`, `trace_id`, and `session_id`. Additionally, prices are user-meaningful and not excluded by R-16.
- Decision: Define `CHAT_FORBIDDEN_FIELDS` as an explicit named tuple (`confidence`, `normalization_version`, `source`, `source_snapshot_id`, `source_id`, `mapping_version`, `food_key`, `fdc_id`). Structural identifiers and prices remain permitted in the user payload; the SSE contract declares no additional exclusions beyond R-16's floor.
- Alternatives: Wildcard `*_id` matching (rejected: strips necessary structural IDs); adopt calculator endpoint's broader exclusion list (rejected: calculator list is endpoint-specific).
- Affects: AC-7, AC-7b, R-16.
- Source: Clarification C-3, Plan §2 (SF-1, SF-2), Tasks T-6, T-8, T-9.

### D-3 Trace referenced out-of-band by stable identifier
- Date: 2026-10-17
- Context: Conversational recommendations must be auditable and correlated with execution traces for downstream judge/eval layers, but streaming payloads should avoid bloat and provenance leaks.
- Decision: Every SSE event carrying metadata/done and the response envelope includes a stable `trace_id`. The execution trace envelope is never embedded in SSE events; it is retrievable out-of-band by identifier.
- Alternatives: Embed full trace in `done` event (rejected: bloats stream and violates clean boundary); omit trace correlation (rejected: breaks auditability and judge integration).
- Affects: AC-10, R-16, Clarification C-1.
- Source: Clarification C-1, Plan §2, Tasks T-3, T-10, T-11.

### D-4 `plan_updated` carries delta plus meal-scoped three-level explanation
- Date: 2026-10-17
- Context: Incremental plan modifications need to satisfy R-17's three-level explanation requirement without retransmitting unchanged full-plan explanations.
- Decision: `PlanUpdatedEvent` carries `delta: MealDelta` (`day`, `slot`, `recipe_id`) and `explanation: MealScopedExplanation` (`recipe: RecipeExplanation`, `constraints: list[ConstraintExplanation]`).
- Alternatives: Delta only (rejected: leaves updated meal unexplained, violating R-17); full plan resend (rejected: inefficient for streaming delta updates).
- Affects: AC-2b, R-17, Clarification C-2.
- Source: Clarification C-2, Plan §2, Task T-3.

### D-5 Trace-side R-16 clause marked strict xfail under F-P3-1
- Date: 2026-10-17
- Context: Upstream `PlanTrace` (and embedded `PlanTraceView`) from p2-003 does not yet carry mapping confidence, normalization version, or source identifiers.
- Decision: `test_trace_retains_audit_provenance` in `test_response_schema.py` is marked `@pytest.mark.xfail(strict=True, reason="F-P3-1: PlanTraceView carries no R-16 audit provenance; owned by p2-003")`. It is not removed or weakened; resolution is owned upstream by p2-003. User payload exclusion passes independently.
- Alternatives: Fabricate provenance in test fixtures (rejected: misleading evidence); omit trace-side test (rejected: hides constitutional gap).
- Affects: AC-8, AC-11b, R-16.
- Source: Plan §4, Task T-9, Finding F-P3-1.

## Consequential clarifications

- **C-1 (trace: referenced, not embedded, 2026-10-17, human):** The trace does not travel in the SSE stream. Every response carries a stable `trace_id` correlating the user-visible response with its trace; the trace itself is retrievable out-of-band by identifier.
- **C-2 (`plan_updated`: delta + scoped three-level explanation, 2026-10-17, human):** A `plan_updated` event carries the delta identifying the changed meal (`day`, `slot`, `recipe_id`) and the three-level explanation scoped to that meal (recipe-level and constraint-level outcomes, including drop causes).
- **C-3 (R-16 exclusion list: layered — R-16 is the floor, endpoints may be stricter, 2026-10-17, human):** R-16's named four categories are the floor. Prices and structural IDs are permitted in the user payload; the SSE contract adds no additional exclusions.

## Overrides

None.

## Deviations from plan

No deviations from plan.

## Findings carried to phase review

- **F-P3-1 (trace-side R-16 gap, owner: p2-003).** The user-payload exclusion
  clause of R-16 passes (the calculator's `OfferRef` carries only
  `food_key`/`listing_name`/`retailer`, so `confidence`/`source_snapshot_id`/
  `mapping_version` never reach the user payload). The trace-side retention
  clause fails because those fields never reach `PlanTraceView`. The R-16
  trace-side fixture is `xfail(strict=True)` with a reason naming F-P3-1.
  **Resolution path (three small reopens):**
    1. p2-002 — extend `OfferRef` with `confidence`, `source_snapshot_id`,
       `mapping_version`; `inspect_candidates` populates them.
    2. p2-003 — `RequirementOutcome` carries the same fields; `QUERY_RECIPES` /
       `QUERY_INGREDIENTS` project `fc.normalization_version`; `PlanService`
       propagates.
    3. p3-001 — `RequirementOutcomeView` carries the fields; the adapter copies.
    4. p3-002 — remove the `xfail`; the test passes.
       **Durable alternative:** extend `BEST_FULFILLMENT` to carry the winning
       edge's provenance (p1-002 reopen + graph rebuild). Recorded for phase review
       as the long-term fix.

- **F-1 (contract module's home constrains p3-004).** `app/chat_contract.py` can
  only be imported by `app` (`api ↛ app` per R-2). When p3-004 implements
  `POST /chat`, its endpoint code must live in `app` (or the contract must
  move). Recorded for p3-004's plan.

- **F-2 (floor constant naming).** `CHAT_FORBIDDEN_FIELDS` names the chat
  payload's full exclusion set; the R-16-floor portion (the named four
  categories) is asserted separately by AC-7b's test. The constant's name
  reflects its scope, not R-16's.

- **BD-3 (fixture path amended).** Amendment A-007 corrects the constitution's
  R-16/R-17 named check paths to `SystemCode/remy/app/tests/api/<name>`,
  formalizing the divergence recorded as p2-002 F-D and p3-001 BD-2a.
  Constitution v1.7.

- **BD-4 (T-15 mis-scoping, resolved).** The original T-15 ("Record decisions")
  asked the Implement stage to write a Close-stage artifact. The implementer
  correctly stopped; T-15 was removed and the CI+advance task renumbered to
  T-15. `decisions.md` is written here by Close. This is the **fourth
  occurrence** of a Close artifact in an Implement task list (p2-002 T-24,
  p2-003 T-17, p3-001 T-16, p3-002 old T-15). **Two one-line kit-prompt fixes
  prevent recurrence:** (a) the plan prompt should say "every task must be an
  Implement-stage artifact; Close-stage artifacts (`decisions.md`,
  `CHANGELOG.md`, `state.json`) are not tasks"; (b) the implement prompt
  should say "if a task asks you to write a Close-stage artifact, stop and
  route to `plan`."

- **N-2 (API_doc §3 divergence).** The deployed `/chat` example shows a legacy
  `plan_updated` (delta only); the contract requires delta + meal-scoped
  explanation (C-2). The doc update is assigned to p3-004 (which implements the
  endpoint and owns the doc).

- **langgraph pending-deprecation warning.** New in CI since p3-001; carried
  into p3-002's output (`LangChainPendingDeprecationWarning: allowed_objects`).
  Not a p3-002 defect. Monitor for the next langgraph major.

- **The three `xfail`s.** Two from p3-001 (F-P3-1 trace-side, in
  `remy/workflows/tests/test_response_schema_workflow.py`) and one from p3-002
  (the same finding, at the R-16 fixture level). All `strict=True`; all
  visible; none silently deferred. When F-P3-1 resolves, all three `xfail`s
  are removed in the same change.
