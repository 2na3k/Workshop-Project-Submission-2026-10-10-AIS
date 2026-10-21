# Review - Constraint evidence filtering

Verdict: APPROVE

## CI evidence

OVERALL: PASS (`ci-results.md`, run 2026-10-05T21:51:43+08:00).

Review gate: PASS (`python3 .sdd/scripts/sdd.py gate review p2-001-constraint-evidence-filtering` executed in WSL environment).

The recorded CI run verifies:
- `test`: 22 passed in 7.50s (`uv run --package remy-api pytest -q tests/features/plan tests/features/dietary tests/features/calculator/test_domain_nutrition.py tests/features/calculator/test_domain_cost.py`)
- `lint`: PASS (`uv run --package remy-api ruff check src/api/features/plan/filtering.py src/api/features/plan/models.py src/api/features/plan/repository.py src/api/features/plan/service.py --select F,E9`)
- `typecheck`: PASS (`uv run --package remy-api mypy src/api/features/plan/filtering.py src/api/features/plan/models.py src/api/features/plan/repository.py --ignore-missing-imports`)

Independently verified by reviewer in WSL:
- AC-9 unit test: `uv run --package remy-api pytest -q tests/features/calculator/test_domain_conversion.py::test_incompatible_unit_basis_is_excluded_and_drops_when_only_option` -> 1 passed.

## Acceptance criteria

| AC | PASS/FAIL | test name or file:line |
|---|---|---|
| AC-1 | PASS | `tests/features/dietary/test_domain_rules.py::test_undeclared_allergen_drops_as_evidence_absent`, `test_unknown_dietary_state_drops_and_explicit_compliance_retains`, and `tests/features/calculator/test_domain_nutrition.py::test_profileless_candidate_is_not_zero_and_drops_when_required` |
| AC-2 | PASS | `tests/features/dietary/test_domain_rules.py::test_undeclared_allergen_drops_as_evidence_absent`, `test_unknown_dietary_state_drops_and_explicit_compliance_retains`, and `tests/features/calculator/test_domain_nutrition.py::test_profileless_candidate_is_not_zero_and_drops_when_required` |
| AC-3 | PASS | `tests/features/dietary/test_domain_rules.py::test_severe_allergen_drops_as_present_exclusion` |
| AC-4 | PASS | `tests/features/dietary/test_domain_rules.py::test_mild_allergen_retains_with_ingredient_warning` |
| AC-4b | PASS | `tests/features/dietary/test_domain_rules.py::test_mild_allergen_without_ingredient_identity_fails` |
| AC-5 | PASS | `tests/features/dietary/test_domain_rules.py::test_undeclared_allergen_drops_as_evidence_absent` |
| AC-6 | PASS | `tests/features/dietary/test_domain_rules.py::test_unknown_dietary_state_drops_and_explicit_compliance_retains` |
| AC-7 | PASS | `tests/features/calculator/test_domain_nutrition.py::test_profileless_candidate_is_not_zero_and_drops_when_required` |
| AC-7b | PASS | `tests/features/calculator/test_domain_nutrition.py::test_partial_profile_with_missing_requested_nutrient_is_not_zero` |
| AC-8 | PASS | `tests/features/calculator/test_domain_cost.py::test_stale_offer_excluded_and_24_hour_boundary_is_fresh` |
| AC-9 | PASS | `tests/features/calculator/test_domain_conversion.py::test_incompatible_unit_basis_is_excluded_and_drops_when_only_option` |
| AC-10 | PASS | `tests/features/plan/test_filtering.py::test_compliant_present_evidence_retains_without_drop_cause` |
| AC-11 | PASS | `tests/features/plan/test_filtering.py::test_absent_and_present_exclusion_causes_are_distinct` |
| AC-12 | PASS | `tests/features/plan/test_filtering.py::test_present_exclusion_precedes_absent_evidence` |
| AC-13 | PASS | `tests/features/dietary/test_domain_rules.py::test_missing_allergen_severity_defaults_to_severe` |
| AC-14 | PASS | `tests/features/plan/test_filtering.py::test_empty_candidate_set_is_reported_distinctly_from_constraint_drop` |
| AC-15 | PASS | `tests/features/plan/test_filtering.py::test_unsupported_codes_are_input_errors_not_evidence_absent` |
| AC-16 | PASS | `tests/features/plan/test_filtering.py::test_all_recipes_drop_returns_empty_pool_with_per_requirement_causes` |
| Integration (repo -> filter) | PASS | `tests/features/plan/test_service_integration.py::test_repository_evidence_reaches_filtering` |
| Integration (filter -> service) | PASS | `tests/features/plan/test_service_integration.py::test_service_propagates_distinct_filter_outcomes` |
| Integration (canonical FULFILLS -> repo) | PASS | `tests/features/plan/test_service_integration.py::test_canonical_evidence_fields_are_consumed` |

