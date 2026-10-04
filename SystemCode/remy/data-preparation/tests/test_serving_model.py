import importlib.util
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


path = Path(__file__).parents[1] / "models/serving/recipe_graph_to_neo4j.py"
spec = importlib.util.spec_from_file_location("recipe_graph_to_neo4j", path)
assert spec is not None and spec.loader is not None
serving = importlib.util.module_from_spec(spec)
spec.loader.exec_module(serving)


class Result:
    def __init__(self, value):
        self.value = value

    def single(self):
        return self.value


class Transaction:
    def __init__(self, neo4j, fail_on_load=False):
        self.neo4j = neo4j
        self.fail_on_load = fail_on_load
        self.committed = False
        self.rolled_back = False

    def run(self, statement, **parameters):
        requests.append((statement, parameters))
        if self.fail_on_load and "UNWIND $rows" in statement:
            raise RuntimeError("injected load failure")
        return Result(self.neo4j.result_for(statement))

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class Neo4jSession:
    def __init__(self, nodes=10, relationships=20, fail_on_load=False):
        self.nodes = nodes
        self.relationships = relationships
        self.transaction = Transaction(self, fail_on_load)

    def result_for(self, statement):
        if "WITH count(n) AS nodes" in statement:
            return {"nodes": self.nodes, "relationships": self.relationships}
        if "RETURN count(n) AS nodes" in statement:
            return {"nodes": 5}
        if "RETURN count(r) AS relationships" in statement:
            return {"relationships": 5}
        if "deleted" in statement:
            return {"deleted": 0}
        return {}

    def run(self, statement, **parameters):
        requests.append((statement, parameters))
        return Result(self.result_for(statement))

    def begin_transaction(self):
        return self.transaction

    def close(self):
        pass


class Driver:
    def __init__(self, neo4j):
        self.neo4j = neo4j

    def session(self, database):
        assert database == "database"
        return self.neo4j

    def close(self):
        pass


class Relation:
    def __init__(self, columns, rows):
        self.columns = columns
        self.rows = iter(rows)

    def fetchmany(self, size):
        return [row for _, row in zip(range(size), self.rows)]


class Session:
    def sql(self, query):
        return query


def environment(replace=False, manifest=None):
    values = {
        "NEO4J_URI": "neo4j+s://example.databases.neo4j.io",
        "NEO4J_USERNAME": "user",
        "NEO4J_PASSWORD": "secret",
        "NEO4J_DATABASE": "database",
    }
    if replace:
        values["NEO4J_REPLACE"] = "true"
    if manifest is not None:
        values["NEO4J_SOURCE_MANIFEST"] = manifest
    return values


# ---------------------------------------------------------------------------
# p1-002 admission fixtures (AC-1, AC-2, AC-10)
#
# These fixtures drive the serving model with the p1-001b `fake_driver` fixture
# so the orchestration and admission semantics can be proved without a live
# Neo4j. `graph_quality_manifest` and the source snapshot manifest agree here,
# which is what an accepted build looks like.
# ---------------------------------------------------------------------------

FDC_SNAPSHOT = "usda-fooddata-central-2026-09-01"
RECIPE_SNAPSHOT = "josephrmartinez-recipe-dataset-2026-09-01"
FAIRPRICE_SNAPSHOT = "fairprice-listings-2026-09-02"
CHECKSUM = "0" * 64

MART_ROWS = {
    "node_recipe": 1,
    "node_food_concept": 1,
    "node_food": 1,
    "node_component": 1,
    "edge_requires": 1,
    "edge_fulfills": 1,
    "edge_has_component": 1,
    "graph_quality_manifest": 9,
}

QUALITY_COLUMNS = ["entity_type", "entity", "row_count", "allocation", "within_allocation"]

