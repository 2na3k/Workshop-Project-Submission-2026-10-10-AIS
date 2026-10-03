---
name: sdd-roadmap
description: Build or revise the roadmap and its phases in the SDD flow. Use after the constitution is approved, or whenever a phase is added, reordered or retired. Maps every goal to a delivering phase and logs every change append-only.
---

# sdd-roadmap

## Inputs
`proposal.md`, `constitution.md`, `AGENTS.md`, existing project state. On a revision, the current
`roadmap.md` and `roadmap-log.md`.

## Procedure
1. `python .sdd/scripts/sdd.py gate roadmap <project>` must pass. Otherwise stop.
2. Map every goal to exactly one delivering phase.
3. Order phases by dependency, then risk.
4. Give each phase Outcome, Goals served, Features, verifiable Exit criteria.
5. Name features `<phase>-<nnn>-<slug>`; keep each inside one working context.
6. Append a `roadmap-log.md` entry for every change, with the reason.

## Do not
- Leave a goal unmapped, or a phase without testable exit criteria.
- Rewrite `roadmap-log.md` history — it is append-only.
- Put feature-level design here.
