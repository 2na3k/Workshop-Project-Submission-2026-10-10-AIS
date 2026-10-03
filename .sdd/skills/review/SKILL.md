---
name: sdd-review
description: Review a completed implementation or a plan in the SDD flow. Use when CI has produced a conclusive result for a feature, or when a plan needs a pre-implementation review. Produces a verdict and routes each finding to the artifact that owns it. Never reviews work it authored and never edits code.
---

# sdd-review

## Inputs
Implementation review: `spec.md`, `plan.md`, `ci-results.md`, `git diff`, tests,
`AGENTS.md`, `constitution.md`. Template: `.sdd/templates/review.md`.
Plan review: `spec.md`, `plan.md`, `constitution.md`, `AGENTS.md` (no diff or CI).
Template: `.sdd/templates/plan-review.md`.

## Procedure
1. `python .sdd/scripts/sdd.py gate review <id>` must pass.
2. Confirm CI OVERALL is PASS or FAIL. Never review on INCONCLUSIVE.
3. One row per AC: result plus the specific test (name or file:line) proving it.
4. Constitution compliance, rule by rule.
5. Plan adherence; note deviations.
6. Verdict: APPROVE | REVISE | REJECT.
7. Route every finding to its owning artifact: implement | plan | spec | constitution.
8. Write `review.md` (or `plan-review.md`).

## Do not
- Review work you authored.
- Approve with CI FAIL.
- Resolve an upstream finding by editing code — route it and stop.
- Edit `spec.md`, `plan.md`, `constitution.md`, or the implementation.
