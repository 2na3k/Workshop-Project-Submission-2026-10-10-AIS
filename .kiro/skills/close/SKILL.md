---
name: sdd-close
description: Close a reviewed feature in the SDD flow. Use when the review verdict is APPROVE and the feature is ready to be recorded as done. Writes decisions, appends to the changelog, and finalizes state. Never edits spec, plan or review artifacts.
---

# sdd-close

## Inputs
`review.md` with `APPROVE`, spec clarifications, `state.json`, `plan.md`. On a phase close, all feature
reviews and decisions for the phase.

## Procedure
1. `python .sdd/scripts/sdd.py gate close <id>` must pass. Otherwise stop.
2. Write `decisions.md`: plan deviations, consequential clarifications (with date and who), overrides.
3. Append a `CHANGELOG.md` entry: feature id + name + date, what changed, ACs covered, link to
   `decisions.md`, breaking changes.
4. Update `state.json`: status `closed`, `review_verdict`, `updated_at`.
5. Bump `loop_count` if the feature took more than one implementation loop.

## Do not
- Edit `spec.md`, `plan.md`, or `review.md` at close.
- Record a clarification in `decisions.md` that is not also in `spec.md`.
- Mark closed without a passing review.
