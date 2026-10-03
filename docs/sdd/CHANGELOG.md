### p1-001-reproducible-source-pipeline - Reproducible, snapshot-pinned source pipeline (2026-10-03)

- Added/Changed/Fixed:
  - Added a versioned source registry declaring the three declared sources
    (FoodData Central, recipe dataset, FairPrice listings) with landed paths,
    snapshot ids, and capture-metadata locations
    (`SystemCode/remy/data-preparation/reproducibility/source_registry.json`).
  - Added `SystemCode/remy/data-preparation/scripts/reproducibility_manifest.py`:
    streaming, deterministic source snapshot hashing (name/size framed,
    path-sorted) plus canonical mart content checksums, emitting one versioned
    JSON source snapshot manifest; fails closed on missing/unreadable/empty
    sources and on missing or invalid capture metadata.
  - Added `SystemCode/remy/data-preparation/scripts/check_reproducibility.py`:
    validates manifest completeness (exactly three declared sources, all required
    marts) and compares mart content checksums against pinned expectations, with
    deterministic non-zero diagnostics naming the divergent mart or missing source.
  - Added `SystemCode/remy/data-preparation/reproducibility/expected_checksums.json`
    (versioned pinned expectations; ships empty under override O-1).
  - Added `SystemCode/remy/data-preparation/tests/test_reproducibility_manifest.py`.
  - Fixed mart relation reads to the canonical `lake.main_mart` (R-1).
  - Changed `SystemCode/Makefile`: the `dbt` target now emits the manifest; added
    `reproducible-manifest`, `reproducibility-check`, and `reproducible-build`
    targets, and made `ci` run `reproducible-build` plus the configured
    test/lint/typecheck `check` target.
  - Documented the source registry/capture-metadata contract, manifest location,
    checker invocation, and reviewed reference-checksum refresh procedure in
    `SystemCode/remy/data-preparation/README.md`.
- Acceptance criteria: AC-1 .. AC-8
- Decisions: docs/sdd/features/p1-001-reproducible-source-pipeline/decisions.md
- Breaking: none
