# Plan - Reproducible, snapshot-pinned source pipeline

## Approach

Use a thin Python reproducibility layer around the existing dbt/DuckDB build: a
versioned source registry identifies the three declared snapshot groups, a
streaming hasher computes source checksums and records source observation
metadata, and a DuckDB reader computes canonical row-content checksums for each
canonical mart before writing one JSON manifest and checking pinned
expectations. The build remains dbt/DuckDB and transformations are not
redesigned.

Cost of the chosen path: the Python layer is a build-time step that must be kept
in sync with dbt model changes. Mitigated by invoking it from the same Make
target that runs the build, so a model change that breaks the checksum contract
fails the build rather than the manifest silently going stale.

Manifest target scope: the manifest step runs in both the dev build target and
the CI target. Running it in the dev path makes stale manifests visible during
local iteration, when the developer can act on them, rather than only at CI when
the mismatch is already committed. If the manifest step proves too slow to run
on every local build, the fallback is to run it in the dev path on demand (a
separate target) and always in CI; that decision belongs to the task that wires
the Makefile, not to this plan.

Rejected alternative: implement the entire manifest and checksum contract as dbt
SQL models only. Rejected because raw multi-file source hashing, source-side
capture metadata validation, chunked hashing of the large FoodData Central
Parquet input, and a clear non-zero CLI failure contract are more controllable
in Python than in SQL models that would have to be run within the dbt graph.

## Design

- Add a versioned source registry for exactly three declared source identities:
  FoodData Central, recipe dataset, and FairPrice listings. Each entry names its
  landed snapshot path(s), configured snapshot id, and source capture/freeze
  metadata path. The registry is the declaration boundary; dbt seeds and
  internal relations are not independently emitted as sources.
- Add a build-time manifest command invoked after a successful dbt build. It
  validates that every declared snapshot path and metadata record is present and
  readable, fails closed on missing/empty/unhashable input, streams source bytes
  in bounded chunks, and computes a SHA-256 checksum without fetching or
  refreshing data. For a source consisting of multiple landed files, paths are
  normalized, sorted, and hashed with deterministic path/length/content framing
  so the group has one stable checksum.
- **Fail-closed on missing source is a first-class behavior, not a side effect.**
  If any declared snapshot path or metadata record is missing, empty, or
  unreadable, the manifest step exits non-zero before producing a manifest and
  before any mart checksum is written. No marts are emitted from a partial
  source set. This behavior has its own test (see Test strategy, "Edge case"
  rows) because R-15's gate depends on it.
- Treat the configured snapshot id and source observation timestamp as source
  metadata, not run metadata. The timestamp is read from the source snapshot's
  capture/freeze record and is required to be non-empty and parseable; the
  current build time is not used as a fallback.
- Compute mart content checksums from DuckDB/DuckLake relations after dbt
  materialization. For each canonical node/edge mart (`node_recipe`,
  `node_food_concept`, `node_food`, `node_component`, `edge_requires`,
  `edge_fulfills`, `edge_has_component`) and `graph_quality_manifest`, use an
  explicit ordered content-column contract, canonical null/type serialization,
  and deterministic ordering by the mart's stable key(s). Build-time metadata
  fields are excluded by the contract rather than being allowed to make
  equivalent builds differ. The checksum implementation must process rows
  incrementally so the large source and marts do not require a full in-memory
  materialization.
- **The mart list is a contract.** Adding a mart to the pipeline requires adding
  it to the checksum contract; the manifest schema version increments when the
  list or any content-column contract changes, and p1-002 / p1-003 must accept
  the new version. Without this rule, the reproducibility guarantee would
  silently narrow as the pipeline grows, because a new mart would be excluded
  from the check until someone remembered to add it.
- Write a single versioned JSON source snapshot manifest as a build artifact. It
  contains schema/version information, the three source entries
  (`source_identity`, `snapshot_id`, `content_checksum`,
  `observation_timestamp`, and declared paths), and a mart checksum section
  containing each mart name, row count, content checksum, and the content-column
  contract/version. The graph quality manifest remains the existing dbt mart and
  is included in the artifact's mart checksums rather than replaced.
- Add a reproducibility-check command that reads the generated manifest and a
  versioned expected-checksums JSON file. It verifies all three required source
  identities are present exactly once, verifies all required mart entries exist,
  compares current mart checksums with pinned expected values, and exits zero
  only when all checks pass. Failure output names the missing source or specific
  divergent mart and the command returns non-zero. Timestamp changes alone do
  not fail the content comparison.
