# Prompt — Proposal

Input:  a pile of project documents (briefs, tickets, architecture notes, meeting
notes, research, existing code) supplied by the human, plus AGENTS.md.
Output: docs/sdd/proposal.md

You are distilling documents into a proposal. A proposal is not a summary and
not a design doc. It is the smallest artifact that answers four questions:

1. What problem are we solving?
2. What outcomes do we want?
3. What are we explicitly not doing?
4. What constrains us?

## Procedure

1. Read every input document end to end before writing anything.
2. Extract only statements that bear on the four questions. Ignore background,
   history, marketing, and implementation detail.
3. Rewrite each extracted statement in your own words, concisely. Do not copy
   marketing language or restate the doc's structure.
4. Merge duplicates. If two documents disagree, keep both readings and note the
   conflict under Constraints (do not silently pick a winner).
5. Attach a source pointer to every Goal, Non-goal, and Constraint. The pointer
   is a filename, a URL, or a ticket id — something a human can open. No pointer
   means the statement is unsupported; either find one or drop the statement.
6. List the input documents under Source material.
7. If a critical piece of information is missing (e.g. no clear problem
   statement exists in any doc), write it as a bracketed placeholder
   `<UNRESOLVED: ...>` rather than inventing it, and flag it to the human.

## Output structure

# Proposal

## Problem
<one paragraph, no more>

## Goals
- G-1 <outcome>  (source: <pointer>)
- G-2 …

## Non-goals
- <what we are explicitly not doing>  (source: <pointer>)

## Constraints
- <technical, organisational, or regulatory limit>  (source: <pointer>)

## Open questions
- <anything the docs left ambiguous that blocks the constitution>

## Source material
- <doc 1>
- <doc 2>

## Rules

- Goals are outcomes, not activities. "Users stay logged in" — not "implement
  token refresh". If a statement reads like a task, it belongs in a plan, not
  a proposal.
- A Non-goal is not the absence of a goal. It is something a reader might
  reasonably expect to be in scope and is explicitly excluded.
- Constraints are external. "We only have two weeks" is a constraint;
  "we will use Redis" is a design decision and does not belong here.
- Every Goal must be testable in principle. If you cannot imagine a spec
  acceptance criterion that would falsify it, it is too vague.
- Number Goals G-1, G-2, … The constitution and specs will trace to these.

## Do not

- Do not design. No components, no APIs, no schemas, no file names.
- Do not enumerate requirements or acceptance criteria — that is the Spec stage.
- Do not resolve contradictions between documents. Surface them.
- Do not pad. A proposal over one page is almost always hiding a spec.
- Do not include anything without a source pointer unless it is marked
  `<UNRESOLVED: ...>`.

## Handoff

When done, hand the file to the human for approval. The constitution stage
reads this file and treats each Goal as something that must be traceable
through the roadmap, specs, plans, and reviews.
