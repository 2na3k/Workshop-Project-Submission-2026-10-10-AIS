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


def _run_report(requirements, candidates, recipes):
    """Execute the dbt model SQL against a small DuckDB fixture warehouse."""
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
    rendered = re.sub(
        r"\{\{ env_var\(\"([A-Z_]+)\", \"\"\) \}\}",
        lambda match: {"REMY_SOURCE_SNAPSHOT_ID": "snapshot-1", "REMY_MART_CONTENT_CHECKSUM": "mart-1", "REMY_BUILD_ID": "build-1"}[match.group(1)],
        rendered,
    )
    rendered = rendered.replace("{{ run_started_at }}", "2026-10-05 00:00:00")
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


def test_whole_recipe_requires_all_four_requirement_dimensions(populated_fixture):
    """AC-6: whole-recipe requires all four per-requirement dimensions."""
    assert populated_fixture["whole_recipe_completeness"]["covered_count"] == 0
    assert populated_fixture["whole_recipe_completeness"]["denominator"] == 2


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
    """AC-13: dimensions and build-association fields are explicit."""
    for field in ("source_snapshot_id", "mart_content_checksum", "build_id"):
        assert field in SQL
    assert SQL.count(" as dimension") == 1


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
