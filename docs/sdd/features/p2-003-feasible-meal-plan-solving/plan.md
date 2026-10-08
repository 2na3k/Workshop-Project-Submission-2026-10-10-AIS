---
feature: p2-003-feasible-meal-plan-solving
---

# Plan - Feasible meal-plan solving

Written against constitution v1.6 (A-005 R-14 relaxation set; A-006 R-8/R-10
cost-drop deferral to p3-004).

## Approach

- **Chosen:** Prove-and-fix the existing `plan` feature in place. Add a
  bounded nutrient-tolerance relaxation (`nutrient_tolerance_pct`) to the
  request schema and the solver, delete the solver's structural relaxations
  and round-robin fallback (both now prohibited by A-005/C-6), make the solver
  surface a deterministic named binding-constraint set on hard infeasibility,
  add a per-recipe nutrition evidence-absent drop that consumes the
  calculator's `PARTIAL_NUTRITION_DATA` through a new public calculator method
  `inspect_candidates`, extend the plan repository to record a per-recipe
  unmapped-requirement fact, and attach a plan-level reasoning structure +
  trace (plan / recipe / constraint) to the response without widening
  audit-only provenance.
- **Rejected:** Rebuild the solver as a fresh module with a native feasibility
  model. Rejected — the spec is a prove-and-fix against pre-existing behavior
  (Non-goals), the solver shape is fixed by R-3, and the existing CP-SAT model
  already expresses the hard horizon and nutrient-bound constraints; the gap is
  the relaxation set, the fallback, the binding-constraint report, the drop
  wiring, and the per-recipe unmapped derivation, not the model core.

## Design

### §0 Baseline inventory (brownfield — what is actually in the code)

Read on 2026-10-08 from `SystemCode/remy/api/src/api/features/plan` and
`.../calculator`, plus `domain`.

**Plan feature structure.**
- `service.py` — `PlanService.generate(self, request) -> PlanResponse`.
  Flow: validate nutrient codes/ranges → `filter_candidates(repo.fetch_candidates(), request)`
  (stores `self.last_filter_result`) → `rank_candidates(filtered, request)` →
  `solve_v2(recipes, request)` returning `(days, relaxations)` → build
  `PlanResponse`. The calculator is **not** invoked anywhere in this path.
- `router.py` — `POST ""` → `PlanResponse`, `Depends(get_plan_service)`.
- `repository.py` — `PlanRepository.fetch_candidates(limit=1000)` runs `QUERY`
  over `(:Recipe)-[:REQUIRES]->(:FoodConcept)-[:BEST_FULFILLMENT]->(:Food)`,
  builds `Recipe`/`Ingredient` with a `Nutrition` dict per ingredient
  (`_build_nutrients`). Recipes with no quantifiable ingredient are dropped at
  build time. **The traversal walks each recipe's `REQUIRES` edges; when an
  edge's `FoodConcept` is absent or its `BEST_FULFILLMENT` is missing, the
  edge is silently skipped.** This is the point where per-recipe
  `unmapped_requirements` will be recorded (F-1).
- `models.py` — dataclasses `Ingredient`, `Recipe`, and p2-001's
  `CandidateOutcome`, `ConstraintEvaluation`, `IngredientWarning`,
  `FilterResult`.
- `schemas.py` — `PlanRequest(horizon_days 1..14, meals_per_day 1..6,
  servings>=1, allergies?, dietary?, nutrients?)`. **No `nutrient_tolerance_pct`.**
  Response: `PlanResponse(plan_id, status: "complete"|"partial", message,
  validation_summary, relaxations, horizon_totals, days)`. `DayResponse`/
  `MealResponse` carry recipe id/title/nutrients/ingredients only. **No
  recipe-level drop record, no constraint-level resolved-concept/offer record,
  no binding constraint, no relaxed marker.**
- `solver_v2.py` — `solve_v2(recipes, request) -> (days, applied_relaxations)`.
  CP-SAT via lazily-imported `ortools`. Hard: exactly `m` meals/day; `n[d,j]<=1`.
  **Relaxation ladder (stages):** (1) `extra_days_per_recipe += 1` (*structural*);
  (2) `drop_consecutive_rule = True` (*structural*); (3) widen nutrient `max`
  by 10%; (4) loosen nutrient `min` by 10%; (5) raise `PlanInfeasible("...")`.
  **Fallback:** on `ImportError`, returns a round-robin plan **ignoring all
  nutrient constraints** (prohibited by C-6). `PlanInfeasible` carries only a
  string.
- `ranking.py`, `aggregation.py`, `exceptions.py`, `dependencies.py` — as
  before. **No `trace.py` in the plan feature.**

**p2-001 outcome vocabulary (as implemented, `filtering.py`).**
- Top-level causes produced by `_top_cause`: `"present-evidence-excludes"`,
  `"evidence-absent"`, or `None`. **No `"unmapped"` top-level cause.**
  Unmapped is tracked only as `FilterResult.unmapped_requirements` (an int).
- Precedence: present-evidence-excludes before evidence-absent, matching p2-001
  D-2.
- `filter_candidates(..., require_fresh, require_cost)` has flags defaulting
  off; `generate` calls it with defaults.

