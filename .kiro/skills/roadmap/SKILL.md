---
name: sdd-roadmap
description: Build or revise the roadmap and its phases in the SDD flow. Use after the constitution is approved, or whenever a phase is added, reordered, or retired. Maps every goal to a delivering phase and logs every change append-only.
---

# sdd-roadmap

## Inputs
`proposal.md`, `constitution.md`, `AGENTS.md`, existing project state.
Template: `.sdd/templates/roadmap.md`.

## Procedure
1. `python .sdd/scripts/sdd.py gate roadmap <project>` must pass.
2. Map every goal to exactly one delivering phase.
3. Order phases by dependency, then risk.
4. Give each phase Outcome, Goals served, Features, verifiable Exit criteria,
   Risks & unknowns.
5. Populate the Feature order & shared contracts table. Shared contracts are
   what the collision check uses.
6. Name features `<phase>-<nnn>-<slug>`.
7. Append a `## Re-plan log` entry for every change, with the reason.

## Do not
- Leave a goal unmapped, or a phase without testable exit criteria.
- Rewrite `## Re-plan log` history — it is append-only.
- Put feature-level design here.
