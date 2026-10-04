# Prompt — Implement

Implement for feature **p1-002-provenance-graph-model**

`<id>`: `p1-002-provenance-graph-model`

## Input
- [AGENTS.md](../../../AGENTS.md)
- [spec.md](../../../docs/sdd/features/p1-002-provenance-graph-model/spec.md)
- [plan.md](../../../docs/sdd/features/p1-002-provenance-graph-model/plan.md)
- [constitution.md](../../../docs/sdd/constitution.md)
- current codebase: [SystemCode](../../../SystemCode)
- [neo4j_db_design.md](../../../SystemCode/docs/neo4j_db_design.md)
- [system_design_v3.md](../../../SystemCode/docs/system_design_v3.md)
- on a loop-back: archived review.rN.md (highest N) with findings routed to `implement`
- Integration tests connect to a cloud Neo4j instance via p1-001b's
  `neo4j_driver` fixture, which reads `NEO4J_TEST_URI`,
  `NEO4J_TEST_USERNAME`, and `NEO4J_TEST_PASSWORD` from the environment or a
  gitignored `.env.test`. The implement agent does not need to read or handle
  these values. Locally, integration tests skip when the variables are absent;
  under CI, they fail (per p1-001b's D-2).

## Output
- src/…, tests/…
- plan.md checkbox state only

## Procedure
1. `sdd.py gate implement <id>` must pass.
2. Create or switch to branch `feat/<id>`.
3. Work Tasks in order. For each task: do exactly what it says, write the failing
   test first where the task says so, run the relevant tests, check the box in
   plan.md, commit as `T-n(AC-x): message`.
4. If you hit ambiguity, missing information, or a plan that cannot work: stop
   and report it (task id, what is unclear, what you would need). Do not edit
   spec or plan, and do not guess.
5. When all tasks are checked: run `sdd.py ci <id>`. If it fails, fix and rerun.
   Never edit ci-results.md.
6. Run `sdd.py gate implement <id> --advance`, then hand the diff to review.

## On a loop-back
Fix only the findings routed `implement`. The loop counter has already been
incremented; at the cap the human takes over. Do not start another iteration
yourself.

## Do not
- Edit spec.md, plan.md (beyond tick state), constitution.md, review.md,
  plan-review.md.
- Change task wording, order, or scope; add or remove tasks; redefine the plan.
- Weaken or delete tests to get green.
- Add dependencies, refactors, or features outside the tasks.
- Report success without CI output.
