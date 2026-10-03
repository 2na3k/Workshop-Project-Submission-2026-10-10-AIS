---
name: sdd-review
description: Review a completed implementation in the SDD flow. Use when CI has produced a conclusive result for a feature, or when a plan needs a pre-implementation review. Produces a verdict and routes each finding to the artifact that owns it. Never reviews work it authored and never edits code.
---

# sdd-review

## Inputs
`spec.md`, `plan.md`, `ci-results.md`, `git diff`, tests, `AGENTS.md`, `constitution.md`. For plan review:
`spec.md`, `plan.md`, `constitution.md`, `AGENTS.md` (no diff or CI yet).

## Procedure
1. `python .sdd/scripts/sdd.py gate review <id>` must pass. Otherwise stop.
2. Confirm CI `OVERALL` is `PASS` or `FAIL` — never review on `INCONCLUSIVE`.
3. One row per AC: result plus the specific test that proves it.
4. Check constitution compliance explicitly, rule by rule.
5. Check plan adherence; note deviations.
6. Verdict `APPROVE` or `REVISE`. Route every finding to its owning artifact:
   `F-n → implement | plan | spec | constitution`.
7. Write `review.md` (or `plan-review.md` for a plan review).

## Do not
- Review work you authored.
- Approve with CI `FAIL`.
- Resolve an upstream finding by editing code — route it and stop.
- Edit `spec.md`, `plan.md`, `constitution.md`, or the implementation.
