# Decisions - Workflow recommendation service

## Decisions

### D-1 Provenance gap remains owned by p2-003
- Date: 2026-10-16
- Context: R-16 requires audit provenance to remain in the execution trace, and R-13 requires mapping confidence in the trace. The p2-003 `PlanTrace` currently carries neither provenance fields nor mapping confidence.
- Decision: p3-001 embeds the complete `PlanTrace` shape it receives in `PlanTraceView` and does not invent or recover the missing fields. Finding F-P3-1 remains owned by p2-003. The trace-side R-16 assertion is xfailed with a reason naming F-P3-1.
- Alternatives: Fabricate missing provenance fields in the workflow (rejected: violates R-16 and fabrication prohibitions); reopen p2-003 to add provenance to PlanTrace during p3-001 (rejected: reopens upstream feature outside scope; tracked as F-P3-1).
- Affects: AC-10, AC-21, R-13, R-16; downstream p3-002 trace consumers.
- Source: Plan F-2 and Finding F-P3-1.

### D-2 API and workflow boundaries
- Date: 2026-10-16
- Context: p3-001 needs both the plan response and trace while preserving inward dependency direction. The codebase already includes `app` as an import-linter root package.
- Decision: The workflow owns `PlanInput`, `PlanResult`, and `PlanTraceView`; `PlanServiceAdapter` in `app` calls `PlanService.generate`, unpacks its tuple, and maps API types to workflow-owned types. The composition root wires the adapter and configured LLM clients. The `workflows` package does not import `api`.
- Alternatives: Workflows package directly imports API schemas (rejected: violates R-2 inward dependency direction); communicate over HTTP localhost (rejected: network overhead and redundant validation); create a new shared contract package (rejected: reopens closed p2 packages unnecessarily).
- Affects: AC-4, AC-16, R-2.
- Source: Plan C-1, C-7, and Revision Note F-3; `.importlinter` contracts.

### D-3 p2-003 return-shape prerequisite landed
- Date: 2026-10-16
- Context: The adapter requires the plan result and trace as one return value; reading mutable `last_trace` state would not be reentrant.
- Decision: Prerequisite P-1 is satisfied by the p2-003 reopen. `PlanService.generate` returns `(PlanResponse, PlanTrace)`, and `PlanResponse` carries recipe and constraint outcomes. The adapter has an integration test against the real service with a mocked Neo4j driver.
- Alternatives: Read mutable `last_trace` property on `PlanService` (rejected: stateful, non-reentrant, and fragile); ignore PlanTrace (rejected: violates AC-5 and AC-10).
- Affects: AC-4, AC-16.
- Source: p2-003 decision D-6; commit `7e567b3`; implementation commits `e3c43a7` and `40121b8`.

### D-4 LangChain dependencies
- Date: 2026-10-16
- Context: Workflow LLM nodes use LangChain's `init_chat_model`, with Ollama as the default configured provider.
- Decision: `remy-workflows` declares compatible `langchain>=0.3,<1` and `langchain-ollama>=0.3,<1` dependencies alongside `langgraph>=0.2,<1`. The `<1` bounds keep the dependency resolver compatible with the existing LangGraph bound.
- Alternatives: Write custom HTTP clients for Ollama/OpenAI from scratch (rejected: violates project design using LangGraph/LangChain ecosystem); declare unpinned or `>=1` bounds (rejected: resolver conflicts with langgraph).
- Affects: P-2, AC-2, AC-11, AC-12.
- Source: T-1 dependency resolution and `SystemCode/remy/workflows/pyproject.toml`.

### D-5 Trace-side R-16 assertion is deferred
- Date: 2026-10-16
- Context: The current `PlanTrace` cannot satisfy the trace-side provenance assertion because those fields are absent upstream.
- Decision: The test remains present and xfailed with the F-P3-1 reason. It is not weakened or removed; p2-003 owns resolution.
- Alternatives: Remove the trace-side assertion entirely (rejected: hides known constitutional contract gap); fabricate provenance in test fixtures (rejected: misleading test pass).
- Affects: AC-21, R-16.
- Source: Plan F-2 and D-1 above.

