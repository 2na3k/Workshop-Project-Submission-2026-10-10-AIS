# Prompt — Close

Close for feature **p3-002-explainable-response-contract**

`<id>`: `p3-002-explainable-response-contract`

## Input
- [AGENTS.md](../../../AGENTS.md)
- [review.md](../../../docs/sdd/features/p3-002-explainable-response-contract/review.md)
- [spec.md](../../../docs/sdd/features/p3-002-explainable-response-contract/spec.md)
- [plan.md](../../../docs/sdd/features/p3-002-explainable-response-contract/plan.md)
- [state.json](../../../docs/sdd/features/p3-002-explainable-response-contract/state.json)
- [CHANGELOG.md](../../../docs/sdd/CHANGELOG.md)

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
