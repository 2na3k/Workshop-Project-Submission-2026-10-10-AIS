"""Admission-gated, capacity-gated projection of the canonical marts into Neo4j.

Admission is decided here, not in the manifest: ``reproducibility_manifest.py``
states facts (sources, snapshots, checksums, counts) and this model decides
whether those facts plus ``graph_quality_manifest`` satisfy the acceptance rule.
Every check that can reject a build runs before a driver is created, so a
rejected refresh cannot mutate the published graph.
"""

import json
import os
from decimal import Decimal
from pathlib import Path

from neo4j import GraphDatabase


OWNER = "remy_recipe_graph"
MANIFEST_ENV = "NEO4J_SOURCE_MANIFEST"
MANIFEST_SCHEMA_VERSION = 1
CONTRACT_VERSION = 1
REQUIRED_SOURCES = ("FoodData Central", "recipe dataset", "FairPrice listings")
REQUIRED_MARTS = (
    "node_recipe",
    "node_food_concept",
    "node_food",
    "node_component",
    "edge_requires",
    "edge_fulfills",
    "edge_has_component",
    "graph_quality_manifest",
)

NODES = (
    ("Recipe", "node_recipe", "recipe_id"),
    ("FoodConcept", "node_food_concept", "canonical_key"),
    ("Food", "node_food", "food_key"),
    ("Component", "node_component", "component_id"),
)
RETIRED_LABELS = ("Product", "Offer", "Allergen", "Diet")

NODE_ENTITIES = tuple(label for label, _, _ in NODES)
RELATIONSHIP_ENTITIES = ("REQUIRES", "FULFILLS", "HAS_COMPONENT")
ENTITY_MART = {label: mart for label, mart, _ in NODES} | {
    "REQUIRES": "edge_requires",
    "FULFILLS": "edge_fulfills",
    "HAS_COMPONENT": "edge_has_component",
}
# Each linking record is stamped with the snapshot of the source that produced it.
LINK_SOURCE = {
    "REQUIRES": "recipe dataset",
    "FULFILLS": "FoodData Central",
    "HAS_COMPONENT": "FoodData Central",
}
# (relationship, mart, start label, start key column, end label, end key column)
EDGES = (
    ("REQUIRES", "edge_requires", "Recipe", "recipe_id", "FoodConcept", "normalized_name"),
    ("FULFILLS", "edge_fulfills", "Food", "food_key", "FoodConcept", "canonical_key"),
    ("HAS_COMPONENT", "edge_has_component", "Food", "food_key", "Component", "component_id"),
)

NODE_STATEMENTS = {
    label: (
        "UNWIND $rows AS row\n"
        + "MERGE (n:" + label + " {" + key + ": row." + key + "})\n"
        + "SET n += row, n.projection_owner = '" + OWNER + "'"
    )
    for label, _, key in NODES
}

EDGE_LOADS = (
    ("REQUIRES", "REQUIRES", "edge_requires", """
UNWIND $rows AS row
MATCH (a:Recipe {recipe_id: row.recipe_id})
MATCH (b:FoodConcept {canonical_key: row.normalized_name})
MERGE (a)-[e:REQUIRES {occurrence_id: row.occurrence_id}]->(b)
SET e += row, e.projection_owner = $owner
"""),
    ("FOOD_FULFILLS", "FULFILLS", "edge_fulfills", """
UNWIND $rows AS row
MATCH (a:Food {food_key: row.food_key})
MATCH (b:FoodConcept {canonical_key: row.canonical_key})
MERGE (a)-[e:FULFILLS {candidate_key: row.candidate_key}]->(b)
SET e += row, e.projection_owner = $owner
"""),
    ("HAS_COMPONENT", "HAS_COMPONENT", "edge_has_component", """
UNWIND $rows AS row
MATCH (a:Food {food_key: row.food_key})
MATCH (b:Component {component_id: row.component_id})
MERGE (a)-[e:HAS_COMPONENT {id: row.id}]->(b)
SET e += row, e.projection_owner = $owner
"""),
)


