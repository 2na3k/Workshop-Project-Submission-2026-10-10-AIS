# Review - Workflow recommendation service

Verdict: APPROVE

## CI evidence

OVERALL: PASS (`ci-results.md`, run 2026-10-16T12:39:53+08:00).

Review gate: PASS (`python3 .sdd/scripts/sdd.py gate review p3-001-workflow-recommendation-service` executed in WSL environment).

The recorded CI run verifies:
- `test`: 67 passed, 2 xfailed, 2 warnings in 24.32s (`uv run --package remy-api pytest -q remy/api/tests/features/plan && uv run --package remy-workflows pytest -q remy/workflows/tests && uv run --package remy-app pytest -q remy/app/tests`)
- `lint`: PASS (`uv run --package remy-workflows ruff check remy/workflows/src remy/workflows/tests --select F,E9 && uv run --package remy-app ruff check remy/app/src remy/app/tests --select F,E9`)
- `typecheck`: PASS (`uv run --package remy-workflows mypy remy/workflows/src --ignore-missing-imports && uv run --package remy-app mypy remy/app/src --ignore-missing-imports` - 11 source files across workflows and app)
- `lint-imports`: PASS (`uv run lint-imports` - Analyzed 61 files, 107 dependencies; 4 contracts kept, 0 broken)

Independently verified by reviewer in WSL:
- Workflows test suite: `uv run --package remy-workflows pytest -v remy/workflows/tests` -> 25 passed, 2 xfailed in 9.73s.
- App test suite: `uv run --package remy-app pytest -v remy/app/tests` -> 4 passed in 8.51s.
- Architecture contracts: `uv run lint-imports` -> 4 kept, 0 broken.

## Acceptance criteria

| AC | PASS/FAIL | test name or file:line |
|---|---|---|
| AC-1 | PASS | `remy/workflows/tests/test_graph_order.py::test_three_nodes_run_in_order_and_return_one_outcome_and_trace` (L27), `test_extract_failure_skips_plan_and_generate` (L39) |
| AC-2 | PASS | `remy/workflows/tests/test_extract.py::test_natural_language_extracts_constraints_and_records_llm` (L10) |
| AC-3 | PASS | `remy/workflows/tests/test_extract.py::test_structured_constraints_are_passed_through_without_calling_llm` (L21) |
| AC-4 | PASS | `remy/app/tests/test_import_boundary.py::test_workflow_source_does_not_import_api` (L4) and CI command `uv run lint-imports` (4 kept, 0 broken) |
| AC-5 | PASS | `remy/workflows/tests/test_plan_node.py::test_feasible_result_preserves_slots_and_three_level_reasoning` (L31) |
| AC-6 | PASS | `remy/workflows/tests/test_plan_node.py::test_infeasible_result_preserves_binding_constraints_and_dropped_candidates` (L45) |
| AC-7 | PASS | `remy/workflows/tests/test_plan_node.py::test_relaxed_label_and_tolerance_are_unchanged` (L56) |
| AC-8 | PASS | `remy/workflows/tests/test_generate.py::test_structured_generation_preserves_evidence_absent_and_returns_text` (L27) |
| AC-9 | PASS | `remy/workflows/tests/test_response_schema_workflow.py::test_user_payload_excludes_provenance` (L45) and `remy/workflows/tests/test_generate.py::test_generation_prompt_and_payload_exclude_audit_provenance` (L50) |
| AC-10 | PASS | `remy/workflows/tests/test_trace_envelope.py::test_trace_envelope_reaches_plan_reasoning_and_records_llm_calls` (L1) |
| AC-11 | PASS | `remy/workflows/tests/test_generate.py::test_structured_references_must_be_subsets_of_plan` (L34) and `test_selected_evidence_absent_output_fails_deterministic_check` (L41) |
| AC-12 | PASS | `remy/workflows/tests/test_generate.py::test_llm_failure_is_explicit` (L58) |
| AC-13 | PASS | `remy/workflows/tests/test_plan_node.py::test_port_failure_is_a_plan_failure_without_feasibility_claim` (L63) |
| AC-14 | PASS | `remy/workflows/tests/test_extract.py::test_invalid_constraint_sets_fail_before_plan_is_called` (L30) |
| AC-15 | PASS | `remy/workflows/tests/test_plan_node.py::test_empty_pool_and_no_assignment_remain_distinct` (L74) |
| AC-16 | PASS | `remy/app/tests/test_plan_adapter.py::test_adapter_maps_real_tuple_losslessly` (L26) and `remy/app/tests/test_integration_adapter_plan.py::test_real_plan_service_tuple_maps_through_adapter_with_mocked_neo4j` (L15) |
| AC-17 | PASS | `remy/workflows/tests/test_extract.py::test_unapplied_constraints_are_retained_in_outcome_and_trace` (L46) |
| AC-18 | PASS | `remy/workflows/tests/test_extract.py::test_ambiguous_severity_is_not_invented_and_tolerance_defaults_to_zero` (L65) |
| AC-19 | PASS | `remy/workflows/tests/test_plan_node.py::test_mild_allergen_warning_is_preserved` (L82) |
| AC-20 | PASS | `remy/workflows/tests/test_plan_node.py::test_horizon_only_request_is_sent_unchanged` (L90) |
| AC-21 | PASS | `remy/workflows/tests/test_response_schema_workflow.py::test_user_payload_excludes_provenance` (L45), `remy/workflows/tests/test_explanation_shape_workflow.py::test_outcome_has_three_levels_and_distinct_drop_causes` (L29), and `remy/workflows/tests/test_response_schema_workflow.py::test_trace_side_provenance_is_deferred_to_f_p3_1` (L66, XFAIL) |
| Interface (Extract -> Plan) | PASS | `remy/workflows/tests/test_integration_extract_to_plan.py::test_extracted_constraints_reach_plan_port` (L5) |
| Interface (Plan -> PlanService) | PASS | `remy/app/tests/test_integration_adapter_plan.py::test_real_plan_service_tuple_maps_through_adapter_with_mocked_neo4j` (L15) |
| Interface (Generate -> Outcome) | PASS | `remy/workflows/tests/test_integration_generate_to_outcome.py::test_generate_structured_output_drives_final_outcome` (L5) |
| Interface (Workflow -> Caller) | PASS | `remy/workflows/tests/test_integration_workflow_envelope.py::test_workflow_caller_receives_outcome_and_trace` (L1) |

