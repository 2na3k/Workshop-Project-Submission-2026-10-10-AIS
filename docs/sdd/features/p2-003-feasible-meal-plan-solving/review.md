# Review - Feasible meal-plan solving

Verdict: APPROVE

## CI evidence

OVERALL: PASS (`ci-results.md`, run 2026-10-09T12:57:53+08:00).

Review gate: PASS (`python3 .sdd/scripts/sdd.py gate review p2-003-feasible-meal-plan-solving` executed in WSL environment).

The recorded CI run verifies:
- `test`: 79 passed, 1 warning in 11.56s (`uv run --package remy-api pytest -q tests/features/calculator tests/features/plan`)
- `lint`: PASS (`uv run --package remy-api ruff check src/api/features/calculator src/api/features/plan --select F,E9`)
- `typecheck`: PASS (`uv run --package remy-api mypy src/api/features/calculator src/api/features/plan --ignore-missing-imports` - 31 source files)

Independently verified by reviewer in WSL:
- Plan & inspect test suite: `uv run --package remy-api pytest -v tests/features/plan tests/features/calculator/test_inspect_candidates.py` -> 39 passed, 1 warning in 12.80s.

## Acceptance criteria

| AC | PASS/FAIL | test name or file:line |
|---|---|---|
| AC-1 | PASS | `tests/features/plan/test_domain_solver.py::test_feasible_returns_plan` (L38) |
| AC-2 | PASS | `tests/features/plan/test_domain_solver.py::test_infeasible_names_individually_binding_set` (L26) |
| AC-2b | PASS | `tests/features/plan/test_response_contract.py::test_infeasibility_reason_discriminator` (L70) |
| AC-3 | PASS | `tests/features/plan/test_domain_solver.py::test_producible_never_infeasible` (L33) |
| AC-4 | PASS | `tests/features/plan/test_service_nutrition_drop.py::test_tracked_partial_nutrition_drops` (L75) |
| AC-4b | PASS | `tests/features/plan/test_service_nutrition_drop.py::test_drop_categorized_under_nutrient` (L87) |
| AC-4c | PASS | `tests/features/plan/test_service_nutrition_drop.py::test_goal_on_missing_nutrient_drops` (L100) |
| AC-5 | PASS | `tests/features/plan/test_service_nutrition_drop.py::test_untracked_partial_nutrition_retained` (L108) |
| AC-6 | PASS | `tests/features/plan/test_causes.py::test_present_evidence_cause_distinct` (L4) |
| AC-7 | PASS | `tests/features/plan/test_causes.py::test_multi_cause_precedence` (L12) |
| AC-8a | PASS | `tests/features/plan/test_response_contract.py::test_plan_level_record` (L105) |
| AC-8b | PASS | `tests/features/plan/test_response_contract.py::test_recipe_level_record` (L112) |
| AC-8c | PASS | `tests/features/plan/test_response_contract.py::test_constraint_level_record` (L119) |
| AC-9 | PASS | `tests/features/plan/test_tolerance.py::test_relaxed_plan_labeled_and_records_tolerance` (L23) and `tests/features/plan/test_tolerance.py::test_structural_relaxations_are_not_applied` (L34) |
| AC-10 | PASS | `tests/features/plan/test_tolerance.py::test_widening_insufficient_hard_infeasible` (L30) |
| AC-11 | PASS | `tests/features/plan/test_response_contract.py::test_no_audit_provenance_in_response` (L130) |
| AC-12 | PASS | `tests/features/plan/test_response_contract.py::test_deterministic_across_runs` (L86) |
| AC-13 | PASS | `tests/features/plan/test_service_nutrition_drop.py::test_unmapped_cause_and_binding` (L118) |
| AC-14 | PASS | `tests/features/plan/test_solver_unavailable.py::test_tolerance_out_of_range_rejected_without_solver_invocation` (L11) |
| AC-14b | PASS | `tests/features/plan/test_tolerance.py::test_tolerance_absent_defaults_zero` (L41) |
| AC-15 | PASS | `tests/features/plan/test_solver_unavailable.py::test_solver_unavailable_hard_fail` (L38) |
| Interface (calculator -> plan) | PASS | `tests/features/plan/test_plan_calculator_integration.py::test_plan_consumes_calculator_partial_nutrition` (L98) |
| Interface (repo -> service) | PASS | `tests/features/plan/test_service_integration.py::test_unmapped_fact_and_relaxed_label_survive_service_path` (L90) |
| Interface (calculator inspect) | PASS | `tests/features/calculator/test_inspect_candidates.py::test_inspect_candidates_returns_missing_nutrients_per_recipe` (L51) |

## Constitution compliance

Violations: none.

