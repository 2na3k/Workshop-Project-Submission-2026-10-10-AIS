---
name: sdd-specify
description: Write a feature spec in the SDD flow. Use when a feature is picked from an active phase and needs acceptance criteria, or when a review sends a feature back with route "spec". Produces testable Given/When/Then criteria and logs every clarification. Never designs or names files.
---

# sdd-specify

## Inputs
`roadmap.md`, `constitution.md`, `AGENTS.md`, current codebase, target phase.
Template: `.sdd/templates/spec.md`.
On a loop-back: the archived `review.rN.md` (highest N) listing findings routed `spec`.

## Procedure
1. `python .sdd/scripts/sdd.py gate specify <id>` must pass.
2. Fill Summary, Traces to (G-n + phase entry), User-facing behavior.
3. Write AC-1..AC-N as Given/When/Then. Each must be independently testable.
4. List edge cases & errors.
5. Non-goals: at least one bullet.
6. Open questions: blocking ones only.
7. Clarify with the human; log every answer under `## Clarifications` with answer,
   date, who. Check off the matching question. Log every clarification,
   consequential or not. Flag consequential ones for `decisions.md` at close.

## Do not
- Design, name files, or choose data structures.
- Resolve open questions without the human.
- Omit a clarification from `## Clarifications`.
- Edit `plan.md`, `constitution.md`, or any review artifact.
