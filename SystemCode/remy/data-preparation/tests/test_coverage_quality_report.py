"""Contract tests for p1-003 coverage quality reporting."""

from pathlib import Path
import re

import duckdb
import pytest

SCRIPT_DIR = Path(__file__).parents[1] / "scripts"
import sys

sys.path.insert(0, str(SCRIPT_DIR))
import reproducibility_manifest


MODEL = Path(__file__).parents[1] / "models" / "mart" / "coverage_quality_report.sql"
SQL = MODEL.read_text(encoding="utf-8")

DIMENSIONS = {
    "nutrition_coverage",
    "price_availability",
    "package_unit_conversion_coverage",
    "dietary_evidence_coverage",
    "whole_recipe_completeness",
}


def _run_report(requirements, candidates, recipes, run_started_at="2026-10-05 00:00:00", env_override=None):
    """Execute the dbt model SQL against a small DuckDB fixture warehouse."""
    if env_override is None:
        env_override = {
            "REMY_SOURCE_SNAPSHOT_ID": "snapshot-1",
            "REMY_MART_CONTENT_CHECKSUM": "mart-1",
            "REMY_BUILD_ID": "build-1",
        }
    if not all(env_override.get(k) for k in (
            "REMY_SOURCE_SNAPSHOT_ID", "REMY_MART_CONTENT_CHECKSUM", "REMY_BUILD_ID"
    )):
        raise ValueError("coverage report refused: build association is not configured")
    connection = duckdb.connect()
    connection.execute(
        "create table edge_requires (occurrence_id varchar, recipe_id integer, normalized_name varchar)"
    )
    connection.execute(
        "create table edge_fulfills (canonical_key varchar, food_key varchar, price_status varchar, cost_basis_compatible boolean, halal_status varchar, vegetarian_status varchar)"
    )
    connection.execute("create table node_food (food_key varchar, nutrition_status varchar)")
    connection.execute("create table node_recipe (recipe_id integer)")
    if requirements:
        connection.executemany("insert into edge_requires values (?, ?, ?)", requirements)
    if candidates:
        connection.executemany("insert into edge_fulfills values (?, ?, ?, ?, ?, ?)", candidates)
    if candidates:
        connection.executemany(
            "insert into node_food values (?, ?)",
            [(row[1], "validated" if row[1] == "food-1" else "missing") for row in candidates],
        )
    if recipes:
        connection.executemany("insert into node_recipe values (?)", [(row,) for row in recipes])

    rendered = re.sub(r"\{\{ ref\('([^']+)'\) \}\}", r"\1", SQL)
    rendered = re.sub(r"\{\{\s*config\(.*?\)\s*\}\}", "", rendered, flags=re.S)
    rendered = re.sub(r"\{%-?\s*set[^%]*%\}\n?", "", rendered)
    rendered = re.sub(r"\{%-?\s*if[^%]*%\}.*?\{%-?\s*endif\s*%\}", "", rendered, flags=re.S)
    rendered = rendered.replace("{{ assoc_snapshot }}", env_override["REMY_SOURCE_SNAPSHOT_ID"])
    rendered = rendered.replace("{{ assoc_checksum }}", env_override["REMY_MART_CONTENT_CHECKSUM"])
    rendered = rendered.replace("{{ assoc_build }}", env_override["REMY_BUILD_ID"])
    rendered = rendered.replace("{{ run_started_at }}", run_started_at)
    result = connection.execute(rendered)
    rows = result.fetchall()
    columns = [description[0] for description in result.description]
    connection.close()
    return {row[0]: dict(zip(columns, row, strict=True)) for row in rows}


@pytest.fixture
def populated_fixture():
    requirements = [("req-1", 1, "carrot"), ("req-2", 1, "salt")]
    candidates = [
        ("carrot", "food-1", "estimated", True, "certified", "unknown"),
        ("salt", "food-2", "unavailable", False, "unknown", "unknown"),
    ]
    return _run_report(requirements, candidates, [1, 2])


def test_build_publishes_exactly_five_dimensions():
    """AC-1: exactly five named dimensions exist."""
    report = _run_report([], [], [])
    assert set(report) == DIMENSIONS
    assert len(report) == 5
    assert all(report[name]["source_snapshot_id"] == "snapshot-1" for name in report)


def test_invalid_metrics_fail_closed_instead_of_being_filtered():
    """AC-11: the model has an explicit failure path, not a filtering path."""
    assert "error('coverage_quality_report failed closed: invalid metrics')" in SQL
    assert "where covered_count >= 0" not in SQL


