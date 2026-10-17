# Review - Explainable response contract

Verdict: APPROVE

## CI evidence

OVERALL: PASS (`ci-results.md`, run 2026-10-17T12:21:26+08:00).

Review gate: PASS (`python3 .sdd/scripts/sdd.py gate review p3-002-explainable-response-contract` executed in WSL environment).

The recorded CI run verifies:
- `test`: 81 passed, 3 xfailed, 3 warnings in 31.06s across:
  - `remy-api`: `uv run --package remy-api pytest -q remy/api/tests/features/plan` (38 passed, 1 warning in 10.20s)
  - `remy-workflows`: `uv run --package remy-workflows pytest -q remy/workflows/tests` (25 passed, 2 xfailed, 1 warning in 8.08s)
  - `remy-app`: `uv run --package remy-app pytest -q remy/app/tests` (18 passed, 1 xfailed, 1 warning in 12.78s)
- `lint`: PASS (`uv run --package remy-workflows ruff check remy/workflows/src remy/workflows/tests --select F,E9 && uv run --package remy-app ruff check remy/app/src remy/app/tests --select F,E9`)
- `typecheck`: PASS (`uv run --package remy-workflows mypy remy/workflows/src --ignore-missing-imports && uv run --package remy-app mypy remy/app/src --ignore-missing-imports` - 12 source files across workflows and app)
- `lint-imports`: PASS (`uv run lint-imports` - Analyzed 62 files, 108 dependencies; 4 contracts kept, 0 broken)

Independently verified by reviewer in WSL:
- App test suite: `uv run --package remy-app pytest -v remy/app/tests` -> 18 passed, 1 xfailed, 1 warning in 14.11s.
- Architecture contracts: `uv run lint-imports` -> 4 kept, 0 broken.

## Acceptance criteria

| AC | PASS/FAIL | test name or file:line |
|---|---|---|
| AC-1 | PASS | `remy/app/tests/test_chat_contract.py::test_chat_request_requires_session_and_message` (L5) |
| AC-2 | PASS | `remy/app/tests/test_chat_contract.py::test_sse_event_type_is_one_of_five` (L19) |
| AC-2b | PASS | `remy/app/tests/test_chat_contract.py::test_plan_updated_carries_delta_and_scoped_explanation` (L43) |
| AC-3 | PASS | `remy/app/tests/api/test_explanation_shape.py::test_all_three_levels_present` (L34), `remy/app/tests/test_chat_contract.py::test_maps_real_trace_envelope_to_explanation` (L97), `test_compiled_workflow_outcome_maps_through_contract` (L237) |
| AC-4 | PASS | `remy/app/tests/api/test_explanation_shape.py::test_drop_causes_are_distinct` (L44), `remy/app/tests/test_chat_contract.py::test_drop_cause_enum_is_closed` (L73) |
| AC-5 | PASS | `remy/app/tests/api/test_explanation_shape.py::test_drop_causes_are_distinct` (L44) |
| AC-6 | PASS | `remy/app/tests/api/test_explanation_shape.py::test_multi_cause_precedence_preserved` (L56), `remy/app/tests/test_chat_contract.py::test_maps_real_trace_envelope_to_explanation` (L146) |
| AC-7 | PASS | `remy/app/tests/api/test_response_schema.py::test_user_payload_excludes_audit_provenance` (L42), `remy/app/tests/test_chat_contract.py::test_events_serialize_to_wire_payloads` (L163) |
| AC-7b | PASS | `remy/app/tests/test_chat_contract.py::test_r16_floor_is_the_named_field_list` (L84) |
| AC-8 | PASS | `remy/app/tests/api/test_response_schema.py::test_trace_retains_audit_provenance` (L48, XFAIL under F-P3-1) |
| AC-9 | PASS | `remy/app/tests/test_chat_contract.py::test_constraint_explanation_fields` (L59), `test_maps_real_trace_envelope_to_explanation` (L137) |
| AC-10 | PASS | `remy/app/tests/test_chat_contract.py::test_events_serialize_to_wire_payloads` (L163), `test_maps_real_trace_envelope_to_explanation` (L139) |
| AC-11a | PASS | `SystemCode/remy/app/tests/api/test_response_schema.py` and `SystemCode/remy/app/tests/api/test_explanation_shape.py` exist and pass |
| AC-11b | PASS | `remy/app/tests/api/test_response_schema.py::test_user_payload_excludes_audit_provenance` (PASS) and `test_trace_retains_audit_provenance` (XFAIL) |
| AC-12 | PASS | `remy/app/tests/test_chat_contract.py::test_failure_outcome_maps_to_error_event` (L209) |
| AC-13 | PASS | `remy/app/tests/test_chat_contract.py::test_maps_real_trace_envelope_to_explanation` (L146) |
| AC-14 | PASS | `remy/app/tests/test_chat_contract.py::test_maps_real_trace_envelope_to_explanation` (L157) |

## Constitution compliance

Violations: none