## Constitution compliance

Violations: none.

| Rule | Result | Evidence |
|---|---|---|
| R-1 | PASS | Uses single canonical graph field names (`BEST_FULFILLMENT`, `freshness_status`, `cost_basis_compatible`, etc.) without aliases or dual support. |
| R-2 | PASS | Inward dependency direction maintained: `PlanService` -> `PlanRepository`, `filtering`, `models`. No cross-feature internal imports; allergen resolution uses public workflows rule function. |
| R-3 | PASS | Pure Python web service and constraint-solving structure maintained; no parallel stores or frameworks added. |
| R-4 | PASS | Graph edge definitions and linking records preserved; repository reads canonical `REQUIRES` and `FULFILLS` evidence. |
| R-5 | PASS | Absent, missing, or blank evidence explicitly drops candidates as `evidence-absent` and is never converted to pass, compliant, or zero. |
| R-6 | PASS | Severe allergen match drops candidate with `present-evidence-excludes`; mild allergen match retains with ingredient-scoped `IngredientWarning`; unknown/undeclared allergen drops as `evidence-absent`. |
| R-7 | PASS | Explicit compliant evidence required for halal, vegan, and vegetarian; unknown/absent states drop as `evidence-absent`. |
| R-8 | PASS | Offers older than 24 hours are treated as unavailable; 24-hour threshold is inclusive; missing fresh offer drops candidate as `evidence-absent`. |
| R-9 | PASS | Missing nutrition profile or missing requested nutrient value contributes no value (not zero) and drops as `evidence-absent`. |
| R-10 | PASS | Incompatible recipe/package unit basis excludes product from cost calculation; requirement left with no compatible product drops as `evidence-absent`. |
| R-11 | PASS | Consumed cost and retail price calculations are not modified by candidate filtering. |
| R-12 | PASS | Nutrient precedence rules are unaffected by this feature. |
| R-13 | PASS | No minimum mapping-confidence floor added; candidate ordering preserved. |
| R-14 | PASS | Plan feasibility floor and binding constraint reporting are unaffected. |
| R-15 | PASS | Real-mart demonstration remains deferred under `docs/findings/data-prep-price-path.md`; fixture-backed candidate validation verified. |
| R-16 | PASS | Plan response boundary is not widened; evaluation drop causes and audit data remain encapsulated in internal candidate outcomes (`FilterResult`, `CandidateOutcome`). |
| R-17 | PASS | Evaluation preserves distinct `evidence-absent` and `present-evidence-excludes` causes at constraint granularity for downstream explanation consumption. |

## Plan adherence

The implementation adheres to the approved plan:
- Tasks T-1 through T-7 are fully implemented and verified.
- The filtering module implements explicit per-constraint evaluations, clarified cause precedence (present-evidence exclusion takes precedence over absent evidence), inclusive 24-hour freshness boundary, default severe allergen severity, and input error validations for unsupported codes.
- Minimal outcome models (`CandidateOutcome`, `ConstraintEvaluation`, `IngredientWarning`, `FilterResult`) provide structured outcomes and distinct drop causes without exposing audit-only internals at the user API boundary.
- Repository hydrates canonical `FULFILLS` evidence and service propagates filtered outcomes.
- Minor organizational deviation: in `plan.md`, AC-1 and AC-2 were initially drafted as single functions in `test_filtering.py`. They were instead implemented and verified directly within the domain-specific rule test suites (`test_domain_rules.py` for allergen/dietary and `test_domain_nutrition.py` for nutrition), while `test_filtering.py` focused on the composite outcome contract. Coverage for AC-1 and AC-2 is comprehensive and complete.

## Findings

None.

## Nits (non-blocking)

- N-1: `tests/features/calculator/test_domain_conversion.py` contains two older pre-existing unit conversion tests that expect legacy string markers (`UNIT_ASSUMED_GRAMS` vs `ML_ASSUMED_GRAMS`). While the AC-9 test (`test_incompatible_unit_basis_is_excluded_and_drops_when_only_option`) passes cleanly, running the whole file directly produces failures on those legacy tests. Recommend cleaning up those legacy tests in p2-002.
- N-2: Running `python` directly in Windows PowerShell can encounter encoding mismatch on UTF-8 characters (e.g. em-dashes `—`) during hash validation; running via WSL (`python3 .sdd/scripts/sdd.py`) works cleanly per `AGENTS.md`.
