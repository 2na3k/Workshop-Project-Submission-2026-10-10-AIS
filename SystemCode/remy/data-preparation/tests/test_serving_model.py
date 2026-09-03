import importlib.util
import os
from pathlib import Path
from unittest.mock import patch


path = Path(__file__).parents[1] / "models/serving/recipe_graph_to_neo4j.py"
spec = importlib.util.spec_from_file_location("recipe_graph_to_neo4j", path)
serving = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(serving)


class Result:
    def single(self):
        return {"deleted": 0}


class Neo4jSession:
    def run(self, statement, **parameters):
        requests.append((statement, parameters))
        return Result()

    def close(self):
        pass


class Driver:
    def session(self, database):
        assert database == "database"
        return Neo4jSession()

    def close(self):
        pass


class Relation:
    columns = ["id"]

    def __init__(self):
        self.rows = iter([(1,)])

    def fetchmany(self, _):
        return list(self.rows)


class Dbt:
    def config(self, **_):
        pass

    def ref(self, _):
        return Relation()


class Session:
    def sql(self, query):
        return query


requests = []
with (
    patch.dict(os.environ, {
        "NEO4J_URI": "neo4j+s://example.databases.neo4j.io",
        "NEO4J_USERNAME": "user",
        "NEO4J_PASSWORD": "secret",
        "NEO4J_DATABASE": "database",
    }, clear=True),
    patch.object(serving.GraphDatabase, "driver", return_value=Driver()) as connect,
):
    result = serving.model(Dbt(), Session())

connect.assert_called_once_with("neo4j+s://example.databases.neo4j.io", auth=("user", "secret"))
assert requests
assert "Recipe" in result and "HAS_COMPONENT" in result
