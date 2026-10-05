"""Failing tests for p1-003 coverage quality reporting (AC-1 through AC-8)."""

DIMENSIONS = [
    "nutrition_coverage",
    "price_availability",
    "package_unit_conversion_coverage",
    "dietary_evidence_coverage",
    "whole_recipe_completeness",
]


def test_build_publishes_exactly_five_dimensions():
    """AC-1: exactly five named dimensions exist (fails until model exists)."""
    assert False, "coverage_quality_report model does not exist yet"


def test_nutrition_measure_uses_requirement_denominator():
    """AC-2: nutrition uses validated status and requirement denominator."""
    assert False, "coverage_quality_report model does not exist yet"


def test_price_measure_uses_estimated_price_status():
    """AC-3: price uses estimated status."""
    assert False, "coverage_quality_report model does not exist yet"


def test_conversion_measure_requires_compatible_unit_basis():
    """AC-4: conversion requires cost_basis_compatible = true."""
    assert False, "coverage_quality_report model does not exist yet"


def test_dietary_measure_requires_explicit_supported_evidence():
    """AC-5: dietary uses exact accepted sets."""
    assert False, "coverage_quality_report model does not exist yet"


def test_whole_recipe_requires_all_four_requirement_dimensions():
    """AC-6: whole-recipe requires all four per-requirement dimensions."""
    assert False, "coverage_quality_report model does not exist yet"


def test_nutrition_only_requirement_is_not_price_or_whole_recipe_complete():
    """AC-7: nutrition present, price/conversion absent stays independent."""
    assert False, "coverage_quality_report model does not exist yet"


def test_zero_populations_are_explicit_not_100_percent():
    """AC-8: zero populations do not fabricate a passing percentage."""
    assert False, "coverage_quality_report model does not exist yet"
