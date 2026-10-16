# Prompt — Implement

Implement for feature **p3-001-workflow-recommendation-service**

`<id>`: `p3-001-workflow-recommendation-service`

## Input
- MUST read: [AGENTS.md](../../../AGENTS.md)
- [constitution.md](../../../docs/sdd/constitution.md)
    - This spec is written against constitution v1.6 (amendments A-001..A-006 applied). If you encounter an archived copy that cites R-14's relaxation set as unclassified, R-8/R-10's recipe-level cost drop as p3-001's obligation, or a `nutrient_tolerance_pct` default other than 0, treat those as superseded.
- [spec.md](../../../docs/sdd/features/p3-001-workflow-recommendation-service/spec.md)
- [plan.md](../../../docs/sdd/features/p3-001-workflow-recommendation-service/plan.md)
- [system_design_v3.md](../../../SystemCode/docs/system_design_v3.md)
- [neo4j_db_design.md](../../../SystemCode/docs/neo4j_db_design.md)
- [workflow_diagram.md](../../../SystemCode/remy/workflows/docs/workflow_diagram.md) — the five-stage LangGraph flow that this feature implements.
- Findings: 
  - [data-prep-price-path.md](../../../docs/findings/data-prep-price-path.md)
- current codebase: [SystemCode](../../../SystemCode)
    - Meal plan API: [plan](../../../SystemCode/remy/api/src/api/features/plan)
    - Calculator API: [calculator](../../../SystemCode/remy/api/src/api/features/calculator)
    - Workflows (to be created): [workflows](../../../SystemCode/remy/workflows)
    - p3 is greenfield. No workflow, response-contract, web, or chat implementation exists in the codebase. The spec describes what p3-001 builds, not what it fixes. The input list's codebase reference is for p2's existing interfaces (which p3-001 consumes), not for a pre-existing p3 layer.
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
   - xfail handling. The trace-side R-16 assertion is xfail-marked with a reason referencing F-P3-1. Do not remove, weaken, or convert it to xpass. The CI output must show xfail for that test; if the CI treats xpass as failure (strict mode), leave the xfail and note the F-P3-1 dependency in the commit message.
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
