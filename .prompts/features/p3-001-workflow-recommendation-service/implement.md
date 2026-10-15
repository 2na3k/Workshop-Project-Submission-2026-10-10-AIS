# Prompt — Implement

Implement for feature **p2-003-feasible-meal-plan-solving**

`<id>`: `p2-003-feasible-meal-plan-solving`

## Input
- MUST read: [AGENTS.md](../../../AGENTS.md)
- [constitution.md](../../../docs/sdd/constitution.md)
- [spec.md](../../../docs/sdd/features/p2-003-feasible-meal-plan-solving/spec.md)
- [plan.md](../../../docs/sdd/features/p2-003-feasible-meal-plan-solving/plan.md)
- [neo4j_db_design.md](../../../SystemCode/docs/neo4j_db_design.md)
- [system_design_v3.md](../../../SystemCode/docs/system_design_v3.md)
- Findings: 
  - [data-prep-price-path.md](../../../docs/findings/data-prep-price-path.md)
- current codebase: [SystemCode](../../../SystemCode)
    - Backend:  [api](../../../SystemCode/remy/api)
        - [fastapi_project_structure.md](../../../SystemCode/remy/api/docs/fastapi_project_structure.md)
        - calculate feature: [calculator](../../../SystemCode/remy/api/src/api/features/calculator)
        - plan feature: [plan](../../../SystemCode/remy/api/src/api/features/plan)
    - Domain: [domain](../../../SystemCode/remy/domain)
    - Workflow (LangGraph,...): [workflows](../../../SystemCode/remy/workflows)
- on a loop-back: archived review.rN.md (highest N) with findings routed to `implement`

## Output
- src/…, tests/…
- plan.md checkbox state only
- create or edit files as documented in plan's `## Tasks` section

## Procedure
1. `sdd.py gate implement <id>` must pass.
2. Create or switch to branch `feat/<id>`.
3. Work Tasks in order. For each task: do exactly what it says, write the failing
   test first where the task says so, run the relevant tests, check the box in
   plan.md, commit as `T-n(AC-x,AC-y,...): message`.
4. If you hit ambiguity, missing information, or a plan that cannot work — or if the code has changed since the plan's Design §0 baseline inventory was written — stop and report it. Record baseline drift as a `BD-n` entry in the plan's `## Revision notes` (original claim, actual state, date, commit). If the plan's design still holds, record only; if the design or spec contract must change, route a finding (`→ plan` or `→ spec`) and let the loop-back handle it. Do not edit spec, plan, or constitution beyond the `## Revision notes` entry, and do not guess.
5. When all tasks are checked: run `sdd.py ci <id>`. If it fails, fix and rerun.
   Never edit ci-results.md.
6. Run `sdd.py gate implement <id> --advance`, then hand the diff to review.

## On a loop-back
Fix only the findings routed `implement`. The loop counter has already been
incremented; at the cap the human takes over. Do not start another iteration
yourself.

## Do not
- Edit spec.md, plan.md (beyond tick state), constitution.md, review.md,
  plan-review.md.
- Change task wording, order, or scope; add or remove tasks; redefine the plan.
- Weaken or delete tests to get green.
- Add dependencies, refactors, or features outside the tasks.
- Report success without CI output.
