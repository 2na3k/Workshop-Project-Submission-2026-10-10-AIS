# Review - Cost and nutrition calculation

Verdict: APPROVE

## CI evidence

OVERALL: PASS (`ci-results.md`, run 2026-10-07T21:16:29+08:00).

Review gate: PASS (`python3 .sdd/scripts/sdd.py gate review p2-002-cost-nutrition-calculation` executed in WSL environment).

The recorded CI run verifies:
- `test`: 40 passed, 1 warning in 10.07s (`uv run --package remy-api pytest -q tests/features/calculator`)
- `lint`: PASS (`uv run --package remy-api ruff check src/api/features/calculator --select F,E9`)
- `typecheck`: PASS (`uv run --package remy-api mypy src/api/features/calculator --ignore-missing-imports` - 16 source files)

Independently verified by reviewer in WSL:
- Full test suite: `uv run --package remy-api pytest -v tests/features/calculator` -> 40 passed in 12.89s.

## Acceptance criteria

| AC | PASS/FAIL | test name or file:line |
|---|---|---|
| AC-1 | PASS | `tests/features/calculator/test_domain_nutrition.py::test_scale_total_per_serving` |
| AC-2 | PASS | `tests/features/calculator/test_domain_nutrition.py::test_nutrient_null_when_any_missing_and_warning_names` |
| AC-3 | PASS | `tests/features/calculator/test_domain_cost.py::test_consumed_vs_retail_distinct_sub_package` |
| AC-4 | PASS | `tests/features/calculator/test_domain_cost.py::test_multi_package_ceil` |
| AC-5 | PASS | `tests/features/calculator/test_domain_cost.py::test_ineligible_excluded_missing_package_warning` |
| AC-6 | PASS | `tests/features/calculator/test_domain_nutrition.py::test_branded_over_generic` |
| AC-7 | PASS | `tests/features/calculator/test_domain_nutrition.py::test_same_source_tie_break` |
| AC-8 | PASS | `tests/features/calculator/test_domain_nutrition.py::test_order_independent_determinism` |
| AC-9 | PASS | `tests/features/calculator/test_mapping_selection.py::test_only_accepted_candidates_usable` and `test_no_accepted_candidate_is_unresolvable` |
| AC-10 | PASS | `tests/features/calculator/test_mapping_selection.py::test_single_confidence_zero_selected_trace` |
| AC-11 | PASS | `tests/features/calculator/test_mapping_selection.py::test_ranking_order_and_runner_up_trace` |
| AC-12 | PASS | `tests/features/calculator/test_mapping_selection.py::test_confidence_zero_and_one_valid` |
| AC-13 | PASS | `tests/features/calculator/test_domain_cost.py::test_package_volume_eligible_and_converted_silently` |
| AC-14 | PASS | `tests/features/calculator/test_domain_conversion.py::test_nutrient_non_mass_unit_warns` |
| AC-15 | PASS | `tests/features/calculator/test_service_errors.py::test_unsupported_unit_and_nonfinite_reject` |
| AC-16 | PASS | `tests/features/calculator/test_service_errors.py::test_unresolvable_and_no_accepted_reject` |
| AC-17 | PASS | `tests/features/calculator/test_resolver.py::test_normalization_and_alias` |
| AC-18 | PASS | `tests/features/calculator/test_response_schema.py::test_user_payload_field_set` |
| AC-19 | PASS | `tests/features/calculator/test_response_schema.py::test_invalid_request_rejected_custom_envelope` |
| AC-20 | PASS | `tests/features/calculator/test_domain_cost.py::test_each_eligibility_condition_excludes` |
| Interface (repo -> service) | PASS | `tests/features/calculator/test_repository_integration.py::test_query_b_reads_deployed_names_and_full_contract` |
| Interface (service -> router) | PASS | `tests/features/calculator/test_calculator_integration.py::test_end_to_end_repo_to_serialized_payload` |
| Interface (service -> trace) | PASS | `tests/features/calculator/test_calculator_integration.py::test_end_to_end_repo_to_serialized_payload` |

## Constitution compliance

Violations: none.

