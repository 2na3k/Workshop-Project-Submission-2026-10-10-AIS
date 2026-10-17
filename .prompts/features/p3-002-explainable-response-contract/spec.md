# Prompt — Spec

Spec for feature **p3-002-explainable-response-contract**

`<id>`: `p3-002-explainable-response-contract`

## Notes

**p3-002 is a contract, not an implementation.** This feature defines the
user-facing response schemas — the request/response/SSE-event shapes — that the
conversational surface (p3-004) will implement against, and the two
constitution-named fixtures (R-16, R-17). It does not implement the `/chat`
endpoint, the SSE mechanism, or any workflow node. Those are p3-004's.

**Phase p2 closed with data-quality findings (DQ-1..DQ-7) tracked, not
blocking.** p3-002's conformance fixtures operate on the shape the workflow
produces; the plan's output quality is upstream.

## Input
- MUST read: [AGENTS.md](../../../AGENTS.md)
- [constitution.md](../../../docs/sdd/constitution.md) — v1.6. Note R-16's
  and R-17's named check paths and their full contracts (both clauses of
  R-16's check; R-17's two-response shape).
- [roadmap.md](../../../docs/sdd/roadmap.md) — phase p3; the
  data-coverage acknowledgment carried from p2.
- [system_design_v3.md](../../../SystemCode/docs/system_design_v3.md)
- [neo4j_db_design.md](../../../SystemCode/docs/neo4j_db_design.md)
- [workflow_diagram.md](../../../SystemCode/remy/workflows/docs/workflow_diagram.md) — the five-stage flow p3-001 implements; p3-002 defines the response contract that surfaces its Outcome to the user.
- [API_doc.md](../../../SystemCode/remy/api/docs/API_doc.md) — §3 (`POST /api/v1/chat`) declares 
  the current chat surface's request shape and SSE event vocabulary. p3-002 refines this into the contract; the doc is the current deployed shape, the spec is the source of truth.
- `p2-001-constraint-evidence-filtering`:
    - [decisions.md](../../../docs/sdd/features/p2-001-constraint-evidence-filtering/decisions.md)
- `p2-002-cost-nutrition-calculation`:
    - [spec.md](../../../docs/sdd/features/p2-002-cost-nutrition-calculation/spec.md)
    - [decisions.md](../../../docs/sdd/features/p2-002-cost-nutrition-calculation/decisions.md)
    - [test_response_schema.py](../../../SystemCode/remy/api/tests/features/calculator/test_response_schema.py) — the user-payload exclusion list p3-002's R-16 fixture mirrors.
- `p2-003-feasible-meal-plan-solving`:
    - [spec.md](../../../docs/sdd/features/p2-003-feasible-meal-plan-solving/spec.md)
    - [decisions.md](../../../docs/sdd/features/p2-003-feasible-meal-plan-solving/decisions.md)
- `p3-001-workflow-recommendation-service`:
    - [spec.md](../../../docs/sdd/features/p3-001-workflow-recommendation-service/spec.md)
    - [plan.md](../../../docs/sdd/features/p3-001-workflow-recommendation-service/plan.md)
    - [decisions.md](../../../docs/sdd/features/p3-001-workflow-recommendation-service/decisions.md)
    - [models.py](../../../SystemCode/remy/workflows/src/workflows/models.py) — `TraceEnvelope`, 
      `Outcome`, `PlanTraceView`, `ConstraintSet`.
    - [trace.py](../../../SystemCode/remy/workflows/src/workflows/trace.py) — the envelope's assembly.
- [CHANGELOG.md](../../../docs/sdd/CHANGELOG.md)
- current codebase:
  - Meal plan API: [plan](../../../SystemCode/remy/api/src/api/features/plan)
  - Calculator API: [calculator](../../../SystemCode/remy/api/src/api/features/calculator)
  - App: [app](../../../SystemCode/remy/app)
  - Workflows: [workflows](../../../SystemCode/remy/workflows)
- **The two constitution-named fixtures do not exist** in the codebase. p3-002 creates them:
    - `tests/api/test_response_schema.py` (R-16)
    - `tests/api/test_explanation_shape.py` (R-17)
- on a loop-back: the archived review.rN.md (highest N) with findings routed to `spec`

