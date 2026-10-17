# Prompt — Implement

Implement for feature **p3-002-explainable-response-contract**

`<id>`: `p3-002-explainable-response-contract`

## Input
- MUST read: [AGENTS.md](../../../AGENTS.md)
- [constitution.md](../../../docs/sdd/constitution.md) — v1.7. Note R-16's
  and R-17's named check paths and their full contracts (both clauses of
  R-16's check; R-17's two-response shape).
- [spec.md](../../../docs/sdd/features/p3-002-explainable-response-contract/spec.md)
- [plan.md](../../../docs/sdd/features/p3-002-explainable-response-contract/plan.md)
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
        - [models.py](../../../SystemCode/remy/workflows/src/workflows/models.py) — `TraceEnvelope`,
          `Outcome`, `PlanTraceView`, `ConstraintSet`.
        - [trace.py](../../../SystemCode/remy/workflows/src/workflows/trace.py) — the envelope's assembly.
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
   - xfail handling. The R-16 trace-side test (test_trace_retains_audit_provenance) is marked @pytest.mark.xfail(strict=True, reason="F-P3-1: ..."). strict=True means an unexpectedly passing test fails the run. Leave the xfail marker untouched during this loop: the trace-side assertion cannot pass until F-P3-1 resolves (owned by p2-003), and removing the marker would either (a) hide the gap (if the test passes) or (b) fail the run (if the test fails without a marker). When F-P3-1 resolves — that is, when p2-003's reopen lands and PlanTraceView carries the provenance — remove the marker in the same change and let the test pass. In this loop, the CI output must show xfail for this test; no other verdict is acceptable.
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
