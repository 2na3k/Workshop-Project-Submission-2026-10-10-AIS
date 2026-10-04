"""Shared pytest fixtures for the data-preparation test suite.

`fake_driver`
    An in-memory stand-in for the Neo4j driver/session/transaction interface
    used by the serving model ``models/serving/recipe_graph_to_neo4j.py``. It
    lets an orchestration test drive the model end-to-end without a live Neo4j
    and assert which statements were issued and with what parameters.

    Emulated surface (derived from the serving model's actual calls):
      * driver: ``session(database=...)``, ``close()``, ``verify_connectivity()``
      * session: ``run(cypher, **params)`` -> result, ``begin_transaction()``,
        ``close()``, and the context-manager protocol ``__enter__``/``__exit__``
      * transaction: ``run(cypher, **params)`` -> result, ``commit()``,
        ``rollback()``
      * result: ``single()`` (the only result method the model uses)

    Every ``run`` on the session or a transaction appends a ``(cypher, params)``
    tuple to ``fake_driver.records`` in call order; tests assert against it.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Literal

import pytest


class _FakeResult:
    """Stands in for a neo4j Result; the serving model only calls ``single()``."""

    def __init__(self, value: dict[str, object]) -> None:
        self._value = value

    def single(self) -> dict[str, object]:
        return self._value

    def data(self) -> list[dict[str, object]]:
        return [self._value]

    def __iter__(self) -> Iterator[dict[str, object]]:
        return iter([self._value])


class _FakeTransaction:
    def __init__(self, driver: _FakeDriver) -> None:
        self._driver = driver
        self.committed = False
        self.rolled_back = False

    def run(self, statement: str, **parameters: object) -> _FakeResult:
        self._driver._record(statement, parameters)
        return _FakeResult(self._driver._result_for(statement))

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def __enter__(self) -> _FakeTransaction:
        return self

    def __exit__(self, *_exc: object) -> Literal[False]:
        return False


class _FakeSession:
    def __init__(self, driver: _FakeDriver, database: str | None) -> None:
        self._driver = driver
        self.database = database
        self.closed = False

    def run(self, statement: str, **parameters: object) -> _FakeResult:
        self._driver._record(statement, parameters)
        return _FakeResult(self._driver._result_for(statement))

    def begin_transaction(self) -> _FakeTransaction:
        transaction = _FakeTransaction(self._driver)
        self._driver.transaction = transaction
        return transaction

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> _FakeSession:
        return self

    def __exit__(self, *_exc: object) -> Literal[False]:
        self.close()
        return False


class _FakeDriver:
    """Records every statement and returns canned results for the model's gates."""

    def __init__(self, nodes: int = 10, relationships: int = 20) -> None:
        self.records: list[tuple[str, dict[str, object]]] = []
        self.transaction: _FakeTransaction | None = None
        self.closed = False
        self._occupancy: dict[str, object] = {
            "nodes": nodes,
            "relationships": relationships,
        }

    def _record(self, cypher: str, params: dict[str, object]) -> None:
        self.records.append((cypher, params))

    def _result_for(self, statement: str) -> dict[str, object]:
        if "WITH count(n) AS nodes" in statement:
            return dict(self._occupancy)
        if "RETURN count(n) AS nodes" in statement:
            return {"nodes": 0}
        if "RETURN count(r) AS relationships" in statement:
            return {"relationships": 0}
        if "deleted" in statement:
            return {"deleted": 0}
        return {}

    def session(self, database: str | None = None, **_kwargs: object) -> _FakeSession:
        return _FakeSession(self, database)

    def verify_connectivity(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def fake_driver() -> _FakeDriver:
    """Return a recording fake Neo4j driver for orchestration tests (AC-1)."""
    return _FakeDriver()