- Pin expected mart checksums in a reviewed, version-controlled file generated
  from an accepted reference build. Refreshing those values is an intentional
  reference-build update, not an automatic action during a normal build; the
  source snapshot manifest records the actual source checksum and timestamp for
  auditability.
- The expected-checksums file carries its own schema version, separate from the
  manifest version. The two version fields move independently: the manifest
  version tracks the shape of the emitted artifact, the expected-checksums
  version tracks the shape of the pinned values. A build whose manifest version
  does not match the version the checker expects fails closed.

## Files to touch

- `SystemCode/remy/data-preparation/reproducibility/source_registry.json` —
  declare the three source identities, landed paths, snapshot ids, and
  capture/freeze metadata locations.
- `SystemCode/remy/data-preparation/reproducibility/expected_checksums.json` —
  versioned pinned mart checksum expectations from the accepted reference build.
  Carries its own `schema_version`.
- `SystemCode/remy/data-preparation/scripts/reproducibility_manifest.py` —
  validate declared snapshots, stream source checksums, read source observation
  metadata, compute canonical mart checksums, and write the manifest. Fail-closed
  on any missing/unreadable declared snapshot occurs here.
- `SystemCode/remy/data-preparation/scripts/check_reproducibility.py` — validate
  manifest completeness and compare current checksums with pinned expectations,
  including deterministic non-zero diagnostics.
- `SystemCode/remy/data-preparation/tests/test_reproducibility_manifest.py` —
  unit and integration tests for source declarations, source hashing/metadata,
  canonical mart hashing, manifest completeness, and reproducibility-check
  outcomes.
- `SystemCode/Makefile` — add the reproducible build/check command to the
  configured CI command set, and add the dev-path invocation of the manifest
  step. The concrete test/lint commands cited here are the ones recorded in
  `AGENTS.md` once that tooling block is filled in (see Risks).
- `SystemCode/remy/data-preparation/README.md` — document the source
  registry/capture metadata contract, manifest location, reference checksum
  refresh procedure, and CI command.
- `SystemCode/remy/data-preparation/models/mart/schema.yml` — add contract tests
  asserting that each reproducibility-facing mart exposes **exactly** the columns
  named in its content-column contract (not merely that the named columns
  exist). This makes a silent column addition or rename fail at dbt test time
  rather than only at checksum time. Do not alter graph schema names.

## Constitution alignment

- **R-1** → The content-column contract names the canonical schema columns for
  each mart; no legacy or dual naming is accepted by the checksum contract or
  the schema.yml contract tests.
- **R-3** → Keeps the existing Python data-preparation tooling, declarative
  dbt/DuckDB lakehouse, and graph-serving shape; adds no alternate backend or
  storage shape.
- **R-4** → The manifest this feature produces carries source identity, snapshot
  id, content checksum, and observation timestamp for every declared source;
  this is the provenance p1-002 needs to satisfy R-4's edge-provenance checks at
  load time. The manifest is a statement of facts; the acceptance decision is
  applied by p1-002, not embedded here.
- **R-15** → Emits source snapshot identity, snapshot id, source content
  checksum, observation timestamp, mart content checksums, and quality-manifest
  evidence; the CI gate fails before a build is accepted when provenance is
  incomplete or content diverges.

## Test strategy

