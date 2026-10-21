# Review - Conversational constraint interface

Verdict: APPROVE

## CI evidence

OVERALL: PASS (`ci-results.md`, run 2026-10-18T23:29:20+08:00).

Review gate: PASS (`python3 .sdd/scripts/sdd.py gate review p3-004-conversational-constraint-interface` executed in WSL environment).

The recorded CI run verifies:
- `test`: 119 passed, 0 skipped, 4 warnings across:
  - `remy-api`: `uv run --package remy-api pytest -q remy/api/tests/features/plan` (44 passed, 1 warning in 9.94s)
  - `remy-workflows`: `uv run --package remy-workflows pytest -q remy/workflows/tests` (30 passed, 1 warning in 2.88s)
  - `remy-app`: `uv run --package remy-app pytest -q remy/app/tests` (45 passed, 2 warnings in 12.32s)
- `lint`: PASS (`ruff check --select F,E9` across all packages)
- `typecheck`: PASS (`mypy --ignore-missing-imports` across all packages)
- `lint-imports`: PASS (`uv run lint-imports` - Analyzed 66 files, 122 dependencies; 4 contracts kept, 0 broken)

Independently verified by reviewer in WSL:
- Workflows test suite: `uv run --package remy-workflows pytest -v remy/workflows/tests` -> 30 passed, 0 skipped, 1 warning in 2.84s.
- App test suite: `uv run --package remy-app pytest -v remy/app/tests` -> 45 passed, 0 skipped, 2 warnings in 12.30s.
- API plan test suite: `uv run --package remy-api pytest -v remy/api/tests/features/plan` -> 44 passed, 1 warning in 9.86s.
- Architecture contracts: `uv run lint-imports` -> 4 kept, 0 broken.

All 11 previously-skipped tests across `remy-workflows` and `remy-app` have been un-skipped, resolved, and verified passing.

## Acceptance criteria

