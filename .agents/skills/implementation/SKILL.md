---
name: sdd-implement
description: Implement a feature from tasks in the SDD flow using a test-first loop. Use whenever a feature is at the implement stage, when an agent is asked to build or fix a feature that has a spec, plan and tasks, or after a review sends it back with route "implement". Runs CI to produce evidence and never edits specs or plans.
---

# sdd-implement

## Inputs
`spec.md`, `plan.md` (including `## Tasks`), `constitution.md`, `AGENTS.md`,
codebase, tests.
On a loop-back: the archived `review.rN.md` (highest N) listing findings routed
`implement`.

## Procedure
1. `python .sdd/scripts/sdd.py gate implement <id>` must pass.
2. Create or switch to branch `feat/<id>`.
3. Work tasks in order. For each task: do exactly what it says, write the failing
   test first where the task says so, run the relevant tests, check the box in
   `plan.md`, commit as `T-n(AC-x): message`.
4. If you hit ambiguity, missing information, or a plan that cannot work: stop and
   report it (task id, what is unclear, what you would need). Do not edit spec or
   plan, and do not guess.
5. When all tasks are checked: `python .sdd/scripts/sdd.py ci <id>`. If it fails,
   fix and rerun. Never edit `ci-results.md`.
6. `python .sdd/scripts/sdd.py gate implement <id> --advance`, then hand the diff
   to review.

## On a loop-back
Fix only the findings routed `implement`. `sdd.py loop <id> fail` has already
counted the iteration; at the cap it exits 2 and the human takes over. Do not
start another iteration yourself.

## Do not
- Edit `spec.md`, `plan.md` (beyond checkbox state), `constitution.md`,
  `review.md`, `plan-review.md`.
- Change task wording, order, or scope; add or remove tasks; redefine the plan.
- Weaken or delete tests to get green.
- Add dependencies, refactors, or features outside the tasks.
- Report success without CI output.
