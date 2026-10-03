# Prompt — Tasks

Input:  plan.md with an APPROVE or APPROVE-WITH-NITS plan review.
Output: plan.md, `## Tasks` section appended.

Each task:
- [ ] **T-n** <imperative title>
  - Type: test | impl
  - Covers: AC-n
  - Files:
  - Done when: <observable condition>

Order test tasks before the impl tasks they cover. Every AC must be covered by
at least one task. Tasks are the last thing added to plan.md before Implement.

The approved task list is normalized and hashed into state.json as `tasks_hash`.
That hash is the anchor for detecting unauthorized task edits during Implement.

Do not add tasks when the plan review verdict is REVISE.
