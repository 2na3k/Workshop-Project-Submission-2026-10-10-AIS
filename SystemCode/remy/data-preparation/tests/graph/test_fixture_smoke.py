"""Smoke tests proving the cloud Neo4j integration fixture works.

These tests require a live, dedicated Neo4j test instance configured through
``NEO4J_TEST_URI`` / ``NEO4J_TEST_USERNAME`` / ``NEO4J_TEST_PASSWORD`` (see
``tests/graph/conftest.py``). They are marked ``integration`` so local runs can
exclude them with ``pytest -m "not integration"``. When the instance is not
configured the fixture skips locally and fails under CI.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


def test_write_read_through_fixture(neo4j_driver) -> None:
    """AC-2: a record written through the fixture driver reads back in the test."""
    with neo4j_driver.session() as session:
        session.run(
            "CREATE (r:Probe {probe_key: $key, value: $value})",
            key="p1-001b",
            value=42,
        )

    with neo4j_driver.session() as session:
        record = session.run(
            "MATCH (r:Probe {probe_key: $key}) RETURN r.value AS value",
            key="p1-001b",
        ).single()

    assert record is not None
    assert record["value"] == 42


def test_second_test_sees_clean_state(neo4j_driver) -> None:
    """AC-3: the fixture clears the graph, so this test starts from empty.

    ``test_write_read_through_fixture`` runs first and leaves a ``Probe`` node;
    the function-scoped clear in the fixture must remove it before this test so
    no state leaks from one test to the next.
    """
    with neo4j_driver.session() as session:
        count = session.run("MATCH (n) RETURN count(n) AS total").single()["total"]

    assert count == 0
