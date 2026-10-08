# Prompt — Plan

Plan for feature **p2-003-feasible-meal-plan-solving**

`<id>`: `p2-003-feasible-meal-plan-solving`

## Notes

**IMPORTANT**: Since this is a brownfield feature, the plan must read the code before writing the
design and files-to-touch. The plan's design and files-to-touch must reflect what is actually there,
not what the spec assumes.

## Input

- MUST read: [AGENTS.md](../../../AGENTS.md)
- [constitution.md](../../../docs/sdd/constitution.md)
    - This plan is written against constitution version 1.6 (amendments A-005 and A-006 applied on
      2026-10-08).
    - If you encounter an archived plan or an older constitution copy that cites R-14's relaxation
      set as unclassified, R-8/R-10's recipe-level cost drop as a p2-003 obligation, or a
      nutrient_tolerance_pct default other than 0, treat those as superseded.
- Amendments: [amendments](../../../docs/amendments), specifically A-005 (R-14 relaxation set) and
  A-006 (R-8/R-10 cost-drop deferral to p3-004).
- [spec.md](../../../docs/sdd/features/p2-003-feasible-meal-plan-solving/spec.md)
- [sdd.json](../../../sdd.json) — read the current check set; confirm it will cover
  src/api/features/plan and tests/features/plan.
- [neo4j_db_design.md](../../../SystemCode/docs/neo4j_db_design.md)
- [system_design_v3.md](../../../SystemCode/docs/system_design_v3.md)
- Findings: [data-prep-price-path.md](../../../docs/findings/data-prep-price-path.md)
- Decisions:
    - [decisions.md](../../../docs/sdd/features/p2-001-constraint-evidence-filtering/decisions.md)
    - [decisions.md](../../../docs/sdd/features/p2-002-cost-nutrition-calculation/decisions.md)
- current codebase: [SystemCode](../../../SystemCode)
    - Backend:  [api](../../../SystemCode/remy/api)
        - [fastapi_project_structure.md](../../../SystemCode/remy/api/docs/fastapi_project_structure.md)
        - calculate feature: [calculator](../../../SystemCode/remy/api/src/api/features/calculator)
        - plan feature: [plan](../../../SystemCode/remy/api/src/api/features/plan)
    - Domain: [domain](../../../SystemCode/remy/domain)
    - Workflow (LangGraph,...): [workflows](../../../SystemCode/remy/workflows)
