# Workflow

## Flow

    proposal → constitution → roadmap(+phases) → spec → clarify → plan
      → plan-review → tasks → implement → ci → review → close
      → phase-review → retro → amendments
      ↺ any REVISE routes findings upstream and loops

## Ownership

| Stage | Owner | Input | Primary output |
|---|---|---|---|
| Proposal | Human | problem/context | `proposal.md` |
| Constitution | Constitution agent | proposal, AGENTS.md, source material, architecture | `constitution.md` |
| Roadmap + phases | Roadmap agent | proposal, constitution, AGENTS.md | `roadmap.md`, `roadmap-log.md` |
| Spec | Spec agent | roadmap, phase, constitution, AGENTS.md | `features/<id>/spec.md` |
| Clarify | Spec agent + Human | spec questions, AGENTS.md | updated `spec.md` |
| Plan | Plan agent | spec, codebase, constitution, AGENTS.md | `features/<id>/plan.md` |
| Plan Review | Plan reviewer | spec, plan, constitution, AGENTS.md | `plan-review.md` |
| Collision Check | `sdd.py` | all phase plans | `phase-reviews/pN-collisions.md` |
| Tasks | Plan agent | approved plan | `plan.md` `## Tasks` |
| Implement | Implementation agent | AGENTS.md, spec, plan, tasks, code | source + tests |
| CI | `sdd.py` | repository | `ci-results.md` |
| Review | Reviewer | diff, spec, plan, CI, AGENTS.md | `review.md` |
| Close | Implementation agent | approved implementation, review | `decisions.md`, `CHANGELOG.md`, `state.json` |
| Phase Review | Human + Roadmap agent | completed phase | `phase-reviews/pN.md` |
| Retro | Human + Roadmap agent | completed phase | `retros/pN.md` |
| Amendment | Constitution agent + Human | phase findings, retro | `amendments/A-*.md` + updated `constitution.md` |

Two structural rules: **the reviewer is never the author**, and **a stage may only
write its own artifact**.

## Verdict semantics

**Plan review**
- `APPROVE` — tasks may be added; plan frozen for this loop.
- `APPROVE-WITH-NITS` — tasks may be added; nits recorded, non-blocking.
- `REVISE` — tasks must not be added; findings route upstream. No automatic
  override. A human may record a signed, timestamped override in `decisions.md`
  surfacing at phase review. It documents proceeding against the verdict; it does
  not change the verdict.

**CI**
- `PASS` / `FAIL` / `INCONCLUSIVE`. Infra-caused failures are `INCONCLUSIVE`, not
  `FAIL`, so they trigger no review finding. `sdd.py` retries them up to a
  configurable limit.

**Review**
- `APPROVE` / `REVISE`. Findings route explicitly: `F-n → implement | plan | spec |
  constitution`. A finding routed to `constitution` cannot be resolved by editing
  code.

## Finding routing

    F-1 → implement      fix the code
    F-2 → plan           fix the plan, then re-review, then re-tasks
    F-3 → spec           fix the spec (clarify), then re-plan
    F-4 → constitution   amendment proposal, human approval

Routing upward invalidates downstream hashes. `sdd.py check` will refuse to
advance until the artifact is re-reviewed or restored.

## State & hashes

`state.json` records hashes of approved artifacts, so later edits are detectable.

- `spec_hash` — `spec.md` excluding `## Clarifications` (which grows in Clarify).
- `plan_hash` — `plan.md` excluding `## Tasks` and `## Revision notes`.
- `tasks_hash` — the `## Tasks` section only.

**Normalization**: strip trailing whitespace, collapse consecutive blank lines,
normalize line endings. Markdown structure is preserved.

Drift between a hash and the artifact is a **state violation**. `sdd.py check`
fails and the feature cannot advance until resolved by re-review or restore.

## Clarifications

Every clarification is recorded in `spec.md` under `## Clarifications` with the
answer, date, and who. Consequential clarifications — scope change, constitution
conflict, cross-feature impact — are *additionally* recorded in `decisions.md` at
Close. Never omit a clarification from the spec.

## Collision check

Before Tasks are approved for any feature in a phase, `sdd.py collision <phase>`
compares every feature's `## Files to touch` and `## Design`. Same file in two
features → `HIGH` → blocks Tasks approval until plans are amended or a human
records an override. Same identifier but no file overlap → `LOW` → informational.

## Amendments

An amendment is a proposal to change the constitution. `constitution.md` is edited
in place and its version increments; the amendment file is the durable record of
why and is never deleted. `constitution.md` keeps no changelog — `amendments/` is
the changelog.

## Constitution escalation

    Phase Review → amendment proposal → Constitution agent → Human approval
      → constitution.md updated, amendment marked approved

## Design principle

The kit has templates, prompts, skills, scripts, and examples. The project has
only the state it needs:

    proposal, constitution, roadmap (+ phases + log), specs, plans (+ tasks),
    reviews, machine evidence (CI, collisions), state (hashes + verdicts),
    decisions, phase reviews, retros, amendments, changelog

That keeps the SDD layer small while preserving approval boundaries, the audit
trail, and the loop-back semantics that keep it agile rather than waterfall.