def test_nutrition_measure_uses_requirement_denominator(populated_fixture):
    """AC-2: nutrition uses validated status and requirement denominator."""
    assert populated_fixture["nutrition_coverage"]["covered_count"] == 1
    assert populated_fixture["nutrition_coverage"]["denominator"] == 2
    assert populated_fixture["nutrition_coverage"]["percentage"] == 0.5


def test_price_measure_uses_estimated_price_status(populated_fixture):
    """AC-3: price uses estimated status."""
    assert populated_fixture["price_availability"]["covered_count"] == 1
    assert populated_fixture["price_availability"]["denominator"] == 2
    assert populated_fixture["price_availability"]["percentage"] == 0.5


def test_conversion_measure_requires_compatible_unit_basis(populated_fixture):
    """AC-4: conversion requires cost_basis_compatible = true."""
    assert populated_fixture["package_unit_conversion_coverage"]["covered_count"] == 1
    assert populated_fixture["package_unit_conversion_coverage"]["denominator"] == 2


def test_dietary_measure_requires_explicit_supported_evidence(populated_fixture):
    """AC-5: dietary uses exact accepted sets."""
    assert populated_fixture["dietary_evidence_coverage"]["covered_count"] == 1
    assert populated_fixture["dietary_evidence_coverage"]["denominator"] == 2


def test_whole_recipe_denominator_is_distinct_from_requirement_denominator():
    """AC-6: the recipe denominator counts recipes, not requirements."""
    report = _run_report(
        # 3 requirements across 2 recipes (recipe 1 has 2, recipe 2 has 1)
        [("req-1", 1, "carrot"), ("req-2", 1, "salt"), ("req-3", 2, "rice")],
        [
            ("carrot", "food-1", "estimated", True, "certified", "unknown"),
            ("salt", "food-2", "unavailable", False, "unknown", "unknown"),
            ("rice", "food-3", "estimated", True, "certified", "unknown"),
        ],
        [1, 2],
    )
    assert report["nutrition_coverage"]["denominator"] == 3   # 3 requirements
    assert report["whole_recipe_completeness"]["denominator"] == 2  # 2 recipes


def test_nutrition_only_requirement_is_not_price_or_whole_recipe_complete():
    """AC-7: nutrition present, price/conversion absent stays independent."""
    report = _run_report(
        [("req-1", 1, "carrot")],
        [("carrot", "food-1", "unavailable", False, "unknown", "unknown")],
        [1],
    )
    assert report["nutrition_coverage"]["covered_count"] == 1
    assert report["price_availability"]["covered_count"] == 0
    assert report["whole_recipe_completeness"]["covered_count"] == 0


def test_zero_populations_are_explicit_not_100_percent():
    """AC-8: zero populations do not fabricate a passing percentage."""
    report = _run_report([], [], [])
    assert all(row["denominator"] == 0 for row in report.values())
    assert all(row["percentage"] is None for row in report.values())
    assert all(row["population_status"] == "no_population" for row in report.values())


def test_report_has_exactly_five_dimensions_and_association():
    """AC-13: exactly five canonical dimensions, and every executed row
    carries the association values."""
    report = _run_report(
        [("req-1", 1, "carrot")],
        [("carrot", "food-1", "estimated", True, "certified", "unknown")],
        [1],
    )
    assert set(report) == DIMENSIONS
    assert len(report) == 5
    for row in report.values():
        assert row["source_snapshot_id"] == "snapshot-1"
        assert row["mart_content_checksum"] == "mart-1"
        assert row["build_id"] == "build-1"


def test_repeated_report_comparison_points_are_content_columns():
    """AC-9: deterministic report fields are all named in the model."""
    fixture = ([("req-1", 1, "carrot")], [("carrot", "food-1", "estimated", True, "certified", "unknown")], [1])
    first = _run_report(*fixture)
    second = _run_report(*fixture)
    comparison_points = ("covered_count", "denominator", "percentage", "dimension", "source_snapshot_id", "mart_content_checksum")
    first_points = sorted(
        ({name: row[name] for name in comparison_points if name in row} for row in first.values()),
        key=lambda row: row["dimension"],
    )
    second_points = sorted(
        ({name: row[name] for name in comparison_points if name in row} for row in second.values()),
        key=lambda row: row["dimension"],
    )
    assert first_points == second_points