- Reference: [API_doc.md](../../../SystemCode/remy/api/docs/API_doc.md) (current deployed shape;
  spec supersedes).
  Use this only to (a) identify the current response/request field names so the plan's baseline
  inventory can name what exists, and (b) confirm the file path for the in-place R-1 update.
    - The API doc's /plan response shows a partial status for relaxed plans. The spec's AC-9 says
      relaxed plans are returned with a relaxed label; confirm against the plan stage whether the
      existing status vocabulary (complete / partial) is reused or replaced. The spec's terminology
      is "labeled as relaxed," not "partial" — the plan should record the mapping.
    - The API doc's /plan response does not carry a nutrient_tolerance_pct field or a relaxed
      marker. Both are new; the plan updates the doc in the same change.
    - The API doc's error envelope is the same custom {"error": {code, message, details, timestamp}}
      shape p2-002 uses; AC-14/AC-15 should assert it if the code uses it.
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
    - Baseline inventory — record these in the plan's Design §0:
        - The plan feature's actual structure — PlanService.generate's current signature, what it
          returns, and where the solver is invoked. Read
          SystemCode/remy/api/src/api/features/plan/service.py.
        - The solver's actual relaxation ladder — does it relax repeats, no-consecutive, nutrient
          min/max?
          With what values? Read plan/solver.py (or wherever OR-Tools is wrapped). A-005 forbids
          structural relaxations; the plan must record which are present in code.
        - The solver-unavailable fallback — is there a round-robin or degraded path when OR-Tools is
          unavailable? Read the solver module. Q5 says hard failure; the plan must record the
          current behavior.
        - The plan request schema — PlanRequest's current fields (does it have
          nutrient_tolerance_pct? no — it's new). Read schemas.py in the plan feature.
        - The plan response schema — what does the current response carry at the three levels
          (plan / recipe / constraint)? The spec requires all three; the plan should record which
          exist today.
        - The trace state — does the plan feature have a trace concept? (Likely no; p2-002's was
          new.) The plan should confirm and design PlanTrace.
        - p2-001's outcome vocabulary — read filtering.py's FilterResult / CandidateOutcome; record
          the exact cause names and precedence as implemented. The spec's precedence
          (present-evidence-excludes → evidence-absent → unmapped) needs to match or be reconciled.
        - p2-002's calculator public surface — read calculator/service.py and calculator/router.py;
          confirm what's publicly callable. The spec's Q7 assumes inspect_candidates is new; the
          plan verifies nothing equivalent exists.
        - The pre-existing failures in the plan feature's tests — run pytest tests/features/plan and
          record the current state.
        - The per-AC status table (present | absent | needs-fix) for p2-003's ACs.
    - Spec vocabulary vs code vocabulary.
        - For each noun the spec names that does not exist as a symbol in the code (for example
          nutrient_tolerance_pct, inspect_candidates, unmapped cause, "binding constraint"), record
          it in the baseline inventory as "new." For each noun the spec names that does exist but
          with a different meaning, record the mismatch. The plan's design must reconcile: either
          the code changes to match the spec, or (if the mismatch is a spec defect) a plan → spec
          finding is routed.
        - Use grep/rg across src/api/features/plan and src/api/features/calculator for each spec
          noun. Record the command and its result in the baseline inventory, so the reader can
          verify.
    - If the baseline reveals a behavior the spec is silent on but the plan must decide (for
      example, inspect_candidates's exact signature, or the trace's dataclass fields), the plan
      names a default, records it in ## Revision notes as a plan-stage decision, and flags it for
      the reviewer. If the gap is a spec-level contract (a user-visible shape, a new rule, a change
      to the cause precedence or the tolerance semantics), the plan routes a finding to spec and
      stops.
    - p2-001's outcome vocabulary and cause precedence: read filtering.py's FilterResult /
      CandidateOutcome and record the exact cause names and the precedence the code applies.
      p2-003's spec asserts present-evidence-excludes → evidence-absent → unmapped. If the code
      disagrees, or if unmapped is not a distinct top-level cause in the code, record as a p2-001
      finding to route. (p2-001's F-B — its cost_basis_compatible gate — affects the candidate pool
      p2-003 sees, but cost is out of scope, so record it as an upstream state note, not a p2-003
      change.)
3. Fill Approach (chosen + rejected alternative), Design, Files to touch.
    - Trace: the spec names a plan-level trace separate from p2-002's CalculationTrace. The plan's
      Design names the module and dataclass; the spec's ## Execution trace contents become the
      dataclass's fields. The user-facing response carries none of it; the exposure boundary is
      owned by p3-001/p3-002. The plan does not design the exposure.
    - `inspect_candidates` (spec C-7): the plan designs its signature — input (a bulk set of
      candidate recipes with ingredient quantities and the request's servings value), output
      (per-recipe, per-nutrient item-level signals, using p2-002's existing
      CalculationTrace/NutrientProfile types where possible), and where it lives (the calculator's
      service module, exposed through the calculator's public service boundary). The integration
      test covers the plan→calculator boundary.
    - `nutrient_tolerance_pct` (spec AC-14/AC-14b, C-2): a new optional integer field on the plan
      request, closed interval [0, 25], default 0. The plan adds it to the request schema and to the
      solver's bound-widening logic; the widening formula (min' = min × (1 − p/100), max' = max ×
      (1 + p/100), zero bound stays zero) is implemented in the solver.
4. Constitution alignment: one line per relevant rule.
5. Test strategy: one row per AC. No AC untested.
    - Error envelope: if a request is rejected, the plan records the envelope format the code uses
      (FastAPI default {"detail": [...]} or a custom {"error": {code, message, details,
      timestamp}}). If the code uses a custom envelope, the plan's test strategy must assert it on
      at least one rejection AC.
6. Integration per interface: one row in `## Integration per interface` per
   interface the plan names (producer → consumer). Test runs the real code
   under test (dependencies may be mocked, the code under test may not), reads
   from the producer, asserts on the consumer. If it can't run in this
   environment, record the deferral in `## Revision notes` and `decisions.md`;
   don't omit the row. If there are genuinely no producer→consumer interfaces (single-file change),
   write 'None — single-component change.' Otherwise every producer→consumer edge gets a row.
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