**p2-002 calculator public surface.**
- `CostNutritionService.calculate(request) -> (CostNutritionResponse, CalculationTrace)`.
  Resolves ingredient **names** via `repository.resolve_candidates`; raises
  `UnresolvableIngredient` for any unresolved name (all-or-nothing). **Not
  usable as-is for bulk per-recipe inspection keyed on already-resolved
  `canonical_key`s.**
- Reusable domain pieces: `calculator/domain/nutrition.py::missing_nutrients(
  profile: NutrientProfile) -> list[str]`; `NUTRIENT_FIELDS` and
  `NutrientProfile` in `domain/types.py`.
- **No `inspect_candidates` exists.**

**Nutrient vocabulary (three vocabularies).**
- `domain.NutrientProfile`: nine canonical fields.
- Plan `Nutrition` dict: key `calories` (not `calories_kcal`), else same names.
- p2-001 request→field map: `calories → energy_kcal`, etc.

**Baseline tests.** `uv run --package remy-api pytest -q tests/features/plan`
→ **11 passed** on 2026-10-08. No `test_domain_solver.py` exists.

**grep evidence (spec nouns vs code).** Only `FilterResult.unmapped_requirements`
and a solver comment match. All of `nutrient_tolerance_pct`,
`inspect_candidates`, binding-constraint, per-recipe `unmapped` cause, and
`relaxed` label are **new**.

**Spec noun → code status.**

| Spec noun | Status | Reconciliation |
|---|---|---|
| `nutrient_tolerance_pct` | new | add optional `int` [0,25] default 0 to `PlanRequest` + solver widening |
| `inspect_candidates` | new | new public method on `CostNutritionService` |
| binding constraint set | new | new structured value on `PlanInfeasible` + response |
| `relaxed` label | new | new response field |
| per-recipe `unmapped` cause | new (int exists) | **p2-003 extends `PlanRepository` to record per-recipe unmapped facts; p2-003 derives the per-recipe `unmapped` cause from them; no p2-001 code change** (F-1, §4) |
| plan trace | new | new `PlanTrace` dataclass |

**Response status vocabulary mapping (F-5).** Keep `status:
"complete"|"partial"` for backward compatibility; add explicit `relaxed: bool`
+ `applied_tolerance_pct: int`; `status="partial"` iff `relaxed is True`. The
  old structural-`partial` semantics dies with the ladder removal; the API doc
  states this explicitly.

**Error envelope.** Business-logic errors raise `AppError` → custom envelope
`{"error":{code,message,details,timestamp}}`; schema validation uses FastAPI's
default `{"detail":[...]}`. AC-14 (out-of-range) is 422 + `{"detail":...}`;
AC-15 (solver unavailable) is the custom envelope.

### §1 nutrient-tolerance relaxation (A-005 / C-2)

- New optional `nutrient_tolerance_pct: int` with `Field(ge=0, le=25)`, default `0`.
- Replace the four-stage ladder with a **single** permitted relaxation:
  nutrient-bound widening. Applied to integer milli-unit bounds:
  `lo' = round(lo * (1 - p/100))`, `hi' = round(hi * (1 + p/100))`. Zero bound
  stays zero. Goals never widened.
- Solve order: (a) strict; if feasible → not relaxed. (b) if `p > 0`, widened;
  if feasible → relaxed, record `applied_tolerance_pct = p`. (c) otherwise →
  hard infeasibility with a named binding set. **No structural stage, no
  round-robin fallback.**

### §2 Hard infeasibility with a named binding-constraint set (R-14 / C-2)

- `PlanInfeasible` carries a deterministic **individually-binding** constraint
  set. "Binding" characterization: the set of requested constraints whose
  relaxation (single-constraint drop-out probe) admits a plan, plus the
  empty-pool constraints when applicable.
- **Spec-wording note (F-2 resolved).** The spec's AC-2 is being amended in
  this loop from "a minimal set whose relaxation would admit a plan" to "a
  deterministic set of individually-binding constraints." The plan implements
  the amended wording; the spec edit lands in the same loop. This is the
  resolution of the `plan → spec` finding recorded in the prior plan revision.
- Each named constraint is a `NamedConstraint(scope, code, kind)`:
  - `scope ∈ {plan, recipe, requirement}`;
  - `code` is the request code (e.g., `sodium`, `vegan`, `unmapped`);
  - `kind` is the cause (`present-evidence-excludes` / `evidence-absent` /
    `unmapped` / `nutrient-bound` / `horizon`).
    This is the nameable identifier AC-13's second clause requires.
- Empty eligible pool after filtering+dropping → binding set names the
  constraint(s) that emptied the pool.
- Pool non-empty but no assignment fills the horizon → binding set names the
  nutrient constraints that remain violated at the widened bounds
  (deterministic: iterate requested nutrients in request order).
- Plan-level `reason` discriminator: `"no-recipes-survived"` vs
  `"no-assignment"`.
- Determinism (AC-12): `random_seed=0`, `num_search_workers=1`, fixed
  iteration order.
- **Probe cost:** single-constraint drop-out re-solves, bounded by the number
  of requested constraints (small).

### §3 Recipe-level nutrition drop via `inspect_candidates` (R-9 / A-003 / C-3 / C-4 / C-7)

