"""Cloud Neo4j integration fixtures for the graph test suite.

Three fixtures back the ``integration``-marked tests:

``load_test_env``
    Session-scoped. Resolves ``NEO4J_TEST_URI``, ``NEO4J_TEST_USERNAME`` and
    ``NEO4J_TEST_PASSWORD`` from the process environment first, then from a
    gitignored ``.env.test`` at the repository root. An empty value counts as
    missing. When any variable is missing the run is skipped locally and failed
    under CI.

``neo4j_test_connection``
    Session-scoped. Returns the ``(uri, auth)`` tuple after a single
    ``verify_connectivity()`` call, which also resumes an idle-paused instance.
    A connection failure names the URI but never the password.

``neo4j_driver``
    Function-scoped. Builds a driver from the connection, clears the database
    with ``MATCH (n) DETACH DELETE n`` before each test, and closes the driver
    afterwards. Only ``integration``-marked tests request it.

The dedicated test instance is required because the database is cleared before
every test. ``.env.nonprod`` is deliberately never read, so integration tests
cannot run against the development or production Neo4j.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from dotenv import dotenv_values
from neo4j import Driver, GraphDatabase

_REQUIRED_VARS = (
    "NEO4J_TEST_URI",
    "NEO4J_TEST_USERNAME",
    "NEO4J_TEST_PASSWORD",
)


def _in_ci() -> bool:
    """True when the ``CI`` environment variable marks a continuous run."""
    return os.environ.get("CI", "").strip().lower() in {"1", "true", "yes"}


def _repo_root() -> Path:
    """The git repository root, i.e. the nearest ancestor holding ``.git``."""
    for candidate in Path(__file__).resolve().parents:
        if (candidate / ".git").exists():
            return candidate
    # tests/graph/conftest.py -> repository root is five levels up.
    return Path(__file__).resolve().parents[5]


def _resolve(name: str, dotenv_data: dict[str, str | None]) -> str:
    """Process environment first, then ``.env.test``; empty counts as missing."""
    value = os.environ.get(name)
    if not value:
        value = dotenv_data.get(name)
    return value.strip() if value else ""


def _unavailable(missing: list[str]) -> str:
    names = ", ".join(missing)
    where = "the CI environment" if _in_ci() else "the process environment or .env.test"
    return (
        f"Neo4j integration tests need {names} set in {where}; "
        "see .env.test.example."
    )


@pytest.fixture(scope="session")
def load_test_env() -> dict[str, str]:
    """Resolve the three test-instance variables, or skip/fail when missing."""
    env_file = _repo_root() / ".env.test"
    file_values = dotenv_values(env_file) if env_file.exists() else {}
    resolved = {name: _resolve(name, file_values) for name in _REQUIRED_VARS}
    missing = [name for name, value in resolved.items() if not value]
    if missing:
        message = _unavailable(missing)
        if _in_ci():
            pytest.fail(message)
        pytest.skip(message)
    return resolved


@pytest.fixture(scope="session")
def neo4j_test_connection(load_test_env: dict[str, str]) -> tuple[str, tuple[str, str]]:
    """Return ``(uri, auth)`` after one successful connectivity check."""
    uri = load_test_env["NEO4J_TEST_URI"]
    auth = (load_test_env["NEO4J_TEST_USERNAME"], load_test_env["NEO4J_TEST_PASSWORD"])
    try:
        probe = GraphDatabase.driver(uri, auth=auth)
        probe.verify_connectivity()
        probe.close()
    except Exception as exc:  # noqa: BLE001 - reported, never re-raised here
        # Name the URI only: never include the auth tuple or the password.
        message = (
            f"Neo4j test instance at {uri} is unreachable "
            f"({type(exc).__name__}); check the URI and that the instance is online."
        )
        # pytrace=False keeps the secret-bearing load_test_env argument out of
        # the report: only the message above (URI, never the password) is shown.
        if _in_ci():
            pytest.fail(message, pytrace=False)
        pytest.skip(message)
    return uri, auth


@pytest.fixture
def neo4j_driver(
    neo4j_test_connection: tuple[str, tuple[str, str]],
) -> Iterator[Driver]:
    """A live driver on a database cleared before each test."""
    uri, auth = neo4j_test_connection
    driver = GraphDatabase.driver(uri, auth=auth)
    try:
        with driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        yield driver
    finally:
        driver.close()
