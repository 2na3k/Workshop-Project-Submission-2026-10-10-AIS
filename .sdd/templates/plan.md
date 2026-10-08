 Plan - <title>

## Approach
<!-- chosen approach + main rejected alternative, one line each -->

## Design

## Files to touch

## Constitution alignment
<!-- R-n -> how satisfied. One line per relevant rule. -->

## Test strategy

| AC | Test type | Test location / name | Notes |
|---|---|---|---|

## Integration per interface
<!-- Every interface this plan names — a boundary between two artifacts,
     two packages, or two processes — must have at least one test that
     exercises the full path from producer to consumer, not each side in
     isolation. The test runs the real code, reads from the producer, and
     asserts on the consumer.
     If the interface cannot be exercised end to end in this environment
     (external dependency, missing fixture, unavailable service), say so
     here and record the deferral in the plan's Revision notes and the
     feature's decisions.md. Do not omit the row.
     If the plan names no interfaces, write: "None — single-component change." -->

| Interface (producer → consumer) | Test type | Test location / name | Notes |
|---|---|---|---|

## Risks & mitigations

## Scope check
Fits one working context: yes | no

## Revision notes
<!-- F-n -> what changed -->

## Tasks
<!-- Added only after plan review returns APPROVE or APPROVE-WITH-NITS.
     Tasks are hashed into state.json (tasks_hash) and are frozen for this
     implementation loop. Do not edit after approval without a loop-back. -->

### Group 1 - Task Group short description

- [ ] **T-1** Write failing tests for AC-1, AC-2
  - Type: test
  - Covers: AC-1, AC-2
  - Files:
  - Done when:
- [ ] **T-2** …
  - Type: impl
  - Covers:
  - Files:
  - Done when:

### Group 2 - Task Group short description

- [ ] **T-3** Write failing tests for AC-1, AC-2
  - Type: test
  - Covers: AC-1, AC-2
  - Files:
  - Done when:
- [ ] **T-4** …
  - Type: impl
  - Covers:
  - Files:
  - Done when:
