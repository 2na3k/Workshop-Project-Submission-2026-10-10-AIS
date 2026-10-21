# Review - Reproducible, snapshot-pinned source pipeline (p1-001)

Verdict: APPROVE

## CI evidence
OVERALL: PASS

Run `2026-10-03T14:36:38+08:00` — test `uv run --package remy-data-preparation pytest -q remy/data-preparation/tests` (10 passed), lint `ruff check … --select F,E9` (pass), typecheck `mypy … --ignore-missing-imports` (pass). Review gate `sdd.py gate review p1-001-reproducible-source-pipeline` PASSED; state is `implemented`, `ci_overall: PASS`.

Note: the reviewed implementation is **not committed** — `scripts/reproducibility_manifest.py` and `tests/test_reproducibility_manifest.py` are modified vs `HEAD` (`7dd94c6`). The evidence cannot be pinned to a revision (F-11).

## Acceptance criteria

| AC | PASS/FAIL | test name or file:line |
|---|---|---|
| AC-1 (clean build emits marts + quality manifest + source manifest) | FAIL | `tests/test_reproducibility_manifest.py:104` `test_clean_build_emits_required_marts_and_source_manifest` monkeypatches `compute_mart_entries`; no dbt build, no real marts, no `graph_quality_manifest` produced (F-6). Real path also fails at `scripts/reproducibility_manifest.py:337` (F-1). |
| AC-2 (exactly three complete source entries) | PASS | `tests/test_reproducibility_manifest.py:55` `test_manifest_has_exactly_three_complete_source_entries`; enforced at `scripts/reproducibility_manifest.py:311-317`. |
| AC-3 (checksum recomputes; content-derived) | PASS | `tests/test_reproducibility_manifest.py:67` `test_source_checksum_matches_recomputation_and_changes_with_content` (positive + changed-byte divergence). |
| AC-4 (observation timestamp reflects the snapshot, not build time) | PASS | `tests/test_reproducibility_manifest.py:78` `test_observation_timestamp_matches_snapshot_metadata`; no build-clock fallback at `scripts/reproducibility_manifest.py:286-300`. Positive only — see F-9. |
| AC-5 (mart content identical across two clean builds) | FAIL | `tests/test_reproducibility_manifest.py:97` checks the in-memory sorter on two rows only; `:128` fakes `compute_mart_entries`, so both builds trivially match. No real two-clean-build test (F-4); order key is not a stable key (F-5). |
| AC-6 (matching pinned checksums → success, exit 0) | PASS | `tests/test_reproducibility_manifest.py:156` `test_reproducibility_checker_reports_success_and_specific_failures` (exit 0 branch, `:187`). Checker logic at `scripts/check_reproducibility.py:59-76`. Shipped pinned artifact is empty — F-3. |
| AC-7 (divergent mart → failure, names the mart, non-zero) | PASS | `tests/test_reproducibility_manifest.py:188-204` asserts non-zero and `"node_recipe"` in stderr; diagnostic at `scripts/check_reproducibility.py:54-55`. |
| AC-8 (missing declared source → failure, non-zero) | PASS | `tests/test_reproducibility_manifest.py:205-221` asserts non-zero and the source identity in stderr; diagnostic at `scripts/check_reproducibility.py:37-39`. |

## Constitution compliance
Violations: R-15

- **R-15 (reproducible and quality-gated)** — violated as shipped. The CI entry point `make ci` → `reproducible-build` cannot pass: the pinned reference file carries no values (F-3), the manifest step addresses the wrong mart schema (F-1), and source framing fails even when data is present (F-2). The gate that R-15 depends on is therefore not satisfiable, and no reproducibility evidence is produced for a real build.
- **R-1 (single schema, no dual support)** — not violated as written, but F-1 must be corrected to the canonical relation name; reading `lake.mart` when the deployed schema is `lake.main_mart` is the mechanism of F-1 and must not be "supported" as a second name.
- **R-3 (stack shape)** — pass. Reuses dbt/DuckDB/DuckLake and Python; no new backend or store.
- **R-4 (edge provenance)** — pass. The manifest supplies source identity, snapshot id, checksum, and timestamp as facts; acceptance is correctly left to p1-002.

## Plan adherence

All tasks T-1…T-11 are marked `[x]`, but three done-whens are unmet:

