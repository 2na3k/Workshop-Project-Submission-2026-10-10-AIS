# Prompt — Review

Review for feature **p2-003-feasible-meal-plan-solving**

`<id>`: `p2-003-feasible-meal-plan-solving`

## Input
- [AGENTS.md](../../../AGENTS.md)
- [constitution.md](../../../docs/sdd/constitution.md)
- [spec.md](../../../docs/sdd/features/p2-003-feasible-meal-plan-solving/spec.md)
- [plan.md](../../../docs/sdd/features/p2-003-feasible-meal-plan-solving/plan.md)
- [ci-results.md](../../../docs/sdd/features/p2-003-feasible-meal-plan-solving/ci-results.md)
- git diff: `git diff feat/p2-002-cost-nutrition-calculation...
feat/p2-003-feasible-meal-plan-solving -- SystemCode/`

## Output
- MUST follow template: [review.md](../../../.sdd/templates/review.md)
- docs/sdd/features/<id>/review.md

## Role
Reviewer. Must not be the agent that implemented the change.

## Procedure
1. `sdd.py gate review <id>` must pass.
2. Confirm CI OVERALL is PASS or FAIL. Never review on INCONCLUSIVE.
3. Acceptance criteria: one row per AC — result + the specific test (name or
   file:line) that proves it.
4. Constitution compliance: rule by rule, explicit.
5. Plan adherence: note deviations.
6. Verdict: APPROVE | REVISE | REJECT.
7. Route every finding: implement | plan | spec | constitution.
   A finding routed to `constitution` cannot be resolved by editing code.

## Do not
- Review work you authored.
- Approve with CI FAIL.
- Resolve an upstream finding by editing code — route it and stop.
- Edit spec.md, plan.md, constitution.md, or the implementation.
