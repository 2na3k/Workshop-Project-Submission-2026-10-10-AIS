# Prompt — Plan

Plan for feature **p3-002-explainable-response-contract**

`<id>`: `p3-002-explainable-response-contract`

## Notes

**p3-002 is a contract, not an implementation.** This feature defines the
user-facing response schemas — the request/response/SSE-event shapes — that the
conversational surface (p3-004) will implement against, and the two
constitution-named fixtures (R-16, R-17). It does not implement the `/chat`
endpoint, the SSE mechanism, or any workflow node. Those are p3-004's.

**Phase p2 closed with data-quality findings (DQ-1..DQ-7) tracked, not blocking.** p3-002's conformance fixtures operate on p3-001's `TraceEnvelope` shape; the plan solver's output quality is upstream and doesn't affect this contract's verification.

## Input

- MUST read: [AGENTS.md](../../../AGENTS.md)
- [constitution.md](../../../docs/sdd/constitution.md) — v1.6. Note R-16's
  and R-17's named check paths and their full contracts (both clauses of
  R-16's check; R-17's two-response shape).
- Amendments: [amendments](../../../docs/amendments), specifically A-005 (R-14 relaxation set) and
  A-006 (R-8/R-10 cost-drop deferral to p3-004).
- [system_design_v3.md](../../../SystemCode/docs/system_design_v3.md)
- [neo4j_db_design.md](../../../SystemCode/docs/neo4j_db_design.md)
- [workflow_diagram.md](../../../SystemCode/remy/workflows/docs/workflow_diagram.md) — the five-stage flow p3-001 implements; p3-002 defines the response contract that surfaces its Outcome to the user.
- [spec.md](../../../docs/sdd/features/p3-002-explainable-response-contract/spec.md)
- [sdd.json](../../../sdd.json) — read the current check set; confirm it will cover `remy/api/tests/api/` (the new fixture directory p3-002 creates) and any contract module p3-002 adds. Update the check set in the same change if not.
- Findings: [data-prep-price-path.md](../../../docs/findings/data-prep-price-path.md)
- Decisions:
    - [decisions.md](../../../docs/sdd/features/p2-001-constraint-evidence-filtering/decisions.md)
    - [decisions.md](../../../docs/sdd/features/p2-002-cost-nutrition-calculation/decisions.md)
    - [decisions.md](../../../docs/sdd/features/p2-003-feasible-meal-plan-solving/decisions.md)
    - [decisions.md](../../../docs/sdd/features/p3-001-workflow-recommendation-service/decisions.md)
- current codebase:
    - Meal plan API: [plan](../../../SystemCode/remy/api/src/api/features/plan)
    - Calculator API: [calculator](../../../SystemCode/remy/api/src/api/features/calculator)
    - App: [app](../../../SystemCode/remy/app)
    - Workflows: [workflows](../../../SystemCode/remy/workflows)
      - [models.py](../../../SystemCode/remy/workflows/src/workflows/models.py) — `TraceEnvelope`,
        `Outcome`, `PlanTraceView`, `ConstraintSet`.
      - [trace.py](../../../SystemCode/remy/workflows/src/workflows/trace.py) — the envelope's assembly.
- Reference: [API_doc.md](../../../SystemCode/remy/api/docs/API_doc.md) — §3 (`POST /api/v1/chat`) declares
  the current chat surface's request shape and SSE event vocabulary. p3-002 refines this into the contract; the doc is the current deployed shape, the spec is the source of truth.
- **The two constitution-named fixtures do not exist** in the codebase. p3-002 creates them:
    - `tests/api/test_response_schema.py` (R-16)
    - `tests/api/test_explanation_shape.py` (R-17)
  
  p3-002 creates both at those paths. The calculator's `tests/features/calculator/test_response_schema.py` is a **different** test (p2-002's feature-local regression) and is not R-16's fixture.
- p3-002 produces concrete Python types.** A new module with `ChatRequest`, `MetadataEvent`, 
  `TokenEvent`, `PlanUpdatedEvent`, `ErrorEvent`, `DoneEvent`, and the three-level explanation 
  types. This module is what p3-004 imports. The schema types' location is a plan-stage decision (likely `SystemCode/remy/app/src/app/chat_contract.py` or a new package).
- on a loop-back: the archived review.rN.md or plan-review.rN.md (highest N)
  with findings routed to `plan`

## Output

- MUST follow template: [plan.md](../../../.sdd/templates/plan.md)
- docs/sdd/features/<id>/plan.md
- do NOT write `## Tasks` until plan review approves
- sdd.json — the CI check set must include the plan feature's source and test paths. If the feature
  adds or renames source/test files, update the check set in the same change.

## Procedure

1. `sdd.py gate plan <id>` must pass.
2. Read the code the feature changes before writing Files-to-touch, Design, or
   the fixture assignments. Write against what is actually there, not what the
   spec assumes.
   - Confirm `tests/api/test_response_schema.py` and `tests/api/test_explanation_shape.py` are absent; record the confirmation in the plan's `## Design §0`. These are the two files p3-002 creates.

3. Fill Approach (chosen + rejected alternative), Design, Files to touch.
   - The Files-to-touch section must name the two fixtures at the constitution's exact paths.
4. Constitution alignment: one line per relevant rule.
5. Test strategy: one row per AC. No AC untested.
6. Integration per interface: one row in `## Integration per interface` per
   interface the plan names (producer → consumer). Test runs the real code
   under test (dependencies may be mocked, the code under test may not), reads
   from the producer, asserts on the consumer. If it can't run in this
   environment, record the deferral in `## Revision notes` and `decisions.md`;
   don't omit the row. If there are genuinely no producer→consumer interfaces (single-file change),
   write 'None — single-component change.' Otherwise every producer→consumer edge gets a row.

    For p3-002, name at least these producer→consumer edges:
   - **p3-001's `TraceEnvelope` → the contract's input types** (the shapes the contract consumes).
   - **The contract's SSE event types → the serializer** (how the event payloads are produced).
   - **The contract's types → the two fixtures** (the fixtures assert against the contract's shapes).
   
   Additional edges the plan discovers are welcome; these three are required.

7. Risks & mitigations.
8. Scope check: one working context? If no , split.
9. Stop. Submit to plan review.
10. After APPROVE or APPROVE-WITH-NITS: append `## Tasks` (tests before the
    impl tasks they cover). Every AC has ≥1 test row (step 5) and ≥1 task; every interface row has
    ≥1 integration test row (step 6) and ≥1 task; every entry in `## Files to touch` has ≥1 task.
    The `sdd.json` check set must cover the feature's source and test paths (see the `sdd.json`
    section below).

## Do not

- Write `## Tasks` before approval.
- Edit spec.md, constitution.md, or any review artifact.
- Leave an AC uncovered by a task or test.
- Omit an interface row, or leave one without an integration test.
- Mock the code under test (dependencies yes, code under test no).
- Re-implement the consumer in a test.