| Rule | Result | Evidence |
|---|---|---|
| R-1 | PASS | Repository reads canonical `ful.confidence AS confidence` (dropped `mapping_confidence`). Documentation in `API_doc.md` updated in the same change to match response schema. |
| R-2 | PASS | Inward dependency direction maintained: router -> service -> repository/domain -> models. Production calculator code does not import `api.features.plan` internals. |
| R-3 | PASS | Pure Python web service structure preserved; no changes to stack shape. |
| R-4 | PASS | Graph edge definitions respected; repository query projects canonical `FULFILLS` and `Food` fields. |
| R-5 | PASS | Unresolvable ingredients and candidate sets lacking accepted candidates fail with rejection (never zero/inferred). Missing cost packages produce `MISSING_PACKAGE_DATA` with null cost fields; non-evaluable nutrients produce null recipe/per-serving totals. |
| R-6 | PASS | Allergen policy owned upstream by p2-001; not altered here. |
| R-7 | PASS | Dietary compliance owned upstream by p2-001; not altered here. |
| R-8 | PASS | `select_package` enforces `freshness_status == "fresh"`. Any offer not fresh is excluded from cost calculation. |
| R-9 | PASS | Profile-less candidates contribute no value; item emits `PARTIAL_NUTRITION_DATA` listing missing nutrients; totals are null unless every contributing ingredient carries a value. |
| R-10 | PASS | Cost eligibility requires `price_status == "estimated"`, `price_match_status == "accepted"`, `freshness_status == "fresh"`, `price_basis` in `{package_mass, package_volume}`, `currency == "SGD"`, and positive price and package amounts. `cost_basis_compatible` is not gated on. Volume converted silently to grams. |
| R-11 | PASS | Consumed cost (`P * Q / S`) and retail purchase cost (`ceil(Q / S) * P`) are exposed as separate fields with distinct values. |
| R-12 | PASS | Deterministic nutrition precedence applied per nutrient: branded (`crawler_fdc_profile`) > generic (`fooddata_central`/other), then smallest `(nutrition_rank, selection_priority, food_key)` tuple with missing ranks sorting last. Stable under shuffled input order. |
| R-13 | PASS | No confidence floor: package with confidence 0 is selectable if sole eligible. Best-score ordering: unit price -> retail package cost -> -confidence -> lexicographic `(food_key, retailer, listing_name)`. Selected package confidence and runner-up identity recorded in trace. |
| R-14 | PASS | Plan feasibility floor owned by p2-003; not altered here. |
| R-15 | PASS | Real-mart demonstration deferred under `docs/findings/data-prep-price-path.md`; fixture-backed driver verified. |
| R-16 | PASS | User-facing response excludes audit-only provenance (`confidence`, `food_key`, `fdc_id`, `source_*`, versions, ranks, `approval_status`). These are encapsulated in `CalculationTrace` and discarded at the router boundary. |
| R-17 | PASS | Multi-level explanations owned by p2-003/p3-001; calculator supplies the requisite item-level signals (`MISSING_PACKAGE_DATA`, `PARTIAL_NUTRITION_DATA`). |

## Plan adherence

The implementation adheres to the approved plan:
- Tasks T-1 through T-25 are fully executed and passing.
- Stale tests in `test_domain_conversion.py` and `test_resolver.py` repaired (T-3, T-4, T-5).
- Canonical property names and nine nutrients selected in `repository.py` and mapped to `NutrientProfile` and `RetailSKU` (T-6, T-7).
- Domain cost package eligibility, silent volume conversion, and ceil tolerance `1e-9` implemented in `domain/cost.py` (T-8, T-9, T-10, T-11).
- Per-nutrient conflict precedence implemented in `domain/nutrition_select.py` with null-when-any semantics in `domain/nutrition.py` (T-12, T-13, T-14).
- R-13 named fixture `test_mapping_selection.py` created and verified (T-15, T-16).
- Service orchestration, rejection paths, trace generation, and router decoupling implemented and verified (T-17, T-18, T-19, T-20).
- Schemas updated with `MAX_REQUEST_INGREDIENTS = 100` and AC-18 payload fields (T-21).
- `API_doc.md` updated in place to match canonical response shape (T-22).
- End-to-end integration test verifies repository-to-service-to-router payload serialization and trace stripping (T-23).
- Decisions and deferrals documented in `decisions.md` (T-24).

## Findings

- [x] F-A [MAJOR] `plan/filtering.py::_evaluate_freshness` uses a 24-hour timestamp check when `offer_observed_at` exists; amended R-8 requires status comparison (`freshness_status == "fresh"`). — route: implement (p2-001 open follow-up, recorded in `docs/sdd/features/p2-001-constraint-evidence-filtering/decisions.md`)
- [x] F-B [MAJOR] `plan/filtering.py::_evaluate_cost_basis` gates on `cost_basis_compatible`; amended R-10 makes that flag informational. — route: implement (p2-001 open follow-up, recorded in `docs/sdd/features/p2-001-constraint-evidence-filtering/decisions.md`)
- [x] F-C [MAJOR] Real data-preparation marts to Neo4j load is blocked by `data-prep-price-path.md`; repository-to-service integration uses recorded `FULFILLS` rows with mocked Neo4j driver. — route: implement (data-preparation deferral, recorded in `decisions.md`)
- [x] F-D [MINOR] R-16 named fixture check path in constitution is `tests/api/test_response_schema.py`; this feature places its equivalent assertion at `tests/features/calculator/test_response_schema.py`. — route: constitution (recorded in `decisions.md` for phase review)

## Nits (non-blocking)

- N-1: `tests/features/calculator/test_domain_cost.py` and `test_domain_nutrition.py` import `api.features.plan.filtering` and `api.features.plan.models` for cross-feature interaction fixtures. Consider colocating plan-filtering assertions strictly in `tests/features/plan/` in a future cleanup.