- **T-1** marked done while its stated prerequisite is still unmet — `AGENTS.md:31-33` still contains `<package-name>` placeholders, and T-1's own done-when required stopping and routing upstream (F-10).
- **T-6** done-when required a dbt contract test that a silent column addition/rename is *detected*; only an inert `meta.reproducibility_content_columns` block was added (F-7).
- **T-11** done-when required the configured checks plus a demonstrated non-zero path; the non-zero path is shown, but the "configured" checks in `make ci` are not the test/lint/typecheck set recorded in `ci-results.md` (F-10).

Deviations from the Test-strategy table: the planned test names `test_source_checksum_differs_on_changed_content`, `test_reproducibility_check_passes_for_pinned_reference`, `…_names_divergent_mart_and_fails`, `…_rejects_missing_source`, `test_missing_source_snapshot_fails_build`, and `test_unreadable_source_snapshot_fails_build` do not exist as separate tests; several were merged into combined tests. The merged fixtures are weaker than the planned ones in the cases noted below.

## Findings
- [X] F-1 [BLOCKER] Mart relations are read as `lake.mart."<mart>"`, but the canonical deployed 
  schema is `main_mart` (profile `schema: main`, `dbt_project.yml:23` `+schema: mart`, and no `generate_schema_name` macro), and existing code reads `lake.main_mart.*` (`scripts/recipe_estimate.py:34`). Every real manifest run fails with "cannot read required mart" (`scripts/reproducibility_manifest.py:337-341`), defeating AC-1/AC-6, the `make ci` gate, and R-15. (file:line: `scripts/reproducibility_manifest.py:337`) — route: implement
- [X] F-2 [BLOCKER] Source path framing cannot succeed. `compute_file_group_checksum` derives 
  the framed name via `path.relative_to(path_root)` with `path_root=registry_path.parent` (`scripts/reproducibility_manifest.py:211-213`), but the shipped registry paths resolve *outside* that root (`reproducibility/source_registry.json:4-6`: `../../data-crawler/…`, `../seeds/…`). `relative_to` raises `ValueError` even when the files exist, so no checksum can be produced for the declared sources. (file:line: `scripts/reproducibility_manifest.py:211-213,274-276`) — route: implement
- [ ] F-3 [BLOCKER] The pinned reference artifact is empty: `reproducibility/expected_checksums.json` is `{"schema_version": 1, "manifest_schema_version": 1, "marts": {}}`. The checker requires a pinned value for all eight required marts (`scripts/check_reproducibility.py:44-48`), so `make reproducibility-check` — and therefore `make ci` — always fails on the shipped artifact. No accepted-reference checksums were pinned, so AC-6's zero-exit path is unsatisfiable in the real build and R-15's gate is unmet. (file:line: `reproducibility/expected_checksums.json:1`) — route: implement
- [X] F-4 [MAJOR] AC-5 has no integration evidence. 
  `test_two_clean_builds_have_identical_mart_content_checksums` only asserts the in-memory sorter is order-insensitive over two literal rows (`tests/test_reproducibility_manifest.py:97-101`); `test_two_clean_builds_have_identical_manifest_mart_checksums` monkeypatches `compute_mart_entries` to constants (`:128-148`), so both builds match tautologically. No test runs two clean builds of the real pipeline, so non-determinism in the marts — the exact risk the plan's Risks section names — would go undetected. (file:line: `tests/test_reproducibility_manifest.py:97,128`) — route: implement
- [X] F-5 [MAJOR] The mart checksum order key is not a stable key. `compute_rows_checksum` is 
  called with `columns[:1]` as `order_by` (`scripts/reproducibility_manifest.py:344`), i.e. a single first column, contradicting the plan's "deterministic ordering by the mart's stable key(s)". For `edge_requires` the first column `recipe_id` is not unique (many occurrences per recipe) and for `graph_quality_manifest` the first column `entity_type` is not unique, so ties are ordered by incoming DuckDB row order, which is not guaranteed — a direct determinism hole in AC-5's guarantee. (file:line: `scripts/reproducibility_manifest.py:344`) — route: implement
- [X] F-6 [MAJOR] AC-1 is evidenced only against fakes. 
  `test_clean_build_emits_required_marts_and_source_manifest` replaces `compute_mart_entries` with a literal dict and asserts only that the manifest file exists and its keys match (`tests/test_reproducibility_manifest.py:104-125`). No test runs the fixture build path or asserts the canonical marts and `graph_quality_manifest` are actually materialized, contrary to the plan's AC-1 row. (file:line: `tests/test_reproducibility_manifest.py:104-125`) — route: implement
