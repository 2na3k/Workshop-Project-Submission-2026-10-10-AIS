# Prompt — Plan

Plan for feature **p3-001-workflow-recommendation-service**

`<id>`: `p3-001-workflow-recommendation-service`

## Notes

**p3 is greenfield.** No workflow, response-contract, web, or chat implementation
exists in the codebase. This spec describes what p3-001 builds, not what it
fixes. The input list's codebase reference points at p2's interfaces (which
p3-001 consumes), not at a pre-existing p3 layer.

## Input

- MUST read: [AGENTS.md](../../../AGENTS.md)
- [constitution.md](../../../docs/sdd/constitution.md)
    - This spec is written against constitution v1.6 (amendments A-001..A-006 applied). If you encounter an archived copy that cites R-14's relaxation set as unclassified, R-8/R-10's recipe-level cost drop as p3-001's obligation, or a `nutrient_tolerance_pct` default other than 0, treat those as superseded.
- Amendments: [amendments](../../../docs/amendments), specifically A-005 (R-14 relaxation set) and
  A-006 (R-8/R-10 cost-drop deferral to p3-004).
- [system_design_v3.md](../../../SystemCode/docs/system_design_v3.md)
- [neo4j_db_design.md](../../../SystemCode/docs/neo4j_db_design.md)
- [workflow_diagram.md](../../../SystemCode/remy/workflows/docs/workflow_diagram.md) — the five-stage LangGraph flow that this feature implements.
- [spec.md](../../../docs/sdd/features/p3-001-workflow-recommendation-service/spec.md)
- [sdd.json](../../../sdd.json) — read the current check set; confirm it will cover the workflow's source and test paths (SystemCode/remy/workflows/src/workflows/, SystemCode/remy/workflows/tests/) and any adapter file added under app. Update the check set in the same change if not.
- Findings: [data-prep-price-path.md](../../../docs/findings/data-prep-price-path.md)
- Decisions:
    - [decisions.md](../../../docs/sdd/features/p2-001-constraint-evidence-filtering/decisions.md)
    - [decisions.md](../../../docs/sdd/features/p2-002-cost-nutrition-calculation/decisions.md)
    - [decisions.md](../../../docs/sdd/features/p2-003-feasible-meal-plan-solving/decisions.md)
- current codebase: [SystemCode](../../../SystemCode)
    - Meal plan API: [plan](../../../SystemCode/remy/api/src/api/features/plan)
    - Calculator API: [calculator](../../../SystemCode/remy/api/src/api/features/calculator)
    - Workflows (to be created): [workflows](../../../SystemCode/remy/workflows)
    - p3 is greenfield. No workflow, response-contract, web, or chat implementation exists in the codebase. The spec describes what p3-001 builds, not what it fixes. The input list's codebase reference is for p2's existing interfaces (which p3-001 consumes), not for a pre-existing p3 layer.
- Reference: [API_doc.md](../../../SystemCode/remy/api/docs/API_doc.md)
- on a loop-back: the archived review.rN.md or plan-review.rN.md (highest N)
  with findings routed to `plan`

## Output

- MUST follow template: [plan.md](../../../.sdd/templates/plan.md)
- docs/sdd/features/<id>/plan.md
- do NOT write `## Tasks` until plan review approves
- sdd.json — the CI check set must include the plan feature's source and test paths. If the feature
  adds or renames source/test files, update the check set in the same change.

## Procedure