| Rule | Result | Evidence |
|---|---|---|
| R-1 | PASS | Graph canonical names are used as single source of truth; vocabulary consolidation in `domain/types.py` unified request code vs canonical field across packages; API documentation in `API_doc.md` updated in the same change to match `/plan` schemas (`nutrient_tolerance_pct`, `relaxed`, `applied_tolerance_pct`). No code path accepts dual names for the same concept. |
| R-2 | PASS | Inward dependency direction maintained: router -> service -> repository/domain -> models. `PlanService` communicates with the calculator feature strictly via the public method `CostNutritionService.inspect_candidates`, without importing private calculator internals. `domain` remains a leaf. `workflows` does not depend on `api`, `api` does not depend on `app`. |
| R-3 | PASS | Constraint solver remains OR-Tools CP-SAT (`ortools.sat.python.cp_model`), maintaining the fixed stack shape. Structural relaxations and round-robin non-solver fallbacks were removed in compliance with R-3 and C-6. |
| R-4 | PASS | Graph edge definitions and provenance properties on `REQUIRES` and `FULFILLS` edges are preserved. |
| R-5 | PASS | Missing evidence for a tracked constraint drops candidate recipes with an `evidence-absent` cause; never mapped to passing, compliant, or zero. Drops are distinct from present-evidence exclusions and unmapped requirements. |
| R-6 | PASS | Severe allergens drop candidate recipes with `present-evidence-excludes`; mild allergens retain with warnings. Precedence preserved over absent evidence. |
| R-7 | PASS | Explicit dietary compliance required; undeclared or unknown compliance drops candidate recipes as evidence-absent. |
| R-8 | PASS | Freshness filter applied in calculator (`freshness_status == "fresh"`). Per Clarification C-1 / amended A-006, recipe-level cost drop is deferred to budget feature. |
| R-9 | PASS | `PlanService.generate` consumes item-level `PARTIAL_NUTRITION_DATA` via `inspect_candidates`; candidate recipes missing contributing evidence for any tracked nutrient are globally excluded with `evidence-absent` cause categorized under that nutrient constraint. Untracked missing nutrients are retained. |
| R-10 | PASS | Calculator evaluates cost-basis eligibility; per Clarification C-1 / amended A-006, recipe-level cost drop is deferred to budget feature and `MISSING_PACKAGE_DATA` does not drop recipes in p2-003. |
| R-11 | PASS | Consumed cost and retail package price distinctions maintained in calculator; plan does not conflate them. |
| R-12 | PASS | Deterministic nutrient conflict precedence maintained in calculator. |
| R-13 | PASS | Best-score ranking without confidence floor respected; `selected_offer` incorporates `select_package` best-score ranking. |
| R-14 | PASS | Producible plans always return a plan. When no feasible assignment exists after permitted nutrient-bound widening [0, 25]%, solver returns `PlanInfeasible` naming the deterministic set of individually-binding constraints. Structural relaxations and degraded fallbacks are prohibited and removed. |
| R-15 | PASS | Data quality gates respected; real-mart demonstration deferred under `docs/findings/data-prep-price-path.md`; behavior verified against fixture-backed drivers. |
| R-16 | PASS | User-facing response excludes audit-only provenance (`confidence`, `normalization_version`, `food_key`, and source IDs); these are retained only in `PlanTrace`. |
| R-17 | PASS | Response exposes three-level outcomes (plan, recipe, constraint), distinguishing `present-evidence-excludes`, `evidence-absent`, and `unmapped`. |

## Plan adherence

The implementation adheres to the approved plan:
- Tasks T-1 through T-18 were executed and marked complete in `plan.md`.
- Group 1 (T-2, T-3): Request schema updated with `nutrient_tolerance_pct` [0, 25]; solver relaxation ladder replaced with single nutrient-bound widening; structural relaxations and round-robin fallback removed; `SolverUnavailable` raises 503 on missing solver.
- Group 2 (T-4, T-5): Single-constraint drop-out probe implemented in fixed order with deterministic solver parameters (`random_seed=0`, `num_search_workers=1`); `PlanInfeasible` carries structured `NamedConstraint` list and `reason` discriminator (`no-recipes-survived` vs `no-assignment`).
- Group 3 (T-6, T-7): Public method `CostNutritionService.inspect_candidates(recipes, servings)` implemented in calculator service, returning `missing_nutrients` and `selected_offer` without dropping recipes on missing package data.
- Group 4 (T-8, T-9): `PlanRepository.fetch_candidates` records per-recipe `unmapped_requirements: list[RequirementRef]`.
- Group 5 (T-10, T-11, T-12): `inspect_candidates` wired into `PlanService.generate`; tracked nutrient drops applied; cause model derived with precedence `present-evidence-excludes` -> `evidence-absent` -> `unmapped`; `PlanTrace` created; user-facing response provides three-level reasoning without audit provenance.
- Group 6 (T-13): `API_doc.md` updated for the `/plan` request and response contract.
- Group 7 (T-14, T-15): Integration tests verify plan-to-calculator and repository-to-service flows, confirming `MISSING_PACKAGE_DATA` is ignored and `OfferRef.food_key` remains trace-only.
- Group 8 (T-17, T-18): Decisions documented in `decisions.md`; full test suite passing in CI.

Deviations: none.

## Findings

None.

## Nits (non-blocking)

- N-1: Spec sync note recorded in `decisions.md`: In `spec.md` under `## Interfaces & dependencies` (Q7 integration paragraph), `inspect_candidates` is described as returning per-recipe, per-nutrient item-level signals. BD-2 extended it to also return the per-requirement `selected_offer` for AC-8c's constraint-level record. This addition is additive and does not contradict any acceptance criterion; add the one-line description at the next spec touch.
- N-2: Real-mart demonstration remains deferred under `docs/findings/data-prep-price-path.md` due to the upstream dbt parse failure; test coverage relies on fixture-backed drivers.
