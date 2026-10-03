---
name: sdd-close
description: Close a reviewed feature in the SDD flow. Use when the review verdict is APPROVE and the feature is ready to be recorded as done. Writes decisions, appends to the changelog, and finalizes state. Never edits spec, plan or review artifacts.
---

# sdd-close

## Inputs
`review.md` with `APPROVE`, spec clarifications, `plan.md`, `state.json`.
Templates: `.sdd/templates/decisions.md`, `.sdd/templates/changelog-entry.md`.

## Procedure
1. `python .sdd/scripts/sdd.py gate close <id>` must pass.
2. Write `decisions.md`. One `D-n` block per decision. Consequential
   clarifications recorded here. Overrides recorded here. If no deviations,
   write exactly: `No deviations from plan.`
3. Append a `CHANGELOG.md` entry from the template.
4. Update `state.json`: stage `closed`, `review_verdict`, `updated_at`. Bump
   `loops` if the feature took more than one implementation loop.

## Do not
- Edit `spec.md`, `plan.md`, or `review.md` at close.
- Record a clarification in `decisions.md` that is not also in `spec.md`.
- Mark closed without a passing review.