- [X] F-7 [MAJOR] The planned exact-column dbt contract tests were not implemented. The change 
  adds `meta.reproducibility_content_columns` to each mart (`models/mart/schema.yml:5-6,14-15,28-29,51-52,58-59,73-74,110-111,125-126`), but dbt does not enforce `meta`; no test compares the deployed column set against the contract. The only Python check `test_contract_covers_exactly_all_reproducibility_facing_marts` merely compares the Python dict keys to `REQUIRED_MARTS` (`tests/test_reproducibility_manifest.py:151-153`). A silent column addition, rename, or omission — the plan's stated T-6 done-when and Design penalty — is therefore not detected. (file:line: `models/mart/schema.yml:5-6`) — route: implement
- [X] F-8 [MAJOR] The spec's "missing or **unreadable** source snapshot at build time must fail" 
  edge case is half-covered. `test_missing_source_or_metadata_fails_closed` covers a missing file and a missing metadata file, but there is no unreadable-source case (permissions, directory-in-place-of-file), and the planned `test_unreadable_source_snapshot_fails_build` does not exist. Additionally, the missing-source case only asserts `pytest.raises(ValueError)` on `load_source_entries` (`tests/test_reproducibility_manifest.py:84-94`), whereas the plan's done-when required asserting non-zero exit *and* that no manifest is written and no mart checksums are emitted. (file:line: `tests/test_reproducibility_manifest.py:84-94`) — route: implement
- [X] F-9 [MAJOR] AC-4's planned negative case is not covered. The plan lists 
  `test_missing_or_invalid_capture_metadata_fails_closed`; the implementation covers a missing metadata file only, not a present-but-unparseable `observation_timestamp`, even though the code has a distinct invalid-timestamp branch (`scripts/reproducibility_manifest.py:295-300`) that no test exercises. (file:line: `tests/test_reproducibility_manifest.py:84-94`) — route: implement
- [X] F-10 [MAJOR] T-1's prerequisite is unmet and `make ci` is not the project's configured CI 
  command set. `AGENTS.md:31-33` still holds `<package-name>` placeholders despite T-1 being marked done and its done-when requiring an upstream stop; and `Makefile:71-73` wires `ci: reproducible-build`, which runs dbt + manifest + checker only — it does not run the test/lint/typecheck commands recorded in `ci-results.md`. Per `AGENTS.md`, an unmet upstream prerequisite must be routed, not resolved inside implementation. (file:line: `Makefile:71-73`, `AGENTS.md:31-33`) — route: plan
- [X] F-11 [MAJOR] CI evidence is not pinned to a revision. The reviewed implementation is 
  uncommitted: `scripts/reproducibility_manifest.py` and `tests/test_reproducibility_manifest.py` differ from `HEAD` (`7dd94c6`), including typing changes and a `pyproject.toml` mypy/dependency-group addition. The reviewed tree cannot be reproduced from the commit, so the PASS cannot be attributed to a specific revision. (file:line: `SystemCode/remy/data-preparation/scripts/reproducibility_manifest.py:155-177` (uncommitted), `SystemCode/remy/data-preparation/pyproject.toml`) — route: implement

## Nits (non-blocking)
- `from typing import TypedDict` is placed mid-module (`scripts/reproducibility_manifest.py:155`) instead of with the other imports at the top.
- `load_source_entries` writes resolved absolute paths into the build artifact (`scripts/reproducibility_manifest.py:307`), making `source_snapshot_manifest.json` machine-specific; relative-to-project paths would keep the artifact comparable across environments.
- `expected_checksums.json` declares its own `schema_version`, but the checker never validates it against a known value (`scripts/check_reproducibility.py:24-31`), so the plan's "independent expected-checksums version" is not actually enforced.
- `REQUIRED_SOURCES` is hard-coded in the script (`scripts/reproducibility_manifest.py:14`) in addition to the registry, so the declaration is duplicated in two places.
- The `reproducibility/` directory ships only the registry and the empty pinned file; the registry's `metadata_path` records (`reproducibility/metadata/*.json`) do not exist, so the fail-closed path is the only reachable path in this repository state.
- `graph_quality_manifest` ordering by `entity_type` alone (see F-5) also makes the `TOTAL_*` rows order-sensitive; worth a secondary stable key when F-5 is addressed.
