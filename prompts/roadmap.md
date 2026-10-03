# Prompt — Roadmap

## Input
- [AGENTS.md](../AGENTS.md)
- [constitution.md](../docs/sdd/constitution.md)
- existing project state: [state.schema.json](../docs/state.schema.json)
- [proposal.md](../docs/sdd/proposal.md)
- source material: [final_proposal_1_v2.md](../final_proposal_1_v2.md)

## Output
- Template: [roadmap.md](../.sdd/templates/roadmap.md)
- docs/sdd/roadmap.md — roadmap and phases in one file
- append to docs/sdd/roadmap.md `## Re-plan log` for every change

## Procedure
1. Map every goal to exactly one delivering phase. Goal with no phase is a gap.
2. Order phases by dependency, then by risk.
3. For each phase, write: Outcome, Goals served, Features, Exit criteria, Risks.
    - Features are named `<phase>-<nnn>-<slug>`.
    - Exit criteria must be verifiable, not aspirational.
4. Populate the Feature order & shared contracts table. If two features in the
   same phase touch the same file or API surface, the shared-contract row must
   name the contract; the collision check will use this.
5. Later phases may be coarse until the preceding one is done.
6. Append a `## Re-plan log` entry for any change — phases added, reordered,
   retired — with the reason. Append-only.

## Do not
- Leave a goal unmapped, or a phase without testable exit criteria.
- Rewrite prior Re-plan log entries.
- Put feature-level design here.