| AC | PASS/FAIL | test name or file:line |
|---|---|---|
| AC-1 | PASS | `remy/app/tests/api/test_chat_endpoint.py::test_valid_request_starts_event_stream` (L75), `remy/app/tests/api/test_chat_endpoint.py::test_missing_field_rejected` (L88) |
| AC-2 | PASS | `remy/app/tests/api/test_chat_endpoint.py::test_only_five_event_types_emitted` (L99) |
| AC-3 | PASS | `remy/workflows/tests/test_extract.py::test_natural_language_extracts_constraints_and_records_llm` (L10), `remy/workflows/tests/test_plan_node.py::test_plan_node_maps_cost_query_to_plan_input` (L99) |
| AC-4 | PASS | `remy/app/tests/api/test_cost_projection.py::test_cost_surfaced_on_cost_intent` (L147), `remy/app/tests/api/test_chat_endpoint.py::test_cost_intent_turn_drops_uncosted_recipe_end_to_end` (L231) |
| AC-5 | PASS | `remy/workflows/tests/test_extract.py::test_cost_query_absent_without_cost_reference` (L90), `remy/app/tests/api/test_cost_projection.py::test_no_cost_without_intent` (L158) |
| AC-6 | PASS | `remy/app/tests/api/test_cost_projection.py::test_consumed_and_retail_distinct_via_calculator` (L168) |
| AC-7 | PASS | `remy/app/tests/api/test_cost_projection.py::test_missing_package_reported_not_fabricated` (L178) |
| AC-8 | PASS | `remy/api/tests/features/plan/test_service_cost_drop.py::test_uncosted_recipe_dropped_evidence_absent` (L77), `test_uncosted_recipe_retained_when_cost_not_requested` (L98), `remy/app/tests/api/test_chat_endpoint.py::test_cost_intent_turn_drops_uncosted_recipe_end_to_end` (L231) |
| AC-9 | PASS | `remy/api/tests/features/plan/test_cost_drop_eligibility.py::test_non_fresh_package_drops_recipe` (L76) |
| AC-10 | PASS | `remy/api/tests/features/plan/test_cost_drop_eligibility.py::test_ineligible_price_basis_drops_recipe` (L99) |
| AC-11 | PASS | `remy/workflows/tests/test_generate.py::test_unknown_reference_rejected` (L93), `remy/workflows/tests/test_generate.py::test_structured_references_must_be_subsets_of_plan` (L39), `remy/workflows/tests/test_integration_generate_to_outcome.py::test_generate_structured_output_drives_final_outcome` (L6) |
| AC-12 | PASS | `remy/workflows/tests/test_generate.py::test_evidence_absent_not_restated_permissive` (L107), `remy/workflows/tests/test_generate.py::test_selected_evidence_absent_output_fails_deterministic_check` (L47) |
| AC-13 | PASS | `remy/app/tests/api/test_chat_endpoint.py::test_three_levels_present_in_stream` (L430) |
| AC-14 | PASS | `remy/app/tests/api/test_explanation_shape.py::test_drop_causes_are_distinct` (L44), `remy/api/tests/features/plan/test_causes.py::test_present_evidence_cause_distinct` (L6) |
| AC-15 | PASS | `remy/app/tests/api/test_response_schema.py::test_user_payload_excludes_audit_provenance` (L42), `remy/app/tests/api/test_chat_endpoint.py::test_stream_excludes_forbidden_fields` (L451) |
| AC-16 | PASS | `remy/app/tests/api/test_chat_endpoint.py::test_trace_id_present_trace_not_embedded` (L127) |
| AC-17 | PASS | `remy/app/tests/api/test_chat_endpoint.py::test_failure_emits_single_error_event` (L137), `remy/app/tests/api/test_composition.py::test_chat_workflow_failure_uses_error_envelope` (L40) |
| AC-18 | PASS | `remy/app/tests/api/test_chat_endpoint.py::test_plan_updated_has_delta_and_scoped_explanation` (L462) |
| AC-19 | PASS | `remy/app/tests/api/test_chat_endpoint.py::test_two_independent_requests_no_shared_state` (L152) |
| AC-20 | PASS | `remy/app/tests/api/test_response_schema.py` (L42, L48; both clauses PASS), `remy/app/tests/api/test_explanation_shape.py` (L34, L44, L56) at the A-007 paths. |
| AC-21 | PASS | `remy/app/tests/api/test_api_doc_plan_updated.py::test_plan_updated_example_has_explanation` (L7) |

## Constitution compliance

Violations: none

| Rule | Result | Evidence |
|---|---|---|
| R-1 | PASS | Canonical property names are strictly maintained across contracts, models, and repositories. No duplicate concepts or dual names supported. |
| R-2 | PASS | Inward dependency direction maintained: `remy/app` imports `api` and `workflows`; neither `api` nor `workflows` imports `app`. Architecture check `uv run lint-imports` confirms 4 contracts kept, 0 broken. |
| R-3 | PASS | Standard Python web service using FastAPI, LangGraph, OR-Tools, and Neo4j. Stack shape is unchanged. |
| R-4 | PASS | Graph edge provenance preservation is an upstream data-layer concern unaffected by conversational routing. |
| R-5 | PASS | Absent evidence causes candidate drop. Enforced in `PlanService.generate` when `drop_uncosted=True` via `RecipeNutritionSignal.selected_offer is None` producing `evidence-absent` cause. |
| R-6 | PASS | Severe vs mild allergen distinction preserved from upstream plan solver. |
| R-7 | PASS | No inferred dietary compliance: explicit compliance required upstream and passed through workflow extraction intact. |
| R-8 | PASS | Non-fresh price offer filtering is enforced at recipe level in `PlanService.generate(drop_uncosted=True)`. Verified by `remy/api/tests/features/plan/test_cost_drop_eligibility.py::test_non_fresh_package_drops_recipe` (R-8 recipe-level). |
| R-9 | PASS | Missing nutrient profile drops are evaluated upstream in plan solver and preserved. |
| R-10 | PASS | Cost basis eligibility requires `price_status == "estimated"`, `price_match_status == "accepted"`, and `price_basis in {package_mass, package_volume}`. Recipe dropped with `evidence-absent` when no eligible package exists. Verified by `remy/api/tests/features/plan/test_cost_drop_eligibility.py::test_ineligible_price_basis_drops_recipe` (R-10 recipe-level). |
| R-11 | PASS | Consumed cost vs retail package price separation is preserved in domain calculator and streamed distinctly; prices are permitted in chat payload and not conflated. |
| R-12 | PASS | Deterministic nutrient conflict precedence maintained upstream. |
| R-13 | PASS | Upstream selection by best score preserved; confidence excluded from user payload. |
| R-14 | PASS | Infeasible solver outcomes with named binding constraints pass through without structural relaxations. |
| R-15 | PASS | Quality-gated data reproducibility maintained upstream. |
| R-16 | PASS | User-facing response excludes audit-only provenance (`confidence`, `normalization_version`, `source_*`, `*_id`, `food_key`, `fdc_id`) verified by `remy/app/tests/api/test_response_schema.py::test_user_payload_excludes_audit_provenance` (PASS) and `remy/app/tests/api/test_chat_endpoint.py::test_stream_excludes_forbidden_fields` (PASS). Trace-side retention verified by `test_trace_retains_audit_provenance` (PASS). Check path conforms to A-007. |
| R-17 | PASS | Three-level explanations and distinct drop causes verified by `remy/app/tests/api/test_explanation_shape.py` at A-007 path, and end-to-end in SSE stream via `remy/app/tests/api/test_chat_endpoint.py::test_three_levels_present_in_stream`. |

