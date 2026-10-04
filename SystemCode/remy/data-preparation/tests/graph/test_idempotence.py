"""AC-9 idempotence test (real Neo4j)."""
import pytest


@pytest.mark.integration
def test_repeated_accepted_load_is_content_identical(neo4j_driver):
    """AC-9: two loads with the same identity produce identical results (real Neo4j)."""
    import importlib.util
    from pathlib import Path
    path = Path(__file__).parents[2] / "models" / "serving" / "recipe_graph_to_neo4j.py"
    spec = importlib.util.spec_from_file_location("recipe_graph_to_neo4j", path)
    assert spec is not None and spec.loader is not None
    serving = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(serving)

    payload = [{
        "recipe_id": "r1", "occurrence_id": "o1", "normalized_name": "carrot",
        "source": "josephrmartinez/recipe-dataset",
        "source_snapshot_id": "recipe-dataset-v1",
        "normalization_version": "recipe-food-v4",
        "mapping_confidence": 0.93,
        "observed_at": "2026-09-01T00:00:00+00:00",
        "freshness_status": "snapshot",
    }]
    session = neo4j_driver.session()
    serving.load_edges(session, "REQUIRES", payload, owner="remy_recipe_graph")
    # Second load with identical identity: MERGE prevents duplication.
    serving.load_edges(session, "REQUIRES", payload, owner="remy_recipe_graph")
    # Verify no duplicate relationship identity exists.
    result = session.run(
        "MATCH ()-[r:REQUIRES {occurrence_id: 'o1'}]->() RETURN count(r) AS c"
    )
    count = result.single()["c"]
    assert count == 1, f"expected 1 REQUIRES identity, found {count} (duplicate)"
