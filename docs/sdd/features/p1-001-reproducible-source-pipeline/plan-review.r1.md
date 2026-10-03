# Plan review - Reproducible, snapshot-pinned source pipeline (p1-001)

Verdict: **REVISE**

## Checks

| Check | Result | Evidence |
|---|---|---|
| Spec coverage | Pass with gap | AC-1–AC-8 each map to a named test (Test strategy table rows 1–11). Design covers manifest fields (`source_identity`, `snapshot_id`, `content_checksum`, `observation_timestamp`), content-vs-count equality (Q2), pinned-reference comparison (Q4), and the checker contract (AC-6/7/8). However, a spec edge case lacks test coverage — see F-1. |
| Test strategy | Pass with gap | Positive and negative cases for AC-3 and AC-4; content (not count) comparison asserted in AC-5 test; checker diagnostics tested by name for AC-7/AC-8. Gap: the spec's "missing/unreadable source snapshot at build time must fail" edge case has no test row. |
| Constitution | Pass | R-15 owned directly (CI gate via Makefile touch). R-1 handled via exact-column contract tests in `schema.yml`. R-3 respected (no shape change; Python/dbt/DuckDB retained). R-4 claim is correctly scoped: the manifest supplies facts, p1-002 applies acceptance at load. No rule is mis-cited after the F-2 revision. |
| Feasibility | Pass | Streaming hashing addresses the ~27M-row Parquet risk; fail-closed metadata contract is implementable; versioned manifest/expected-checksums split is coherent. Risks & mitigations are concrete. |
| Scope | Pass | Matches spec Non-goals: no pipeline redesign, no graph load, no coverage reporting, no fetching, no freshness evaluation. Fits one working context. |

## Findings

- [ ] F-1 [MAJOR] The spec's edge case — "A declared source snapshot is missing or unreadable at build time: the build must fail rather than silently produce marts from a partial source set" — is designed for (Design: "validates that every declared snapshot path … is present and readable, fails closed") but has **no test** in the Test strategy table. AC-8 covers a missing source in the *manifest* against the *checker*, not the build-time fail-closed path. The spec says "must fail", so this is testable behavior, and R-15's gate depends on it. — route: **plan** (add a negative test row, e.g. `test_missing_source_snapshot_fails_build` in `tests/test_reproducibility_manifest.py`).

## Nits (non-blocking)

- AGENTS.md tooling commands are placeholders (`<command>`); the plan references "the configured CI command set" without naming the concrete test/lint commands. Once AGENTS.md is filled in, the Makefile task should cite them explicitly.
- Approach says the Python layer is invoked "from the same Make target that runs the build" — consider stating whether the manifest step also runs in the existing dev/iteration path or only in the CI target, to avoid stale-manifest surprises during local iteration.
- `edge_has_component` and `graph_quality_manifest` appear in the mart contract but are not named in the spec's mart list (the spec says "canonical marts" generically). Not a conflict — the plan may be stricter — just confirm p1-002/p1-003 expect `graph_quality_manifest` inside the checksum contract.

## Override

<!-- only a human may fill this in. Records a decision, not a new verdict. -->
- Applies to: F-<n>
- Reason:
- Who:
- When:

---

**Reviewer note:** Tasks must NOT be added until F-1 is fixed in the plan and the plan is re-reviewed. The fix is plan-local (one test row); no spec or constitution change is required.
