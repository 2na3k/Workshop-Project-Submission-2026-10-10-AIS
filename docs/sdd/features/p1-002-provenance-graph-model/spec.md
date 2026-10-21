---
feature: p1-002-provenance-graph-model
---

# Spec - Provenance-preserving canonical graph model

## Summary

This feature makes the existing canonical graph projection provable against the
single-schema and provenance requirements. A successful graph refresh will use
the canonical recipe, food-concept, food, nutrition, offer, and relationship
model produced by the accepted data pipeline. Every populated `REQUIRES` and
`FULFILLS` linking record will retain enough provenance to identify its source
and source snapshot, the mapping or normalization version that produced the
link, the mapping confidence where applicable, and the freshness/observation
time needed to interpret the evidence. A refresh will be admitted only from an
accepted source snapshot and quality result, and will fail closed for invalid
references or incomplete provenance.

The feature is a proof-and-conformance change to the existing graph load. It
does not create a second schema or a parallel graph representation.

## Traces to

- **G-4** — "Recipe ingredients are linked to normalized nutrition profiles and
  dated retail offer evidence, with source provenance retained."
- **G-7** — "The data underlying recommendations is reproducible from source
  snapshots, quality-gated on entity counts and referential integrity, and
  queryable as a graph."
- **Roadmap phase p1 → p1-002-provenance-graph-model** *(partial)* — ensure
  populated `REQUIRES` and `FULFILLS` records carry the provenance required by
  R-4, add the single-schema conformance and edge-provenance demonstrations, and
  refuse graph refresh unless the p1-001 manifest has passed.
- **Phase p1 exit criterion** — the quality gate rejects dangling `REQUIRES` or
  `FULFILLS` references and prevents graph refresh when the manifest is not
  accepted; schema-conformance and edge-provenance checks pass for the canonical
  property names and every populated linking record.
- **Constitutional rules:** **R-1** (single schema, no dual support), **R-4**
  (graph provenance on every linking record), and **R-15** (reproducible,
  quality-gated data).

## User-facing behavior

There is no direct end-user UI surface. The observable consumers are the data
operator and downstream recommendation services that query the graph.

- An operator running a refresh from an accepted source snapshot and quality
  result gets a graph containing the canonical node and relationship model.
- A downstream query can follow a recipe requirement to its normalized food
  concept and then inspect compatible food or dated offer evidence without
  losing the source, snapshot, mapping/normalization, confidence, or freshness
  context of the linking record.
- A refresh based on a missing, failed, or incomplete quality result is rejected
  before it can publish a new graph state, and the operator receives a failure
  that identifies the failed admission condition.
- A refresh that would create a dangling recipe, food-concept, food, nutrition,
  or offer reference is rejected rather than publishing an incomplete graph.
- A consumer sees one canonical property vocabulary. Legacy or alternate names
  are not accepted as aliases for the same concept.

## Acceptance criteria

- **AC-1** Given a source snapshot manifest and quality result that identify all
  required inputs and report accepted entity counts and referential integrity,
  when a graph refresh is requested, then the refresh is admitted and publishes
  the canonical recipe, food-concept, food, nutrition, offer, and relationship
  records for that build.

- **AC-2** Given a source snapshot manifest that is missing, invalid, or reports
  a failed quality result, when a graph refresh is requested, then the refresh
  fails with an admission error before publishing new projection data; the
  graph's node and relationship counts and a sample of previously observed
  records are unchanged from before the attempted refresh.

- **AC-3** Given a build containing a populated `REQUIRES` linking record, when
  that record is read from the graph, then it identifies its source and source
  snapshot, the normalization or mapping version applicable to the link, the
  mapping confidence applicable to the link, and a non-empty freshness or
  observation timestamp.

- **AC-4** Given a build containing a populated `FULFILLS` linking record, when
  that record is read from the graph, then it identifies its source and source
  snapshot, the mapping version applicable to the link, its mapping confidence,
  and a non-empty freshness or observation timestamp.

- **AC-5** Given any populated `REQUIRES` or `FULFILLS` record with a missing,
  blank, or invalid required provenance value, when the graph conformance check
  runs, then the check fails and names the affected relationship type or record;
  no such record is accepted as a valid graph projection.

- **AC-6** Given a canonical schema vocabulary for node and relationship
  properties, when the schema-conformance check examines the graph projection,
  then every checked concept uses exactly its canonical property name and no
  alternate property name is accepted as a second spelling of that concept.

- **AC-7** Given a build containing a `REQUIRES` or `FULFILLS` reference to a
  node that is absent from the canonical graph, when the quality or load gate
  runs, then it fails with a dangling-reference error and the graph refresh does
  not publish that build.

- **AC-8** Given a valid accepted build with populated linking records, when the
  edge-provenance check writes and then reads representative `REQUIRES` and
  `FULFILLS` records through the graph load path, then all required provenance
  values are non-null and equal to the values supplied by the accepted build.

- **AC-9** Given a valid accepted build, when the graph load runs twice against
  the same source snapshot and quality result, then the resulting graph's
  canonical linking records are content-identical: no duplicate relationship
  identity appears, and every canonical property value equals the value produced
  by the first load.

- **AC-10** Given a quality result that reports a failed entity allocation or
  referential-integrity check, when the graph load is attempted, then it exits
  non-zero and names the failed quality dimension in its error output.

## Edge cases & errors

- The source snapshot manifest exists but omits one required source, has an
  empty source identity or snapshot identity, or cannot be associated with the
  build: reject the refresh as manifest-incomplete.
- The quality result is present but its acceptance status is false, its counts
  are inconsistent, or its referential-integrity result is unavailable: reject
  the refresh; do not infer acceptance from successful upstream transformations.
- A `REQUIRES` record has no usable mapping confidence because its requirement
  is unresolved: the record cannot be treated as a valid populated link; the
  refresh or conformance check must fail rather than defaulting confidence.
- A `FULFILLS` record has a missing source snapshot or freshness timestamp for
  an offer-backed claim: reject the record rather than treating the offer as
  current or provenance-free.
- A source or version is present on a node but absent from a linking record:
  this does not satisfy edge provenance; the linking record is independently
  invalid.
- Duplicate relationship identities, duplicate canonical property aliases,
  or conflicting values for the same canonical property: fail conformance rather
  than selecting a winner implicitly.
- A refresh fails after validation but before publication: the graph must not
  expose a partially refreshed state, and the failure must be reported to the
  operator.
- An empty canonical relation is valid only when the accepted build explicitly
  reports zero rows; an absent relation or missing count is a quality-gate error.

## Non-goals

- Not redesigning the canonical graph shape, adding new recommendation
  features, or changing the downstream query experience.
- Not creating coverage or completeness measurements; those belong to
  p1-003.
- Not implementing nutrition, allergen, dietary, freshness, price, or meal-plan
  reasoning rules; those belong to later phase features.
- Not exposing audit-only provenance in the end-user response; p3 response
  contracts define that boundary.
- Not repairing missing upstream source data or replacing p1-001's source
  manifest and reproducibility responsibilities.

## Interfaces & dependencies

- **Upstream dependency:** p1-001-reproducible-source-pipeline must provide the
  source snapshot manifest and quality-gate result. Its tracked O-1 follow-up
  (restoring the data-preparation seeds and pinning a real reference checksum)
  is a prerequisite for demonstrating this feature against real data.

- **Test infrastructure dependency:** p1-001b-test-infrastructure (closed
  2026-10-04) provides the fake driver and cloud Neo4j fixtures this feature's
  tests use. The fake-driver tests (AC-1, AC-2, AC-10) use the
  `fake_driver` fixture; the real-Neo4j tests (AC-3 through AC-9) use the
  `neo4j_driver` fixture, which connects to a cloud instance via
  `NEO4J_TEST_URI` / `NEO4J_TEST_USERNAME` / `NEO4J_TEST_PASSWORD`.

- **Shared contract:** p1-003-coverage-quality-reporting consumes the accepted
  canonical graph and its quality result. This feature supplies the graph schema,
  link provenance, and admission decision; it does not own coverage metrics.

- **Graph contract:** the existing canonical node concepts and `REQUIRES`,
  `FULFILLS`, and `HAS_COMPONENT` relationship concepts remain the single
  schema. `REQUIRES` connects recipes to normalized food concepts, and
  `FULFILLS` connects foods or offers to normalized food concepts in the
  repository's established direction.

- **Admission contract:** graph refresh is allowed only after the upstream
  manifest and quality result establish accepted source snapshots, deterministic
  entity counts, and zero dangling `REQUIRES`/`FULFILLS` references. The loader
  reads the p1-001 source snapshot manifest and applies the acceptance rule at
  load time: the manifest states facts (sources, snapshots, checksums,
  timestamps, counts), and the loader decides whether those facts satisfy the
  admission criteria. The acceptance decision is not embedded in the manifest.
  Failure is fail-closed and must not publish a partial refresh.

- **Verification contract:** the feature must provide independently runnable
  schema-conformance and edge-provenance demonstrations corresponding to R-1 and
  R-4, plus a failed-manifest/dangling-reference demonstration for R-15.

- **Scope check:** the plan stage determines whether the work fits one working
  context. If the schema-conformance, edge-provenance, and admission-gate
  concerns split into independent implementation units, the plan should consider
  whether the feature should split into separate features.

## Open questions

_No blocking questions remain for specification. Any implementation-level
choice about how the canonical contract is represented or verified belongs in
the plan, subject to this specification and the constitution._

## Clarifications

_No clarifications recorded; no human clarification was required._