### D-6 p2-003 prerequisite and spec synchronization
- Date: 2026-10-16
- Context: p2-003's C-7 reopen landed before p3-001 implementation. The workflow port returns workflow-owned models, while the adapter calls the real API tuple and maps it.
- Decision: P-1 is recorded as landed; P-2 is recorded as implemented in the workflow package. At the next spec touch, synchronize C-1's wording to state that the workflow port returns workflow-owned models and that the adapter unpacks `(PlanResponse, PlanTrace)` and maps both values.
- Alternatives: Force immediate edit of spec.md during implementation/close (rejected: violates SDD artifact freeze rules for closed/frozen specs); ignore port model mismatch (rejected: port models must remain workflow-owned).
- Affects: p3-001 spec C-1, AC-4, AC-16.
- Source: Plan F-1, P-1, P-2, and revision note F-1.

### D-7 R-16/R-17 fixture path findings route to phase review
- Date: 2026-10-16
- Context: The constitution names `tests/api/test_response_schema.py` and `tests/api/test_explanation_shape.py`, while the checkout contains the calculator response fixture and no named explanation-shape fixture.
- Decision: p3-001 tests the workflow-side equivalents using the calculator test's exclusion list and a workflow-local three-level/distinct-cause assertion. The path divergence and missing named fixture are phase-review inputs; R-17 fixture ownership is p3-002.
- Alternatives: Create tests inside `remy-api` during p3-001 (rejected: modifies API package outside feature scope); ignore R-16/R-17 verification (rejected: violates constitutional compliance obligations).
- Affects: AC-21, R-16, R-17.
- Source: Plan BD-2 and spec C-8.

### D-8 — `RequirementOutcomeView` carries the offer's provenance fields

- Date: 2026-10-17
- Status: adopted (reopen; resolves F-P3-1's workflow-side half)
- Context: p3-002's trace-side R-16 conformance check runs against the
  workflow's trace view (as well as the plan's `PlanTrace`). After p2-002
  and p2-003's reopens, the fields flow to `PlanTraceView` — but the workflow
  declared its own view model (`RequirementOutcomeView` + `OfferView`) without
  them.
- Decision: `OfferView` and `RequirementOutcomeView` gain `confidence`,
  `source_snapshot_id`, and `mapping_version`. The adapter in `remy/app`
  maps them one-to-one from `RequirementOutcome` and `OfferRef`.
- Alternatives: let the workflow view mirror the response DTO (rejected:
  the response DTO excludes provenance; the view must carry what the trace
  carries).
- Affects: `workflows/models.py` (`OfferView`, `RequirementOutcomeView`),
  `app/plan_adapter.py` (mapping), `workflows/tests/test_response_schema_workflow.py`
  (remove the `xfail`s).
- Source: p3-002 F-P3-1 resolution.

## Consequential clarifications

- **C-1 (plan interface, 2026-10-15, spec review):** The workflow reaches the plan path through a workflow-owned interface (dependency inversion), with the adapter in `app` (composition root) calling `PlanService.generate`.
- **C-2 (trace, 2026-10-15, spec review):** The workflow trace embeds `PlanTraceView` unchanged inside a versioned envelope; the Plan node is recorded as one step.
- **C-3 (diagram reconciliation, 2026-10-15, spec review):** Five conceptual stages in `workflow_diagram.md` are realized as three workflow nodes: Extract Constraints, Plan, Generate Response.
- **C-4 (failure semantics, 2026-10-15, spec review):** Outcomes are `plan | infeasible | failure(node, reason)`, always paired with a trace. Failure is all-or-nothing.
- **C-5 (R-3 stack shape, 2026-10-15, spec review):** LangGraph/LangChain and a locally hosted LLM runtime are same-shape additions under R-3.
- **C-6 (amendments, 2026-10-15, spec review):** A-005 and A-006 are approved and merged into constitution v1.6.
- **C-7 (p2-003 return shape, 2026-10-15, spec review):** `PlanService.generate` returns `tuple[PlanResponse, PlanTrace]`.
- **C-8 (AC-21 conformance paths, 2026-10-16, spec review):** Conformance paths reconciled; workflow-side equivalents assert R-16 and R-17 contracts.

## Overrides

None.

## Deviations from plan

No deviations from plan.
