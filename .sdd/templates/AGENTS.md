# AGENTS.md

Read by every agent at every stage. Persistent instruction layer.

## Operating principles

- The project's binding rules are in `docs/sdd/constitution.md`. Read it before
  producing or reviewing any artifact. It overrides convenience.
- `docs/sdd/roadmap.md` is context, not law. The constitution is law.
- Follow the artifact ownership table in `docs/workflow.md`. **Only the owner of a
  stage may write that stage's artifact.** Do not edit another stage's output.
- `ci-results.md`, `state.json`, and `*-collisions.md` are machine-generated.
  Never hand-edit them.
- During Implement: execute the Tasks as written. Do not change task wording,
  order, or scope, and do not redefine the Plan. If the Plan is wrong, stop and
  route a finding upstream.
- Every agent stage that produces or reviews an artifact takes this file as input.

## Pointers

- Binding rules: `docs/sdd/constitution.md`
- Current plan of record: `docs/sdd/roadmap.md`
- Change history of the roadmap: `docs/sdd/roadmap-log.md`

## Project tooling

- test:      `<command>`
- lint:      `<command>`
- typecheck: `<command>`
