# Prompt — Spec

Spec for feature **p3-001-workflow-recommendation-service**

`<id>`: `p3-001-workflow-recommendation-service`

## Notes

**p3 is greenfield.** No workflow, response-contract, web, or chat implementation
exists in the codebase. This spec describes what p3-001 builds, not what it
fixes. The input list's codebase reference points at p2's interfaces (which
p3-001 consumes), not at a pre-existing p3 layer.

**This feature owns all five workflow stages.** The LangGraph workflow covers
constraint extraction, recipe discovery, food-concept resolution, filter/rank,
and response generation — the five nodes in `workflow_diagram.md`. The
conversational surface (p3-004) is the HTTP/SSE wrapper around this workflow;
the individual stages are p3-001's.

**Phase p2 closes with data-quality findings (DQ-1..DQ-7) tracked, not blocking.**
The plan's candidate pool is limited by the deployed graph's coverage. p3-001
consumes whatever the plan produces; the plan's output quality is upstream of
p3-001.

## Input
- MUST read: [AGENTS.md](../../../AGENTS.md)
- [constitution.md](../../../docs/sdd/constitution.md)
    - This spec is written against constitution v1.6 (amendments A-001..A-006 applied). If you encounter an archived copy that cites R-14's relaxation set as unclassified, R-8/R-10's recipe-level cost drop as p3-001's obligation, or a `nutrient_tolerance_pct` default other than 0, treat those as superseded.
- [roadmap.md](../../../docs/sdd/roadmap.md)
    - Read the phase p3 section, including the "data-coverage acknowledgment"
      clause carried from phase p2's exit criteria.
    - **p3-003-web-planner-experience is out of scope** for this SDD effort
      (frontend owned by a separate effort).
- [system_design_v3.md](../../../SystemCode/docs/system_design_v3.md)
- [neo4j_db_design.md](../../../SystemCode/docs/neo4j_db_design.md)
- [workflow_diagram.md](../../../SystemCode/remy/workflows/docs/workflow_diagram.md) — the five-stage LangGraph flow that this feature implements.
- `p2-001-constraint-evidence-filtering` artifact:
  - [decisions.md](../../../docs/sdd/features/p2-001-constraint-evidence-filtering/decisions.md)
  - [filtering.py](../../../SystemCode/remy/api/src/api/features/plan/filtering.py)
- `p2-002-cost-nutrition-calculation` artifact:
  - [spec.md](../../../docs/sdd/features/p2-002-cost-nutrition-calculation/spec.md)
  - [decisions.md](../../../docs/sdd/features/p2-002-cost-nutrition-calculation/decisions.md)
- `p2-003-feasible-meal-plan-solving` artifact:
    - [spec.md](../../../docs/sdd/features/p2-003-feasible-meal-plan-solving/spec.md)
    - [decisions.md](../../../docs/sdd/features/p2-003-feasible-meal-plan-solving/decisions.md)
- [CHANGELOG.md](../../../docs/sdd/CHANGELOG.md)
- current codebase: [SystemCode](../../../SystemCode)
  - Meal plan API: [plan](../../../SystemCode/remy/api/src/api/features/plan)
  - Calculator API: [calculator](../../../SystemCode/remy/api/src/api/features/calculator)
  - Workflows (to be created): [workflows](../../../SystemCode/remy/workflows)
  - p3 is greenfield. No workflow, response-contract, web, or chat implementation exists in the codebase. The spec describes what p3-001 builds, not what it fixes. The input list's codebase reference is for p2's existing interfaces (which p3-001 consumes), not for a pre-existing p3 layer.
- on a loop-back: the archived review.rN.md (highest N) with findings routed to `spec`

## Output
- MUST follow template: [spec.md](../../../.sdd/templates/spec.md)
- docs/sdd/features/p3-001-workflow-recommendation-service/spec.md
- on clarify: update spec.md in place, log every answer in `## Clarifications`

## Procedure
1. `sdd.py gate specify <id>` must pass.
2. **Scope the surfaces.** Name which API surfaces p3-001 owns and which are out
   of scope. At minimum:
    - **In scope:** the LangGraph workflow invoked by the chat endpoint
      (`POST /chat`, owned by p3-004) and its five stages.
    - **Out of scope:** `/verify-dietary` and `/recipes/{id}` (deprioritised);
      `/recommendations/cold-start` (deferred, not on the MVP critical path);
      p3-003's web planner (separate effort).
    - State the endpoint-to-feature mapping explicitly so the spec doesn't
      drift.
3. Fill Summary, Traces to (G-n + phase entry), User-facing behavior.
4. Write acceptance criteria as Given/When/Then, numbered AC-1..AC-N.
   Each must be independently testable.
5. List edge cases & errors.
6. Non-goals: at least one bullet. Non-goals must include:
    - Frontend work (p3-003, separate effort).
    - Cost/budget evaluation on the initial turn (follow-up only, per p3-004's
      A-006 obligation).
7. **Interfaces & dependencies.**
    - Name the input contract: how the workflow receives a user request and
      transforms it into p2-003's `PlanRequest`.
    - Name the output contract: what the workflow returns to its caller
      (result + trace).
    - **Name the trace boundary explicitly.** State whether p3-001 composes
      p2-002's `CalculationTrace` and p2-003's plan-level trace into a
      workflow-level trace, or introduces its own trace that references them.
      If the choice depends on p3-002's needs, state that and log it as an
      open question.
    - Name the p2-003 dependency: the workflow calls p2-003's plan path. Name
      which interface (public service method, endpoint, or internal call).
    - Name the LLM dependency: which LLM (local, e.g., Ollama) and for which
      stages (constraint extraction, response generation).
8. Open questions: blocking ones only.
9. Clarify with the human; log every answer under `## Clarifications` with
   answer, date, who. Check off the matching question. Log every clarification,
   consequential or not. Flag consequential ones for
   `../../../docs/sdd/features/p3-001-workflow-recommendation-service/decisions.md`
   at close.

## Do not
- Design, name files, or choose data structures.
- Resolve open questions without the human.
- Omit a clarification from `## Clarifications`.
- Edit plan.md, constitution.md, or any review artifact.
- Treat p2-002's or p2-003's *implementation* as authoritative for their own
  contracts — their specs are the source of truth; their code is the evidence
  that the specs were met.
- Assume the plan's output quality: p2-003's candidate pool is limited by the
  deployed graph's coverage (DQ-1..DQ-7). The workflow consumes whatever the
  plan produces.
- Add cost or budget to the initial-turn workflow: cost is a follow-up concern
  owned by p3-004 (per A-006).