- New public method on the calculator service:
  `CostNutritionService.inspect_candidates(recipes, servings) ->
  dict[recipe_id -> RecipeNutritionSignal]`. Input: bulk set of candidate
  recipes, each carrying per-ingredient nutrient profiles (already
  materialized by the plan repository) and quantities, plus `servings`. Output
  per recipe: the set of canonical nutrients that are evidence-absent (any
  contributing ingredient missing a value), reusing
  `calculator/domain/nutrition.py::missing_nutrients` and `NUTRIENT_FIELDS`.
  - **Signature (F-4 accepted):** input `list[CandidateRecipe]`
    (each exposing `recipe_id` and a mapping of its ingredients'
    `NutrientProfile`s) + `servings: int`; output
    `dict[str, RecipeNutritionSignal]` where
    `RecipeNutritionSignal(recipe_id: str, missing_nutrients: list[str])`
    (empty = no signal). `servings` is retained for contract symmetry even
    though missingness does not depend on scaling (F-4). The plan maps plan
    `Nutrition` → canonical `NutrientProfile` at the call boundary.
- In `PlanService.generate`, after `filter_candidates` and before `solve_v2`,
  call `inspect_candidates` on the retained pool. For each recipe, for each
  **tracked** nutrient (request supplies a `limit` or a `goal` — C-4), if that
  nutrient is in `missing_nutrients`, drop the recipe with an `evidence-absent`
  cause categorized under that nutrient's constraint (AC-4/AC-4b). A recipe
  evidence-absent for any tracked nutrient is globally excluded (C-3). An
  untracked missing nutrient does not drop (AC-5).
- `MISSING_PACKAGE_DATA` (cost) is **ignored** (A-006 / C-1).

### §4 Per-recipe cause model and precedence (C-5 / R-17)

- p2-003 introduces a per-recipe top-level cause with three values:
  `present-evidence-excludes`, `evidence-absent`, `unmapped`, with precedence
  `present-evidence-excludes` → `evidence-absent` → `unmapped` (C-5).
- **Derivation (F-1).** Per-recipe `unmapped` facts come from
  `PlanRepository.fetch_candidates`, which already traverses each recipe's
  `(:Recipe)-[:REQUIRES]->(:FoodConcept)-[:BEST_FULFILLMENT]->(:Food)` path.
  The repository is extended to record a per-recipe
  `unmapped_requirements: list[RequirementRef]` — the set of the recipe's
  `REQUIRES` edges whose `FoodConcept` is absent or whose `BEST_FULFILLMENT`
  is missing. The traversal is unchanged; the change is to collect the
  misses instead of silently skipping them (§0 identifies the exact skip
  site). `PlanService.generate` derives the per-recipe `unmapped` cause
  directly from that repository fact, then combines it with p2-001's
  `drop_outcomes[*].cause` (for present-evidence-excludes and evidence-absent)
  and p2-003's own nutrition drops (§3) via the C-5 precedence. **No change to
  p2-001's code and no change to p2-001's `FilterResult` contract** — the
  per-recipe fact is a p2-003 artifact, produced by p2-003's own repository
  within p2-003's feature package.
- All applicable causes retained in the recipe-level record (AC-7).
- AC-13's second clause (binding set names the unmapped requirement) is
  satisfied because `NamedConstraint(scope="requirement", code=<requirement
  name>, kind="unmapped")` carries the identifier (§2).

### §5 Three-level reasoning structure + `PlanTrace` (R-16 / R-17)

- New `PlanTrace` dataclass in the plan feature (new module), **separate from
  p2-002's `CalculationTrace`**. Records: plan-level feasibility outcome,
  named binding set + reason, applied tolerance; per-recipe outcome
  (selected / retained-unselected / dropped) and cause(s), referencing the
  calculator's per-nutrient signal (not embedding `CalculationTrace`);
  per-requirement resolved concept and selected offer. The user-facing response
  carries none of the audit-only provenance; exposure boundary is p3-001/
  p3-002's.
- The user-facing `PlanResponse` gains structured, non-provenance fields:
  recipe-level outcome list with causes, constraint-level list (resolved
  concept + offer + warnings), `relaxed`/`applied_tolerance_pct` pair, and a
  binding-constraint block when infeasible. No `confidence`,
  `normalization_version`, or `source_*`/`*_id` fields (AC-11).

## Files to touch

- `SystemCode/remy/api/src/api/features/plan/schemas.py` — add
  `nutrient_tolerance_pct: int` [0,25] default 0 to `PlanRequest`; add response
  fields: recipe-level outcome list, constraint-level list, `relaxed: bool`,
  `applied_tolerance_pct: int`, binding-constraint block; keep
  `status: complete|partial`.
- `SystemCode/remy/api/src/api/features/plan/solver_v2.py` — remove structural
  relaxation stages (1,2) and the round-robin ImportError fallback; implement
  single nutrient-bound widening; raise structured hard infeasibility with a
  deterministic individually-binding set; on ortools unavailable, raise a hard
  error (no fallback).
- `SystemCode/remy/api/src/api/features/plan/exceptions.py` — extend
  `PlanInfeasible` to carry the `NamedConstraint` set + reason; add
  `SolverUnavailable` plan error.
- `SystemCode/remy/api/src/api/features/plan/repository.py` — record
  per-recipe `unmapped_requirements` while building recipes (F-1, §4); no
  other change.
- `SystemCode/remy/api/src/api/features/plan/service.py` — invoke
  `inspect_candidates` on the retained pool; apply per-tracked-nutrient
  evidence-absent drops; derive the per-recipe cause model (§4); build the
  three-level response + `PlanTrace`; map plan `Nutrition` → canonical
  `NutrientProfile` at the calculator call boundary.
