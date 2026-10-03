# Prompt — Phase Review

Input:  completed phase, all feature reviews and decisions.
Output: docs/sdd/phase-reviews/<phase>.md
Role:   human + roadmap agent.

Verify exit criteria are met. Summarize what shipped, what the decisions say,
loop counts per feature, and proposed changes. Record human sign-off.

If the phase revealed a systemic rule that should bind future work, escalate to
an amendment proposal — do not patch the constitution directly.

Retro learnings go in retros/<phase>.md, not here. This file is a sign-off
record and should not be edited after approval.
