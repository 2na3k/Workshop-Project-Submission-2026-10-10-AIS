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

### D-4 Defer dbt singular test execution pending p1-001 O-1
- Date: 2026-10-04
- Context: `tests/mart_edge_provenance.sql` cannot execute because `make dbt`
  fails at the staging layer (missing seeds, per p1-001's O-1). The test file
  is written and its assertions are complete; only its execution is deferred.
- Decision: Write the test; defer execution. Same class as p1-001's F-3.
- Alternatives: Skip the test entirely (rejected — the file must exist for
  the feature to be complete); substitute a Python fixture-based duplicate
  (rejected — duplicates dbt logic, risks drift); block the feature
  (rejected — the rest is independent).
- Affects: AC-5, AC-7; the review's dbt-test evidence.
- Source: Plan T-5; p1-001 decisions O-1.

## Overrides
None.