- `SystemCode/remy/api/src/api/features/plan/models.py` — add per-recipe
  cause/outcome types, `CandidateRecipe`, `RecipeNutritionSignal`,
  `NamedConstraint`, `RequirementRef` (internal dataclasses).
- `SystemCode/remy/api/src/api/features/plan/trace.py` — **new**: `PlanTrace`.
- `SystemCode/remy/api/src/api/features/calculator/service.py` — add public
  `inspect_candidates(recipes, servings)` reusing `missing_nutrients` /
  `NUTRIENT_FIELDS`; no change to `calculate`.
- `SystemCode/remy/api/src/api/features/calculator/__init__.py` — export the
  new method's return type.
- Tests (new): `test_domain_solver.py` (R-14 fixture), `test_service_nutrition_drop.py`
  (AC-4/AC-4b/AC-4c/AC-5/AC-13), `test_causes.py` (AC-6/AC-7),
  `test_tolerance.py` (AC-9/AC-10/AC-14/AC-14b), `test_response_contract.py`
  (AC-2b/AC-8a/AC-8b/AC-8c/AC-11/AC-12),
  `test_solver_unavailable.py` (AC-15),
  `test_plan_calculator_integration.py` (integration; plus a one-line
  assertion that `MISSING_PACKAGE_DATA` is genuinely ignored).
- Tests (extended): `test_service_integration.py` (extend the existing
  fake-driver flow to assert the new reasoning record and relaxed label).
- `SystemCode/remy/api/docs/API_doc.md` — document `nutrient_tolerance_pct`,
  `relaxed`, `applied_tolerance_pct`, binding constraints, three-level
  reasoning; state that the old structural-`partial` semantics is removed
  (F-5); remove the structural-relaxation description.
- `sdd.json` — extend the CI check set to cover `src/api/features/plan` and
  `tests/features/plan` in addition to the calculator paths.

## Constitution alignment

- **R-1** — API doc corrected in the same change; `relaxed` replaces the
  implicit structural-`partial` meaning; one name per concept.
- **R-2** — `PlanService` calls the calculator only through
  `CostNutritionService.inspect_candidates` (public surface); no calculator
  internals imported; the plan repository extension is within the plan feature.
- **R-3** — the solver remains CP-SAT; the change removes prohibited
  relaxations and the degraded fallback.
- **R-5** — evidence-absent nutrition drops with `evidence-absent` cause;
  never treated as pass/zero; distinct from present-evidence-excludes and
  unmapped.
- **R-9 (A-003)** — recipe-level nutrition drop lives here, per tracked
  nutrient, reading the calculator's signal from `inspect_candidates`.
- **R-10 / R-8 (A-004/A-002/A-006)** — cost-side recipe drop not implemented
  here; `MISSING_PACKAGE_DATA` ignored; deferred to p3-004.
- **R-14 (A-005)** — only nutrient-bound widening relaxes; structural
  relaxations and the fallback removed; hard infeasibility names a
  deterministic individually-binding set; producible plan always returned.
- **R-16** — user-facing response carries resolved concept, offer,
  per-requirement outcome, warnings, selections, binding constraints, relaxed
  label; no confidence/normalization/source provenance.
- **R-17** — three-level reasoning with distinct causes including unmapped.

## Test strategy

| AC | Test type | Test location / name | Notes |
|---|---|---|---|
| AC-1 | unit | test_domain_solver.py::test_feasible_returns_plan | eligible pool → plan fills every slot |
| AC-2 | unit | test_domain_solver.py::test_infeasible_names_individually_binding_set | no assignment → no plan, deterministic individually-binding set (spec amended per F-2; the spec edit lands in this loop) |
| AC-3 | unit | test_domain_solver.py::test_producible_never_infeasible | satisfying assignment ⇒ plan |
| AC-4 | unit | test_service_nutrition_drop.py::test_tracked_partial_nutrition_drops | tracked `PARTIAL_NUTRITION_DATA` → evidence-absent drop |
| AC-4b | unit | test_service_nutrition_drop.py::test_drop_categorized_under_nutrient | record names the triggering nutrient |
| AC-4c | unit | test_service_nutrition_drop.py::test_goal_on_missing_nutrient_drops | C-4 goal-triggers-drop |
| AC-5 | unit | test_service_nutrition_drop.py::test_untracked_partial_nutrition_retained | untracked missing nutrient not dropped |
| AC-6 | unit | test_causes.py::test_present_evidence_cause_distinct | severe allergen distinct from evidence-absent/unmapped |
| AC-7 | unit | test_causes.py::test_multi_cause_precedence | precedence present→absent→unmapped; all causes retained |
| AC-8a | unit | test_response_contract.py::test_plan_level_record | feasibility outcome + relaxed/tolerance |
| AC-8b | unit | test_response_contract.py::test_recipe_level_record | per-recipe outcome + cause |
| AC-8c | unit | test_response_contract.py::test_constraint_level_record | resolved concept + offer + warnings |
| AC-9 | unit | test_tolerance.py::test_relaxed_plan_labeled_and_records_tolerance | widening makes feasible → relaxed + applied tolerance; goals/structure untouched |
| AC-10 | unit | test_tolerance.py::test_widening_insufficient_hard_infeasible | hard infeasibility naming binding nutrient |
| AC-11 | unit | test_response_contract.py::test_no_audit_provenance_in_response | no confidence/normalization/source in user payload |
| AC-12 | unit | test_response_contract.py::test_deterministic_across_runs | identical plan / infeasibility+binding set across runs |
| AC-13 | unit | test_service_nutrition_drop.py::test_unmapped_cause_and_binding | unmapped requirement → unmapped cause; binding set names it (F-1 mechanism: plan repository records it) |
| AC-14 | unit (schema) | test_tolerance.py::test_tolerance_out_of_range_rejected | outside [0,25] or non-int → 422 `{"detail":...}`, solver not invoked |
| AC-14b | unit | test_tolerance.py::test_tolerance_absent_defaults_zero | absent → 0; 0 → no widening |
| AC-15 | unit | test_solver_unavailable.py::test_solver_unavailable_hard_fail | custom envelope, no 200, no degraded plan, no trace claiming feasibility |
| AC-2b | unit | test_response_contract.py::test_infeasibility_reason_discriminator | empty-pool vs non-empty-pool reason |

