# Prompt — Plan

## Input
- approved spec.md
- constitution.md
- AGENTS.md
- codebase and architecture
- on a loop-back: the archived review.rN.md or plan-review.rN.md (highest N)
  with findings routed to `plan`

## Output
- docs/sdd/features/<id>/plan.md
- do NOT write `## Tasks` until plan review approves

## Procedure
1. `sdd.py gate plan <id>` must pass.
2. Fill Approach (chosen + main rejected alternative, one line each), Design,
   Files to touch.
3. Constitution alignment: one line per relevant rule.
4. Test strategy: a row per AC. No AC untested.
5. Risks & mitigations.
6. Scope check: does this fit one working context? If no, split the feature.
7. Stop. Submit to plan review.
8. Only after APPROVE or APPROVE-WITH-NITS: append `## Tasks`, test tasks
   before the impl tasks they cover. Every AC must be covered by at least one
   task. Tasks are hashed into state.json (tasks_hash) and frozen for this loop.

## Do not
- Write `## Tasks` before plan review approves.
- Edit spec.md, constitution.md, or any review artifact.
- Leave an AC uncovered by a task or a test.