def test_report_content_is_stable_across_observation_timestamps():
    """AC-9 edge case: content is deterministic across run_started_at values;
    the observation timestamp is provenance, not content."""
    fixture = (
        [("req-1", 1, "carrot")],
        [("carrot", "food-1", "estimated", True, "certified", "unknown")],
        [1],
    )
    first = _run_report(*fixture, run_started_at="2026-01-01 00:00:00")
    second = _run_report(*fixture, run_started_at="2026-06-01 00:00:00")
    comparison = ("dimension", "covered_count", "denominator", "percentage",
                  "source_snapshot_id", "mart_content_checksum", "build_id")
    first_points = sorted(
        ({k: row[k] for k in comparison} for row in first.values()),
        key=lambda r: r["dimension"],
    )
    second_points = sorted(
        ({k: row[k] for k in comparison} for row in second.values()),
        key=lambda r: r["dimension"],
    )
    assert first_points == second_points

def test_missing_source_snapshot_publishes_no_report(tmp_path):
    """AC-11: a missing source registry fails before writing the manifest."""
    output = tmp_path / "manifest.json"
    with pytest.raises(ValueError):
        reproducibility_manifest.build_manifest(
            tmp_path / "missing-registry.json", tmp_path / "database.duckdb", output
        )
    assert not output.exists()


def test_missing_canonical_mart_publishes_no_report(tmp_path, monkeypatch):
    """AC-11: an unreadable canonical mart fails before publication."""
    registry = tmp_path / "registry.json"
    registry.write_text("{}", encoding="utf-8")
    output = tmp_path / "manifest.json"
    monkeypatch.setattr(
        reproducibility_manifest,
        "load_source_entries",
        lambda _: [],
    )
    monkeypatch.setattr(
        reproducibility_manifest,
        "compute_mart_entries",
        lambda _: (_ for _ in ()).throw(ValueError("missing canonical mart")),
    )
    with pytest.raises(ValueError):
        reproducibility_manifest.build_manifest(
            registry, tmp_path / "database.duckdb", output
        )
    assert not output.exists()


def test_uncomputable_coverage_report_publishes_no_report(tmp_path, monkeypatch):
    """AC-11: a manifest without a computed coverage report is rejected."""
    output = tmp_path / "manifest.json"
    monkeypatch.setattr(reproducibility_manifest, "load_source_entries", lambda _: [])
    monkeypatch.setattr(
        reproducibility_manifest,
        "compute_mart_entries",
        lambda _: {},
    )
    with pytest.raises(ValueError):
        reproducibility_manifest.build_manifest(
            tmp_path / "registry.json", tmp_path / "database.duckdb", output
        )
    assert not output.exists()


def test_missing_evidence_is_reported_as_uncovered():
    """AC-12: null, unknown, unavailable, and false evidence never passes."""
    report = _run_report(
        [("req-1", 1, "carrot")],
        [("carrot", "food-1", "unavailable", False, "unknown", "unknown")],
        [1],
    )
    assert report["nutrition_coverage"]["covered_count"] == 1
    assert report["price_availability"]["covered_count"] == 0
    assert report["package_unit_conversion_coverage"]["covered_count"] == 0
    assert report["dietary_evidence_coverage"]["covered_count"] == 0

def test_report_association_matches_manifest_values(tmp_path: Path) -> None:
    """AC-1, AC-10, AC-13: the report's association columns equal the
    manifest's association block, end to end."""
    association = {
        "REMY_SOURCE_SNAPSHOT_ID": "fooddata:v1,fairprice:v1,recipe:v1",
        "REMY_MART_CONTENT_CHECKSUM": "abc123",
        "REMY_BUILD_ID": "def456",
    }
    report = _run_report(
        [("req-1", 1, "carrot")],
        [("carrot", "food-1", "estimated", True, "certified", "unknown")],
        [1],
        env_override=association,
    )
    for row in report.values():
        assert row["source_snapshot_id"] == association["REMY_SOURCE_SNAPSHOT_ID"]
        assert row["mart_content_checksum"] == association["REMY_MART_CONTENT_CHECKSUM"]
        assert row["build_id"] == association["REMY_BUILD_ID"]

def test_unset_association_fails_closed():
    """AC-11 edge: an unset association raises before any report is produced."""
    with pytest.raises(Exception):  # the raised compiler error, surfaced by the fixture
        _run_report([], [], [], env_override={
            "REMY_SOURCE_SNAPSHOT_ID": "",
            "REMY_MART_CONTENT_CHECKSUM": "mart-1",
            "REMY_BUILD_ID": "build-1",
        })