Error-envelope assertions: AC-14 asserts the FastAPI default `{"detail":[...]}`;
AC-15 asserts the custom `{"error":{code,message,details,timestamp}}` envelope.

## Integration per interface

| Interface | Test type | Test location / name | Notes |
|---|---|---|---|
| `CostNutritionService.inspect_candidates` → `PlanService.generate` | integration | test_plan_calculator_integration.py::test_plan_consumes_calculator_partial_nutrition | Real calculator service + real plan service; the calculator repository (Neo4j) is mocked/faked, the solver runs for real; a candidate recipe missing a tracked nutrient is dropped by the plan because the real `inspect_candidates` reported it. **Includes one explicit assertion that a `MISSING_PACKAGE_DATA` signal from the calculator is ignored by the plan (pins A-006/C-1 against drift).** |
| `PlanRepository.fetch_candidates` → `PlanService.generate` | integration | test_service_integration.py (existing, extended) | Existing fake-driver flow feeds real `PlanRepository` → real `PlanService`; extend to assert the new three-level record, `relaxed` label, and per-recipe unmapped fact survive the full path. |

## Risks & mitigations

- **Nutrient vocabulary mismatch.** Mapping bugs could silently mark a present
  nutrient as absent (R-5 false-drop) or vice-versa. Mitigation: explicit map
  at the `inspect_candidates` call boundary; AC-4/AC-5 fixtures pin
  tracked-missing vs untracked-missing; §3 records the mapping.
- **Removing the round-robin fallback** changes behavior when ortools absent.
  Mitigation: required by C-6/AC-15; `R-3`'s CI import check already asserts
  ortools is importable; the hard-fail path is explicit.
- **Binding-constraint probe cost and determinism.** Mitigation: fixed-order
  single-constraint drop-out probe; seed + single-worker force determinism;
  probe re-solves bounded by requested constraints.
- **CI check-set change** could surface pre-existing plan-test issues.
  Mitigation: baseline is 11 passing; surfaced failures recorded.
- **ortools solve time budget.** Mitigation: `rank_candidates` bounds the pool
  (`min(50*meals_per_day, 300)`); `max_time_in_seconds=0.5`; probe re-solves
  bounded.
- **Unmapped-derivation repository change** touches `fetch_candidates`'s
  recipe-building loop. Mitigation: the traversal is unchanged; the change
  records misses instead of skipping them; `test_service_integration.py`'s
  extension asserts the per-recipe `unmapped_requirements` fact survives the
  path.

## Scope check

Fits one working context: **yes.** Source edits within `plan` plus one additive
calculator method; tests under `tests/features/plan`; one doc and one
`sdd.json` edit. The calculator change is additive.

## Revision notes

- **F-1 (plan review, blocker) — resolved in this revision.** AC-13's
  per-recipe `unmapped` cause derivation is now explicitly sourced from
  `PlanRepository.fetch_candidates`'s existing traversal (the
  `REQUIRES → FoodConcept → BEST_FULFILLMENT` path recorded in §0). The
  repository records per-recipe `unmapped_requirements: list[RequirementRef]`;
  the service derives the per-recipe `unmapped` cause from that fact and
  combines it with p2-001's `drop_outcomes[*].cause` and p2-003's own
  nutrition drops via the C-5 precedence. No p2-001 code change; no
  `FilterResult` contract change; the fact is a p2-003 artifact produced
  within p2-003's feature package. §4 now cites §0's skip site explicitly.
- **F-2 (plan review, MAJOR) — resolved in this loop by spec amendment.** The
  spec's AC-2 is being amended from "a minimal set whose relaxation would
  admit a plan" to "a deterministic set of individually-binding constraints."
  The plan implements the amended wording; the spec edit lands in the same
  loop; the `plan → spec` finding is closed by the amendment. §2 records the
  amendment; the AC-2 test row cites the amended wording.
- **F-3 (plan review, MINOR) — resolved.** (a) The empty-pool vs non-empty-pool
  `reason` discriminator has a named test (`AC-2b` in the test strategy). (b)
  C-4's goal-triggers-drop has a named test (`AC-4c`).
- **F-4 (plan review, MINOR) — accepted.** `inspect_candidates(recipes,
  servings)` keeps `servings` for contract symmetry even though missingness
  does not depend on scaling. Recorded for `decisions.md`.
