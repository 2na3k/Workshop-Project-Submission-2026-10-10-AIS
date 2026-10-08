# Prompt — Spec

Spec for feature **p2-003-feasible-meal-plan-solving**

`<id>`: `p2-003-feasible-meal-plan-solving`

## Input
- MUST read: [AGENTS.md](../../../AGENTS.md)
- [constitution.md](../../../docs/sdd/constitution.md)
  - This spec is written against constitution v1.4 (amendments A-001..A-004 applied 2026-10-07). If you encounter an archived copy that cites R-8's freshness threshold, R-9's per-recipe drop, or R-10's cost_basis_compatible, treat those as superseded.
- [roadmap.md](../../../docs/sdd/roadmap.md)
- `p2-001-constraint-evidence-filtering` artifact:
  - [decisions.md](../../../docs/sdd/features/p2-001-constraint-evidence-filtering/decisions.md)
  - [filtering.py](../../../SystemCode/remy/api/src/api/features/plan/filtering.py)
- `p2-002-cost-nutrition-calculation` artifact:
  - [spec.md](../../../docs/sdd/features/p2-002-cost-nutrition-calculation/spec.md)
  - [decisions.md](../../../docs/sdd/features/p2-002-cost-nutrition-calculation/decisions.md)
- [CHANGELOG.md](../../../docs/sdd/CHANGELOG.md)
- [neo4j_db_design.md](../../../SystemCode/docs/neo4j_db_design.md)
- [system_design_v3.md](../../../SystemCode/docs/system_design_v3.md)
- current codebase: [SystemCode](../../../SystemCode)
  - Meal plan API: [plan](../../../SystemCode/remy/api/src/api/features/plan)
- on a loop-back: the archived review.rN.md (highest N) with findings routed to `spec`

## Output
- MUST follow template: [spec.md](../../../.sdd/templates/spec.md)
- docs/sdd/features/p2-003-feasible-meal-plan-solving/spec.md
- on clarify: update spec.md in place, log every answer in `## Clarifications`

## Procedure
1. `sdd.py gate specify <id>` must pass.
2. Fill Summary, Traces to (G-n + phase entry), User-facing behavior.
3. Write acceptance criteria as Given/When/Then, numbered AC-1..AC-N.
   Each must be independently testable.
4. List edge cases & errors.
5. Non-goals: at least one bullet.
6. Interfaces & dependencies.
7. Open questions: blocking ones only.
8. Clarify with the human; log every answer under `## Clarifications` with
   answer, date, who. Check off the matching question. Log every clarification,
   consequential or not. Flag consequential ones for `../../../docs/sdd/features/p2-003-feasible-meal-plan-solving/decisions.md` at close.

## Do not
- Design, name files, or choose data structures.
- Resolve open questions without the human.
- Omit a clarification from `## Clarifications`.
- Edit plan.md, constitution.md, or any review artifact.
- Read p2-002's implementation as authoritative for its own contract — the spec is the source of 
  truth; the code is the evidence that it was met.
