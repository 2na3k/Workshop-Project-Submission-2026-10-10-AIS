"""AC-1 smoke tests for the fake driver fixture.

These tests prove the ``fake_driver`` fixture emulates the exact
driver/session/transaction surface the serving model
(``models/serving/recipe_graph_to_neo4j.py``) uses, so an orchestration test
can drive the serving model end-to-end without contacting a live Neo4j, and can
assert which statements were issued and with what parameters.

The smoke fixtures supply an *accepted* build: since p1-002 the model decides
admission from the p1-001 source snapshot manifest plus ``graph_quality_manifest``
before it opens a session, so the fixture has to provide both for the model to
reach the driver surface the smoke test is asserting.
"""

import importlib.util
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest


_PACKAGE_ROOT = Path(__file__).parents[1]
_spec = importlib.util.spec_from_file_location(
    "recipe_graph_to_neo4j_fake_smoke",
    _PACKAGE_ROOT / "models" / "serving" / "recipe_graph_to_neo4j.py",
)
assert _spec is not None and _spec.loader is not None
serving = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(serving)

_CHECKSUM = "0" * 64
_SNAPSHOTS = {
    "FoodData Central": "usda-fooddata-central-2026-09-01",
    "recipe dataset": "josephrmartinez-recipe-dataset-2026-09-01",
    "FairPrice listings": "fairprice-listings-2026-09-02",
}
# One row per canonical entity; totals are the sums the model recomputes.
_MART_ROWS = {
    "node_recipe": 1,
    "node_food_concept": 1,
    "node_food": 1,
    "node_component": 1,
    "edge_requires": 1,
    "edge_fulfills": 1,
    "edge_has_component": 1,
    "graph_quality_manifest": 9,
    "coverage_quality_report": 5,
}
_QUALITY_ROWS = [
    ("node", "Recipe", 1, 14000, True),
    ("node", "FoodConcept", 1, 35000, True),
    ("node", "Food", 1, 32000, True),
    ("node", "Component", 1, 3200, True),
    ("relationship", "REQUIRES", 1, 155000, True),
    ("relationship", "FULFILLS", 1, 50000, True),
    ("relationship", "HAS_COMPONENT", 1, 3200, True),
    ("node", "TOTAL_NODE", 4, 84200, True),
    ("relationship", "TOTAL_RELATIONSHIP", 3, 208200, True),
]
# (key column, rows) per canonical mart, with linking endpoints that resolve and
# the canonical edge provenance the serving contract requires (R-4). The accepted
# snapshot id, observation time and requirement freshness basis are applied by the
# loader from the manifest, so they are not fixture columns here.
_RELATIONS: dict[str, tuple[list[str], list[tuple[object, ...]]]] = {
    "node_recipe": (["recipe_id"], [("r1",)]),
    "node_food_concept": (["canonical_key"], [("carrot",)]),
    "node_food": (["food_key"], [("f1",)]),
    "node_component": (["component_id"], [("c1",)]),
    "edge_requires": (
        ["recipe_id", "occurrence_id", "normalized_name", "source",
         "normalization_version", "mapping_confidence",
         "observed_at", "freshness_status"],
        [("r1", "o1", "carrot", "josephrmartinez/recipe-dataset",
          "recipe-food-v4", 1.0,
          "2026-09-01T00:00:00+00:00", "snapshot")],
    ),
    "edge_fulfills": (
        ["candidate_key", "food_key", "canonical_key", "source", "mapping_version",
         "mapping_confidence", "observed_at", "freshness_status"],
        [("k1", "f1", "carrot", "fooddata_central", "recipe_food_to_dbt:v4", 1.0,
          "2026-09-02T00:00:00+00:00", "snapshot")],
    ),
    "edge_has_component": (["id", "food_key", "component_id"], [("h1", "f1", "c1")]),
}


def _serving_env(manifest: str) -> dict[str, str]:
    return {
        "NEO4J_URI": "neo4j+s://example.databases.neo4j.io",
        "NEO4J_USERNAME": "user",
        "NEO4J_PASSWORD": "secret",
        "NEO4J_DATABASE": "neo4j",
        "NEO4J_REPLACE": "true",
        "NEO4J_SOURCE_MANIFEST": manifest,
    }


def _accepted_manifest(directory: Path) -> str:
    document = {
        "schema_version": 2,
        "contract_version": 1,
        "sources": [
            {"source_identity": identity, "snapshot_id": snapshot,
             "content_checksum": _CHECKSUM, "observation_timestamp": "2026-09-01T00:00:00+00:00",
             "paths": ["seeds"]}
            for identity, snapshot in _SNAPSHOTS.items()
        ],
        "marts": {
            mart: {"row_count": rows, "content_checksum": _CHECKSUM,
                   "content_columns": ["id"], "contract_version": 1}
            for mart, rows in _MART_ROWS.items()
        },
    }
    target = directory / "source_snapshot_manifest.json"
    target.write_text(json.dumps(document), encoding="utf-8")
    return str(target)


class _Relation:
    """Minimal stand-in for the dbt cursor-like relation the model reads."""

    def __init__(self, columns: list[str], rows: list[tuple[object, ...]]) -> None:
        self.columns = columns
        self._rows = iter(rows)

    def fetchmany(self, size: int) -> list[tuple[object, ...]]:
        return [row for _, row in zip(range(size), self._rows, strict=False)]


class _ManifestDbt:
    """dbt stand-in whose quality manifest and marts form an accepted build."""

    def config(self, **_kwargs: object) -> None:
        pass

    def ref(self, name: str) -> _Relation:
        if name == "graph_quality_manifest":
            return _Relation(
                ["entity_type", "entity", "row_count", "allocation", "within_allocation"],
                list(_QUALITY_ROWS),
            )
        columns, rows = _RELATIONS[name]
        return _Relation(columns, rows)


class _DbtSession:
    def sql(self, query: str) -> str:
        return query


def test_serving_model_runs_through_fake(fake_driver, tmp_path) -> None:
    """AC-1: the serving model drives end-to-end through the fake with no live Neo4j.

    A missing method on the fake would raise ``AttributeError`` here rather than
    surfacing later in a dependent test.
    """
    with (
        patch.dict(os.environ, _serving_env(_accepted_manifest(tmp_path)), clear=True),
        patch.object(
            serving.GraphDatabase, "driver", return_value=fake_driver
        ) as connect,
    ):
        result = serving.model(_ManifestDbt(), _DbtSession())

    connect.assert_called_once_with(
        "neo4j+s://example.databases.neo4j.io", auth=("user", "secret")
    )
    assert isinstance(result, str)
    assert fake_driver.records
    assert fake_driver.transaction.committed


def test_fake_records_statements(fake_driver) -> None:
    """AC-1: the fixture records each ``run(cypher, **params)`` in call order."""
    session = fake_driver.session(database="neo4j")
    session.run("MATCH (n) RETURN count(n) AS nodes", db="neo4j")
    transaction = session.begin_transaction()
    transaction.run(
        "MERGE (n:Recipe {recipe_id: $id})", id="r1", owner="remy_recipe_graph"
    )

    assert fake_driver.records[0] == (
        "MATCH (n) RETURN count(n) AS nodes",
        {"db": "neo4j"},
    )
    assert fake_driver.records[1] == (
        "MERGE (n:Recipe {recipe_id: $id})",
        {"id": "r1", "owner": "remy_recipe_graph"},
    )
    assert [cypher for cypher, _ in fake_driver.records] == [
        "MATCH (n) RETURN count(n) AS nodes",
        "MERGE (n:Recipe {recipe_id: $id})",
    ]


def test_integration_marker_registered(pytestconfig: pytest.Config) -> None:
    """AC-4: the ``integration`` marker is registered (see pyproject.toml).

    The plan expects this assertion to fail until the marker is registered in
    ``pyproject.toml``; T-2 landed that registration, so it is green here. The
    ``-m "not integration"`` filter behavior itself is exercised at the CI level
    (Design section 4), not by invoking pytest as a subprocess.
    """
    markers = pytestconfig.getini("markers")
    assert any(
        line.split(":", 1)[0].strip() == "integration" for line in markers
    ), f"'integration' marker not registered; found: {markers}"