## Output
- MUST follow template: [spec.md](../../../.sdd/templates/spec.md)
- docs/sdd/features/p3-002-explainable-response-contract/spec.md
- on clarify: update spec.md in place, log every answer in `## Clarifications`

## Procedure
1. `sdd.py gate specify <id>` must pass.
2. **Scope the surfaces.** p3-002 owns the *shape* of the chat surface, not
   its implementation.
    - **In scope:** the `/chat` request schema; the SSE event schemas
      (`metadata`, `token`, `plan_updated`, `error`, `done`); the user-facing
      three-level explanation shape; the audit-provenance boundary; the two
      constitution-named fixtures `tests/api/test_response_schema.py` (R-16)
      and `tests/api/test_explanation_shape.py` (R-17); the judge/eval
      integration hooks.
    - **Out of scope:** the `/chat` endpoint implementation and SSE mechanics
      (p3-004); the workflow nodes (p3-001); the web planner (p3-003, separate
      effort); the judge/eval layer's own implementation.
    - State the endpoint-to-feature mapping explicitly (define vs. implement).
3. Fill Summary, Traces to (G-n + phase entry), User-facing behavior.
4. Write acceptance criteria as Given/When/Then, numbered AC-1..AC-N.
   Each must be independently testable.
5. List edge cases & errors.
6. Non-goals: at least one bullet.
    - Implementing the `/chat` endpoint or the SSE mechanism (p3-004 owns the
      implementation; p3-002 defines the schemas).
    - Implementing the workflow nodes (p3-001).
    - The web planner (p3-003, separate effort).
    - The judge/eval layer's implementation (p3-002 exposes the hooks; the
      judge is a later feature).
    - Cost/budget evaluation (p3-004, per A-006).
    - Re-deciding p2's reasoning: three-level outcomes and drop causes pass
      through unchanged.
7. **Interfaces & dependencies.**
    - **Input contract:** p3-001's `TraceEnvelope` (schema version, outcome,
      input, node executions, LLM invocations, embedded `PlanTraceView`) and
      `Outcome` (`plan | infeasible | failure`).
    - **Output contract:** the user-facing request schema for `/chat`; the SSE
      event schemas (`metadata`, `token`, `plan_updated`, `error`, `done`);
      the three-level explanation shape (plan / recipe / constraint with
      distinct drop causes); the audit-provenance boundary.
    - **Trace boundary:** the trace is not part of the user-facing payload
      (R-16). The judge/eval hooks expose a trace identifier and either embed
      or reference the trace so a downstream judge can assess the trajectory.
    - **Fixtures:** `tests/api/test_response_schema.py` (R-16) and
      `tests/api/test_explanation_shape.py` (R-17) are created by this feature
      at the constitution's named paths. The R-16 fixture asserts both
      clauses: user-payload exclusion and trace-side retention.
    - **Dependency (F-P3-1):** R-16's trace-side clause requires
      `confidence`/`source_snapshot_id`/`mapping_version` to reach the trace
      via `OfferRef` and `PlanTrace`. The fix is a p2-002 reopen (extend
      `OfferRef`) plus a p2-003 propagation. If the reopen hasn't landed when
      p3-002's fixture is written, the trace-side clause is `xfail` with a
      reason referencing F-P3-1; the user-payload clause passes regardless.
    - **Judge/eval integration hooks:** the response stream exposes the fields a future 
      judge/eval layer will need: a stable identifier correlating the response with its trace; the trace boundary (embedded or referenced); and the Generate Response node's structured references. No judge/eval API surface is planned in the current roadmap. p3-002 defines the hooks so a later feature can consume them without a contract change; it does not define endpoints, storage, or metrics.
8. Open questions: blocking ones only.
9. Clarify with the human; log every answer under `## Clarifications` with
   answer, date, who. Check off the matching question. Log every clarification,
   consequential or not. Flag consequential ones for
   `../../../docs/sdd/features/p3-002-explainable-response-contract/decisions.md`
   at close.

## Do not
- Design, name files, or choose data structures.
- Resolve open questions without the human.
- Omit a clarification from `## Clarifications`.
- Edit plan.md, constitution.md, or any review artifact.
- Treat p2-002's or p2-003's *implementation* as authoritative for their own
  contracts — their specs are the source of truth; their code is the evidence
  that the specs were met.