1. `sdd.py gate plan <id>` must pass.
2. Read the code the feature changes before writing Files-to-touch, Design, or
   the fixture assignments. Write against what is actually there, not what the
   spec assumes.

    **Baseline inventory — record these in the plan's Design §0.** p3-001 is greenfield; the "code" to read is p2's, not p3's.
    - **`PlanService.generate`'s current signature and return shape.** Read `SystemCode/remy/api/src/api/features/plan/service.py`. Record what it returns (`PlanResponse` today; the p2-003 reopen per C-7 changes it to `(PlanResponse, PlanTrace)`). Confirm whether the reopen has landed.
    - **`PlanTrace`'s and `PlanResponse`'s field shapes.** Read `plan/models.py` and `plan/schemas.py`. Record `RecipeOutcome`, `RequirementOutcome`, `NamedConstraint`, `PlanTrace`'s fields, and `PlanResponse`'s fields. These are what the adapter maps.
    - **`PlanRequest`'s field shape.** Read `plan/schemas.py`. Record the request's fields (`horizon_days`, `meals_per_day`, `servings`, `nutrients`, `allergies`, `dietary`, `nutrient_tolerance_pct`). These are what Extract Constraints produces.
    - **The `plan` router and dependency wiring.** Read `plan/router.py` and `plan/dependencies.py`. Record how `PlanService` is constructed and injected.
    - **The `.importlinter` configuration.** Read `.importlinter`. Record the current `root_packages` and `forbidden` contracts. Confirm whether `app` is present (Q2 — expected: no).
    - **The `workflows` package state.** Read `SystemCode/remy/workflows/`. Confirm the greenfield posture — nothing exists except perhaps a doc (`workflow_diagram.md`). Record exactly what's there.
    - **The `app` package state.** Read `SystemCode/remy/api/src/api/app/` (or wherever the composition root is). Record what's there and where the adapter would live.
    - **`sdd.json`'s check set.** Record the current `test`, `lint`, `typecheck` commands. Confirm they cover the workflow paths (expected: no — the workflow doesn't exist yet).
    - **LangGraph/LangChain availability.** Confirm whether the packages are installed in the project's environment. If not, adding them is a plan-stage task.
    - **The LLM client's local-hosted option.** Confirm which library/config Ollama or equivalent is expected to be reached through (langchain-ollama, direct HTTP, etc.). Record the choice as a plan-stage default.
    - **Per-AC status table:** `present | absent | needs-fix`. For greenfield, most ACs are `absent`; the ones requiring only pass-through of p2's contract may be `present` if the adapter can be built trivially. Record honestly.
3. Fill Approach (chosen + rejected alternative), Design, Files to touch.
4. Constitution alignment: one line per relevant rule.
5. Test strategy: one row per AC. No AC untested.
6. Integration per interface: one row in `## Integration per interface` per
   interface the plan names (producer → consumer). Test runs the real code
   under test (dependencies may be mocked, the code under test may not), reads
   from the producer, asserts on the consumer. If it can't run in this
   environment, record the deferral in `## Revision notes` and `decisions.md`;
   don't omit the row. If there are genuinely no producer→consumer interfaces (single-file change),
   write 'None — single-component change.' Otherwise every producer→consumer edge gets a row.

    For p3-001, name at least these producer→consumer edges in the Integration table:
    - **Extract Constraints output → Plan node input:** the parsed constraint set.
    - **Plan node → p2-003 plan path (through the workflow-owned interface):** the `PlanRequest` in, `(PlanResponse, PlanTrace)` out.
    - **Generate Response node → workflow outcome:** the structured output (referenced IDs, drop causes) and the text.
    - **Workflow → caller (p3-004, p3-002):** the outcome and the trace envelope.
    Additional edges the plan discovers are welcome; these four are required.
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
- **Assume `PlanService.generate` returns a tuple unless p2-003's reopen (C-7) has landed.** If the reopen hasn't landed, the plan records the dependency in `## Revision notes` and the adapter test's deferral; the plan does not read `service.last_trace`.
- **Design the workflow-owned plan interface with `api` types.** The interface uses workflow-owned models; the adapter in `app` maps between them.
- **Add `app` to the `.importlinter` root packages without confirming Q2.** Q2 is a plan-stage task; the plan resolves it, not assumes it.
- **Assume LangGraph/LangChain/Ollama are installed.** Confirm the packages exist; if not, adding them is part of the plan.
