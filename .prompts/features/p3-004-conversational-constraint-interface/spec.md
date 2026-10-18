# Prompt — Spec

Spec for feature **p3-004-conversational-constraint-interface**

`<id>`: `p3-004-conversational-constraint-interface`

## Notes

**p3-004 is implementation.** Implement `POST /chat` in `remy/app` against p3-002's contract, fold on-demand cost into `/chat`, and land the A-006 recipe-level cost drop in `api`'s plan service. It does not redefine p3-002's schemas, p3-001's nodes, or p2's reasoning.

**Phase p2 closed with data-quality findings (DQ-1..DQ-7) tracked, not blocking.** p3-004 builds against whatever the plan produces; coverage compensation is out of scope.

## Input
- MUST read: [AGENTS.md](../../../AGENTS.md)
- [constitution.md](../../../docs/sdd/constitution.md) — v1.7. Note R-16's
  and R-17's named check paths and their full contracts (both clauses of
  R-16's check; R-17's two-response shape).
- [roadmap.md](../../../docs/sdd/roadmap.md) — phase p3; the
  data-coverage acknowledgment carried from p2.
- [A-006-r8-r10-cost-drop-deferral.md](../../../docs/amendments/A-006-r8-r10-cost-drop-deferral.md): recipe-level cost drop in api plan service consuming MISSING_PACKAGE_DATA; fixtures at SystemCode/remy/api/tests/features/plan/; asserts R-8/R-10 recipe-level.
- [A-007-fixture-path.md](../../../docs/amendments/A-007-fixture-path.md): R-16/R-17 fixture paths at SystemCode/remy/app/tests/api/<name>.
- Confirmed clarifications (log in ## Clarifications, do not re-litigate): A-006 layer = api plan 
  service; stateless per turn; reuse p3-001 Generate Response; DQ-1..DQ-7 accepted; D-a (cost folded into /chat using existing ChatResponseEnvelope shape); D-b (intent detection extends p3-001 extraction node output with optional cost_query field).
- [system_design_v3.md](../../../SystemCode/docs/system_design_v3.md)
- [neo4j_db_design.md](../../../SystemCode/docs/neo4j_db_design.md)
- [workflow_diagram.md](../../../SystemCode/remy/workflows/docs/workflow_diagram.md) — the five-stage flow p3-001 implements; p3-002 defines the response contract that surfaces its Outcome to the user.
- [API_doc.md](../../../SystemCode/remy/api/docs/API_doc.md) — §3 (`POST /api/v1/chat`) declares 
  the current chat surface's request shape and SSE event vocabulary.
  - The SSE stream carries only p3-002's event set. User payloads must exclude CHAT_FORBIDDEN_FIELDS; the trace_id references, never embeds, the trace (p3-002 C-1, C-3).
- `p2-001-constraint-evidence-filtering`:
    - [decisions.md](../../../docs/sdd/features/p2-001-constraint-evidence-filtering/decisions.md)
- `p2-002-cost-nutrition-calculation`:
    - [spec.md](../../../docs/sdd/features/p2-002-cost-nutrition-calculation/spec.md)
    - [decisions.md](../../../docs/sdd/features/p2-002-cost-nutrition-calculation/decisions.md)
    - [test_domain_cost.py](../../../SystemCode/remy/api/tests/features/calculator/test_domain_cost.py)
- `p2-003-feasible-meal-plan-solving`:
    - [spec.md](../../../docs/sdd/features/p2-003-feasible-meal-plan-solving/spec.md)
    - [decisions.md](../../../docs/sdd/features/p2-003-feasible-meal-plan-solving/decisions.md)
- `p3-001-workflow-recommendation-service`:
    - [spec.md](../../../docs/sdd/features/p3-001-workflow-recommendation-service/spec.md)
    - [decisions.md](../../../docs/sdd/features/p3-001-workflow-recommendation-service/decisions.md)
- `p3-002-explainable-response-contract`:
    - [spec.md](../../../docs/sdd/features/p3-002-explainable-response-contract/spec.md)
    - [decisions.md](../../../docs/sdd/features/p3-002-explainable-response-contract/decisions.md)
- [CHANGELOG.md](../../../docs/sdd/CHANGELOG.md)
- current codebase:
  - Meal plan API: [plan](../../../SystemCode/remy/api/src/api/features/plan)
  - Calculator API: [calculator](../../../SystemCode/remy/api/src/api/features/calculator)
  - App: [app](../../../SystemCode/remy/app)
  - Workflows: [workflows](../../../SystemCode/remy/workflows)
- on a loop-back: the archived review.rN.md (highest N) with findings routed to `spec`

## Output
- MUST follow template: [spec.md](../../../.sdd/templates/spec.md)
- docs/sdd/features/p3-004-conversational-constraint-interface/spec.md
- on clarify: update spec.md in place, log every answer in `## Clarifications`

## Procedure
1. `sdd.py gate specify <id>` must pass.
2. **Scope the surfaces.** p3-002 owns the *shape* of the chat surface, not
   its implementation.
   - In scope: /chat endpoint in remy/app; intent detection adding cost_query to the extraction output; on-demand cost for recipe and ingredient names via existing calculator/CostNutritionService; reuse of p3-001 Generate Response for safe re-expression; A-006 cost drop in api plan service; API_doc §3 plan_updated update; fixtures for the drop and the chat contract.
   - Out of scope: p3-002 contract redefinition; new SSE events; session store; judge/eval implementation; DQ compensation; web planner (p3-003).
3. Fill Summary, Traces to (G-n + phase entry), User-facing behavior.
4. Write acceptance criteria as Given/When/Then, numbered AC-1..AC-N.
   Each must be independently testable.
5. List edge cases & errors.
6. Non-goals: at least one bullet.
   - Session/state persistence (stateless per turn).
   - Redefining p3-002 schemas or adding SSE event types.
   - Re-deciding p2 reasoning or drop causes.
   - Compensating for DQ-1..DQ-7.
   - Web planner (p3-003).
   - Judge/eval implementation.
7. **Interfaces & dependencies.**
8. Open questions: blocking ones only.
9. Clarify with the human; log every answer under `## Clarifications` with
   answer, date, who. Check off the matching question. Log every clarification,
   consequential or not. Flag consequential ones for
   `../../../docs/sdd/features/p3-004-conversational-constraint-interface/decisions.md`
   at close. 
   - Pre-confirmed human decisions (the seven in Inherited obligations) must be logged as 
      clarifications on first write, not reopened.

## Do not
- Design, name files, or choose data structures.
- Resolve open questions without the human.
- Omit a clarification from `## Clarifications`.
- Edit plan.md, constitution.md, or any review artifact.
- Treat p2-002's or p2-003's *implementation* as authoritative for their own
  contracts — their specs are the source of truth; their code is the evidence
  that the specs were met.