| AC | Test type | Test location / name | Notes |
|---|---|---|---|
| AC-1 | Integration test | `tests/test_reproducibility_manifest.py::test_clean_build_emits_required_marts_and_source_manifest` | Run the clean data-preparation build against declared fixture snapshots and assert canonical marts, `graph_quality_manifest`, and the single source snapshot manifest are produced. |
| AC-2 | Unit/integration test | `tests/test_reproducibility_manifest.py::test_manifest_has_exactly_three_complete_source_entries` | Assert exactly FoodData Central, recipe dataset, and FairPrice entries occur once and all required fields are non-empty. |
| AC-3 | Unit test (positive) | `tests/test_reproducibility_manifest.py::test_source_checksum_matches_recomputation` | Recompute the checksum through the independent/streaming verification path over the same fixture snapshot and compare with the recorded value. |
| AC-3 | Unit test (negative) | `tests/test_reproducibility_manifest.py::test_source_checksum_differs_on_changed_content` | Mutate one byte of a fixture snapshot and assert the recomputed checksum differs from the recorded value. |
| AC-4 | Unit test (positive) | `tests/test_reproducibility_manifest.py::test_observation_timestamp_matches_snapshot_metadata` | Supply source capture/freeze metadata and assert the manifest preserves it. |
| AC-4 | Unit test (negative) | `tests/test_reproducibility_manifest.py::test_missing_or_invalid_capture_metadata_fails_closed` | Omit or corrupt the capture metadata and assert the build fails rather than defaulting to build-run time. |
| AC-5 | Rebuild integration test | `tests/test_reproducibility_manifest.py::test_two_clean_builds_have_identical_mart_content_checksums` | Build twice from the same pinned fixture snapshots after cleaning outputs and compare every listed mart checksum, not only row counts. |
| AC-6 | CLI integration test | `tests/test_reproducibility_manifest.py::test_reproducibility_check_passes_for_pinned_reference` | Run the checker against a manifest matching `expected_checksums.json` and assert zero exit status and success output. |
| AC-7 | CLI integration test | `tests/test_reproducibility_manifest.py::test_reproducibility_check_names_divergent_mart_and_fails` | Alter one mart checksum in a temporary manifest, assert non-zero exit status, and assert the mart name appears in diagnostics. |
| AC-8 | CLI integration test | `tests/test_reproducibility_manifest.py::test_reproducibility_check_rejects_missing_source` | Remove one declared source entry from the manifest, assert non-zero exit status, and assert the missing source identity appears in diagnostics. |
| Edge case | Unit test (negative) | `tests/test_reproducibility_manifest.py::test_missing_source_snapshot_fails_build` | Remove a declared source snapshot from the fixture, run the manifest step, assert non-zero exit and that no manifest is written and no mart checksums are emitted. Tests the fail-closed build-time path, distinct from AC-8 which tests the checker against an incomplete manifest. |
| Edge case | Unit test (negative) | `tests/test_reproducibility_manifest.py::test_unreadable_source_snapshot_fails_build` | Make a declared source snapshot unreadable (e.g., permissions or a directory-in-place-of-file) and assert the same fail-closed behavior as above. |

## Risks & mitigations

- **Large FoodData Central input makes hashing exceed CI budget.** Stream files
  in bounded chunks, avoid loading all rows/bytes into memory, measure the
  fixture/full-data runtime, and retain a fallback for partition-wise/parallel
  hashing only if measurement requires it.
- **Raw source layout differs between environments.** Resolve paths relative to
  the data-preparation project, normalize path separators and file ordering, and
  fail with the missing declared path rather than silently selecting an alternate
  file.
- **CSV/Parquet byte-level differences obscure semantic equality.** Source
  snapshot checksums intentionally attest to the landed snapshot content; mart
  checksums separately use canonical typed rows and exclude build-time metadata.
  The manifest records both layers distinctly.
- **Existing transformations contain unstable ordering or tie-breaks.** The
  two-clean-build test compares complete mart content and should expose the first
  divergent mart; deterministic ordering/tie-break fixes remain in scope, while
  transformation redesign remains out of scope.
- **Reference checksum drift becomes stale after a legitimate source change.**
  Require an explicit, reviewed reference-build refresh of
  `expected_checksums.json`; never rewrite expected values during the check
  itself, and document the procedure. A refresh of expected values is itself an
  event that should be recorded in `decisions.md` at close.
- **Source capture metadata is unavailable in the current landed-data layout.**
  Make the registry's capture/freeze record a required input and fail closed
  until the source snapshot is accompanied by that record; do not infer a
  timestamp from the build clock or filesystem modification time.
- **Manifest schema becomes a cross-feature incompatibility.** Version the
  manifest and checksum content contract; the manifest version increments when
  the mart list or any content-column contract changes, and the checker fails
  closed when the manifest version does not match what it expects. Keep source
  and mart fields stable and documented, and coordinate only the shared manifest
  contract with p1-002/p1-003 without taking on their graph-load or coverage
  responsibilities.
- **A new mart is added to the pipeline without being added to the checksum
  contract.** Treated as a contract change: the mart list in Design is
  authoritative, the schema.yml contract tests assert exactly the columns named
  in the contract, and the manifest version increments. A pipeline change that
  adds a mart without updating the contract fails the manifest version check
  against the checker.