def _rows(relation, batch_size):
    while rows := relation.fetchmany(batch_size):
        yield [
            {
                column: float(value) if isinstance(value, Decimal) else value
                for column, value in zip(relation.columns, row, strict=True)
            }
            for row in rows
        ]


def _materialise(relation, batch_size):
    collected = []
    for payload in _rows(relation, batch_size):
        collected.extend(payload)
    return collected


def _read_source_manifest():
    """Load and schema-validate the accepted p1-001 source snapshot manifest."""
    configured = os.getenv(MANIFEST_ENV, "").strip()
    if not configured:
        raise ValueError(
            f"admission failed: a source snapshot manifest is required; set {MANIFEST_ENV}"
        )
    path = Path(configured)
    if not path.is_file():
        raise ValueError(f"admission failed: source snapshot manifest is not readable: {path}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(
            f"admission failed: source snapshot manifest is malformed JSON: {path}: {error}"
        ) from error
    if not isinstance(document, dict):
        raise ValueError(f"admission failed: source snapshot manifest is malformed: {path}")

    schema_version = document.get("schema_version")
    if schema_version != MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            f"admission failed: source snapshot manifest schema_version {schema_version!r} "
            f"is unsupported, expected {MANIFEST_SCHEMA_VERSION}"
        )
    contract_version = document.get("contract_version")
    if contract_version != CONTRACT_VERSION:
        raise ValueError(
            f"admission failed: source snapshot manifest contract_version {contract_version!r} "
            f"is unsupported, expected {CONTRACT_VERSION}"
        )

    raw_sources = document.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ValueError(
            f"admission failed: source snapshot manifest lists no sources, "
            f"expected exactly {REQUIRED_SOURCES}"
        )
    snapshots: dict[str, str] = {}
    for entry in raw_sources:
        if not isinstance(entry, dict):
            raise ValueError("admission failed: every source snapshot manifest entry must be an object")
        identity = entry.get("source_identity")
        if not isinstance(identity, str) or not identity.strip():
            raise ValueError(
                "admission failed: every source snapshot manifest entry needs a non-blank source_identity"
            )
        snapshot_id = entry.get("snapshot_id")
        if not isinstance(snapshot_id, str) or not snapshot_id.strip():
            raise ValueError(
                f"admission failed: source {identity} has a blank snapshot_id"
            )
        checksum = entry.get("content_checksum")
        if not isinstance(checksum, str) or not checksum.strip():
            raise ValueError(f"admission failed: source {identity} has a blank content_checksum")
        snapshots[identity] = snapshot_id
    missing_sources = [item for item in REQUIRED_SOURCES if item not in snapshots]
    if missing_sources:
        raise ValueError(
            f"admission failed: source snapshot manifest is missing required sources: {missing_sources}"
        )

    raw_marts = document.get("marts")
    if not isinstance(raw_marts, dict):
        raise ValueError("admission failed: source snapshot manifest has no mart coverage section")
    counts: dict[str, int] = {}
    for mart in REQUIRED_MARTS:
        entry = raw_marts.get(mart)
        if not isinstance(entry, dict):
            raise ValueError(
                f"admission failed: source snapshot manifest mart coverage is incomplete: {mart}"
            )
        row_count = entry.get("row_count")
        if not isinstance(row_count, int) or row_count < 0:
            raise ValueError(
                f"admission failed: source snapshot manifest mart {mart} has no deterministic row_count"
            )
        counts[mart] = row_count

    return {"sources": snapshots, "marts": counts}


