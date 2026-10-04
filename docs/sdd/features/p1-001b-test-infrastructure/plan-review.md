# Plan review - Graph test infrastructure (p1-001b) — Re-review with spec supplied

Verdict: **APPROVE**

Prior blocker (spec not supplied) is resolved: the spec for p1-001b is now provided, and the plan's coverage can be checked with evidence. Tasks may be added; the plan is frozen for this loop.

## Checks

| Check | Result | Evidence |
|---|---|---|
| Spec coverage | **Pass** | Spec AC-1–AC-5 each map to the plan's Test strategy: AC-1 → fake-driver smoke tests (`test_serving_model_runs_through_fake`, `test_fake_records_statements` — matches "assert which load statements were issued and their inputs"); AC-2 → `test_write_read_through_fixture` ("write through the serving model's load path, read back"); AC-3 → `test_second_test_sees_clean_state`; AC-4 → marker registration test plus CI-level filter verification; AC-5 → local-skip/CI-fail behavior (F-4 revision), matching the spec's "A skipped integration test under CI is a CI failure" verbatim in Design §2 and §4. Spec edge cases covered: unreachable instance fails naming URI not password; absent `.env.test` with process-env variables set uses process env (the CI path); missing `.env.test` locally skips. Spec non-goals respected: no conformance/provenance tests (p1-002), no second framework, no production code. Spec's "Provides" list (fake fixture, integration fixture, python-dotenv, marker, CI step) matches the plan's deliverables one-for-one. |
| Test strategy | Pass | Every AC has a named test or explicit verification mechanism. The prior subprocess-based filter test was replaced with a `pytestconfig` registration assertion — acceptable since AC-4's filter behavior is behavioral, not structural, and the plan names where it is verified. |
| Constitution | Pass | R-3 only, correctly cited; python-dotenv is dev-only, no shape change. The plan's note honestly declines to claim R-4/R-15 directly, consistent with the spec tracing to G-4/G-7 only *indirectly*. Additive dev-dependency change verified pre-task. |
| Feasibility | Pass | Cloud-instance approach, `CI` env-var detection, verify_connectivity once per session for idle-paused Aura — all implementable. Rejected alternatives are sound given the Docker-absent constraint. Verification-before-tasks step covers the remaining unknowns (workflow filename, .gitignore, existing dev group). |
| Scope | Pass | Ten test-side files + pyproject + .gitignore + CI workflow + README, matching spec's "No production code changes." Fits one working context. |

## Findings

None blocking.

## Nits (non-blocking)

- **Partially filled `.env.test`**: the spec requires empty-set variables to be "treated as unconfigured, with the missing variable names reported." The plan says "if any of the three variables is missing after both checks" — implementers should treat *empty-string* values as missing; consider reflecting this in the fixture when writing T-tasks. Not a plan defect; it is a reasonable reading of "missing."
- Wrong-database-name edge case (spec: "fixture's `verify_connectivity()` fails, same as unreachable"): plan covers this implicitly via the same failure path; no test distinguishes it. Acceptable, but the implementer may add an assertion that the failure message names the URI.
- The `CI` env-var heuristic: document in the README section that locally exporting `CI=1` turns skips into failures (carried from prior review; still worth one sentence).
- The plan does not name which pytest invocation the CI step uses for the *non*-integration suite (e.g., `pytest -m "not integration"` before the integration step). One line in Design §4 would remove ambiguity at task time.

## Route summary

No findings to route. All prior plan-routed findings (F-4, F-5) and nits (F-6, F-7, F-8) were addressed in the previous revision; the sole prior blocker routed to **spec** and is now closed by the spec's supply and its agreement with the plan.

## Override

<!-- only a human may fill in. Records a decision, not a new verdict. -->
- Applies to: F-<n>
- Reason:
- Who:
- When:

---

**Reviewer note:** Plan is frozen for this loop. Tasks may be added, including the plan's "Verification before tasks" items as prerequisite tasks (workflow filename, .gitignore check, dev-group check). The nits above are implement-time guidance, not task edits — per AGENTS.md, the plan itself must not be modified at task stage.