| Rule | Result | Evidence |
|---|---|---|
| R-1 | PASS | Single schema maintained across chat contract models and canonical representations. Field names align with domain and workflow concepts; no duplicate concepts or parallel schemas introduced. |
| R-2 | PASS | Inward dependency direction maintained: `remy/app/src/app/chat_contract.py` lives in the composition root `remy-app`, importing from `workflows.models`. No outward dependency violations. Architecture contract check `uv run lint-imports` reports 4 kept, 0 broken. |
| R-3 | PASS | Standard Python backend models using Pydantic v2 within existing web service architecture. No new stack shape or parallel frameworks added. |
| R-4 | PASS | Graph edge provenance preservation is an upstream data/graph concern unaffected by response contracts. |
| R-5 | PASS | Absent evidence causes recipe drop; contract defines `DropCause.EVIDENCE_ABSENT` and preserves it distinct from exclusions. |
| R-6 | PASS | Severe allergen drops; mild allergen warnings preserved in `ConstraintExplanation.warnings`. |
| R-7 | PASS | No inferred dietary compliance: upstream dietary evaluation results pass through intact into constraint outcomes. |
| R-8 | PASS | Non-fresh price offer filtering is upstream; contract faithfully exposes selected public offer details when present. |
| R-9 | PASS | Missing nutrition profile drops are upstream; carried faithfully through explanation outcomes. |
| R-10 | PASS | Cost basis eligibility is upstream; recipe-level cost drops are out of scope per A-006. |
| R-11 | PASS | Consumed cost vs retail price distinction preserved upstream; prices are not excluded by R-16 floor. |
| R-12 | PASS | Deterministic nutrient conflict precedence maintained upstream. |
| R-13 | PASS | Selection by best score is upstream; mapping confidence is strictly excluded from user payload. |
| R-14 | PASS | Feasibility floor naming binding constraints preserved: `PlanExplanation` carries binding constraints, `relaxed`, and `applied_tolerance_pct` directly from trace without re-deciding or relaxing. |
| R-15 | PASS | Quality-gated data reproducibility is an upstream data-prep concern; tests use fixture-backed data. |
| R-16 | PASS | User response excludes audit-only provenance (`confidence`, `normalization_version`, `source_*`, `*_id`, `food_key`, `fdc_id`) verified by `remy/app/tests/api/test_response_schema.py::test_user_payload_excludes_audit_provenance` (PASS). Trace-side retention is tested via `test_trace_retains_audit_provenance` (XFAIL under F-P3-1). Check path conforms to `SystemCode/remy/app/tests/api/test_response_schema.py` per approved Amendment A-007. |
| R-17 | PASS | Three-level explanations (plan, recipe, constraint) and distinct drop causes (`evidence-absent`, `present-evidence-excludes`, `unmapped`) verified by `remy/app/tests/api/test_explanation_shape.py`. Check path conforms to `SystemCode/remy/app/tests/api/test_explanation_shape.py` per approved Amendment A-007. |

## Plan adherence

The implementation adheres strictly to the approved plan:
- Tasks T-1 through T-15 were executed and marked complete (`[x]`) in `plan.md`.
- Group 0 (T-1): Confirmed prerequisites and constitution v1.7 with Amendment A-007 check paths.
- Group 1 (T-2..T-5): Created `app/chat_contract.py` defining `ChatRequest`, 5 SSE event models (`MetadataEvent`, `TokenEvent`, `PlanUpdatedEvent`, `ErrorEvent`, `DoneEvent`), explanation models (`OfferView`, `ConstraintExplanation`, `RecipeExplanation`, `PlanExplanation`, `DropCause` closed enum), `MealDelta`, and `MealScopedExplanation`.
- Group 2 (T-6..T-8): Implemented `CHAT_FORBIDDEN_FIELDS` audit floor and pure mapper `from_trace_envelope` preserving p2 cause precedence and outcome mapping.
- Group 3 (T-9..T-13): Created constitution-named fixtures `remy/app/tests/api/test_response_schema.py` (R-16) and `remy/app/tests/api/test_explanation_shape.py` (R-17); verified wire payload serialization, error event mapping, and end-to-end compiled workflow integration.
- Group 4 (T-14): Verified test check coverage in `sdd.json`.
- Group 5 (T-15): Full test suite passing with 4 import contracts kept and 0 broken.

Deviations: none.

## Findings

None blocking.

## Nits (non-blocking)

- N-1: Upstream finding F-P3-1 remains tracked and owned by p2-003: `PlanTrace` (and embedded `PlanTraceView`) does not carry mapping confidence, normalization version, or source identifiers. The trace-side R-16 conformance test in `remy/app/tests/api/test_response_schema.py::test_trace_retains_audit_provenance` is appropriately marked `@pytest.mark.xfail(strict=True, reason="F-P3-1: ...")` and will turn into a hard failure if provenance lands unexpectedly without removing the marker.
- N-2: `API_doc.md` §3 displays a legacy `plan_updated` example without scoped explanations. As specified in Clarification C-2 and plan §1/§2, `plan_updated` carries both delta and meal-scoped explanation; doc update is assigned to p3-004 upon endpoint implementation.
