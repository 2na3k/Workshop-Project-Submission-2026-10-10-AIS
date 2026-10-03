# Prompt — Amendment

## Input
- phase review, retro, or a finding routed to `constitution`
- current constitution.md

## Output
- docs/sdd/amendments/A-<date>-<slug>.md
- on approval: edit constitution.md in place, increment Version

## Role
Constitution agent proposes; human approves.

## Procedure
1. Fill Trigger, Current rule(s), Proposed change (exact text including the
   Check: line), Impact (in-flight and completed features to re-check),
   Version bump.
2. Wait for human decision.
3. On approval: edit constitution.md in place, increment Version, mark the
   amendment `approved`.
4. Impacted features are re-checked against the new rule; the check is recorded
   in the phase review.

## Do not
- Edit constitution.md without an approved amendment.
- Delete the amendment file after approval — it is the changelog.
- Change multiple unrelated rules in one amendment.
