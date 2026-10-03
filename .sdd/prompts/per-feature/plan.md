# Prompt — Plan

Input:  approved spec.md, constitution.md, AGENTS.md, codebase, architecture.
Output: docs/sdd/features/<id>/plan.md

Fill: Approach, Design, Files to touch, Constitution alignment (one line per
relevant rule), Test strategy (a row per AC — no AC may be untested), Risks &
mitigations, Scope check.

Scope check answers one question: does this fit a single working context?
If no, split the feature.

Do **not** write Tasks. Tasks are added only after Plan Review approves.

Never edit spec.md from this stage. If the spec is wrong, stop and route it.
