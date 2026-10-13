import os
from contextlib import asynccontextmanager

from neo4j import GraphDatabase
from .monitoring import get_client, shutdown_monitoring


def create_driver():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    return GraphDatabase.driver(uri, auth=(user, password))


@asynccontextmanager
async def lifespan(app):
    app.state.neo4j_driver = create_driver()
    get_client()
    try:
        yield
    finally:
        try:
            app.state.neo4j_driver.close()
        finally:
            shutdown_monitoring()
