# Prompt — Phase Review

## Input
- completed phase
- all feature reviews and decisions for the phase
- roadmap.md

## Output
- docs/sdd/phase-reviews/pN.md

## Role
Human with the roadmap agent.

## Procedure
1. Verify exit criteria are met, with evidence.
2. Summarize what shipped, what the decisions say.
3. Capture retro learnings: went well, went badly, loop counts per feature.
   Retros live inside this file under `## Retro`.
4. Proposed changes: roadmap re-plan, constitution amendment, or proposal change.
5. Record human sign-off.

## Escalation
If the phase revealed a systemic rule that should bind future work, escalate to
an amendment proposal. Do not patch the constitution directly.

## Do not
- Edit after sign-off — this is a sign-off record.
- Approve exit criteria that are not verifiably met.
