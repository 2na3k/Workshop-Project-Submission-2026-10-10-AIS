# Prompt — Plan

Plan for feature **p2-002-cost-nutrition-calculation**

`<id>`: `p2-002-cost-nutrition-calculation`

## Notes
**IMPORTANT**: Since this is a brownfield feature, the plan must read the code before writing the design and files-to-touch. The plan's design and files-to-touch must reflect what is actually there, not what the spec assumes.

## Input
- MUST read: [AGENTS.md](../../../AGENTS.md)
- [constitution.md](../../../docs/sdd/constitution.md)
  - The spec's `## Clarifications` (C-1..C-9) are resolved. The plan consumes them as fixed. If the code contradicts a clarification, the plan records the contradiction in the baseline inventory and designs a fix; it does not re-open the clarification.
  - This plan is written against constitution version 1.4 (amendments A-001..A-004 applied on 2026-10-07). If you encounter an archived plan or an older constitution copy that cites R-8's freshness threshold, R-9's per-recipe drop, R-10's `cost_basis_compatible`, or R-4's freshness timestamp, treat those as superseded.
- Amendments: [amendments](../../../docs/amendments) (R-4, R-8, R-9, R-10; constitution v1.4)
- [spec.md](../../../docs/sdd/features/p2-002-cost-nutrition-calculation/spec.md)
- [neo4j_db_design.md](../../../SystemCode/docs/neo4j_db_design.md)
- [system_design_v3.md](../../../SystemCode/docs/system_design_v3.md)
- Findings: [data-prep-price-path.md](../../../docs/findings/data-prep-price-path.md)
- current codebase: [SystemCode](../../../SystemCode)
    - Backend:  [api](../../../SystemCode/remy/api)
      - [fastapi_project_structure.md](../../../SystemCode/remy/api/docs/fastapi_project_structure.md)
      - calculate feature: [calculator](../../../SystemCode/remy/api/src/api/features/calculator)
    - Domain: [domain](../../../SystemCode/remy/domain)
    - Workflow (LangGraph,...): [workflows](../../../SystemCode/remy/workflows)
- Reference: [API_doc.md](../../../SystemCode/remy/api/docs/API_doc.md) (current deployed shape; spec supersedes).
  Use this only to (a) identify the current response/request field names so the plan's baseline inventory can name what exists, and (b) confirm the file path for the in-place R-1 update. Do not treat any of the following as spec-level requirements — the amended spec is authoritative:
  - Endpoints 2–6 (/plan, /chat, /verify-dietary, /recipes/{id}, /recommendations/cold-start) are 
      NOT in p2-002 scope; the plan MUST not touch them.
  - fdc_id is present in the item response in the doc; AC-18 removes it.
  - matched_package carries package_title/package_price_sgd/package_amount_g/package_count; AC-18 keeps only listing_name + retailer in the user payload, the rest moves to the trace.
  - warnings are {code, message}; AC-2/C-2 require PARTIAL_NUTRITION_DATA to name the missing canonical nutrients.
- on a loop-back: the archived review.rN.md or plan-review.rN.md (highest N)
  with findings routed to `plan`

## Output
- MUST follow template: [plan.md](../../../.sdd/templates/plan.md)
- docs/sdd/features/<id>/plan.md
- do NOT write `## Tasks` until plan review approves

## Procedure
1. `sdd.py gate plan <id>` must pass.
2. Read the code the feature changes before writing Files-to-touch, Design, or
   the fixture assignments. Write against what is actually there, not what the
   spec assumes.
   - Baseline inventory — record these in the plan's Design §0:
     - The repository's actual return type for fetch_food_facts, and whether the call raises or 
      returns.
     - The service's actual consumption of the repository's output.
     - `select_package`'s actual ranking key and eligibility conditions (currently: unit price → 
       retail cost → confidence → lexicographic; no freshness check).
     - `domain/units.to_grams`'s actual signature and warning codes (currently: UNIT_ASSUMED_GRAMS, 
       deprecated grams_per_tbsp/grams_per_piece).
     - `schemas.py`'s current request/response shapes for the calculate endpoint (from the code, not the API doc).
     - The error envelope used when a request is rejected (FastAPI default or custom).
     - The state of the T-2 `__post_init__` interval check on RetailSKU (present or removed).
     - The state of `FoodFacts.observed_at` (present or removed).
     - The pre-existing test failures (currently: 2 stale `test_domain_conversion`, 1 `test_resolver::test_normalization_and_alias`).
     - A per-AC status table: present | absent | needs-fix.
   - The baseline must be evidence-based: "run on <date>, read at <path>." Past plans that wrote the baseline from the spec's assumptions were rejected.
   - If the baseline reveals a behavior the spec is silent on but the plan must decide (for example the error envelope format, or the `MAX_REQUEST_INGREDIENTS` value), the plan names a default, records it in `## Revision` notes as a plan-stage decision, and flags it for the reviewer to route if needed. If the gap is a spec-level contract (user-visible shape, a new rule), the plan routes a finding to ``spec`` and stops.
   - p2-001's freshness predicate: does it check freshness_status == "fresh" or a timestamp? Read [filtering.py](../../../SystemCode/remy/api/src/api/features/plan/filtering.py) and record the answer. If timestamp-based, record as a p2-001 finding to route; the calculator's independent check still satisfies R-8.
   - p2-001's cost-eligibility predicate: does it use cost_basis_compatible or price_status/price_match_status/price_basis? If the former, record as a p2-001 finding to route.
3. Fill Approach (chosen + rejected alternative), Design, Files to touch.
   - Trace: if the spec names an internal trace, the plan's Design names the module and dataclass; the ## Execution trace section's contents become the dataclass's fields. The router discards the trace for now; the plan does not add an exposure boundary.
4. Constitution alignment: one line per relevant rule.
5. Test strategy: one row per AC. No AC untested.
   - Error envelope: if a request is rejected, the plan records the envelope format the code uses (FastAPI default {"detail": [...]} or a custom {"error": {code, message, details, timestamp}}). If the code uses a custom envelope, the plan's test strategy must assert it on at least one rejection AC.
6. Integration per interface: one row in `## Integration per interface` per
   interface the plan names (producer → consumer). Test runs the real code
   under test (dependencies may be mocked, the code under test may not), reads
   from the producer, asserts on the consumer. If it can't run in this
   environment, record the deferral in `## Revision notes` and `decisions.md`;
   don't omit the row. If there are genuinely no producer→consumer interfaces (single-file change), write 'None — single-component change.' Otherwise every producer→consumer edge gets a row.
7. Risks & mitigations.
8. Scope check: one working context? If no , split.
9. Stop. Submit to plan review.
10. After APPROVE or APPROVE-WITH-NITS: append `## Tasks` (tests before the
    impl tasks they cover). Every AC has ≥1 test row (step 5) and ≥1 task; every interface row has ≥1 integration test row (step 6) and ≥1 task.

## Do not
- Write `## Tasks` before approval.
- Edit spec.md, constitution.md, or any review artifact.
- Leave an AC uncovered by a task or test.
- Omit an interface row, or leave one without an integration test.
- Mock the code under test (dependencies yes, code under test no).
- Re-implement the consumer in a test.
