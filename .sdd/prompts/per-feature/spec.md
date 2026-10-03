# Prompt — Spec

## Input
- roadmap.md (target phase, feature slot)
- constitution.md
- AGENTS.md
- current codebase
- on a loop-back: the archived review.rN.md (highest N) with findings routed to `spec`

## Output
- docs/sdd/features/<id>/spec.md
- on clarify: update spec.md in place, log every answer in `## Clarifications`

## Procedure
1. `sdd.py gate specify <id>` must pass.
2. Fill Summary, Traces to (G-n + phase entry), User-facing behavior.
3. Write acceptance criteria as Given/When/Then, numbered AC-1..AC-N.
   Each must be independently testable.
4. List edge cases & errors.
5. Non-goals: at least one bullet.
6. Interfaces & dependencies.
7. Open questions: blocking ones only.
8. Clarify with the human; log every answer under `## Clarifications` with
   answer, date, who. Check off the matching question. Log every clarification,
   consequential or not. Flag consequential ones for `decisions.md` at close.

## Do not
- Design, name files, or choose data structures.
- Resolve open questions without the human.
- Omit a clarification from `## Clarifications`.
- Edit plan.md, constitution.md, or any review artifact.
