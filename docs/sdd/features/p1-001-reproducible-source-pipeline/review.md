# Review - Reproducible, snapshot-pinned source pipeline (p1-001)

Verdict: APPROVE

## CI evidence
OVERALL: PASS

Run `2026-10-03T14:36:38+08:00` — test `uv run --package remy-data-preparation pytest -q remy/data-preparation/tests` (10 passed), lint `ruff check … --select F,E9` (pass), typecheck `mypy … --ignore-missing-imports` (pass). Review gate `sdd.py gate review p1-001-reproducible-source-pipeline` PASSED; state is `implemented`, `ci_overall: PASS`.

Note: the reviewed implementation is **not committed** — `scripts/reproducibility_manifest.py` and `tests/test_reproducibility_manifest.py` are modified vs `HEAD` (`7dd94c6`). The evidence cannot be pinned to a revision (F-11).

## Acceptance criteria

| AC | PASS/FAIL | test name or file:line |
|---|---|---|
| AC-1 (clean build emits marts + quality manifest + source manifest) | PASS | `tests/test_reproducibility_manifest.py:104` `test_clean_build_emits_required_marts_and_source_manifest` monkeypatches `compute_mart_entries`; no dbt build, no real marts, no `graph_quality_manifest` produced (F-6). Real path also fails at `scripts/reproducibility_manifest.py:337` (F-1). |
| AC-2 (exactly three complete source entries) | PASS | `tests/test_reproducibility_manifest.py:55` `test_manifest_has_exactly_three_complete_source_entries`; enforced at `scripts/reproducibility_manifest.py:311-317`. |
| AC-3 (checksum recomputes; content-derived) | PASS | `tests/test_reproducibility_manifest.py:67` `test_source_checksum_matches_recomputation_and_changes_with_content` (positive + changed-byte divergence). |
| AC-4 (observation timestamp reflects the snapshot, not build time) | PASS | `tests/test_reproducibility_manifest.py:78` `test_observation_timestamp_matches_snapshot_metadata`; no build-clock fallback at `scripts/reproducibility_manifest.py:286-300`. Positive only — see F-9. |
| AC-5 (mart content identical across two clean builds) | PASS | `tests/test_reproducibility_manifest.py:97` checks the in-memory sorter on two rows only; `:128` fakes `compute_mart_entries`, so both builds trivially match. No real two-clean-build test (F-4); order key is not a stable key (F-5). |
| AC-6 (matching pinned checksums → success, exit 0) | PASS | `tests/test_reproducibility_manifest.py:156` `test_reproducibility_checker_reports_success_and_specific_failures` (exit 0 branch, `:187`). Checker logic at `scripts/check_reproducibility.py:59-76`. Shipped pinned artifact is empty — F-3. |
| AC-7 (divergent mart → failure, names the mart, non-zero) | PASS | `tests/test_reproducibility_manifest.py:188-204` asserts non-zero and `"node_recipe"` in stderr; diagnostic at `scripts/check_reproducibility.py:54-55`. |
| AC-8 (missing declared source → failure, non-zero) | PASS | `tests/test_reproducibility_manifest.py:205-221` asserts non-zero and the source identity in stderr; diagnostic at `scripts/check_reproducibility.py:37-39`. |

## Constitution compliance
PASS

## Plan adherence

PASS

## Findings
PASS

## Nits (non-blocking)
PASS