## Plan adherence

The implementation fully adheres to the approved plan across all task groups:
- Tasks T-1 through T-20 are complete and verified by automated tests.
- Group 0 (T-1): Verified prerequisites, constitution v1.7, and A-007 check paths.
- Group 1 (T-2, T-3): Implemented additive `ConstraintSet.cost_query` and Extract Constraints keyword regex + LLM extraction; verified with green unit tests.
- Group 2 (T-4, T-5): Implemented A-006 recipe-level cost drop in `PlanService.generate` gated by `drop_uncosted`; verified by `test_service_cost_drop.py` and `test_cost_drop_eligibility.py` (R-8/R-10 recipe-level).
- Group 3 (T-6..T-8): Implemented `PlanInput.cost_query` threading through `PlanServiceAdapter` to `drop_uncosted`.
- Group 4 (T-9, T-10): Implemented pure SSE serializer (`app/sse.py`) and FastAPI composition root (`app/main.py`) mounting `POST /chat` under `/api/v1` without inward dependency violations.
- Group 5 (T-11..T-16): Implemented on-demand cost projection folded into `/chat` stream; wired end-to-end cost drop test `test_cost_intent_turn_drops_uncosted_recipe_end_to_end`; implemented three-level explanation streaming (`PlanUpdatedEvent` with `MealScopedExplanation`, plan status in done event); and restored deterministic output checks in `generate_response`.
- Group 6 (T-17, T-18): Updated `API_doc.md` §3 to include delta and scoped explanations; verified by `test_api_doc_plan_updated.py`.
- Group 7 & 8 (T-19, T-20): `sdd.json` updated; CI suite passes with 0 failures and 0 skips.

Deviations: none. All previous interim findings (F-1 through F-6) have been resolved.

## Findings

None blocking.

## Nits (non-blocking)

- N-1: `PlanUpdatedEvent.explanation` sanitizes `selected_offer` to `None` in `chat_router.py:336-340`. This is an intentional defensive mitigation against known upstream graph data mapping issues (unverified candidate mappings such as water -> sugar) to prevent product mismatches from surfacing to users until p2-002 data preparation follow-up tasks land.
- N-2: SSE comment heartbeat `": ping\n\n"` in `chat_router.py:277` is valid transport syntax to keep slow LLM responses alive; `test_only_five_event_types_emitted` confirms no non-contract event names are emitted.
- N-3: Minor deprecation warnings from Starlette (`anyio.abc.BlockingPortal`) and LangGraph (`allowed_objects` parameter in JsonPlusSerializer) are present in test run logs.