def _read_quality_manifest(dbt, batch_size):
    """Read ``graph_quality_manifest`` into an entity -> row_count mapping."""
    rows = _materialise(dbt.ref("graph_quality_manifest"), batch_size)
    if not rows:
        raise ValueError("admission failed: graph_quality_manifest reported no quality result")
    if any(not row.get("within_allocation") for row in rows):
        failed = ", ".join(str(row["entity"]) for row in rows if not row.get("within_allocation"))
        raise ValueError(f"graph_quality_manifest allocation failed: {failed}")
    required_columns = {"entity", "row_count", "within_allocation"}
    if not required_columns.issubset(rows[0]):
        raise ValueError(
            "admission failed: graph_quality_manifest is missing required columns: "
            f"{sorted(required_columns - set(rows[0]))}"
        )
    quality = {}
    for row in rows:
        entity = row["entity"]
        row_count = row["row_count"]
        if not isinstance(row_count, int) or row_count < 0:
            raise ValueError(f"graph_quality_manifest has a non-deterministic row_count for {entity}")
        quality[entity] = row_count
    return quality


def _admit(accepted, quality):
    """Apply the acceptance rule to the manifest facts and the quality result."""
    for entity in NODE_ENTITIES + RELATIONSHIP_ENTITIES:
        if entity not in quality:
            raise ValueError(
                f"admission failed: graph_quality_manifest has no quality result for {entity}"
            )
    for entity in NODE_ENTITIES + RELATIONSHIP_ENTITIES:
        mart = ENTITY_MART[entity]
        if quality[entity] != accepted["marts"][mart]:
            raise ValueError(
                f"admission failed: mart coverage mismatch for {entity}: quality reports "
                f"{quality[entity]}, the accepted source snapshot manifest reports {accepted['marts'][mart]}"
            )
    node_total = sum(quality[entity] for entity in NODE_ENTITIES)
    relationship_total = sum(quality[entity] for entity in RELATIONSHIP_ENTITIES)
    for entity, expected in (("TOTAL_NODE", node_total), ("TOTAL_RELATIONSHIP", relationship_total)):
        reported = quality.get(entity)
        if reported is None:
            raise ValueError(f"admission failed: graph_quality_manifest has no {entity} total")
        if reported != expected:
            raise ValueError(
                f"admission failed: graph_quality_manifest {entity} total {reported} does not "
                f"match the deterministic entity counts {expected}"
            )
    return node_total, relationship_total


def _key_set(dbt, mart, key, batch_size):
    columns = dbt.ref(mart)
    if key not in columns.columns:
        raise ValueError(f"admission failed: canonical mart {mart} does not provide key column {key}")
    return {row[key] for row in _materialise(columns, batch_size)}


def _assert_referential_integrity(dbt, keys, batch_size):
    """Reject a mart whose linking rows point at nodes the build does not contain."""
    for relationship, mart, start_label, start_column, end_label, end_column in EDGES:
        relation = dbt.ref(mart)
        for column in (start_column, end_column):
            if column not in relation.columns:
                raise ValueError(
                    f"admission failed: canonical mart {mart} does not provide endpoint column {column}"
                )
        start_keys, end_keys = keys[start_label], keys[end_label]
        for row in _materialise(relation, batch_size):
            if row[start_column] not in start_keys or row[end_column] not in end_keys:
                raise ValueError(
                    f"graph refresh refused: dangling {relationship} reference between "
                    f"{start_label} {row[start_column]!r} and {end_label} {row[end_column]!r}"
                )


def _stamp_provenance(relation, relationship, snapshot_id, batch_size):
    """Attach the accepted source snapshot to every linking record.

    A row that already carries a snapshot must agree with the accepted manifest;
    an unagreed snapshot means the row cannot be associated with this build.
    """
    for payload in _rows(relation, batch_size):
        for row in payload:
            existing = row.get("source_snapshot_id")
            if existing not in (None, "") and existing != snapshot_id:
                raise ValueError(
                    f"graph refresh refused: {relationship} record carries source snapshot "
                    f"{existing!r} which is not the accepted {snapshot_id!r}"
                )
            row["source_snapshot_id"] = snapshot_id
        yield payload


