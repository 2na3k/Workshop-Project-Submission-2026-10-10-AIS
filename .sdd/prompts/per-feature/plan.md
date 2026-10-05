# Prompt — Plan

## Input
- approved spec.md
- constitution.md
- AGENTS.md
- codebase and architecture
- on a loop-back: the archived review.rN.md or plan-review.rN.md (highest N)
  with findings routed to `plan`

## Output
- docs/sdd/features/<id>/plan.md
- do NOT write `## Tasks` until plan review approves

## Procedure
1. `sdd.py gate plan <id>` must pass.
2. Read the code the feature changes before writing Files-to-touch, Design, or
   the fixture assignments. Write against what is actually there, not what the
   spec assumes.
3. Fill Approach (chosen + rejected alternative), Design, Files to touch.
4. Constitution alignment: one line per relevant rule.
5. Test strategy: one row per AC. No AC untested.
6. Integration per interface: one row in `## Integration per interface` per
   interface the plan names (producer → consumer). Test runs the real code
   under test (dependencies may be mocked, the code under test may not), reads
   from the producer, asserts on the consumer. If it can't run in this
   environment, record the deferral in `## Revision notes` and `decisions.md`;
   don't omit the row. No interfaces → write "None — single-component change."
7. Risks & mitigations.
8. Scope check: one working context? If no, split.
9. Stop. Submit to plan review.
10. After APPROVE or APPROVE-WITH-NITS: append `## Tasks` (tests before the
    impl tasks they cover). Every AC and every interface row needs ≥1 task.
    Tasks are hashed into state.json (tasks_hash) and frozen.

## Do not
- Write `## Tasks` before approval.
- Edit spec.md, constitution.md, or any review artifact.
- Leave an AC uncovered by a task or test.
- Omit an interface row, or leave one without an integration test.
- Mock the code under test (dependencies yes, code under test no).
- Re-implement the consumer in a test.
