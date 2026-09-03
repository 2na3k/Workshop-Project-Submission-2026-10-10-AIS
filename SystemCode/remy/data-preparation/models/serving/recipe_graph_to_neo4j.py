"""Load the built recipe graph marts into Neo4j."""

import os
from decimal import Decimal

from neo4j import GraphDatabase


RECIPE_NODE = """
UNWIND $rows AS row
MERGE (r:Recipe {recipe_id: row.recipe_id})
SET r.title = row.title, r.instructions = row.instructions,
    r.image_name = row.image_name, r.source = row.source,
    r.source_license = row.source_license
"""

CONCEPT_NODE = """
UNWIND $rows AS row
MERGE (c:FoodConcept {canonical_key: row.canonical_key})
SET c.name = row.name, c.status = row.status,
    c.normalization_version = row.normalization_version
"""

FOOD_NODE = """
UNWIND $rows AS row
MERGE (f:Food {food_key: row.food_key})
SET f += row
REMOVE f.source_id
"""

COMPONENT_NODE = """
UNWIND $rows AS row
MERGE (c:Component {component_id: row.component_id})
SET c.name = row.name, c.source = row.source
"""

REQUIRES_EDGE = """
UNWIND $rows AS row
MATCH (r:Recipe {recipe_id: row.recipe_id})
MATCH (c:FoodConcept {canonical_key: row.normalized_name})
MERGE (r)-[e:REQUIRES {occurrence_id: row.occurrence_id}]->(c)
SET e.position = row.position, e.raw_text = row.raw_text,
    e.cleaned_text = row.cleaned_text, e.normalized_name = row.normalized_name,
    e.quantity = row.quantity, e.unit = row.unit,
    e.preparation = row.preparation, e.source = row.source
"""

FULFILLS_EDGE = """
UNWIND $rows AS row
MATCH (f:Food {food_key: row.food_key})
MATCH (c:FoodConcept {canonical_key: row.canonical_key})
MERGE (f)-[e:FULFILLS {kind: row.kind}]->(c)
SET e.confidence = row.confidence, e.match_method = row.match_method,
    e.context = row.context, e.ratio = row.ratio, e.source = row.source
"""

COMPONENT_EDGE = """
UNWIND $rows AS row
MATCH (f:Food {food_key: row.food_key})
MATCH (c:Component {component_id: row.component_id})
MERGE (f)-[e:HAS_COMPONENT {id: row.id}]->(c)
SET e.pct_weight = row.pct_weight, e.is_refuse = row.is_refuse,
    e.gram_weight = row.gram_weight, e.data_points = row.data_points,
    e.min_year_acquired = row.min_year_acquired, e.source = row.source
"""


def model(dbt, session):
    dbt.config(materialized="table", tags=["serving"])

    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        raise ValueError("NEO4J_PASSWORD must be set")

    batch_size = int(os.getenv("NEO4J_BATCH_SIZE") or "5000")
    if batch_size <= 0:
        raise ValueError("NEO4J_BATCH_SIZE must be positive")

    uri = os.getenv("NEO4J_URI") or "bolt://localhost:7687"
    user = os.getenv("NEO4J_USERNAME") or os.getenv("NEO4J_USER") or "neo4j"
    driver = GraphDatabase.driver(uri, auth=(user, password))
    neo4j = driver.session(database=os.getenv("NEO4J_DATABASE") or "neo4j")
    run = lambda statement, rows=None: neo4j.run(statement, rows=rows or []).single()

    for statement in (
        "CREATE CONSTRAINT recipe_food_recipe_id IF NOT EXISTS FOR (r:Recipe) REQUIRE r.recipe_id IS UNIQUE",
        "CREATE CONSTRAINT recipe_food_concept_key IF NOT EXISTS FOR (c:FoodConcept) REQUIRE c.canonical_key IS UNIQUE",
        "CREATE CONSTRAINT recipe_food_key IF NOT EXISTS FOR (f:Food) REQUIRE f.food_key IS UNIQUE",
        "CREATE CONSTRAINT recipe_food_component_id IF NOT EXISTS FOR (c:Component) REQUIRE c.component_id IS UNIQUE",
    ):
        run(statement)

    if os.getenv("NEO4J_REPLACE", "").lower() in {"1", "true", "yes"}:
        for label in ("Food", "Recipe", "FoodConcept", "Component"):
            while True:
                result = run(f"MATCH (n:{label}) WITH n LIMIT {batch_size} DETACH DELETE n RETURN count(*) AS deleted")
                if result["deleted"] < batch_size:
                    break

    loads = (
        ("Recipe", dbt.ref("node_recipe"), RECIPE_NODE),
        ("FoodConcept", dbt.ref("node_food_concept"), CONCEPT_NODE),
        ("Food", dbt.ref("node_food"), FOOD_NODE),
        ("Component", dbt.ref("node_component"), COMPONENT_NODE),
        ("REQUIRES", dbt.ref("edge_requires"), REQUIRES_EDGE),
        ("FULFILLS", dbt.ref("edge_fulfills"), FULFILLS_EDGE),
        ("HAS_COMPONENT", dbt.ref("edge_has_component"), COMPONENT_EDGE),
    )

    counts = []
    for label, relation, statement in loads:
        columns = relation.columns
        loaded = 0
        while rows := relation.fetchmany(batch_size):
            payload = [
                {
                    column: float(value) if isinstance(value, Decimal) else value
                    for column, value in zip(columns, row, strict=True)
                }
                for row in rows
            ]
            run(statement, payload)
            loaded += len(rows)
        counts.append((label, loaded))

    neo4j.close()
    driver.close()
    return session.sql(" UNION ALL ".join(
        f"SELECT '{label}' AS entity, {loaded} AS loaded_rows"
        for label, loaded in counts
    ))