def model(dbt, session):
    dbt.config(materialized="table", tags=["serving"])
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        raise ValueError("NEO4J_PASSWORD must be set")
    batch_size = int(os.getenv("NEO4J_BATCH_SIZE") or "5000")
    if batch_size <= 0:
        raise ValueError("NEO4J_BATCH_SIZE must be positive")

    replace = os.getenv("NEO4J_REPLACE", "").lower() in {"1", "true", "yes"}
    if not replace:
        raise ValueError("NEO4J_REPLACE=true is required so stale projection-owned facts are withdrawn")

    accepted = _read_source_manifest()
    quality = _read_quality_manifest(dbt, batch_size)
    projected_nodes, projected_relationships = _admit(accepted, quality)

    uri = os.getenv("NEO4J_URI") or "bolt://localhost:7687"
    user = os.getenv("NEO4J_USERNAME") or os.getenv("NEO4J_USER") or "neo4j"
    driver = GraphDatabase.driver(uri, auth=(user, password))
    neo4j = driver.session(database=os.getenv("NEO4J_DATABASE") or "neo4j")

    def run(statement, **parameters):
        return neo4j.run(statement, **parameters).single()

    occupancy = run("MATCH (n) WITH count(n) AS nodes OPTIONAL MATCH ()-[r]->() RETURN nodes, count(r) AS relationships")
    if occupancy["nodes"] > 180000 or occupancy["relationships"] > 360000:
        neo4j.close()
        driver.close()
        raise ValueError("Neo4j current occupancy already exceeds the operational gate")

    for label, _, key in NODES:
        run(f"CREATE CONSTRAINT remy_{label.lower()}_{key} IF NOT EXISTS FOR (n:{label}) REQUIRE n.{key} IS UNIQUE")

    transaction = neo4j.begin_transaction()

    def tx_run(statement, **parameters):
        return transaction.run(statement, **parameters).single()

    counts = []
    try:
        keys = {label: _key_set(dbt, mart, key, batch_size) for label, mart, key in NODES}
        _assert_referential_integrity(dbt, keys, batch_size)

        while True:
            result = tx_run(
                "MATCH ()-[r]->() WHERE r.projection_owner = $owner WITH r LIMIT $limit DELETE r RETURN count(*) AS deleted",
                owner=OWNER, limit=batch_size,
            )
            if result["deleted"] < batch_size:
                break
        for label in NODE_ENTITIES + RETIRED_LABELS:
            while True:
                result = tx_run(
                    f"MATCH (n:{label}) WHERE n.projection_owner = $owner AND NOT (n)--() WITH n LIMIT $limit DELETE n RETURN count(*) AS deleted",
                    owner=OWNER, limit=batch_size,
                )
                if result["deleted"] < batch_size:
                    break
        remaining = tx_run("MATCH (n) WITH count(n) AS nodes OPTIONAL MATCH ()-[r]->() RETURN nodes, count(r) AS relationships")
        final_nodes = remaining["nodes"] + projected_nodes
        final_relationships = remaining["relationships"] + projected_relationships

        if final_nodes > 180000 or final_relationships > 360000:
            raise ValueError(f"Neo4j operational capacity gate failed: nodes={final_nodes}, relationships={final_relationships}")

        loads = [(label, None, mart, NODE_STATEMENTS[label]) for label, mart, _ in NODES]
        loads.extend(EDGE_LOADS)

        for entity, relationship, mart, statement in loads:
            relation = dbt.ref(mart)
            loaded = 0
            if relationship is None:
                payloads = _rows(relation, batch_size)
            else:
                snapshot_id = accepted["sources"][LINK_SOURCE[relationship]]
                payloads = _stamp_provenance(relation, relationship, snapshot_id, batch_size)
            for payload in payloads:
                tx_run(statement, rows=payload, owner=OWNER)
                loaded += len(payload)
            counts.append((entity, loaded))
        transaction.commit()
    except Exception:
        try:
            transaction.rollback()
        except Exception:
            pass
        raise
    finally:
        neo4j.close()
        driver.close()
    return session.sql(" UNION ALL ".join(
        f"SELECT '{entity}' AS entity, {loaded} AS loaded_rows" for entity, loaded in counts
    ))
