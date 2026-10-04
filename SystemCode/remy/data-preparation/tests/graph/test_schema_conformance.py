"""Schema conformance: only canonical property names are emitted (AC-6)."""
import pytest
@pytest.mark.integration
def test_only_canonical_property_names_are_emitted(neo4j_driver):
    import importlib.util
    from pathlib import Path
    path = Path(__file__).parents[2] / "models/serving/recipe_graph_to_neo4j.py"
    spec = importlib.util.spec_from_file_location("recipe_graph_to_neo4j", path)
    assert spec is not None and spec.loader is not None
    serving = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(serving)
    bad_row = {
        "recipe_id": "r1", "occurrence_id": "o1", "normalized_name": "carrot",
        "source": "josephrmartinez/recipe-dataset",
        "normalization_version": "recipe-food-v4", "mapping_confidence": 0.93,
        "observed_at": "2026-09-01T00:00:00+00:00", "freshness_status": "snapshot",
        "confidence": 0.93,
    }
    with pytest.raises(ValueError) as exc:
        serving._filter_canonical(bad_row, serving.CANONICAL_EDGE_PROPERTIES["REQUIRES"])
    assert "non-canonical" in str(exc.value)
    assert "confidence" in str(exc.value)
