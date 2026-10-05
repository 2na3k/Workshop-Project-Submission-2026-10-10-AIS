# Decisions - Provenance-preserving canonical graph model

## Decisions

### D-1 Canonical property allowlists enforced at load
- Date: 2026-10-04
- Context: R-1 requires a single canonical schema with no dual support.
- Decision: The loader enforces CANONICAL_NODE_PROPERTIES and
  CANONICAL_EDGE_PROPERTIES and rejects any property outside them.
- Alternatives: Rely on the mart to emit only canonical names (rejected —
  the loader is the last line of defense); accept both canonical and legacy
  names as aliases (rejected by R-1).
- Affects: AC-6; every graph load.
- Source: Plan T-7.

### D-2 Idempotence via MERGE on identity keys
- Date: 2026-10-04
- Context: AC-9 requires two accepted loads to produce content-identical
  linking records with no duplicate identity.
- Decision: Use MERGE with the canonical identity keys
  (REQUIRES.occurrence_id, FULFILLS.candidate_key) so a second load updates
  rather than duplicates.
- Alternatives: Clear-and-reload (rejected — the ownership-scoped cleanup is
  destructive by design and shouldn't run on a redundant second load);
  reject the second load (rejected — AC-9 requires it to complete).
- Affects: AC-9.
- Source: Plan T-10.

### D-3 Reject populated links with missing provenance; never repair
- Date: 2026-10-04
- Context: F-2 — the loader default-filled missing source_snapshot_id,
  observed_at, and freshness_status from the manifest. R-4 and AC-5 require
  missing required provenance to be rejected, not synthesized.
- Decision: `_stamp_provenance` calls `_assert_edge_provenance` per row;
  missing or invalid provenance raises before the row is written, and the
  transaction rolls back.
- Alternatives: Default-fill from the manifest (the original behavior —
  rejected, hides incomplete links); skip the record silently (rejected,
  the record's absence would be invisible to the operator).
- Affects: AC-5; R-4.
- Source: Review F-2.

### D-4 Defer dbt singular test execution pending the data-preparation price-path finding
- Date: 2026-10-04
- Context: `tests/mart_edge_provenance.sql` cannot execute because `make dbt`
  fails at the parse stage. The block is upstream, in the data-preparation
  package, at `models/staging/stg_retail_listing.sql`, which references
  `retail_aisle_listing` and `retail_search_listing` — two nodes that no
  model, seed, or source produces. The seeds themselves are present and
  used by the other staging models. The data-preparation package is not
  owned by this effort; see `docs/findings/data-prep-price-path.md`.
- Decision: The test file is written and its assertions are complete;
  execution is deferred pending the price-path finding's resolution. Same
  class as p1-001's F-3 and p1-003's D-1.
- Alternatives: Skip the test entirely (rejected — the file must exist for
  the feature to be complete); substitute a Python fixture-based duplicate
  (rejected — duplicates dbt logic, risks drift); modify the
  data-preparation package to rewire the price path (rejected — out of
  scope; the change is the package owner's to make); block the feature
  (rejected — the rest is independent).
- Affects: AC-5, AC-7; the review's dbt-test evidence.
- Source: Plan T-5; `docs/findings/data-prep-price-path.md`.

## Overrides
None.