- **F-5 (plan review, MINOR) — accepted.** `status="partial"` iff `relaxed`;
  the old structural-`partial` semantics dies with the ladder removal; the API
  doc change states this explicitly.
- **Nits applied.** `RecipeNutritionSignal`'s field renamed
  `partial_nutrition` → `missing_nutrients`. The integration test explicitly
  asserts `MISSING_PACKAGE_DATA` is ignored.
- **U-1 (upstream state note, not a p2-003 change):** p2-001 tracks unmapped
  only as `FilterResult.unmapped_requirements` (int). p2-003 derives its own
  per-recipe `unmapped` cause from the plan repository, not from p2-001.
  p2-001's F-B is noted only.
- **Deferral — none.** Both integration rows run in this environment with the
  fake Neo4j driver and the real solver.

## Tasks

### Group 0 — pre-task admin

- [ ] **T-1** Verify rule IDs, AC numbers, and spec-text against the frozen artifacts; land the AC-2 cleanup
  - Type: admin
  - Covers: F-2 (spec amendment landing), spec AC-2 cleanup nit
  - Files: `docs/sdd/features/p2-003-feasible-meal-plan-solving/spec.md` (AC-2 duplicate sentence cleanup only; the F-2 wording change is already in place from the prior loop), `docs/sdd/features/p2-003-feasible-meal-plan-solving/plan.md` (Design §0 / Constitution alignment — edit only if a citation is wrong)
  - Done when: every cited rule (R-1, R-2, R-3, R-5, R-8, R-9, R-10, R-14, R-16, R-17) and every AC (AC-1..AC-15 incl. AC-2b, AC-4b, AC-4c, AC-8a..AC-8c, AC-14b) is confirmed present in the current approved `constitution.md` (v1.6) and `spec.md`; the AC-2 duplicate sentence is deleted; `spec_hash` is re-recorded after re-review if the deletion changes it

