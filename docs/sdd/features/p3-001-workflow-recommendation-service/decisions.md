# Decisions - Workflow recommendation service

## Decisions

### D-1 Provenance gap remains owned by p2-003
- Date: 2026-10-16
- Status: recorded deferral
- Context: R-16 requires audit provenance to remain in the execution trace, and R-13 requires mapping confidence in the trace. The p2-003 `PlanTrace` currently carries neither provenance fields nor mapping confidence.
- Decision: p3-001 embeds the complete `PlanTrace` shape it receives in `PlanTraceView` and does not invent or recover the missing fields. Finding F-P3-1 remains owned by p2-003. The trace-side R-16 assertion is xfailed with a reason naming F-P3-1.
- Affects: AC-10, AC-21, R-13, R-16; downstream p3-002 trace consumers.
- Source: plan F-2 and Finding F-P3-1.

### D-2 API and workflow boundaries
- Date: 2026-10-16
- Status: adopted
- Context: p3-001 needs both the plan response and trace while preserving inward dependency direction. The codebase already includes `app` as an import-linter root package.
- Decision: the workflow owns `PlanInput`, `PlanResult`, and `PlanTraceView`; `PlanServiceAdapter` in `app` calls `PlanService.generate`, unpacks its tuple, and maps API types to workflow-owned types. The composition root wires the adapter and configured LLM clients. The `workflows` package does not import `api`.
- Affects: AC-4, AC-16, R-2.
- Source: plan C-1, C-7, and Revision Note F-3; `.importlinter` contracts.

### D-3 p2-003 return-shape prerequisite landed
- Date: 2026-10-16
- Status: adopted
- Context: the adapter requires the plan result and trace as one return value; reading mutable `last_trace` state would not be reentrant.
- Decision: prerequisite P-1 is satisfied by the p2-003 reopen. `PlanService.generate` returns `(PlanResponse, PlanTrace)`, and `PlanResponse` carries recipe and constraint outcomes. The adapter has an integration test against the real service with a mocked Neo4j driver.
- Affects: AC-4, AC-16.
- Source: p2-003 decision D-6; commit `7e567b3`; implementation commits `e3c43a7` and `40121b8`.

### D-4 LangChain dependencies
- Date: 2026-10-16
- Status: adopted
- Context: workflow LLM nodes use LangChain's `init_chat_model`, with Ollama as the default configured provider.
- Decision: `remy-workflows` declares compatible `langchain>=0.3,<1` and `langchain-ollama>=0.3,<1` dependencies alongside `langgraph>=0.2,<1`. The `<1` bounds keep the dependency resolver compatible with the existing LangGraph bound.
- Affects: P-2, AC-2, AC-11, AC-12.
- Source: T-1 dependency resolution and `SystemCode/remy/workflows/pyproject.toml`.

### D-5 Trace-side R-16 assertion is deferred
- Date: 2026-10-16
- Status: recorded deferral
- Context: the current `PlanTrace` cannot satisfy the trace-side provenance assertion because those fields are absent upstream.
- Decision: the test remains present and xfailed with the F-P3-1 reason. It is not weakened or removed; p2-003 owns resolution.
- Affects: AC-21, R-16.
- Source: plan F-2 and D-1 above.

### D-6 p2-003 prerequisite and spec synchronization
- Date: 2026-10-16
- Status: recorded
- Context: p2-003's C-7 reopen landed before p3-001 implementation. The workflow port returns workflow-owned models, while the adapter calls the real API tuple and maps it.
- Decision: P-1 is recorded as landed; P-2 is recorded as implemented in the workflow package. At the next spec touch, synchronize C-1's wording to state that the workflow port returns workflow-owned models and that the adapter unpacks `(PlanResponse, PlanTrace)` and maps both values.
- Affects: p3-001 spec C-1, AC-4, AC-16.
- Source: plan F-1, P-1, P-2, and revision note F-1.

### D-7 R-16/R-17 fixture path findings route to phase review
- Date: 2026-10-16
- Status: recorded deferral
- Context: the constitution names `tests/api/test_response_schema.py` and `tests/api/test_explanation_shape.py`, while the checkout contains the calculator response fixture and no named explanation-shape fixture.
- Decision: p3-001 tests the workflow-side equivalents using the calculator test's exclusion list and a workflow-local three-level/distinct-cause assertion. The path divergence and missing named fixture are phase-review inputs; R-17 fixture ownership is p3-002.
- Affects: AC-21, R-16, R-17.
- Source: plan BD-2 and spec C-8.

## Overrides

None.
