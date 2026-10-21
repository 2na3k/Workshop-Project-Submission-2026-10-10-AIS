# Amendment A-007 — R-16/R-17 named check paths

status: approved
Proposed by: (spec/plan owner)
Date: 2026-10-17

## Trigger
p3-002's plan review surfaced that R-16's and R-17's named check paths
(`tests/api/test_response_schema.py`, `tests/api/test_explanation_shape.py`)
have diverged from the deployed placement across three features: p2-002's F-D,
p3-001's BD-2a, and p3-002's plan. The divergence is structural: the contract
types the fixtures assert against live in `remy-app` (the only package the
`.importlinter` contracts permit to import both `api` and `workflows`), so the
fixtures must run where `remy-app` is importable.

## Current rule(s)
R-16 and R-17 name `tests/api/<name>` as their check paths.

## Proposed change
Correct R-16's and R-17's check paths to
`SystemCode/remy/app/tests/api/<name>`. The `tests/api/<name>` leaf is
preserved; the package prefix is made explicit. No other rule text changes.

## Impact
- **Completed features:** p2-002's F-D and p3-001's BD-2a are resolved by A-007
  (they recorded the divergence; A-007 makes it constitutional).
- **In-flight features:** p3-002 (the plan that triggered A-007) and p3-003/
  p3-004 (which will consume the contract) cite the amended path.
- **Behavioral change:** none — the paths are already the deployed placement.
- **No data migration.**

## Version bump
1.6 -> 1.7

## Human decision
- Reviewer:
- Decision:
- Date:
