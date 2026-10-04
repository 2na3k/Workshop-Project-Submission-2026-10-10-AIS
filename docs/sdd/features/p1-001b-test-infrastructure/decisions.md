# Decisions - Graph test infrastructure

## Decisions

### D-1 Testcontainers, not a shared CI service
- Date: 2026-10-04
- Context: The integration fixture needs a Neo4j instance. A shared CI service
  would require lifecycle coordination and cross-test state management; a
  per-session container is self-contained.
- Decision: Use `testcontainers` for the integration fixture, session-scoped.
- Alternatives: `docker compose` service — rejected for state management
  complexity; a pre-provisioned Neo4j — rejected for portability.
- Affects: Every integration test in the data-preparation package.
- Source: p1-001b plan, Design section 2.

## Overrides
None.
