---
name: sdd-plan
description: Write a feature plan and add tasks in the SDD flow. Use when a spec is approved and clarified, or when a review sends a feature back with route "plan". Produces approach, design, test strategy and tasks. Tasks are added only after plan review approves; never writes before that.
---

# sdd-plan

## Inputs
Approved `spec.md`, `constitution.md`, `AGENTS.md`, codebase, architecture. On a loop-back also the
archived `review.rN.md` or `plan-review.rN.md` (highest N) listing findings routed `plan`.

## Procedure
1. `python .sdd/scripts/sdd.py gate plan <id>` must pass. Otherwise stop.
2. Fill Approach, Design, Files to touch.
3. Constitution alignment: one line per relevant rule.
4. Test strategy: one row per AC. No AC untested.
5. Risks & mitigations, then the scope check — one working context? If no, split the feature.
6. Submit to plan review. Stop here.
7. Only after `APPROVE` or `APPROVE-WITH-NITS`: append `## Tasks`, test tasks before the impl tasks
   they cover. Every AC must be covered by at least one task.

## Do not
- Write `## Tasks` before plan review approves.
- Edit `spec.md`, `constitution.md`, or any review artifact.
- Leave an AC uncovered by a task or a test.