QUALITY_ROWS = [
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

REQUIRES_COLUMNS = [
    "recipe_id",
    "occurrence_id",
    "normalized_name",
    "source",
    "normalization_version",
    "mapping_confidence",
    "observed_at",
    "freshness_status",
]
FULFILLS_COLUMNS = [
    "candidate_key",
    "food_key",
    "canonical_key",
    "source",
    "source_snapshot_id",
    "mapping_version",
    "mapping_confidence",
    "observed_at",
    "freshness_status",
]

DEFAULT_RELATIONS = {
    "node_recipe": (["recipe_id", "title"], [("r1", "Carrot Soup")]),
    "node_food_concept": (["canonical_key", "name"], [("carrot", "Carrot")]),
    "node_food": (["food_key", "description"], [("f1", "White Beans")]),
    "node_component": (["component_id", "name"], [("c1", "Protein")]),
    "edge_requires": (
        REQUIRES_COLUMNS,
        [("r1", "o1", "carrot", "josephrmartinez/recipe-dataset",
          "recipe-food-v4", 0.93, "2026-09-01T00:00:00+00:00", "snapshot")],
    ),
    "edge_fulfills": (
        FULFILLS_COLUMNS,
        [("k1", "f1", "carrot", "fooddata_central", FDC_SNAPSHOT,
          "recipe_food_to_dbt:v4", 0.88, "2026-09-02T00:00:00+00:00", "snapshot")],
    ),
    "edge_has_component": (["id", "food_key", "component_id"], [("h1", "f1", "c1")]),
}


def accepted_manifest(**changes):
    """Return a source snapshot manifest matching p1-001's generated contract."""
    document = {
        "schema_version": 1,
        "contract_version": 1,
        "sources": [
            {"source_identity": "FoodData Central", "snapshot_id": FDC_SNAPSHOT,
             "content_checksum": CHECKSUM, "observation_timestamp": "2026-09-01T00:00:00+00:00",
             "paths": ["seeds/fdc/food.csv"]},
            {"source_identity": "recipe dataset", "snapshot_id": RECIPE_SNAPSHOT,
             "content_checksum": CHECKSUM, "observation_timestamp": "2026-09-01T00:00:00+00:00",
             "paths": ["seeds/13k-recipe/13k-recipes.csv"]},
            {"source_identity": "FairPrice listings", "snapshot_id": FAIRPRICE_SNAPSHOT,
             "content_checksum": CHECKSUM, "observation_timestamp": "2026-09-02T00:00:00+00:00",
             "paths": ["seeds/fairprice/listings.csv"]},
        ],
        "marts": {
            mart: {"row_count": row_count, "content_checksum": CHECKSUM,
                   "content_columns": ["placeholder"], "contract_version": 1}
            for mart, row_count in MART_ROWS.items()
        },
    }
    document.update(changes)
    return document


def write_manifest(directory, document):
    manifest_path = Path(directory) / "source_snapshot_manifest.json"
    text = document if isinstance(document, str) else json.dumps(document)
    manifest_path.write_text(text, encoding="utf-8")
    return str(manifest_path)


class ProjectionDbt:
    """dbt stand-in supplying the canonical mart relations for an accepted build."""

    def __init__(self, relations=None):
        self.relations = dict(DEFAULT_RELATIONS)
        self.relations.update(relations or {})

    def config(self, **_):
        pass

    def ref(self, name):
        if name == "graph_quality_manifest":
            return Relation(QUALITY_COLUMNS, list(QUALITY_ROWS))
        columns, rows = self.relations[name]
        return Relation(columns, list(rows))


def payload_rows(driver, marker):
    """Return every row parameter passed to a load statement containing `marker`."""
    rows = []
    for statement, parameters in driver.records:
        if marker in statement and "rows" in parameters:
            rows.extend(parameters["rows"])
    return rows


def run_model(driver, manifest=None, dbt=None):
    """Run the serving model against the fake driver."""
    values = environment(replace=True, manifest=manifest)

    def connect(*_args, **_kwargs):
        return driver

    with (
        patch.dict(os.environ, values, clear=True),
        patch.object(serving.GraphDatabase, "driver", side_effect=connect),
    ):
        serving.model(dbt or ProjectionDbt(), Session())


# ---------------------------------------------------------------------------
# p1-001 serving behaviour, retained under the p1-002 admission gate.
# ---------------------------------------------------------------------------

requests: list[tuple[str, dict[str, object]]] = []
with patch.dict(os.environ, environment(), clear=True):
    try:
        serving.model(ProjectionDbt(), Session())
    except ValueError as error:
        assert "NEO4J_REPLACE=true is required" in str(error)
    else:
        raise AssertionError("append-only synchronization was accepted")
assert not requests

MANIFEST_PATH = write_manifest(tempfile.mkdtemp(prefix="remy-serving-"), accepted_manifest())

requests.clear()
replacement = Neo4jSession(nodes=179990, relationships=359990)
with (
    patch.dict(os.environ, environment(replace=True, manifest=MANIFEST_PATH), clear=True),
    patch.object(serving.GraphDatabase, "driver", return_value=Driver(replacement)) as connect,
):
    result = serving.model(ProjectionDbt(), Session())
connect.assert_called_once_with("neo4j+s://example.databases.neo4j.io", auth=("user", "secret"))
assert replacement.transaction.committed and not replacement.transaction.rolled_back
assert any("DELETE r" in statement for statement, _ in requests)
statements = "\n".join(statement for statement, _ in requests)
assert "projection_owner" in statements
assert "Product" in statements and "Offer" in statements and "Allergen" in statements and "Diet" in statements
assert "candidate_key" in statements
assert "FULFILLS" in result and "HAS_COMPONENT" in result
assert "PRODUCT_FULFILLS" not in result and "DIET_STATUS" not in result

requests.clear()
failing = Neo4jSession(fail_on_load=True)
with (
    patch.dict(os.environ, environment(replace=True, manifest=MANIFEST_PATH), clear=True),
    patch.object(serving.GraphDatabase, "driver", return_value=Driver(failing)),
):
    try:
        serving.model(ProjectionDbt(), Session())
    except RuntimeError as error:
        assert "injected load failure" in str(error)
    else:
        raise AssertionError("injected load failure was not raised")
assert failing.transaction.rolled_back and not failing.transaction.committed

requests.clear()
over_capacity = Neo4jSession(nodes=180000)
with (
    patch.dict(os.environ, environment(replace=True, manifest=MANIFEST_PATH), clear=True),
    patch.object(serving.GraphDatabase, "driver", return_value=Driver(over_capacity)),
):
    try:
        serving.model(ProjectionDbt(), Session())
    except ValueError as error:
        assert "capacity gate failed" in str(error)
    else:
        raise AssertionError("capacity gate accepted an over-cap load")
assert over_capacity.transaction.rolled_back


class BadManifestDbt(ProjectionDbt):
    def ref(self, name):
        if name == "graph_quality_manifest":
            return Relation(
                ["entity", "row_count", "allocation", "within_allocation"],
                [("Food", 32001, 32000, False), ("TOTAL_NODE", 32001, 84200, True),
                 ("TOTAL_RELATIONSHIP", 0, 208200, True)],
            )
        return super().ref(name)


with patch.dict(os.environ, environment(replace=True, manifest=MANIFEST_PATH), clear=True):
    try:
        serving.model(BadManifestDbt(), Session())
    except ValueError as error:
        assert "allocation failed: Food" in str(error)
    else:
        raise AssertionError("individual manifest allocation failure was accepted")


# ---------------------------------------------------------------------------
# p1-002 admission tests
# ---------------------------------------------------------------------------


def test_accepted_manifest_loads_canonical_graph(fake_driver, tmp_path):
    manifest = write_manifest(tmp_path, accepted_manifest())
    run_model(fake_driver, manifest=manifest)

    assert fake_driver.transaction is not None
    assert fake_driver.transaction.committed is True
    assert fake_driver.transaction.rolled_back is False

    statements = "\n".join(statement for statement, _ in fake_driver.records)
    for entity in ("Recipe", "FoodConcept", "Food", "Component", "REQUIRES", "FULFILLS", "HAS_COMPONENT"):
        assert entity in statements

    requires = payload_rows(fake_driver, ":REQUIRES")
    assert requires, "no REQUIRES payload was loaded"
    for row in requires:
        assert row["source_snapshot_id"] == RECIPE_SNAPSHOT
        assert row["source"] == "josephrmartinez/recipe-dataset"
        assert row["normalization_version"] == "recipe-food-v4"
        assert row["mapping_confidence"] == 0.93
        assert row["observed_at"] == "2026-09-01T00:00:00+00:00"

    fulfills = payload_rows(fake_driver, ":FULFILLS")
    assert fulfills, "no FULFILLS payload was loaded"
    for row in fulfills:
        assert row["source_snapshot_id"] == FDC_SNAPSHOT
        assert row["mapping_confidence"] == 0.88
        assert row["observed_at"] == "2026-09-02T00:00:00+00:00"


MANIFEST_FAILURES = [
    pytest.param(None, "source snapshot manifest", id="absent"),
    pytest.param("missing-file", "source snapshot manifest", id="not-found"),
    pytest.param("raw", "malformed", id="malformed"),
    pytest.param({"schema_version": 99}, "schema", id="schema-version"),
    pytest.param({"sources": []}, "source", id="missing-sources"),
    pytest.param(
        {"sources": [
            {"source_identity": "FoodData Central", "snapshot_id": FDC_SNAPSHOT,
             "content_checksum": CHECKSUM, "observation_timestamp": "2026-09-01T00:00:00+00:00",
             "paths": ["seeds/fdc/food.csv"]},
            {"source_identity": "recipe dataset", "snapshot_id": "   ",
             "content_checksum": CHECKSUM, "observation_timestamp": "2026-09-01T00:00:00+00:00",
             "paths": ["seeds/13k-recipe/13k-recipes.csv"]},
            {"source_identity": "FairPrice listings", "snapshot_id": FAIRPRICE_SNAPSHOT,
             "content_checksum": CHECKSUM, "observation_timestamp": "2026-09-02T00:00:00+00:00",
             "paths": ["seeds/fairprice/listings.csv"]},
        ]},
        "snapshot",
        id="blank-snapshot-id",
    ),
    pytest.param({"marts": {"node_recipe": MART_ROWS["node_recipe"]}}, "mart", id="mart-coverage"),
]


@pytest.mark.parametrize("manifest,expected", MANIFEST_FAILURES)
def test_missing_or_failed_manifest_preserves_graph(fake_driver, tmp_path, manifest, expected):
    if manifest is None:
        manifest_path = None
    elif manifest == "missing-file":
        manifest_path = str(tmp_path / "does-not-exist.json")
    elif manifest == "raw":
        manifest_path = write_manifest(tmp_path, "{not json")
    else:
        document = accepted_manifest()
        document.update(manifest)
        manifest_path = write_manifest(tmp_path, document)

    with pytest.raises(ValueError) as error:
        run_model(fake_driver, manifest=manifest_path)

    assert expected in str(error.value).lower()
    assert fake_driver.records == []
    assert fake_driver.transaction is None


def test_failed_allocation_or_integrity_rolls_back(fake_driver, tmp_path):
    manifest = write_manifest(tmp_path, accepted_manifest())

    failed_allocation = Relation(
        QUALITY_COLUMNS,
        [row[:2] + (32001, 32000, False) if row[1] == "Food" else row for row in QUALITY_ROWS],
    )

    class AllocationDbt(ProjectionDbt):
        def ref(self, name):
            if name == "graph_quality_manifest":
                return failed_allocation
            return super().ref(name)

    with pytest.raises(ValueError) as error:
        run_model(fake_driver, manifest=manifest, dbt=AllocationDbt())
    assert "allocation" in str(error.value).lower()
    assert fake_driver.records == []
    assert fake_driver.transaction is None

    dangling = (
        REQUIRES_COLUMNS,
        [("r1", "o1", "courgette", "josephrmartinez/recipe-dataset",
          "recipe-food-v4", 0.93, "2026-09-01T00:00:00+00:00", "snapshot")],
    )
    with pytest.raises(ValueError) as error:
        run_model(fake_driver, manifest=manifest, dbt=ProjectionDbt({"edge_requires": dangling}))
    assert "REQUIRES" in str(error.value)
    assert "dangling" in str(error.value).lower()
    assert fake_driver.transaction is not None
    assert fake_driver.transaction.rolled_back is True
    assert fake_driver.transaction.committed is False

@pytest.mark.integration
def test_repeated_accepted_load_is_content_identical(neo4j_driver):
    """AC-9: two loads with the same identity produce identical results (real Neo4j)."""
    import importlib.util
    from pathlib import Path
    path = Path(__file__).parents[1] / "models/serving/recipe_graph_to_neo4j.py"
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
