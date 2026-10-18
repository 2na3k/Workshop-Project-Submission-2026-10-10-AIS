# Prompt — Plan

Plan for feature **p3-004-conversational-constraint-interface**

`<id>`: `p3-004-conversational-constraint-interface`

## Notes

**p3-004 is implementation.** Implement `POST /chat` in `remy/app` against p3-002's contract, fold on-demand cost into `/chat`, and land the A-006 recipe-level cost drop in `api`'s plan service. It does not redefine p3-002's schemas, p3-001's nodes, or p2's reasoning.

**Phase p2 closed with data-quality findings (DQ-1..DQ-7) tracked, not blocking.** p3-004 builds against whatever the plan produces; coverage compensation is out of scope.

## Input

- MUST read: [AGENTS.md](../../../AGENTS.md)
- [constitution.md](../../../docs/sdd/constitution.md) — v1.7. Note R-16's
  and R-17's named check paths and their full contracts (both clauses of
  R-16's check; R-17's two-response shape).
- Amendments: [amendments](../../../docs/amendments)
  - [A-006-r8-r10-cost-drop-deferral.md](../../../docs/amendments/A-006-r8-r10-cost-drop-deferral.md): recipe-level cost drop in api plan service consuming MISSING_PACKAGE_DATA; fixtures at SystemCode/remy/api/tests/features/plan/; asserts R-8/R-10 recipe-level.
  - [A-007-fixture-path.md](../../../docs/amendments/A-007-fixture-path.md): R-16/R-17 fixture paths at SystemCode/remy/app/tests/api/<name>.
  - Confirmed clarifications (log in ## Clarifications, do not re-litigate): A-006 layer = api plan
    service; stateless per turn; reuse p3-001 Generate Response; DQ-1..DQ-7 accepted; D-a (cost folded into /chat using existing ChatResponseEnvelope shape); D-b (intent detection extends p3-001 extraction node output with optional cost_query field).
- [system_design_v3.md](../../../SystemCode/docs/system_design_v3.md)
- [neo4j_db_design.md](../../../SystemCode/docs/neo4j_db_design.md)
- [workflow_diagram.md](../../../SystemCode/remy/workflows/docs/workflow_diagram.md) — the five-stage flow p3-001 implements; p3-002 defines the response contract that surfaces its Outcome to the user.
- [spec.md](../../../docs/sdd/features/p3-004-conversational-constraint-interface/spec.md)
- [sdd.json](../../../sdd.json) — read the current check set; confirm it covers 
  `remy/app/tests/api/` (the R-16/R-17 fixture directory, A-007 paths) and       
  `remy/api/tests/features/plan/` (the R-8/R-10 recipe-level fixtures). Update the check set in 
  the same change if not.
- Findings: [data-prep-price-path.md](../../../docs/findings/data-prep-price-path.md)
- Decisions:
    - [decisions.md](../../../docs/sdd/features/p2-001-constraint-evidence-filtering/decisions.md)
    - [decisions.md](../../../docs/sdd/features/p2-002-cost-nutrition-calculation/decisions.md)
    - [decisions.md](../../../docs/sdd/features/p2-003-feasible-meal-plan-solving/decisions.md)
    - [decisions.md](../../../docs/sdd/features/p3-001-workflow-recommendation-service/decisions.md)
    - [decisions.md](../../../docs/sdd/features/p3-002-explainable-response-contract/decisions.md)
- current codebase:
    - Meal plan API: [plan](../../../SystemCode/remy/api/src/api/features/plan)
    - Calculator API: [calculator](../../../SystemCode/remy/api/src/api/features/calculator)
    - App: [app](../../../SystemCode/remy/app)
    - Workflows: [workflows](../../../SystemCode/remy/workflows)
      - [models.py](../../../SystemCode/remy/workflows/src/workflows/models.py) —
                  `TraceEnvelope`, `Outcome`, `PlanTraceView`, `ConstraintSet`.
      - [trace.py](../../../SystemCode/remy/workflows/src/workflows/trace.py) —
                  the envelope's assembly.
      - Extract Constraints node (the `cost_query` field's home; see C-6).
- [API_doc.md](../../../SystemCode/remy/api/docs/API_doc.md) — §3 (`POST /api/v1/chat`) declares
  the current chat surface's request shape and SSE event vocabulary.
    - The SSE stream carries only p3-002's event set. User payloads must exclude CHAT_FORBIDDEN_FIELDS; the trace_id references, never embeds, the trace (p3-002 C-1, C-3).
- on a loop-back: the archived review.rN.md or plan-review.rN.md (highest N)
  with findings routed to `plan`

## Output

- MUST follow template: [plan.md](../../../.sdd/templates/plan.md)
- docs/sdd/features/<id>/plan.md
- do NOT write `## Tasks` until plan review approves
- sdd.json — the CI check set must include the plan feature's source and test paths. The check
  set must cover, at minimum:
    - `remy/api/src/api/features/plan` (A-006 cost drop)
    - `remy/api/tests/features/plan/` (R-8/R-10 recipe-level fixtures)
    - `remy/app/src/app/` (`/chat` endpoint, SSE, contract wiring, cost projection)
    - `remy/app/tests/api/` (R-16/R-17 named fixtures, A-007 paths)
    - `remy/workflows/src/workflows/` (`cost_query` addition)
    - `remy/api/docs/API_doc.md` (AC-21 doc change)
      Update the check set in the same change if any of the above is absent.

## Procedure

1. `sdd.py gate plan <id>` must pass.
2. Read the code the feature changes before writing Files-to-touch, Design, or
   the fixture assignments. Write against what is actually there, not what the
   spec assumes.
3. Fill Approach (chosen + rejected alternative), Design, Files to touch.

    The Design must also name, explicitly:
    - the **R-8/R-10 recipe-level fixture modules** under
             `SystemCode/remy/api/tests/features/plan/`;
    - the **cost-intent predicate** (what counts as cost intent; fallback when
             ambiguous) so AC-4/AC-5 are demonstrably testable;
    - confirmation that the `cost_query` addition to p3-001's extraction output
             is **additive and backward-compatible** with p3-001's existing tests (or,
             if not, a clarification routed per the do-not list);
    - the R-16 fixture asserts the **full `CHAT_FORBIDDEN_FIELDS`** set, not
             only `confidence`/`normalization_version`/`source_*`.
4. Constitution alignment: one line per relevant rule.
5. Test strategy: one row per AC. No AC untested.
6. Integration per interface: one row in `## Integration per interface` per
   interface the plan names (producer → consumer). Test runs the real code
   under test (dependencies may be mocked, the code under test may not), reads
   from the producer, asserts on the consumer. If it can't run in this
   environment, record the deferral in `## Revision notes` and `decisions.md`;
   don't omit the row. If there are genuinely no producer→consumer interfaces (single-file change),
   write 'None — single-component change.' Otherwise every producer→consumer edge gets a row.

    For p3-004, name at least these producer→consumer edges:
    - **p3-001 `TraceEnvelope` → `/chat` handler** (workflow run → event stream)
      - **`/chat` handler → SSE serializer** (event objects → wire frames)
      - **api plan service `MISSING_PACKAGE_DATA` → plan candidate pool** (the
               A-006 cost drop consuming the calculator's item-level signal)
      - **calculator service → `/chat` on-demand cost projection**
      - **p3-002 contract types → R-16/R-17 fixtures**
      - **`cost_query` field (workflows) → `/chat` intent branch**
    
    Additional edges the plan discovers are welcome; these six are required.
7. Risks & mitigations.
8. Scope check: one working context? If no , split.
9. Stop. Submit to plan review.
10. After APPROVE or APPROVE-WITH-NITS: append `## Tasks` (tests before the
    impl tasks they cover). Every AC has ≥1 test row (step 5) and ≥1 task; every interface row has
    ≥1 integration test row (step 6) and ≥1 task; every entry in `## Files to touch` has ≥1 task.
    The `sdd.json` check set must cover the feature's source and test paths (see the `sdd.json`
    section below).

## Do not

- Write `## Tasks` before approval.
- Edit spec.md, constitution.md, or any review artifact.
- Leave an AC uncovered by a task or test.
- Omit an interface row, or leave one without an integration test.
- Mock the code under test (dependencies yes, code under test no).
- Re-implement the consumer in a test.