- [ ] **T-2** Baseline-run the plan feature tests and record the CI check-set state
  - Type: admin
  - Covers: plan Design §0 baseline; `sdd.json` drift guard
  - Files: `docs/sdd/features/p2-003-feasible-meal-plan-solving/plan.md` (## Revision notes — record the run output), `sdd.json` (only if the check set does not already cover `src/api/features/plan` and `tests/features/plan`)
  - Done when: `cd remy/api && uv run --package remy-api pytest -q tests/features/plan` is confirmed at 11 passed (baseline); `sdd.json`'s check commands are confirmed to cover both plan paths (and updated if not); the current state is recorded in the plan's `## Revision notes`

### Group 1 — solver relaxation set and fallback (A-005 / C-6 / R-3 / R-14)

- [ ] **T-3** Write failing tests: relaxation set is nutrient-bound-widening-only; structural relaxations prohibited; round-robin fallback removed
  - Type: test
  - Covers: AC-9, AC-10, AC-14, AC-14b, AC-15
  - Files: `tests/features/plan/test_tolerance.py` (`test_relaxed_plan_labeled_and_records_tolerance`, `test_widening_insufficient_hard_infeasible`, `test_tolerance_out_of_range_rejected`, `test_tolerance_absent_defaults_zero`), `tests/features/plan/test_solver_unavailable.py` (`test_solver_unavailable_hard_fail`)
  - Done when: the tests fail against the current solver's four-stage ladder and round-robin fallback; AC-9/AC-10 pin nutrient-bound widening and hard infeasibility; AC-14 asserts the FastAPI `{"detail":[...]}` envelope at 422 with no solver invocation; AC-14b pins absent-default 0 and 0-means-no-widening; AC-15 asserts the custom `{"error":{code,message,details,timestamp}}` envelope, no `200 OK`, no degraded plan

- [ ] **T-4** Add `nutrient_tolerance_pct` to the request schema; replace the relaxation ladder with a single widening stage; remove the fallback
  - Type: impl
  - Covers: AC-9, AC-10, AC-14, AC-14b, AC-15 (R-3, R-14 per A-005)
  - Files: `SystemCode/remy/api/src/api/features/plan/schemas.py` (`nutrient_tolerance_pct: int` with `Field(ge=0, le=25)` default 0), `SystemCode/remy/api/src/api/features/plan/solver_v2.py`, `SystemCode/remy/api/src/api/features/plan/exceptions.py` (add `SolverUnavailable` error)
  - Done when: T-3 passes; structural stages (1, 2) and the round-robin `ImportError` fallback are removed; solve order is strict → widened → hard infeasibility; bound widening is `lo' = round(lo * (1 - p/100))` and `hi' = round(hi * (1 + p/100))`, zero bound stays zero, goals not widened; ortools-unavailable raises `SolverUnavailable` (custom envelope); `nutrient_tolerance_pct` validated at the schema boundary

### Group 2 — hard infeasibility with a named binding-constraint set (R-14 / C-2)

- [ ] **T-5** Write failing tests: `PlanInfeasible` carries the deterministic individually-binding set; reason discriminator
  - Type: test
  - Covers: AC-2, AC-2b, AC-3, AC-12
  - Files: `tests/features/plan/test_domain_solver.py` (`test_infeasible_names_individually_binding_set`, `test_producible_never_infeasible`, `test_feasible_returns_plan`), `tests/features/plan/test_response_contract.py` (`test_infeasibility_reason_discriminator`, `test_deterministic_across_runs`)
  - Done when: the tests fail against the current solver; AC-2 asserts a deterministic set of individually-binding constraints (per the amended spec wording); AC-3 asserts a satisfying assignment always returns a plan; AC-2b asserts the `no-recipes-survived` vs `no-assignment` discriminator; AC-12 asserts identical output across runs

- [ ] **T-6** Implement the binding-constraint probe and the structured `PlanInfeasible`
  - Type: impl
  - Covers: AC-2, AC-2b, AC-3, AC-12 (R-14)
  - Files: `SystemCode/remy/api/src/api/features/plan/solver_v2.py`, `SystemCode/remy/api/src/api/features/plan/exceptions.py` (`PlanInfeasible` carries `NamedConstraint` set + `reason`), `SystemCode/remy/api/src/api/features/plan/models.py` (`NamedConstraint` dataclass with `scope`/`code`/`kind`)
  - Done when: T-5 passes; single-constraint drop-out probe implemented in fixed request order; determinism forced (`random_seed=0`, `num_search_workers=1`); empty-pool and non-empty-pool cases both produce the named set with the correct `reason`; probe cost bounded by the number of requested constraints

### Group 3 — `inspect_candidates` on the calculator (C-7 / R-2)

- [ ] **T-7** Write failing test: calculator exposes `inspect_candidates` returning per-recipe missing-nutrient signals
  - Type: test
  - Covers: AC-4, AC-5, AC-13 (interface repo→service); C-7
  - Files: `tests/features/calculator/test_inspect_candidates.py` (new)
  - Done when: the test fails because the method does not exist; the test drives the method directly with a small set of candidate recipes (each carrying per-ingredient `NutrientProfile`s), asserting per-recipe `missing_nutrients` and empty-signal behavior; reuses `calculator/domain/nutrition.py::missing_nutrients`

- [ ] **T-8** Implement `CostNutritionService.inspect_candidates(recipes, servings)`
  - Type: impl
  - Covers: AC-4, AC-5, AC-13; C-7 (R-2)
  - Files: `SystemCode/remy/api/src/api/features/calculator/service.py`, `SystemCode/remy/api/src/api/features/calculator/__init__.py` (export the return type), `SystemCode/remy/api/src/api/features/calculator/models.py` (`RecipeNutritionSignal` + `CandidateRecipe` input shape if not reused)
  - Done when: T-7 passes; the method takes `list[CandidateRecipe]` and `servings: int` and returns `dict[str, RecipeNutritionSignal]`; `RecipeNutritionSignal(recipe_id, missing_nutrients)`; `servings` is accepted for contract symmetry (F-4) and does not affect missingness; no change to `calculate`

### Group 4 — per-recipe unmapped fact in the plan repository (F-1)

- [ ] **T-9** Write failing test: `PlanRepository.fetch_candidates` records per-recipe `unmapped_requirements`
  - Type: test
  - Covers: AC-13 (interface repo→service, second row)
  - Files: `tests/features/plan/test_service_integration.py` (extend the existing fake-driver flow) or a focused new test in the same file asserting per-recipe `unmapped_requirements` for a recipe with a `REQUIRES` edge missing its `FoodConcept` / `BEST_FULFILLMENT`
  - Done when: the test fails against the current repository (which silently skips those edges); the new per-recipe fact is asserted on the real `PlanRepository` output

- [ ] **T-10** Extend `PlanRepository` to record `unmapped_requirements` per recipe
  - Type: impl
  - Covers: AC-13 (F-1); R-2 (fact stays within the plan feature)
  - Files: `SystemCode/remy/api/src/api/features/plan/repository.py`, `SystemCode/remy/api/src/api/features/plan/models.py` (`RequirementRef` dataclass; `Recipe` gains `unmapped_requirements`)
  - Done when: T-9 passes; the traversal is unchanged; the skip site identified in plan §0 records the missed `REQUIRES` edge into the recipe's `unmapped_requirements`; no p2-001 code change

### Group 5 — nutrition drop, cause model, three-level response (R-9 / C-3 / C-4 / C-5 / R-16 / R-17)

- [ ] **T-11** Write failing tests: nutrition drop on tracked nutrients, goal-triggers-drop, untracked retention, cause precedence, per-recipe categorization
  - Type: test
  - Covers: AC-4, AC-4b, AC-4c, AC-5, AC-6, AC-7, AC-13
  - Files: `tests/features/plan/test_service_nutrition_drop.py` (`test_tracked_partial_nutrition_drops`, `test_drop_categorized_under_nutrient`, `test_goal_on_missing_nutrient_drops`, `test_untracked_partial_nutrition_retained`, `test_unmapped_cause_and_binding`), `tests/features/plan/test_causes.py` (`test_present_evidence_cause_distinct`, `test_multi_cause_precedence`)
  - Done when: the tests fail against the current service (which does not invoke the calculator or derive the per-recipe cause); AC-4/AC-4b/AC-4c pin the per-tracked-nutrient drop and its categorization; AC-5 pins untracked retention; AC-6/AC-7 pin cause distinctness and precedence `present-evidence-excludes → evidence-absent → unmapped`; AC-13 pins the `unmapped` cause and its binding-set naming

- [ ] **T-12** Wire `inspect_candidates` into `PlanService.generate`; derive the per-recipe cause model; build the three-level response
  - Type: impl
  - Covers: AC-4, AC-4b, AC-4c, AC-5, AC-6, AC-7, AC-8a, AC-8b, AC-8c, AC-11, AC-13 (R-5, R-9, R-16, R-17); all interface rows
  - Files: `SystemCode/remy/api/src/api/features/plan/service.py`, `SystemCode/remy/api/src/api/features/plan/models.py` (per-recipe cause/outcome types), `SystemCode/remy/api/src/api/features/plan/schemas.py` (recipe-level outcome list, constraint-level list, `relaxed: bool`, `applied_tolerance_pct: int`, binding-constraint block; keep `status: complete|partial` per F-5), `SystemCode/remy/api/src/api/features/plan/trace.py` (new `PlanTrace`)
  - Done when: T-11 passes; `PlanService.generate` calls `inspect_candidates` on the retained pool between filtering and solving; per-tracked-nutrient drops are applied per C-4; the per-recipe cause is derived per §4 (repository fact + p2-001 causes + p2-003's nutrition drops, combined per C-5 precedence); the response carries the three-level record and the `relaxed`/`applied_tolerance_pct` pair; no audit-only provenance in the user payload (AC-11); the `MISSING_PACKAGE_DATA` signal is not consumed (A-006 / C-1)

- [ ] **T-13** Write failing tests: response contract at three levels; no audit provenance; relaxed label
  - Type: test
  - Covers: AC-8a, AC-8b, AC-8c, AC-11
  - Files: `tests/features/plan/test_response_contract.py` (`test_plan_level_record`, `test_recipe_level_record`, `test_constraint_level_record`, `test_no_audit_provenance_in_response`)
  - Done when: the tests fail against the current response schema; AC-8a/AC-8b/AC-8c pin each granularity; AC-11 asserts no `confidence`/`normalization_version`/`source_*`/`*_id` in the serialized user payload; the `relaxed` label and `applied_tolerance_pct` are present only when a widening was applied

### Group 6 — API doc correction (R-1)

- [ ] **T-14** Update `API_doc.md` for the new `/plan` request and response shape
  - Type: impl
  - Covers: R-1; AC-9, AC-11
  - Files: `SystemCode/remy/api/docs/API_doc.md` (`/plan` section)
  - Done when: the doc documents `nutrient_tolerance_pct`, `relaxed`, `applied_tolerance_pct`, the binding-constraint block, and the three-level reasoning; the doc states the old structural-`partial` semantics is removed (F-5) and removes the structural-relaxation description; the doc's response example parses against the current `PlanResponse` schema

### Group 7 — integration tests

- [ ] **T-15** Plan → calculator integration test
  - Type: integration
  - Covers: interface `CostNutritionService.inspect_candidates` → `PlanService.generate`; AC-4, AC-5, AC-13
  - Files: `tests/features/plan/test_plan_calculator_integration.py` (`test_plan_consumes_calculator_partial_nutrition`)
  - Done when: real calculator service + real plan service run together; the calculator repository (Neo4j) is mocked/faked, the solver runs for real; a candidate recipe missing a tracked nutrient is dropped by the plan because the real `inspect_candidates` reported it; **one explicit assertion that a `MISSING_PACKAGE_DATA` signal from the calculator is ignored by the plan** (pins A-006/C-1)

- [ ] **T-16** Plan repository → plan service integration test (extend existing)
  - Type: integration
  - Covers: interface `PlanRepository.fetch_candidates` → `PlanService.generate`; AC-8a/AC-8b/AC-8c, AC-13
  - Files: `tests/features/plan/test_service_integration.py` (extend)
  - Done when: the existing fake-driver flow asserts the new three-level record, the `relaxed` label, and the per-recipe `unmapped_requirements` fact survive the full path

### Group 8 — CI check set

- [ ] **T-17** Extend `sdd.json` to cover the plan feature
  - Type: impl
  - Covers: `sdd.json` scope (per plan Output); the p2-002 CI-drift lesson
  - Files: `sdd.json`
  - Done when: the `test`, `lint`, and `typecheck` commands cover `src/api/features/plan` and `tests/features/plan` in addition to `src/api/features/calculator` and `tests/features/calculator`; `sdd.py ci p2-003-feasible-meal-plan-solving` runs the extended set

### Group 9 — closing admin

- [ ] **T-18** Record feature decisions
  - Type: admin
  - Covers: F-1..F-5 decisions; C-1..C-7 consequential flags; A-005 and A-006 citations; spec amendment AC-2
  - Files: `docs/sdd/features/p2-003-feasible-meal-plan-solving/decisions.md`
  - Done when: F-1 (unmapped fact sourced from the plan repository), F-2 (spec AC-2 amended to "individually-binding"), F-3 (reason discriminator, goal-triggers-drop), F-4 (`servings` for contract symmetry), F-5 (`status=partial` iff `relaxed`), C-1..C-7 and the AC-2 amendment are recorded; A-005 and A-006 referenced with their impact; no overrides

- [ ] **T-19** Run the full API test suite and `sdd.py ci`
  - Type: verification
  - Covers: all ACs and interfaces
  - Files: (all above)
  - Done when: `cd remy/api && uv run --package remy-api pytest -q tests/features/plan tests/features/calculator` passes; `sdd.py ci p2-003-feasible-meal-plan-solving` reports `OVERALL: PASS`; the real-mart demonstration remains deferred under `docs/findings/data-prep-price-path.md` and is recorded as such
