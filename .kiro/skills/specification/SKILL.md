---
name: sdd-specify
description: Write a feature spec in the SDD flow. Use when a feature is picked from an active phase and needs acceptance criteria, or when a review sends a feature back with route "spec". Produces testable Given/When/Then criteria and logs every clarification. Never designs or names files.
---

# sdd-specify

## Inputs
`roadmap.md`, `constitution.md`, `AGENTS.md`, current codebase, target phase. On a loop-back also the
archived `review.rN.md` (highest N) listing findings routed `spec`.

## Procedure
1. `python .sdd/scripts/sdd.py gate specify <id>` must pass. Otherwise stop.
2. Summarize the feature; trace to goal and phase/feature id.
3. Write AC-1..n as Given/When/Then. Each must be independently testable.
4. List blocking open questions under `## Open questions`.
5. Clarify with the human; log every answer under `## Clarifications` with answer, date and who.
   Check off the matching question. Log every clarification, consequential or not.
6. Flag consequential clarifications for `decisions.md` at close.

## Do not
- Design, name files, or choose data structures.
- Resolve open questions without the human.
- Omit a clarification from `## Clarifications`.
- Edit `plan.md`, `constitution.md`, or any review artifact.
