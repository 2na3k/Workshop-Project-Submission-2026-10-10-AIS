# Prompt — Close

Close for feature **p2-003-feasible-meal-plan-solving**

`<id>`: `p2-003-feasible-meal-plan-solving`

## Input
- [review.md](../../../docs/sdd/features/p2-003-feasible-meal-plan-solving/review.md)
- [spec.md](../../../docs/sdd/features/p2-003-feasible-meal-plan-solving/spec.md)
- [plan.md](../../../docs/sdd/features/p2-003-feasible-meal-plan-solving/plan.md)
- [state.json](../../../docs/sdd/features/p2-003-feasible-meal-plan-solving/state.json)
- [CHANGELOG.md](../../../docs/sdd/CHANGELOG.md)
- [AGENTS.md](../../../AGENTS.md)

## Output
- MUST follow template:
  - [changelog-entry.md](../../../.sdd/templates/changelog-entry.md)
  - [decisions.md](../../../.sdd/templates/decisions.md)
- docs/sdd/features/<id>/decisions.md
- append entry to CHANGELOG.md
- update state.json to stage `closed`

## Procedure
1. `sdd.py gate close <id>` must pass.
2. decisions.md: one D-n block per decision (Context, Decision, Alternatives,
   Affects, Source). Consequential clarifications recorded here. Overrides
   recorded here. If no deviations, write exactly:
   `No deviations from plan.`
3. Append a CHANGELOG entry per templates/changelog-entry.md.
4. Update state.json: stage `closed`, review_verdict, updated_at. Bump loops
   if this feature took more than one implementation loop.

## Do not
- Edit spec.md, plan.md, or review.md at close.
- Record a clarification in decisions.md that is not also in spec.md.
- Mark closed without a passing review.
