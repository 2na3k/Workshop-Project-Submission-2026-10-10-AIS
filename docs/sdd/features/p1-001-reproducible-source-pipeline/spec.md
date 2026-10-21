---
feature: p1-001-reproducible-source-pipeline
---

# Spec - Reproducible, snapshot-pinned source pipeline

## Summary

The data-preparation pipeline builds the canonical marts (recipe, food-concept,
food, component nodes and the `REQUIRES` / `FULFILLS` / `HAS_COMPONENT` edges)
and a graph quality manifest from declared source datasets, then projects them
into the graph store. Today the pipeline runs, but it does not **prove** that a
rebuild is reproducible: it does not emit a single manifest that pins every
source it consumed (source identity, snapshot id, content checksum, observation
timestamp), and nothing demonstrates that the marts are content-identical across
rebuilds from the same pinned sources.

This feature makes the existing build provable against R-15. It requires the
build to emit a source snapshot manifest covering every declared source, to
compute a content checksum and observation timestamp for each source at build
time (neither exists upstream today), and to produce marts whose content is
identical across rebuilds from the same pinned sources. A reproducibility check
in CI compares the current build against pinned expected content checksums
recorded from an accepted reference build; where the current build is
non-deterministic or omits source provenance, this feature fixes it and lands
the fix with the test that first fails.

## Traces to

- **G-7** — "The data underlying recommendations is reproducible from source
  snapshots, quality-gated on entity counts and referential integrity, and
  queryable as a graph."
- **Roadmap phase p1 → feature p1-001-reproducible-source-pipeline** *(partial)* —
  "Existing build from raw sources to canonical marts. Remaining work: emit a
  source snapshot manifest (source, snapshot id, checksum, timestamp); make
  entity and relationship counts deterministic across rebuilds; add the
  reproducibility test to CI."
- **Phase p1 exit criterion** — "A clean rebuild from the declared source
  snapshots produces the canonical marts and a quality manifest with
  deterministic entity and relationship counts. Demonstrated by a CI
  reproducibility test, not asserted."
- Governing constitutional rule: **R-15** (data is reproducible and
  quality-gated). This feature shares the "Source snapshot manifest and
  quality-gate result" contract with p1-002 and p1-003.

## User-facing behavior

The direct consumers of this feature are the downstream pipeline stages
(p1-002 graph load, p1-003 coverage reporting) and the operator who runs the
build. There is no end-user UI surface.

- An operator who runs a clean build from the declared source snapshots gets the
  canonical marts, the graph quality manifest, and a source snapshot manifest
  naming every declared source and pinning each by snapshot id, content
  checksum, and observation timestamp.
- An operator who runs the build again from the same pinned snapshots gets marts
  whose content checksums are identical to the previous run's.
- An operator (or CI) who runs the reproducibility check gets a pass when the
  current build's content checksums match the pinned expected checksums, and a
  non-zero failure naming the specific mart or source whose checksum diverged.
- A downstream stage that reads the source snapshot manifest can determine, for
  any mart, which source snapshots the build consumed and when they were
  observed, without inspecting raw source files.

## Acceptance criteria

- **AC-1** Given the declared source snapshots are present, when a clean build is
  run, then it completes and produces the canonical marts, the graph quality
  manifest, and a source snapshot manifest.
- **AC-2** Given a completed clean build, when the source snapshot manifest is
  read, then it contains exactly one entry for each of the three declared
  sources (FoodData Central, recipe dataset, FairPrice listings), and each entry
  carries a source identity, a snapshot id, a content checksum, and an
  observation timestamp, all non-empty.
- **AC-3** Given a completed clean build, when a manifest entry's content
  checksum is recomputed over the same source snapshot, then the recomputed
  value equals the recorded value. This demonstrates the checksum is derived
  from the source content, not a placeholder.
- **AC-4** Given a completed clean build, when a manifest entry's observation
  timestamp is compared to the source snapshot's own recorded capture time (or
  the build's fetch-and-freeze time for that source), then they agree. This
  demonstrates the timestamp reflects the observation, not the build-run time.
- **AC-5** Given the same pinned source snapshots, when a clean build is run
  twice from a clean state, then each mart's content checksum is identical
  across both runs. (Content equality, not count equality.)
- **AC-6** Given a build whose content checksums match the pinned expected
  checksums recorded from the accepted reference build, when the reproducibility
  check runs, then it reports success and exits zero.
- **AC-7** Given a build whose content checksum for any mart diverges from the
  pinned expected value, when the reproducibility check runs, then it reports
  failure, names the specific mart whose checksum diverged, and exits non-zero.
- **AC-8** Given a declared source is absent from the source snapshot manifest,
  when the reproducibility check runs, then it reports failure and exits
  non-zero.

## Edge cases & errors

- A declared source snapshot is missing or unreadable at build time: the build
  must fail rather than silently produce marts from a partial source set.
