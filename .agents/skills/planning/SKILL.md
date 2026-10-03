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
5. Risks & mitigations, then the scope check — one working context? If no, split.
6. Stop here. Submit to plan review.
7. Only after APPROVE or APPROVE-WITH-NITS: append `## Tasks`, test tasks before
   the impl tasks they cover. Every AC must be covered by at least one task.
   The task list is hashed into `state.json` (`tasks_hash`) and is frozen for
   this loop.

## Do not
- Write `## Tasks` before plan review approves.
- Edit `spec.md`, `constitution.md`, or any review artifact.
- Leave an AC uncovered by a task or a test.
- Edit the `## Tasks` section after approval without a recorded loop-back.