- **AGENTS.md tooling block is a placeholder.** The Makefile target added by
  this feature must cite the concrete test/lint commands, but those commands are
  currently `<command>` placeholders in `AGENTS.md`. Until that block is filled
  in, the CI command set that AC-8 depends on is not actually configured, and
  the plan cannot name the concrete invocation. This is a prerequisite: `AGENTS.md`
  must be completed before the task that wires the Makefile target can be
  verified. If it is not completed as part of this feature's setup, add it as an
  explicit prerequisite task before the Makefile task.

## Scope check
Fits one working context: yes

The source manifest, mart checksum contract, checker, CI target, reference
artifact, and focused tests form one cohesive reproducibility boundary. Graph
loading, coverage reporting, source fetching, freshness evaluation, and
transformation redesign remain explicitly out of scope.

## Revision notes

- F-1 → Initial plan drafted from the approved feature specification,
  constitution, existing dbt/DuckDB pipeline, and architecture documents.
- F-2 → Constitution alignment corrected: removed R-12 (not on the prompt's
  relevant-rule list; its subject is the nutrient conflict tie-break, not
  general pipeline determinism), added R-1 (the content-column contract names
  canonical schema columns) and R-4 (the manifest carries the provenance p1-002
  needs to satisfy its edge-provenance checks).
- F-3 → Noted the cost of the Python layer in Approach, and added the
  "mart list is a contract" rule to Design plus a corresponding risk bullet and
  manifest-version behavior.
- F-4 → Split AC-4's test into positive (timestamp preserved) and negative
  (missing/invalid metadata fails closed). Clarified that the schema.yml
  contract tests assert the exact column set, not merely that named columns
  exist.
- F-5 → Stated that the expected-checksums file carries its own `schema_version`
  independent of the manifest version, and that the checker fails closed on a
  version mismatch.
- F-6 → Removed the "plan gate is currently blocked" risk bullet. The state has
  been advanced to `specified` with `spec_hash` recorded and a history event
  appended; the gate now passes.
- F-7 → Plan review fix: added two Edge case test rows covering the spec's
  "missing or unreadable source snapshot at build time must fail" behavior
  (`test_missing_source_snapshot_fails_build`,
  `test_unreadable_source_snapshot_fails_build`). This closes the gap between
  Design ("fails closed on missing/empty/unhashable input") and Test strategy.
- F-8 → Elevated "AGENTS.md tooling block is a placeholder" from a nit to a
  risk bullet naming the prerequisite: the Makefile task cannot be verified
  until the tooling block is filled in.
- F-9 → Named the manifest-target scope decision in Approach: the manifest step
  runs in both dev and CI targets, with a fallback to on-demand in dev if the
  step proves too slow.


## Tasks
<!-- Added after plan review APPROVE. Tasks are hashed into state.json and are frozen for this implementation loop. Do not edit without a recorded loop-back. -->
- [x] **T-1** Verify the concrete test, lint, and typecheck commands required by the project tooling contract before wiring the Makefile target; if `AGENTS.md` still contains placeholders, stop the Makefile work and route the prerequisite upstream rather than inventing commands.
    - Type: prerequisite
    - Covers: CI/build verification prerequisite for AC-6, AC-7, AC-8
    - Files: `AGENTS.md`
    - Done when: The concrete commands are available to the Makefile task, or an explicit upstream blocker is recorded and the dependent task is not started.
- [x] **T-2** Write failing tests for source declaration, source checksum recomputation, observation metadata, and fail-closed missing/unreadable source behavior.
    - Type: test
    - Covers: AC-2, AC-3, AC-4; edge cases for missing or unreadable source snapshots and missing/invalid capture metadata
    - Files: `SystemCode/remy/data-preparation/tests/test_reproducibility_manifest.py`
    - Done when: Tests assert exactly three complete source entries, checksum equality and changed-content divergence, preserved capture timestamps, and non-zero failure with no manifest or mart checksums for missing/unreadable inputs.
- [x] **T-3** Write a failing clean-build integration test for the required output set.
    - Type: test
    - Covers: AC-1
    - Files: `SystemCode/remy/data-preparation/tests/test_reproducibility_manifest.py`
    - Done when: The test invokes the fixture build path and asserts all canonical marts, `graph_quality_manifest`, and one source snapshot manifest are emitted.