## Constitution compliance

Violations: none.

| Rule | Result | Evidence |
|---|---|---|
| R-1 | PASS | Single schema used across workflow types; workflow models align directly with canonical graph and solver schema concepts. No duplicate naming conventions introduced. |
| R-2 | PASS | Inward dependency direction maintained: `remy/workflows` does not import `api` or `app`. Workflow interacts with planning via workflow-owned port `PlanPort`. The composition root adapter in `remy/app` (`PlanServiceAdapter`) mediates calls to `PlanService.generate`. CI check `uv run lint-imports` reports 4 kept contracts, 0 broken ("domain is a leaf", "workflows does not depend on api", "api does not depend on app", "api does not depend on workflows"). Verified by `test_import_boundary.py::test_workflow_source_does_not_import_api`. |
| R-3 | PASS | Python backend shape preserved; LangGraph and LangChain libraries added within existing web service architecture without introducing parallel frameworks, relational serving layers, or non-Python runtimes (confirmed same-shape per spec C-5). |
| R-4 | PASS | Provenance property preservation on graph edges is an upstream data-layer concern and unaffected by the workflow orchestration layer. |
| R-5 | PASS | Absent-evidence drops from upstream plan solver are carried through unchanged. Generate Response node includes a deterministic validation check (`test_selected_evidence_absent_output_fails_deterministic_check`) ensuring evidence-absent drops are never restated as permissive or passing in generated recommendations. |
| R-6 | PASS | Severe vs mild allergen distinction preserved. Mild-allergen ingredient warnings pass through intact to the outcome and generated text (`test_mild_allergen_warning_is_preserved`). Extraction never downgrades severity without explicit user instruction (`test_ambiguous_severity_is_not_invented_and_tolerance_defaults_to_zero`). |
| R-7 | PASS | Dietary compliance evaluation remains upstream in p2 solver; workflow extraction explicitly forwards stated dietary constraints (`test_natural_language_extracts_constraints_and_records_llm`). |
| R-8 | PASS | Freshness filtering is enforced upstream in calculator/plan candidate selection; cost evaluation is deferred per A-006 to conversational interface (p3-004). |
| R-9 | PASS | Nutrient profile requirement drops are evaluated upstream in p2 solver and preserved faithfully in workflow plan outcome and trace. |
| R-10 | PASS | Cost basis eligibility is evaluated upstream in calculator; recipe-level cost drops are out of scope for p3-001 per A-006. |
| R-11 | PASS | Consumed cost vs retail price distinction is maintained in upstream calculator and not conflated by workflow. |
| R-12 | PASS | Nutrient conflict precedence is maintained deterministically upstream. |
| R-13 | PASS | Upstream best-score ranking is preserved. Confidence recording in trace is subject to upstream `PlanTrace` availability (Finding F-P3-1). |
| R-14 | PASS | Feasibility floor naming binding constraints is preserved: infeasible solver results pass through with binding constraints intact (`test_infeasible_result_preserves_binding_constraints_and_dropped_candidates`), relaxed plan labels and applied tolerance pass through unchanged (`test_relaxed_label_and_tolerance_are_unchanged`), and the workflow never applies structural relaxations or widens tolerances. |
| R-15 | PASS | Quality-gated data reproducibility is an upstream data-prep concern; tests use fixture-backed drivers. |
| R-16 | PASS | User-displayable outcome excludes audit-only provenance (`confidence`, `normalization_version`, `source_*`, `*_id`, `food_key`) verified by `test_user_payload_excludes_provenance`. LLM generation prompt excludes provenance fields (`test_generation_prompt_and_payload_exclude_audit_provenance`). Trace-side retention is deferred under Finding F-P3-1 and tested via xfail (`test_trace_side_provenance_is_deferred_to_f_p3_1`). |
| R-17 | PASS | Three-level explanations (plan, recipe, constraint) and distinct drop causes (`evidence-absent`, `present-evidence-excludes`, `unmapped`) are exposed in outcomes and trace (`test_outcome_has_three_levels_and_distinct_drop_causes`). |