- A source is consumed by the build but its content checksum or observation
  timestamp cannot be computed (e.g., an empty file, a file with no capture
  time): this is a manifest-completeness failure (AC-2), not a value to be
  defaulted or blanked.
- Checksums match but observation timestamps have drifted between runs (e.g.,
  the source was re-fetched at a different time from the same bytes): the
  manifest reflects the new observation time; the content checksum still
  matches, and the reproducibility check passes on content. The manifest's
  timestamp difference is not a reproducibility failure.
- A non-deterministic ordering or tie-break inside the existing build changes
  which rows survive between runs: the fix is in scope; the reproducibility
  check fails first on the divergent checksum.
- The build consumes a source that is a point-in-time retail snapshot
  (stale-prone): the manifest records its observation timestamp; freshness
  evaluation for reasoning is out of scope here (belongs to p2).
- Two builds whose checksums match but whose row-level metadata differs (e.g.,
  a build-time column): the checksum must be computed over content fields only,
  and build-time metadata must be excluded from the checksum by design. If this
  distinction is not achievable, that is a scope question for the plan.
- Computing a checksum over a large source (e.g., the USDA food_nutrient
  Parquet, ~27M rows) may be expensive; the check must complete within the
  project's CI budget. If it does not, chunked or parallel hashing is a plan
  concern.

## Non-goals

- Not rebuilding the pipeline or redesigning its transformations; this feature
  makes the existing build provable, not new.
- Not loading or verifying the graph store, and not asserting edge-level
  provenance on `REQUIRES` / `FULFILLS` records — that is p1-002.
- Not computing or publishing coverage/completeness measures — that is p1-003.
- Not evaluating source freshness, staleness, or offer validity for reasoning —
  that is p2.
- Not crawling, acquiring, or refreshing source data. Sources are consumed as
  already-declared snapshots. Reading landed source files to compute checksums
  is in scope; fetching or re-fetching them is not.
- Not defining the graph query experience or any end-user response.
- Not introducing a general-purpose data-quality framework; the manifest and
  reproducibility check are scoped to this feature's three declared sources and
  the canonical marts.

## Interfaces & dependencies

- **Depends on:** nothing upstream (first feature in p1).
- **Shares the contract** "Source snapshot manifest and quality-gate result"
  with **p1-002-provenance-graph-model** and **p1-003-coverage-quality-reporting**.
  The manifest is a statement of facts (sources, snapshots, checksums,
  timestamps, mart content checksums); the acceptance decision — whether the
  manifest permits a graph load — is applied by p1-002 at load time, not
  embedded in the manifest. This keeps R-15's gate at the load boundary and
  keeps the two features' responsibilities separate. The concrete field names
  and storage form of the manifest and the pinned expected checksums are a Plan
  concern, not fixed here.
- **Constitutional dependency:** R-15 governs. This feature owns the
  reproducible-content and source-manifest half of R-15's check. The
  referential-integrity half (zero dangling `REQUIRES` / `FULFILLS`) is
  exercised at load time by p1-002.
- **Tooling dependency:** the reproducibility check must run under the project's
  configured CI command set so R-15's check is satisfiable. A reproducibility
  regression is recorded in `ci-results.md` when the check fails.

## Open questions
<!-- all resolved; retained here for traceability -->

- [x] Q1: Which source datasets count as "declared sources"? **FoodData Central,
  recipe dataset, and FairPrice listings** — the three inputs named in the
  data-preparation README. dbt seeds and internal source relations are not
  declared sources for the manifest.
- [x] Q2: Is count equality sufficient evidence of reproducibility? **No —
  content must match.** The reproducibility check compares content checksums
  per mart, not just counts.
- [x] Q3: Do the snapshot content checksum and observation timestamp already
  exist upstream? **No.** The build must compute the content checksum over each
  raw source snapshot at build time and record the source's own capture time
  (or the fetch-and-freeze time for that source) as the observation timestamp.
- [x] Q4: Two full clean rebuilds in CI, or compare against pinned expected
  counts? **Compare against pinned expected content checksums** recorded from an
  accepted reference build. CI runs a single build and compares its checksums
  to the pinned values. No dual rebuild in CI.

## Clarifications

- Q1 → FoodData Central, recipe dataset, and FairPrice listings are the three
  declared sources. Date: 2026-10-03. Who: Human.
- Q2 → Content must match; reproducibility is defined by content checksums per
  mart, not by count equality. Date: 2026-10-03. Who: Human.
- Q3 → Neither exists upstream; the build computes content checksums and records
  observation timestamps from the source's own capture time. This expands scope
  to include reading landed source files for hashing, but not fetching them.
  Date: 2026-10-03. Who: Human.
- Q4 → Compare against pinned expected content checksums from an accepted
  reference build; CI runs a single build. Date: 2026-10-03. Who: Human.
  Consequential: yes — this is a weaker guarantee than a dual-rebuild check, and
  it means the reference checksums must themselves be refreshed via an
  amendment to the pinned values whenever an upstream source legitimately
  changes. The procedure for refreshing pinned values is a Plan concern.
