# Decisions - Reproducible, snapshot-pinned source pipeline

## Decisions

### D-1 Canonical mart relation is `lake.main_mart`
- Date: 2026-10-03
- Context: F-1 — the manifest read `lake.mart."<mart>"`, but the deployed schema is
  `main_mart` (profile `schema: main` alongside `dbt_project.yml` `+schema: mart`,
  with no `generate_schema_name` macro). Every real manifest run failed with
  "cannot read required mart", defeating AC-1, AC-6, the `make ci` gate, and R-15.
- Decision: Read every reproducibility-facing mart from `lake.main_mart."<mart>"`.
  No dual-name support is added; the canonical name is the only accepted one.
- Alternatives: Accept both `lake.mart` and `lake.main_mart` — rejected by R-1
  (single schema, no dual support). Read the schema dynamically — rejected as
  masking a schema drift that should fail loudly.
- Affects: AC-1, AC-6; R-1; the manifest reader and every mart checksum.
- Source: F-1 (review.r1.md)

### D-2 Multi-file source checksum framing is name-sorted, not registry-relative
- Date: 2026-10-03
- Context: F-2 — `compute_file_group_checksum` derived each framed file name with
  `path.relative_to(path_root)`, but the shipped registry paths resolve outside the
  registry directory (`../../data-crawler/...`, `../seeds/...`), so `relative_to`
  raised `ValueError` even when the files existed.
- Decision: Frame each file by its resolved base name length-prefixed with its
  byte size, over files ordered by resolved absolute POSIX path, so a source group
  has one stable, environment-independent checksum.
- Alternatives: Normalize registry paths to live under the registry directory —
  rejected, because declared sources legitimately point at crawled and served data
  outside `reproducibility/`.
- Affects: AC-2, AC-3; source snapshot hashing.
- Source: F-2 (review.r1.md)

### D-3 Composite stable ordering keys per mart
- Date: 2026-10-03
- Context: F-5 — the mart checksum used `columns[:1]` as its order key, so for
  `edge_requires` (`recipe_id`) and `graph_quality_manifest` (`entity_type`) the
  key is non-unique and ties fell back to DuckDB's incoming row order, an
  unguaranteed determinism hole in AC-5.
- Decision: Declare explicit composite order keys per mart in `MART_ORDER_KEYS`
  (e.g. `edge_requires: (recipe_id, occurrence_id)`,
  `graph_quality_manifest: (entity_type, entity)`).
- Alternatives: Keep first-column ordering — rejected; it cannot satisfy AC-5 for
  the non-unique-key marts.
- Affects: AC-5; mart content checksums.
- Source: F-5 (review.r1.md)

### D-4 Consequential clarification Q4: pinned expected checksums, single build in CI
- Date: 2026-10-03
- Context: Q4 chose comparing the current build against pinned expected content
  checksums from an accepted reference build over a dual-rebuild CI check.
- Decision: Reproducibility is checked by comparing the current build's mart
  content checksums to version-controlled pinned expectations; CI runs a single
  build. This is a weaker guarantee than two independent rebuilds, so the pinned
  values may only be refreshed by an explicit, reviewed reference-build update and
  never rewritten during the check itself.
- Alternatives: Two full clean rebuilds in CI — rejected for cost and because it
  still provides no accepted reference to compare against.
- Affects: AC-6; the pinned-file refresh procedure documented in the
  data-preparation README.
- Source: spec.md Q4 (Consequential: yes)

## Overrides

### O-1 Defer F-3 pending the data-preparation price-path finding
- Applies to: F-3
- Reason: F-3 requires pinning real checksums from an accepted reference build.
  The build cannot run because `dbt` fails to parse the project. The block is
  upstream, in the data-preparation package, at
  `models/staging/stg_retail_listing.sql`, which references `retail_aisle_listing`
  and `retail_search_listing` — two nodes that no model, seed, or source produces.
  The seeds themselves are present and used by the other staging models
  (`branded_food`, `food`, `food_component`, `13k-recipes`,
  `price_mapped_nutrients`). The data-preparation package is not owned by this
  effort; see `docs/findings/data-prep-price-path.md`.
- Decision: F-3 deferred under human override.
  `reproducibility/expected_checksums.json` ships empty
  (`{"schema_version": 1, "manifest_schema_version": 1, "marts": {}}`) and
  `make reproducibility-check` fails closed with a clear "missing pinned
  checksum" error. That is intentional: the pinned file must not carry a
  fabricated baseline. The remaining findings (F-1, F-2, F-4..F-11) are resolved
  in this loop.
- Alternatives: Fabricate placeholder pinned checksums — rejected, it would make
  R-15's gate pass on invented values; modify the data-preparation package to
  rewire the price path — rejected, out of scope; restore the seeds inside
  p1-001 — rejected as out-of-scope (the seeds are present; the missing piece is
  not a seed); block close indefinitely — rejected in favour of a tracked
  follow-up.
- Impact: R-15's gate is not satisfiable end-to-end until the data-preparation
  price-path finding is resolved. `sdd.py ci` passes because its
  test/lint/typecheck checks do not exercise `make reproducibility-check`; the
  p1-001 code is verified as typed, lint-clean, and unit-tested, but its
  end-to-end reproducibility claim is not yet demonstrated.
- Who: Racker-Hank
- When: 2026-10-03
- Follow-up: Resolve `docs/findings/data-prep-price-path.md` (the data-preparation
  package owner rewires or supplies the missing nodes); then run
  `make dbt DBT_TARGET=nonprod`; pin the resulting checksums into
  `expected_checksums.json`; land the real-build integration tests F-4/F-6/F-7;
  re-review and close F-3. Tracked separately under the finding.
