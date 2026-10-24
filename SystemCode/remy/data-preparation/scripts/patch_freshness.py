"""Patch FULFILLS edges to mark estimated prices as fresh for local dev."""

import os
import time
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

SHARED_ENV_PATH = Path(__file__).resolve().parents[3] / ".env.nonprod"
load_dotenv(SHARED_ENV_PATH)

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USERNAME", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD")

QUERY = """
MATCH (f:Food)-[ful:FULFILLS {price_status: 'estimated'}]->(fc:FoodConcept)
SET ful.freshness_status = 'fresh'
RETURN count(ful) AS updated
"""

def main():
    if not PASSWORD:
        print("ERROR: NEO4J_PASSWORD not set in .env.nonprod.")
        return

    print(f"Connecting to {URI} to patch freshness...")

    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    max_retries = 10

    try:
        for attempt in range(max_retries):
            try:
                with driver.session() as session:
                    result = session.run(QUERY)
                    count = result.single()["updated"]
                    print(f"✓ Successfully marked {count} FULFILLS edges as fresh.")
                    return
            except ServiceUnavailable:
                if attempt < max_retries - 1:
                    print(f"Neo4j not ready yet (attempt {attempt + 1}/{max_retries}). Waiting 5s...")
                    time.sleep(5)
                else:
                    print("ERROR: Neo4j never became available.")
    finally:
        driver.close()

if __name__ == "__main__":
    main()