- [x] **T-4** Write a failing two-clean-build integration test for canonical mart content equality.
    - Type: test
    - Covers: AC-5
    - Files: `SystemCode/remy/data-preparation/tests/test_reproducibility_manifest.py`
    - Done when: Two clean builds from identical pinned fixtures compare content checksums for every mart in the checksum contract, not merely row counts.
- [x] **T-5** Write failing checker tests for reference success, divergent-mart diagnostics, missing-source diagnostics, and version/mart completeness failures.
    - Type: test
    - Covers: AC-6, AC-7, AC-8
    - Files: `SystemCode/remy/data-preparation/tests/test_reproducibility_manifest.py`
    - Done when: The checker returns zero for matching pinned values, returns non-zero and names the divergent mart for a mismatch, and returns non-zero and names the missing source for an incomplete manifest.
- [x] **T-6** Write failing dbt contract tests for the exact content-column set of every reproducibility-facing mart.
    - Type: test
    - Covers: AC-5 and the mart-list/content-column contract edge case
    - Files: `SystemCode/remy/data-preparation/models/mart/schema.yml`, `SystemCode/remy/data-preparation/tests/test_reproducibility_manifest.py`
    - Done when: A silent mart column addition, rename, or omission is detected by the contract test, and the test covers all seven node/edge marts plus `graph_quality_manifest`.
- [x] **T-7** Implement the versioned source registry and streaming source snapshot hashing with deterministic multi-file framing and required capture/freeze metadata validation.
    - Type: impl
    - Covers: AC-2, AC-3, AC-4; missing, empty, unreadable, and invalid-metadata edge cases
    - Files: `SystemCode/remy/data-preparation/reproducibility/source_registry.json`, `SystemCode/remy/data-preparation/scripts/reproducibility_manifest.py`
    - Done when: Exactly the three declared sources are resolved relative to the data-preparation project, all required inputs are validated before output, checksums are recomputable from source content, and observation timestamps never fall back to build time.
- [x] **T-8** Implement manifest assembly after dbt materialization, including schema version, source entries, mart entries, row counts, and the authoritative mart/content-column contract.
    - Type: impl
    - Covers: AC-1, AC-2, AC-4, AC-5
    - Files: `SystemCode/remy/data-preparation/scripts/reproducibility_manifest.py`, `SystemCode/remy/data-preparation/models/mart/schema.yml`
    - Done when: A successful build emits one complete manifest only after all declared sources validate, mart rows are canonically serialized and deterministically ordered, build-time metadata is excluded, and manifest versioning is enforced.
- [x] **T-9** Implement the expected-checksums artifact and reproducibility checker with independent schema-version validation and deterministic failure diagnostics.
    - Type: impl
    - Covers: AC-6, AC-7, AC-8
    - Files: `SystemCode/remy/data-preparation/reproducibility/expected_checksums.json`, `SystemCode/remy/data-preparation/scripts/check_reproducibility.py`
    - Done when: Matching pinned checksums exit zero; any mart mismatch exits non-zero and names that mart; missing source or mart entries and incompatible manifest/expected schema versions exit non-zero with actionable names.
- [ ] **T-10** Wire the reproducible build and check into the development and CI Make targets using the verified project commands, and document operation and reference-checksum refresh procedures.
    - Type: impl
    - Covers: AC-1, AC-6, AC-7, AC-8 and the CI-budget/reference-refresh risks
    - Files: `SystemCode/Makefile`, `SystemCode/remy/data-preparation/README.md`
    - Done when: The normal configured build path and CI path run dbt, emit the manifest, and run the checker in the intended order; failures propagate non-zero; the README documents source metadata, manifest location, checker invocation, and reviewed expected-value refresh.
- [ ] **T-11** Run the focused reproducibility tests, dbt contract tests, configured lint/typecheck checks, and the reproducible build/check command; record the resulting evidence without changing the approved task wording or order.
    - Type: verification
    - Covers: AC-1 through AC-8 and all listed edge cases
    - Files: `SystemCode/remy/data-preparation/tests/test_reproducibility_manifest.py`, `SystemCode/remy/data-preparation/models/mart/schema.yml`, `SystemCode/Makefile`
    - Done when: Test-first failures are resolved, all focused and configured checks pass, the checker demonstrates both zero and non-zero paths, and CI evidence is produced for the feature.
