"""Contract tests for p1-003 coverage quality reporting."""

from pathlib import Path

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


def test_build_publishes_exactly_five_dimensions():
    """AC-1: exactly five named dimensions exist."""
    assert SQL.count("'nutrition_coverage'") == 1
    assert SQL.count("'price_availability'") == 1
    assert SQL.count("'package_unit_conversion_coverage'") == 1
    assert SQL.count("'dietary_evidence_coverage'") == 1
    assert SQL.count("'whole_recipe_completeness'") == 1


def test_nutrition_measure_uses_requirement_denominator():
    """AC-2: nutrition uses validated status and requirement denominator."""
    assert "nutrition_status, 'missing') = 'validated'" in SQL
    assert "count(*) filter (where nutrition_covered)" in SQL


def test_price_measure_uses_estimated_price_status():
    """AC-3: price uses estimated status."""
    assert "price_status, 'unavailable') = 'estimated'" in SQL


def test_conversion_measure_requires_compatible_unit_basis():
    """AC-4: conversion requires cost_basis_compatible = true."""
    assert "cost_basis_compatible, false)" in SQL


def test_dietary_measure_requires_explicit_supported_evidence():
    """AC-5: dietary uses exact accepted sets."""
    assert "halal_status in ('certified', 'retailer_claim', 'ingredient_screen_pass')" in SQL
    assert "vegetarian_status in ('retailer_claim', 'ingredient_screen_pass')" in SQL


def test_whole_recipe_requires_all_four_requirement_dimensions():
    """AC-6: whole-recipe requires all four per-requirement dimensions."""
    assert "rf.nutrition_covered" in SQL
    assert "rf.price_covered" in SQL
    assert "rf.conversion_covered" in SQL
    assert "rf.dietary_covered" in SQL
    assert "from recipe_flags" in SQL


def test_nutrition_only_requirement_is_not_price_or_whole_recipe_complete():
    """AC-7: nutrition present, price/conversion absent stays independent."""
    assert "nutrition_covered" in SQL and "price_covered" in SQL
    assert "price_covered, false" not in SQL


def test_zero_populations_are_explicit_not_100_percent():
    """AC-8: zero populations do not fabricate a passing percentage."""
    assert "case when denominator = 0 then null" in SQL
    assert "'no_population'" in SQL


def test_report_has_exactly_five_dimensions_and_association():
    """AC-13: dimensions and build-association fields are explicit."""
    for field in ("source_snapshot_id", "mart_content_checksum", "build_id"):
        assert field in SQL
    assert SQL.count(" as dimension") == 1


def test_repeated_report_comparison_points_are_content_columns():
    """AC-9: deterministic report fields are all named in the model."""
    for field in (
        "covered_count",
        "denominator",
        "percentage",
        "dimension",
        "source_snapshot_id",
        "mart_content_checksum",
    ):
        assert field in SQL


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
