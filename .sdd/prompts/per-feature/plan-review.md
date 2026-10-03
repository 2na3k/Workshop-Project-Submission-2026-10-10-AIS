# Prompt — Plan Review

## Input
- spec.md
- plan.md
- constitution.md
- AGENTS.md

## Output
- docs/sdd/features/<id>/plan-review.md

## Role
Reviewer. Must not be the agent that wrote the plan.

## Procedure
1. Check, with evidence, each of: Spec coverage, Test strategy, Constitution
   alignment, Feasibility, Scope.
2. Verdict:
    - APPROVE — Tasks may be added. Plan frozen for this loop.
    - REVISE — Tasks must NOT be added. Route each finding to the owning artifact.
    - REJECT — The plan is not fixable by revision; the spec or constitution
      needs rework first. Route all findings upward.
3. Route every finding to: plan | spec | constitution.
4. There is no automatic override. A REVISE or REJECT blocks Tasks until the
   upstream artifact is fixed and the plan is re-reviewed. A human may record an
   explicit override in `decisions.md`, signed and timestamped, surfaced at
   phase review. The override does not change the verdict.

## Do not
- Add Tasks yourself.
- Review a plan you wrote.
- Resolve a finding by editing the plan when it routes to spec or constitution.
