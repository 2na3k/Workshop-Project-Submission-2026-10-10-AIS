# Prompt — Plan Review

Input:  spec.md, plan.md, constitution.md, AGENTS.md.
Output: docs/sdd/features/<id>/plan-review.md
Role:   reviewer. Must not be the agent that wrote the plan.

Check, with evidence: Spec coverage (every AC addressed), Test strategy
(every AC has a real test), Constitution alignment, Feasibility, Scope.

Verdict:
- APPROVE — Tasks may be added; plan is frozen for this loop.
- APPROVE-WITH-NITS — Tasks may be added; nits recorded, non-blocking.
- REVISE — Tasks must NOT be added. Route each finding to the owning artifact.

There is no automatic override. A REVISE blocks Tasks until the upstream
artifact is fixed and the plan is re-reviewed. A human may record an explicit
override in decisions.md — signed, timestamped, surfaced at Phase Review. The
override does not change the verdict; it documents proceeding against it.
