# Amendment proposal

status: approved
Proposed by: Kiro (specification agent), on behalf of p2-002 spec review
Date: 2026-10-07

## Trigger

Phase review of p2-002-cost-nutrition-calculation, blocker 1. The spec review
observed that R-4's "freshness timestamp" and R-8's "threshold" language do not
match the deployed graph, which carries a two-value `freshness_status`
(`fresh` / `unknown`) on `FULFILLS` and no freshness timestamp on any edge.
The mismatch is between the constitution's vocabulary and the schema the
constitution is supposed to govern. The fix is to the constitution's wording,
not to the graph.

## Current rule(s)

### R-4 Graph provenance preserved on every linking record
- Rule: Every linking record must preserve provenance — source, source ID /
  snapshot, mapping confidence, mapping/normalization version, and freshness
  timestamp — on the `REQUIRES` and `FULFILLS` edges that connect recipes, food
  concepts, nutrition profiles, and offers.
- Why: Proposal G-4, G-7; Neo4j design doc.
- Check: Named test fixture — `tests/graph/test_edge_provenance.py` writes a
  populated `REQUIRES` and `FULFILLS` edge through the code path that creates them
  and asserts every provenance property is non-null on read.

## Proposed change

Replace R-4's rule text and check to describe the provenance vocabulary that
the deployed graph actually carries. The freshness property is a declared
status, not a timestamp. Every other provenance property in R-4 stays as-is.

**New rule text:**

### R-4 Graph provenance preserved on every linking record
- Rule: Every linking record must preserve provenance — source, source ID /
  snapshot, mapping confidence, mapping/normalization version, and a declared
  freshness signal — on the `REQUIRES` and `FULFILLS` edges that connect
  recipes, food concepts, nutrition profiles, and offers. The freshness signal
  must be present and non-null on every such edge; its vocabulary (a status
  enum, a timestamp, or a derived field) is defined by the spec that owns the
  edge's producer.
- Why: Proposal G-4, G-7; Neo4j design doc. The change from "timestamp" to
  "declared freshness signal" matches the deployed `FULFILLS.freshness_status`
  property, which is a two-value enum (`fresh` / `unknown`) declared by the
  graph projection. The constitution governs provenance presence; the spec
  governs vocabulary.
- Check: Named test fixture — `tests/graph/test_edge_provenance.py` writes a
  populated `REQUIRES` and `FULFILLS` edge through the code path that creates
  them and asserts every provenance property is non-null on read, including
  the freshness signal.

## Impact

- **p1-002-provenance-graph-model** — closed. Its AC-3/AC-4/AC-8 write/read
  tests assert every provenance property is non-null. If the edge's
  freshness property is `freshness_status`, the tests already pass against the
  new wording. If the tests assert a timestamp-named property that does not
  exist, the tests were passing vacuously or were skipped; the phase review
  should verify which.
- **p2-002-cost-nutrition-calculation** — in flight. Its spec (2026-10-07) reads
  `freshness_status` into the trace and does not perform time arithmetic.
  Under the new R-4 wording, the spec is conformant.
- **p2-001-constraint-evidence-filtering** — closed. Its freshness predicate is
  the trigger for the companion R-8 amendment. See A-002.
- **p1-001-reproducible-source-pipeline**, **p1-003-coverage-quality-reporting**
  — not affected; they do not rely on a freshness timestamp.
- No code change is required by this amendment. It corrects the constitution's
  vocabulary to match the deployed schema.

## Version bump
1.1 -> 1.2

## Human decision
- Reviewer:
- Decision:
- Date:
