"""AC-1 smoke tests for the fake driver fixture.

These tests prove the ``fake_driver`` fixture emulates the exact
driver/session/transaction surface the serving model
(``models/serving/recipe_graph_to_neo4j.py``) uses, so an orchestration test
can drive the serving model end-to-end without contacting a live Neo4j, and can
assert which statements were issued and with what parameters.
"""

import importlib.util
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


def _serving_env() -> dict[str, str]:
    return {
        "NEO4J_URI": "neo4j+s://example.databases.neo4j.io",
        "NEO4J_USERNAME": "user",
        "NEO4J_PASSWORD": "secret",
        "NEO4J_DATABASE": "neo4j",
        "NEO4J_REPLACE": "true",
    }


class _Relation:
    """Minimal stand-in for the dbt cursor-like relation the model reads."""

    def __init__(self, columns: list[str], rows: list[tuple[object, ...]]) -> None:
        self.columns = columns
        self._rows = iter(rows)

    def fetchmany(self, size: int) -> list[tuple[object, ...]]:
        return [row for _, row in zip(range(size), self._rows, strict=False)]


class _ManifestDbt:
    """dbt stand-in whose ``graph_quality_manifest`` passes the gate."""

    def config(self, **_kwargs: object) -> None:
        pass

    def ref(self, name: str) -> _Relation:
        if name == "graph_quality_manifest":
            return _Relation(
                ["entity", "row_count", "allocation", "within_allocation"],
                [
                    ("TOTAL_NODE", 8, 84200, True),
                    ("TOTAL_RELATIONSHIP", 8, 208200, True),
                ],
            )
        return _Relation(["id"], [(1,)])


class _DbtSession:
    def sql(self, query: str) -> str:
        return query


def test_serving_model_runs_through_fake(fake_driver) -> None:
    """AC-1: the serving model drives end-to-end through the fake with no live Neo4j.

    A missing method on the fake would raise ``AttributeError`` here rather than
    surfacing later in a dependent test.
    """
    with (
        patch.dict(os.environ, _serving_env(), clear=True),
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
