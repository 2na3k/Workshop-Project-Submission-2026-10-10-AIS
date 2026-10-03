# Prompt — Implement

## Input
- AGENTS.md
- spec.md
- plan.md (including `## Tasks`)
- constitution.md
- codebase, tests
- on a loop-back: archived review.rN.md (highest N) with findings routed to `implement`

## Output
- src/…, tests/…
- plan.md checkbox state only

## Procedure
1. `sdd.py gate implement <id>` must pass (or the feature stage is `implement`).
2. Create or switch to branch `feat/<id>`.
3. Work Tasks in order. For each task: do exactly what it says, write the failing
   test first where the task says so, run the relevant tests, check the box in
   plan.md, commit as `T-n(AC-x): message`.
4. If you hit ambiguity, missing information, or a plan that cannot work: stop
   and report it (task id, what is unclear, what you would need). Do not edit
   spec or plan, and do not guess.
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