## Plan adherence

The implementation adheres to the approved plan:
- Tasks T-1 through T-17 were executed and marked complete in `plan.md`.
- Group 0 (T-1, T-2): Prerequisites P-1 (p2-003 C-7 return-shape reopen) and P-2 (`langchain` and `langchain-ollama` added to `remy/workflows/pyproject.toml`) verified; package skeleton created with workflow-owned models, state, port, and trace envelope without importing `api`.
- Group 1 (T-3, T-4): Extract Constraints node implemented with LangChain client wrapper; tests assert natural language parsing, structured pass-through, early failure on invalid constraints, unapplied constraint reporting, and conservative severity/tolerance defaults.
- Group 2 (T-5, T-6): Plan node implemented delegating to `PlanPort`; preserves feasible plans, infeasible results with binding constraints, relaxed plans, empty pool vs no assignment discrimination, and mild allergen warnings.
- Group 3 (T-7, T-8): Generate Response node implemented with structured output validation (subset check, drop-cause mapping, evidence-absent non-permissive check); R-16 provenance excluded from prompt and output; explicit failure on LLM unavailability.
- Group 4 (T-9, T-10, T-11): `StateGraph` assembled with early exit edges; versioned `TraceEnvelope` assembled at all exit paths; workflow integration edge tests pass.
- Group 5 (T-12, T-13): `PlanServiceAdapter` implemented in `remy/app`, mapping real `(PlanResponse, PlanTrace)` tuple to workflow models losslessly; import boundary tests verify `remy/workflows` does not import `api`.
- Group 6 (T-14, T-15): `sdd.json` updated with test, lint, typecheck, and lint-imports checks; workflow-side R-16/R-17 conformance tests added.
- Group 7 (T-16, T-17): Decisions recorded in `decisions.md`; full CI suite passing.

Deviations: none.

## Findings

None blocking.

## Nits (non-blocking)

- N-1: Upstream finding F-P3-1 remains tracked and owned by p2-003: `PlanTrace` does not carry R-16 audit provenance (`confidence`, `normalization_version`, `source_*`, `*_id`). The trace-side R-16 tests in workflows are marked `xfail` and documented in `decisions.md` (D-1, D-5).
- N-2: Documentation synchronization note: In `spec.md` under `## Clarifications` (C-1), the wording states that the workflow-owned port returns `(PlanResponse, PlanTrace)`. Per plan BD-1, D-2, and D-6, the port returns workflow-owned models `(PlanResult, PlanTraceView)` while the adapter calls `PlanService.generate` and unpacks the tuple. This wording should be updated at the next spec touch.
- N-3: Phase-review routing per BD-2: The constitution names `tests/api/test_response_schema.py` (which exists at `tests/features/calculator/test_response_schema.py`, precedent F-D) and `tests/api/test_explanation_shape.py` (which does not exist; to be owned by p3-002). Workflow-side mirrors were implemented and tested in `test_response_schema_workflow.py` and `test_explanation_shape_workflow.py`.
