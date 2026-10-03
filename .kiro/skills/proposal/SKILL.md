---
name: sdd-propose
description: Distill project documents into a proposal in the SDD flow. Use when a project has input documents (briefs, tickets, architecture notes, research) but no docs/sdd/proposal.md yet, or when the problem statement needs to be re-derived. Produces goals, non-goals, constraints and source pointers. Never designs or writes acceptance criteria.
---

# sdd-propose

## Inputs
One or more project documents supplied by the human: briefs, tickets, meeting
notes, architecture docs, research, existing code. Plus `AGENTS.md`.

## Procedure
1. `python .sdd/scripts/sdd.py gate constitution <project>` is not applicable —
   this stage precedes the constitution. Skip the gate.
2. Confirm `docs/sdd/proposal.md` does not already exist. If it does, stop and
   ask the human whether to replace or amend it.
3. Read every input document end to end.
4. Extract statements bearing on: problem, goals, non-goals, constraints.
   Ignore background, history, marketing, implementation detail.
5. Rewrite each in your own words, concisely. Merge duplicates. Preserve
   conflicts rather than resolving them.
6. Attach a source pointer (filename, URL, ticket id) to every Goal, Non-goal,
   and Constraint.
7. Number Goals G-1, G-2, …
8. List every input under `## Source material`.
9. Mark missing critical information as `<UNRESOLVED: ...>` and flag it.
10. Write `docs/sdd/proposal.md` and hand it to the human for approval.

## Do not
- Design, name files, or propose components.
- Write acceptance criteria or requirements — that is the Spec stage.
- Resolve contradictions between source documents.
- Include a Goal, Non-goal, or Constraint without a source pointer.
- Pad the document. One page is the target; over one page usually means a spec
  is trying to escape.
- Proceed to the constitution stage before the human approves the proposal.
