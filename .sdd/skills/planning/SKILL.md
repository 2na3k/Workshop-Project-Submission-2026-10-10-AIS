---
name: sdd-plan
description: Write a feature plan and add tasks in the SDD flow. Use when a spec is approved and clarified, or when a review sends a feature back with route "plan". Produces approach, design, test strategy and tasks. Tasks are added only after plan review approves; never writes before that.
---

# sdd-plan

## Inputs
Approved `spec.md`, `constitution.md`, `AGENTS.md`, codebase, architecture.
Template: `.sdd/templates/plan.md`.
On a loop-back: the archived `review.rN.md` or `plan-review.rN.md` (highest N)
listing findings routed `plan`.

## Procedure
1. `python .sdd/scripts/sdd.py gate plan <id>` must pass.
2. Fill Approach (chosen + main rejected alternative, one line each), Design,
   Files to touch.
3. Constitution alignment: one line per relevant rule.
4. Test strategy: one row per AC. No AC untested.
5. **Integration per interface.** For every interface the plan names — a
   boundary between two artifacts, two packages, or two processes — add a
   row to `## Integration per interface` for a test that exercises the full
   path from producer to consumer. The test runs the real code under test
   (dependencies may be mocked, the code under test may not), reads from the
   real producer, and asserts on the real consumer. If the interface cannot
   be exercised end to end in this environment, record the deferral in
   `## Revision notes` and the feature's `decisions.md`; do not omit the row.
   If the plan names no interfaces, write "None — single-component change."
6. Risks & mitigations, then the scope check — one working context? If no, split.
7. Stop here. Submit to plan review.
8. Only after APPROVE or APPROVE-WITH-NITS: append `## Tasks`, test tasks before
   the impl tasks they cover. Every AC must be covered by at least one task,
   and every interface row must be covered by at least one task. The task list
   is hashed into `state.json` (`tasks_hash`) and is frozen for this loop.

## Do not
- Write `## Tasks` before plan review approves.
- Edit `spec.md`, `constitution.md`, or any review artifact.
- Leave an AC uncovered by a task or a test.
- Leave an interface uncovered by an integration test, or silently omit an
  interface that the plan names.
- Mock the code under test in an integration test (mock its dependencies if
  needed; the code under test runs for real).
- Re-implement the consumer in the test (the test runs the real consumer, or
  it's a deferral).
- Edit the `## Tasks` section after approval without a recorded loop-back.
