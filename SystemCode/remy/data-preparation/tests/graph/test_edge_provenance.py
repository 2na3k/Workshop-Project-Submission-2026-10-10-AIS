"""Real-Neo4j proof that populated linking records keep their provenance.

AC-3, AC-4, AC-5 and AC-8 cannot be proved by a fake driver: they assert what a
consumer reads back out of a live graph after the serving model's own load path
has written it. These tests therefore run against the dedicated cloud Neo4j test
instance through the ``neo4j_driver`` fixture (see ``tests/graph/conftest.py``),
which clears the database before every test.

The write path exercised here is the serving model's own: ``load_edges`` runs the
``EDGE_LOADS`` Cypher from ``models/serving/recipe_graph_to_neo4j.py`` after
applying the ``EDGE_PROVENANCE`` contract the serving schema declares. A record
that reaches the graph without that vocabulary is a projection defect, not
something a consumer can repair at query time, so every assertion compares
read-back values against the values the accepted build supplied.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

_MODEL_PATH = Path(__file__).resolve().parents[2] / "models/serving/recipe_graph_to_neo4j.py"
_spec = importlib.util.spec_from_file_location("recipe_graph_to_neo4j", _MODEL_PATH)
assert _spec is not None and _spec.loader is not None
serving = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(serving)

OWNER = serving.OWNER

# One populated record per linking type: the identity and endpoint columns the
# load statement matches on, plus the canonical provenance vocabulary the
# accepted build reports. These values are evidence from the build, never
# defaults invented when the graph is read.
REQUIRES_INPUT: dict[str, object] = {
    "recipe_id": 10234,
    "occurrence_id": "10234:1",
    "normalized_name": "carrot",
    "source": "josephrmartinez/recipe-dataset",
    "source_snapshot_id": "josephrmartinez-recipe-dataset-2026-09-01",
    "normalization_version": "recipe-food-v4",
    "mapping_confidence": 0.93,
    "observed_at": "2026-09-01T00:00:00+00:00",
    "freshness_status": "snapshot",
}
FULFILLS_INPUT: dict[str, object] = {
    "candidate_key": "candidate:0f1e2d3c4b5a6978899aabbccddeeff00112233445566778899aabbccddeeff",
    "food_key": "fdc:516627",
    "canonical_key": "carrot",
    "source": "fooddata_central",
    "source_snapshot_id": "usda-fooddata-central-2026-09-01",
    "mapping_version": "recipe_food_to_dbt:v4",
    "mapping_confidence": 0.88,
    "observed_at": "2026-09-02T00:00:00+00:00",
    "freshness_status": "snapshot",
}
# (relationship, identity property, input record)
CASES = (
    ("REQUIRES", "occurrence_id", REQUIRES_INPUT),
    ("FULFILLS", "candidate_key", FULFILLS_INPUT),
)


def _required_provenance(relationship: str) -> list[str]:
    """The canonical provenance properties the serving contract requires."""
    contract = getattr(serving, "EDGE_PROVENANCE", None)
    assert contract is not None, "the serving model declares no EDGE_PROVENANCE contract"
    assert relationship in contract, f"EDGE_PROVENANCE declares no contract for {relationship}"
    return list(contract[relationship])


def _seed_endpoints(session) -> None:
    """Create the canonical nodes a populated linking record points at."""
    session.run(
        "CREATE (:Recipe {recipe_id: $recipe_id, projection_owner: $owner})",
        recipe_id=REQUIRES_INPUT["recipe_id"],
        owner=OWNER,
    )
    session.run(
        "CREATE (:FoodConcept {canonical_key: $canonical_key, projection_owner: $owner})",
        canonical_key="carrot",
        owner=OWNER,
    )
    session.run(
        "CREATE (:Food {food_key: $food_key, projection_owner: $owner})",
        food_key=FULFILLS_INPUT["food_key"],
        owner=OWNER,
    )


def _read_back(session, relationship: str, identity: str, value: object) -> dict[str, object]:
    record = session.run(
        f"MATCH ()-[e:{relationship} {{{identity}: $value}}]->() RETURN properties(e) AS properties",
        value=value,
    ).single()
    assert record is not None, f"{relationship} {value!r} was not projected into the graph"
    return dict(record["properties"])


def test_requires_provenance_is_preserved(neo4j_driver) -> None:
    """AC-3: a populated REQUIRES record reads back with full requirement provenance."""
    required = _required_provenance("REQUIRES")
    assert {"source", "source_snapshot_id", "normalization_version", "mapping_confidence",
            "observed_at", "freshness_status"}.issubset(set(required)), (
        "the serving contract must declare source, source snapshot, normalization "
        f"version, mapping confidence and freshness for REQUIRES, found {sorted(required)}"
    )

    with neo4j_driver.session() as session:
        _seed_endpoints(session)
        serving.load_edges(session, "REQUIRES", [dict(REQUIRES_INPUT)], OWNER)

    with neo4j_driver.session() as session:
        properties = _read_back(session, "REQUIRES", "occurrence_id", REQUIRES_INPUT["occurrence_id"])

    for name in required:
        assert name in properties, f"REQUIRES record is missing provenance property {name}"
        value = properties[name]
        assert value not in (None, ""), f"REQUIRES provenance {name} is blank in the graph"
        assert value == REQUIRES_INPUT[name], f"REQUIRES {name} changed on projection: {value!r}"


def test_fulfills_provenance_is_preserved(neo4j_driver) -> None:
    """AC-4: a populated FULFILLS record reads back with full fulfillment provenance."""
    required = _required_provenance("FULFILLS")
    assert {"source", "source_snapshot_id", "mapping_version", "mapping_confidence",
            "observed_at", "freshness_status"}.issubset(set(required)), (
        "the serving contract must declare source, source snapshot, mapping version, "
        f"mapping confidence and freshness for FULFILLS, found {sorted(required)}"
    )

    with neo4j_driver.session() as session:
        _seed_endpoints(session)
        serving.load_edges(session, "FULFILLS", [dict(FULFILLS_INPUT)], OWNER)

    with neo4j_driver.session() as session:
        properties = _read_back(session, "FULFILLS", "candidate_key", FULFILLS_INPUT["candidate_key"])

    for name in required:
        assert name in properties, f"FULFILLS record is missing provenance property {name}"
        value = properties[name]
        assert value not in (None, ""), f"FULFILLS provenance {name} is blank in the graph"
        assert value == FULFILLS_INPUT[name], f"FULFILLS {name} changed on projection: {value!r}"


@pytest.mark.parametrize("relationship,identity,record", CASES)
def test_missing_provenance_fails(neo4j_driver, relationship, identity, record) -> None:
    """AC-5: the load path refuses a populated link with missing or blank provenance.

    Node-level provenance does not satisfy edge-level provenance, so a linking
    record that omits or blanks one required value is rejected rather than
    published with a default, and the graph keeps its prior state.
    """
    required = _required_provenance(relationship)
    assert required, f"EDGE_PROVENANCE declares no required provenance for {relationship}"

    with neo4j_driver.session() as session:
        _seed_endpoints(session)
        before = session.run("MATCH ()-[e]->() RETURN count(e) AS total").single()["total"]

        for name in required:
            for defective_value in (None, ""):
                with pytest.raises(ValueError) as error:
                    serving.load_edges(
                        session, relationship, [{**record, name: defective_value}], OWNER
                    )
                message = str(error.value)
                assert relationship in message, f"error must name {relationship}: {message}"
                assert name in message, f"error must name the affected provenance {name}: {message}"

        after = session.run("MATCH ()-[e]->() RETURN count(e) AS total").single()["total"]

    assert after == before, f"a refused {relationship} record must not reach the graph"


def test_write_read_provenance_matches_input(neo4j_driver) -> None:
    """AC-8: writing then reading through the load path preserves every supplied value."""
    with neo4j_driver.session() as session:
        _seed_endpoints(session)
        for relationship, _identity, case in CASES:
            serving.load_edges(session, relationship, [dict(case)], OWNER)

    with neo4j_driver.session() as session:
        for relationship, identity, case in CASES:
            properties = _read_back(session, relationship, identity, case[identity])
            required = _required_provenance(relationship)
            projected = {name: properties.get(name) for name in required}
            supplied = {name: case[name] for name in required}
            assert projected == supplied, (
                f"{relationship} provenance differs after write/read through the "
                f"load path: supplied {supplied}, projected {projected}"
            )
            # The link must stay traversable in the deployed direction.
            endpoint = session.run(
                f"MATCH ()-[e:{relationship} {{{identity}: $value}}]->(fc:FoodConcept) "
                "RETURN fc.canonical_key AS canonical_key",
                value=case[identity],
            ).single()
            assert endpoint is not None and endpoint["canonical_key"] == "carrot"
