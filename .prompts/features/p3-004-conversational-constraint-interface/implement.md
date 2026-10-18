# Prompt — Implement

Implement for feature **p3-004-conversational-constraint-interface**

`<id>`: `p3-004-conversational-constraint-interface`

## Input
- MUST read: [AGENTS.md](../../../AGENTS.md)
- [constitution.md](../../../docs/sdd/constitution.md) — v1.7. Note R-16's
  and R-17's named check paths and their full contracts (both clauses of
  R-16's check; R-17's two-response shape).
- [spec.md](../../../docs/sdd/features/p3-004-conversational-constraint-interface/spec.md) 
- Amendments: [amendments](../../../docs/amendments)
  - [A-006-r8-r10-cost-drop-deferral.md](../../../docs/amendments/A-006-r8-r10-cost-drop-deferral.md): recipe-level cost drop in api plan service consuming MISSING_PACKAGE_DATA; fixtures at SystemCode/remy/api/tests/features/plan/; asserts R-8/R-10 recipe-level.
  - [A-007-fixture-path.md](../../../docs/amendments/A-007-fixture-path.md): R-16/R-17 fixture paths at SystemCode/remy/app/tests/api/<name>.
  - Read spec ## Clarifications (C-1..C-7 confirmed) and plan ## Revision notes (r1→r2 findings F-1..F-4 resolved; r2 is frozen).
- [plan.md](../../../docs/sdd/features/p3-004-conversational-constraint-interface/plan.md)
- [system_design_v3.md](../../../SystemCode/docs/system_design_v3.md)
- [neo4j_db_design.md](../../../SystemCode/docs/neo4j_db_design.md)
- [workflow_diagram.md](../../../SystemCode/remy/workflows/docs/workflow_diagram.md) — the five-stage flow p3-001 implements; p3-002 defines the response contract that surfaces its Outcome to the user.
- Findings:
  - [data-prep-price-path.md](../../../docs/findings/data-prep-price-path.md)
- current codebase:
    - Meal plan API: [plan](../../../SystemCode/remy/api/src/api/features/plan)
    - Calculator API: [calculator](../../../SystemCode/remy/api/src/api/features/calculator)
    - App: [app](../../../SystemCode/remy/app)
    - Workflows: [workflows](../../../SystemCode/remy/workflows)
      - [models.py](../../../SystemCode/remy/workflows/src/workflows/models.py) —
                  `TraceEnvelope`, `Outcome`, `PlanTraceView`, `ConstraintSet`.
      - [trace.py](../../../SystemCode/remy/workflows/src/workflows/trace.py) —
                  the envelope's assembly.
      - Extract Constraints node (the `cost_query` field's home; see C-6).
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
    - The plan's F-5(a)–(d) verify-on-touch items are expected drift candidates — verify and record as BD-n entries if the real code differs, don't silently adapt.
    - T-13's fixture wires real PlanServiceAdapter + real PlanService; faking the port there is not permitted (verdict fold-forward). Record as a spec deviation if it can't be wired.
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
