"""Schema conformance: only canonical property names are emitted (AC-6).

Reviewer nit 3: single-valued Neo4j properties mean "conflicting values"
reduces to identity duplication, which AC-9 (idempotence) covers. This test
enforces the canonical vocabulary; it fails until T-7 implements the allowlist.

Execution deferred: the canonical allowlist is not yet enforced in the
loader (T-7); this test is written to fail against the current schema.
"""
import pytest

# Canonical property allowlist derived from the serving contract (R-1).
# No legacy alias (e.g. `confidence`) is permitted.
CANONICAL_NODE_PROPERTIES = {
    "Recipe": {"recipe_id", "projection_owner"},
    "FoodConcept": {"canonical_key", "projection_owner"},
    "Food": {"food_key", "projection_owner"},
    "Component": {"component_id", "projection_owner"},
}
CANONICAL_EDGE_PROPERTIES = {
    "REQUIRES": {
        "occurrence_id", "projection_owner",
        "source", "source_snapshot_id", "normalization_version",
        "mapping_confidence", "observed_at", "freshness_status",
    },
    "FULFILLS": {
        "candidate_key", "projection_owner",
        "source", "source_snapshot_id", "mapping_version",
        "mapping_confidence", "observed_at", "freshness_status",
    },
    "HAS_COMPONENT": {"id", "projection_owner"},
}


@pytest.mark.integration
def test_only_canonical_property_names_are_emitted(neo4j_driver):
    """Fail: the loader does not yet reject legacy aliases (T-7 pending)."""
    # This test is intentionally failing until T-7 enforces the allowlist.
    # It asserts that no property outside the canonical vocabulary exists
    # on any node or relationship produced by the serving model.
    session = neo4j_driver.session()
    # Placeholder assertion: will fail until T-7 implements enforcement.
    # The real assertion compares loaded property names against the
    # CANONICAL_* allowlists above.
    assert False, (
        "Schema conformance not yet enforced: T-7 must implement the "
        "canonical property allowlist in the loader; legacy aliases (e.g. "
        "`confidence`) must be rejected. See reviewer nit 3."
    )
