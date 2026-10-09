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
  audit-only provenance. **Plus a vocabulary consolidation across the p2 reasoning core** 
  (request code + canonical field only; `domain/types.py` as the sole map authority), which the T-11 wiring surfaced.
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
- Plan `Nutrition` dict: canonical field names (matches the deployed `Food` node), per BD-4.
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

**Error envelope.** All 4xx rejections — schema validation and business-logic
errors alike — use the project's custom envelope
`{"error":{code,message,details,timestamp}}`, installed by the
`RequestValidationError` handler in main.py. FastAPI's default
`{"detail":[...]}` shape does not reach the client. AC-14 (out-of-range
`nutrient_tolerance_pct`) is 422 with the custom envelope and code
`VALIDATION_ERROR`; AC-15 (solver unavailable) is the custom envelope with
its own code. **Baseline drift: the prior version of this paragraph claimed
the FastAPI default for schema validation. See Revision notes BD-1**.

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
  - **Signature (F-4 accepted; extended per BD-2 and r6 F-1):** input is
    `list[CandidateRecipe]` + `servings: int`. Each `CandidateRecipe` carries:
    - `recipe_id: str`;
    - `requirements: list[CandidateRequirement]`, each carrying
      `canonical_key: str` (the resolved food concept, passed through from the
      plan repository — **not** re-resolved by name in the calculator) and
      `scaled_grams: float` (the requirement's quantity in grams, already
      scaled by `servings` — pinned so `select_package`'s `count·price`
      tie-break and AC-12 determinism hold);
    - `nutrient_profiles: list[NutrientProfile]` for the recipe's ingredients
      (for missing-nutrient detection).

    Output is `dict[str, RecipeNutritionSignal]` where
    `RecipeNutritionSignal(recipe_id: str, missing_nutrients: list[str],
    selected_offer: OfferRef | None)`.
    - `missing_nutrients` is empty when the recipe has no evidence-absent
      canonical nutrient; non-empty otherwise.
    - `selected_offer` is the offer chosen by the calculator's existing
      `select_package` ranking, keyed on each requirement's `canonical_key`,
      using that requirement's `scaled_grams` as the quantity, over the
      concept's eligible `FULFILLS` edges (eligibility per p2-002's C-4 rule:
      `price_status == "estimated"`, `price_match_status == "accepted"`,
      `freshness_status == "fresh"`, `price_basis in {package_mass,
      package_volume}`). Ranking is unit price → retail cost → confidence →
      lexicographic `(food_key, retailer, listing_name)` (p2-002's
      `select_package` ordering). **The ranking operates over the concept's
      `FULFILLS` edges, not restricted to the `BEST_FULFILLMENT`-chosen Food**
      — matches p2-002's `select_package`, which ranks across the resolved
      key's accepted edges.
    - If a requirement has no eligible offer, its `selected_offer` is `None`.
      **A `None` selected_offer does not drop the recipe and does not cause
      infeasibility — cost stays non-gating per A-006/C-1.** The
      constraint-level record for that requirement carries no offer; the
      per-recipe outcome is unaffected.
    - `OfferRef(food_key: str, listing_name: str, retailer: str)`.
      `listing_name` + `retailer` go to the user-facing constraint-level
      record (AC-8c); `food_key` goes to `PlanTrace` (R-16).
    - The plan service maps plan `Nutrition` → canonical `NutrientProfile`
      at the call boundary; the plan repository supplies the per-requirement
      `canonical_key` (already present in its traversal) and the scaled
      `scaled_grams`.
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
- `SystemCode/remy/api/src/api/features/calculator/models.py` — add
  `OfferRef`, `CandidateRecipe`, and `CandidateRequirement` dataclasses (T-7).
- Tests (new, plan feature): `test_domain_solver.py` (R-14 fixture),
  `test_service_nutrition_drop.py` (AC-4/AC-4b/AC-4c/AC-5/AC-13),
  `test_causes.py` (AC-6/AC-7), `test_tolerance.py` (AC-9/AC-10/AC-14/AC-14b),
  `test_response_contract.py` (AC-2b/AC-8a/AC-8b/AC-8c/AC-11/AC-12),
  `test_solver_unavailable.py` (AC-15), `test_plan_calculator_integration.py`
  (integration; plus a one-line assertion that `MISSING_PACKAGE_DATA` is
  genuinely ignored).
- Tests (new, calculator feature): `test_inspect_candidates.py` (T-6;
  exercises the new public method's per-recipe missing-nutrient signals;
  lives with the calculator feature's tests, not the plan feature's).
- Tests (extended): `test_service_integration.py` (extend the existing
  fake-driver flow to assert the new reasoning record and relaxed label).
- `SystemCode/remy/api/docs/API_doc.md` — document `nutrient_tolerance_pct`,
  `relaxed`, `applied_tolerance_pct`, binding constraints, three-level
  reasoning; state that the old structural-`partial` semantics is removed
  (F-5); remove the structural-relaxation description.
- `sdd.json` — no change needed; T-1 confirmed the CI check set already
  covers `src/api/features/plan` and `tests/features/plan`. T-18 re-confirms
  at close.
- `SystemCode/remy/domain/src/domain/types.py` — the vocabulary authority rewrite.
- `SystemCode/remy/domain/src/domain/nutrients.py` — the fix's function rewrites.
- `SystemCode/remy/api/src/api/features/plan/filtering.py` — where `_recipe_nutrients` writes canonical keys and `_evaluate_nutrients` reads them.
- `SystemCode/remy/api/src/api/features/plan/ranking.py` — the shared `REQUEST_TO_CANONICAL` import.

## Constitution alignment

- **R-1** — API doc corrected in the same change; `relaxed` replaces the
  implicit structural-`partial` meaning; one name per concept.
- **R-1 (extended by the vocabulary consolidation)** — the p2 reasoning core uses one internal vocabulary (graph canonical names) and one request vocabulary; boundary translation to the API contract happens only at the DTO. No module accepts two names for the same concept.
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
| AC-14 | unit (schema) | test_tolerance.py::test_tolerance_out_of_range_rejected | outside [0,25] or non-int → 422 with the custom envelope (code: VALIDATION_ERROR), solver not invoked |
| AC-14b | unit | test_tolerance.py::test_tolerance_absent_defaults_zero | absent → 0; 0 → no widening |
| AC-15 | unit | test_solver_unavailable.py::test_solver_unavailable_hard_fail | custom envelope, no 200, no degraded plan, no trace claiming feasibility |
| AC-2b | unit | test_response_contract.py::test_infeasibility_reason_discriminator | empty-pool vs non-empty-pool reason |

Error-envelope assertions: both AC-14 and AC-15 assert the project's custom
`{"error":{code,message,details,timestamp}}` envelope (the `main.py
RequestValidationError` handler converts schema validation errors to this
shape; FastAPI's default `{"detail":[...]}` never reaches the client).

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
calculator method; tests under `tests/features/plan` and one new test file under
`tests/features/calculator`; one doc edit. `sdd.json` needs no change (T-1
confirmed coverage). The calculator change is additive.

## Revision notes

- **T-1 baseline (2026-10-08):** `cd SystemCode/remy/api && uv run
  --package remy-api pytest -q tests/features/plan` → **11 passed**.
  `sdd.json` already includes `src/api/features/plan` and
  `tests/features/plan` in its test, lint, and typecheck commands; no check-set
  change was needed.
- **BD-R1 (2026-10-08; observed at `dffeb58`):** Design §0 says the repository
  silently skips both requirements with no `FoodConcept` and those without
  `BEST_FULFILLMENT`. Actual state: the query uses `MATCH` for `FoodConcept`,
  so a requirement with no concept is absent from returned rows; a missing
  best fulfillment is collected without a marker and built as an ordinary
  ingredient. The unmapped-record design still holds. The repository change
  will preserve the same `REQUIRES` → `FoodConcept` → `BEST_FULFILLMENT` path
  while retaining missing-link facts for recipe-level reporting; no spec or
  contract change is needed.
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
- BD-1 (baseline drift, plan review loop 2) — 2026-10-08.
  - Original claim (plan Design §0): "schema validation uses FastAPI's
    default {"detail":[...]}" and "AC-14 (out-of-range) is 422 +
    {"detail":...}."
  - Actual state: main.py installs a RequestValidationError handler
    that converts all schema-validation errors into the project's custom
    {"error":{code,message,details,timestamp}} envelope with code
    VALIDATION_ERROR. FastAPI's default {"detail":[...]} shape never
    reaches the client. The prior plan's baseline was written from the
    framework default, not from the app's installed handler.
  - Design still holds? Yes. The plan's design says "reject with 422 and
    the custom envelope"; only the plan's description of which envelope is
    wrong. No design change. No spec change (AC-14 names the status, not the
    envelope shape).
  - Corrective edit: Design §0's error-envelope paragraph and T-2's
    Done when: now assert the custom envelope at 422 with code
    VALIDATION_ERROR. The test-strategy row and the closing envelope note
    are corrected to match.
  - Route: implement → plan (task-text change requires re-review of the
    hashed ## Tasks). Plan re-review and tasks_hash re-record before
    resuming at T-2.
  - Date: 2026-10-08.
- **BD-2 (baseline drift, implement loop 1, T-11 block) — 2026-10-09.**
  - **Original claim (plan Design §3, `## Files to touch`, T-11):**
    `inspect_candidates` returns per-recipe `missing_nutrients` only; AC-8c's
    "selected offer" per requirement is satisfied from the plan feature's
    existing data (the plan repository's traversal).
  - **Actual state:** the plan repository's traversal
    (`(:Recipe)-[:REQUIRES]->(:FoodConcept)-[:BEST_FULFILLMENT]->(:Food)`)
    does not carry offer identity, `listing_name`, or `retailer`.
    `BEST_FULFILLMENT` (per `neo4j_db_design.md`'s `EDGE_BEST_FULFILLMENT`)
    carries `food_key`, `nutrition_rank`, `selection_priority`, and dietary/
    allergen attributes — no offer. Offer data lives on `FULFILLS`. The plan's
    §0 baseline read `BEST_FULFILLMENT`'s schema but did not identify the
    offer-identity gap for AC-8c.
  - **Design still holds?** Yes, with the resolution below. The plan's design
    says the response carries the selected offer at constraint granularity; the
    plan just didn't name where the offer comes from.
  - **Resolution (Fix B, confirmed):** `inspect_candidates` extends to return
    `selected_offer: OfferRef | None` per recipe, computed by the calculator's
    existing `select_package` ranking over the concept's eligible `FULFILLS`
    edges (not restricted to the `BEST_FULFILLMENT`-chosen Food; matches
    p2-002's selection scope). `OfferRef(food_key, listing_name, retailer)`;
    `listing_name` + `retailer` go to the user-facing constraint-level record
    (AC-8c), `food_key` goes to `PlanTrace` (R-16). The plan service maps the
    returned `OfferRef` into the AC-8c record. No plan-repository change for
    offers; no second offer-selection rule.
  - **Corrective edits:** Design §3's signature block (extended); T-6's and
    T-7's done-when (offer assertions); T-11's `Files:` trailing parenthetical
    and done-when (offer mapping); this entry.
  - **Route:** `implement → plan` (task-text change). Plan re-review,
    `plan_hash` re-record, `tasks_hash` re-record before resuming at T-11.
  - **Date:** 2026-10-09.
- **BD-3 (baseline drift / contract gap, implement loop 1, T-11 block, r6 resolution) — 2026-10-09.**
  - **Original claim (plan Design §3, BD-2 revision):** `CandidateRecipe`
    carries "a mapping of its ingredients' `NutrientProfile`s"; the calculator
    can select offers from that alone.
  - **Actual state (r6 F-1):** offer selection needs, per requirement, the
    **canonical key** (the plan repository already resolves it; passing it
    through avoids a non-deterministic re-resolution by name) and the
    **scaled gram quantity** (so `select_package`'s `count·price` tie-break
    and AC-12 determinism hold). The BD-2 revision's input shape did not
    carry either.
  - **Design still holds?** Yes, with the F-1 resolution. The design says the
    response carries the selected offer at constraint granularity; the input
    shape just needed the two additional fields.
  - **Resolution:** `CandidateRecipe` gains `requirements:
    list[CandidateRequirement]` where each `CandidateRequirement` carries
    `canonical_key` and `scaled_grams`; the calculator keys offer selection on
    those. No re-resolution by name; determinism holds.
  - **Corrective edits:** Design §3 signature block (fuller input shape);
    T-6 and T-7 done-whens (input fixtures and offer assertions); T-14's
    done-when (offer path through the real integration); F-2a/b/c text fixes;
    nit-list corrections.
  - **Route:** `implement → plan`. Plan re-review, `plan_hash` and
    `tasks_hash` re-record before resuming at T-11.
  - **Date:** 2026-10-09.
- **BD-4 (baseline drift, vocabulary mismatch, T-11 block) — 2026-10-09.**
  - **Original claim (§0 "Nutrient vocabulary (three vocabularies)"):** three vocabularies exist; the plan identified them but did not declare which one is canonical, and did not verify that the plan feature's local maps agreed with each other.
  - **Actual state:** five distinct vocabularies for the same nine values across four packages (request code; graph canonical; `NutrientProfile`'s `calories_kcal`/`carbs_g`/`sugar_g`; the plan `Nutrition` dict's initial names; `service.py`'s `calories_kcal` target). `filtering.py`'s `_evaluate_nutrients` did `field, _ = REQUEST_TO_CANONICAL[nutrient.code]` against a now-flat map; `_recipe_nutrients` wrote request-code keys while `_evaluate_nutrients` read canonical — the two disagreed, producing `ValueError: too many values to unpack` and, before the fix, silently marking every nutrient as evidence-absent.
  - **Design still holds?** Yes, with the resolution below.
  - **Resolution:** `domain/types.py` becomes the single vocabulary authority. Two vocabularies exist: request code and canonical field (graph names). One translation table `REQUEST_TO_CANONICAL`; every module imports it; no module declares its own. `NutrientProfile`'s three divergent fields renamed to canonical. `Nutrients` DTO keeps its public-contract names and translates via a boundary constructor.
  - **Corrective edits:** `domain/types.py` (rewrite); `domain/nutrients.py` (`sum_nutrition`, `calculate_portion_nutrients` iterate `NUTRIENT_FIELDS`); `calculator/repository.py` (canonical keyword args); `calculator/schemas.py` (boundary translation); `plan/filtering.py` (`_recipe_nutrients` writes canonical; dead map deleted); `plan/ranking.py` (shared map); `plan/service.py` (shared map; canonical reads); `plan/solver_v2.py` (shared map; cast for mypy); `plan/models.py` (`Recipe.nutrients` uses `field(default_factory=Nutrition)`); test fixtures renamed.
  - **Route:** `implement → plan`. Plan re-review, `plan_hash` and `tasks_hash` re-record.
  - **Date:** 2026-10-09.
  - **Prevention:** the `types.py` authority, the `Literal` types (`RequestCode`, `CanonicalField`) that make mypy flag unknown names, and the round-trip tests that build fixtures from the producer's output.
- **BD-4b (BD-4 completion, 2026-10-09).** The vocabulary fix's first pass missed two functions in `filtering.py` (`_recipe_nutrients` wrote request-code keys, `_evaluate_nutrients` read canonical keys — the two disagreed, producing `ValueError: too many values to unpack` in the drop path); two functions in `domain/nutrients.py` (`calculate_portion_nutrients`, `sum_nutrition` — signature/type mismatches from the half-applied rename); and the `_evaluate_allergens`/`_evaluate_dietary` calls in `filter_candidates` were commented out. Fixes: `_recipe_nutrients` iterates `NUTRIENT_FIELDS` and writes canonical keys; the two `_evaluate_*` calls are re-enabled; `sum_nutrition` uses `result: Nutrition = {}` and populates on demand; `calculate_portion_nutrients` iterates `NUTRIENT_FIELDS`; `plan/models.py`'s `Recipe.nutrients` uses `field(default_factory=Nutrition)`; `plan/solver_v2.py` casts the `.get()` result. All 79 tests pass, mypy clean.
- **Phase-review inputs from p2-003:** the six BD entries (BD-1 envelope; BD-2 offer source; BD-3 offer input shape; BD-4 vocabulary; BD-4b vocabulary completion; plus the repository skip-site note); the four `annotation-unchecked` mypy sites (`filtering.py:186`, `service.py:162,176,177`); the starlette `BlockingPortal` deprecation carried from p2-002; the `sdd.json` check-set recommendation (template-based or plan-review-time coverage check); the plan-prompt recommendation (declare one canonical vocabulary per feature; name producer→consumer key names; build tests from producer output). The vocabulary fix touched a closed feature (p2-002) and the shared `domain` package; the phase review records the cross-feature impact.

## Tasks

### Group 0 — pre-task admin

- [x] **T-1** Baseline-run the plan feature tests and record the CI check-set state
  - Type: admin
  - Covers: plan Design §0 baseline; `sdd.json` drift guard
  - Files: `docs/sdd/features/p2-003-feasible-meal-plan-solving/plan.md` (## Revision notes — record the run output), `sdd.json` (only if the check set does not already cover `src/api/features/plan` and `tests/features/plan`)
  - Done when: `cd remy/api && uv run --package remy-api pytest -q tests/features/plan` is confirmed at 11 passed (baseline); `sdd.json`'s check commands are confirmed to cover both plan paths (and updated if not); the current state is recorded in the plan's `## Revision notes`

### Group 1 — solver relaxation set and fallback (A-005 / C-6 / R-3 / R-14)

- [x] **T-2** Write failing tests: relaxation set is nutrient-bound-widening-only; structural
  relaxations prohibited; round-robin fallback removed
  - Type: test
  - Covers: AC-9, AC-10, AC-14, AC-14b, AC-15
  - Files: `tests/features/plan/test_tolerance.py` (`test_relaxed_plan_labeled_and_records_tolerance`, `test_widening_insufficient_hard_infeasible`, `test_tolerance_out_of_range_rejected`, `test_tolerance_absent_defaults_zero`), `tests/features/plan/test_solver_unavailable.py` (`test_solver_unavailable_hard_fail`)
  - Done when: the tests fail against the current solver's four-stage ladder and round-robin fallback; AC-9/AC-10 pin nutrient-bound widening and hard infeasibility; AC-14 asserts the project's custom `{"error":{code,message,details,timestamp}}` envelope at 422 with code `VALIDATION_ERROR` and no solver invocation; AC-14b pins absent-default 0 and 0-means-no-widening; AC-15 asserts the same custom envelope with its own code, no `200 OK`, no degraded plan

- [x] **T-3** Add `nutrient_tolerance_pct` to the request schema; replace the relaxation ladder
  with a single widening stage; remove the fallback
  - Type: impl
  - Covers: AC-9, AC-10, AC-14, AC-14b, AC-15 (R-3, R-14 per A-005)
  - Files: `SystemCode/remy/api/src/api/features/plan/schemas.py` (`nutrient_tolerance_pct: int` with `Field(ge=0, le=25)` default 0), `SystemCode/remy/api/src/api/features/plan/solver_v2.py`, `SystemCode/remy/api/src/api/features/plan/exceptions.py` (add `SolverUnavailable` error)
  - Done when: T-2 passes; structural stages (1, 2) and the round-robin `ImportError` fallback are removed; solve order is strict → widened → hard infeasibility; bound widening is `lo' = round(lo * (1 - p/100))` and `hi' = round(hi * (1 + p/100))`, zero bound stays zero, goals not widened; ortools-unavailable raises `SolverUnavailable` (custom envelope); `nutrient_tolerance_pct` validated at the schema boundary

### Group 2 — hard infeasibility with a named binding-constraint set (R-14 / C-2)

- [x] **T-4** Write failing tests: `PlanInfeasible` carries the deterministic
  individually-binding set; reason discriminator
  - Type: test
  - Covers: AC-2, AC-2b, AC-3, AC-12
  - Files: `tests/features/plan/test_domain_solver.py` (`test_infeasible_names_individually_binding_set`, `test_producible_never_infeasible`, `test_feasible_returns_plan`), `tests/features/plan/test_response_contract.py` (`test_infeasibility_reason_discriminator`, `test_deterministic_across_runs`)
  - Done when: the tests fail against the current solver; AC-2 asserts a deterministic set of individually-binding constraints (per the amended spec wording); AC-3 asserts a satisfying assignment always returns a plan; AC-2b asserts the `no-recipes-survived` vs `no-assignment` discriminator; AC-12 asserts identical output across runs

- [x] **T-5** Implement the binding-constraint probe and the structured `PlanInfeasible`
  - Type: impl
  - Covers: AC-2, AC-2b, AC-3, AC-12 (R-14)
  - Files: `SystemCode/remy/api/src/api/features/plan/solver_v2.py`, `SystemCode/remy/api/src/api/features/plan/exceptions.py` (`PlanInfeasible` carries `NamedConstraint` set + `reason`), `SystemCode/remy/api/src/api/features/plan/models.py` (`NamedConstraint` dataclass with `scope`/`code`/`kind`)
  - Done when: T-4 passes; single-constraint drop-out probe implemented in fixed request order; determinism forced (`random_seed=0`, `num_search_workers=1`); empty-pool and non-empty-pool cases both produce the named set with the correct `reason`; probe cost bounded by the number of requested constraints

### Group 3 — `inspect_candidates` on the calculator (C-7 / R-2)

- [x] **T-6** Write failing test: calculator exposes `inspect_candidates` returning per-recipe
  missing-nutrient signals
  - Type: test
  - Covers: AC-4, AC-5, AC-13 (interface repo→service); C-7
  - Files: `tests/features/calculator/test_inspect_candidates.py` (new)
  - Done when: the test fails because the method does not exist; the test drives the method directly with a small set of candidate recipes (each carrying per-ingredient `NutrientProfile`s), asserting per-recipe `missing_nutrients` and empty-signal behavior; reuses `calculator/domain/nutrition.py::missing_nutrients`; **additionally asserts `selected_offer`**: for a recipe with an eligible `FULFILLS` offer, the returned `OfferRef` matches the calculator's ranking (unit price → retail cost → confidence → lexicographic; eligibility per C-4); for a recipe with no eligible offer, `selected_offer is None`; a recipe that is missing a tracked nutrient **still returns a `selected_offer` if any eligible offer exists** — missingness and offer selection are independent; the test's input fixtures construct `CandidateRecipe`s carrying per-requirement `canonical_key` and `scaled_grams`, and assert that a `None` selected_offer yields an offer-less signal without dropping the recipe

- [x] **T-7** Implement `CostNutritionService.inspect_candidates(recipes, servings)`
  - Type: impl
  - Covers: AC-4, AC-5, AC-13; C-7 (R-2)
  - Files: `SystemCode/remy/api/src/api/features/calculator/service.py`, `SystemCode/remy/api/src/api/features/calculator/__init__.py` (export the return type), `SystemCode/remy/api/src/api/features/calculator/models.py` (`RecipeNutritionSignal` + `CandidateRecipe` input shape if not reused)
  - Done when: T-6 passes; the method takes `list[CandidateRecipe]` and `servings: int` and returns `dict[str, RecipeNutritionSignal]`; each `CandidateRecipe` carries `recipe_id`, `requirements` (each with `canonical_key` and `scaled_grams`), and `nutrient_profiles`; `RecipeNutritionSignal(recipe_id, missing_nutrients, selected_offer)`; `selected_offer` is computed by the calculator's existing `select_package` ranking, keyed on each requirement's `canonical_key` with that requirement's `scaled_grams`, over the concept's eligible `FULFILLS` edges (no restriction to the `BEST_FULFILLMENT`-chosen Food); a requirement with no eligible offer yields `selected_offer is None` and **does not drop the recipe**; `OfferRef(food_key, listing_name, retailer)`, `CandidateRecipe`, and `CandidateRequirement` are defined in `calculator/models.py`; `servings` is accepted for contract symmetry (F-4); no change to `calculate`

### Group 4 — per-recipe unmapped fact in the plan repository (F-1)

- [x] **T-8** Write failing test: `PlanRepository.fetch_candidates` records per-recipe
  `unmapped_requirements`
  - Type: test
  - Covers: AC-13 (interface repo→service, second row)
  - Files: `tests/features/plan/test_service_integration.py` (extend the existing fake-driver flow) or a focused new test in the same file asserting per-recipe `unmapped_requirements` for a recipe with a `REQUIRES` edge missing its `FoodConcept` / `BEST_FULFILLMENT`
  - Done when: the test fails against the current repository (which silently skips those edges); the new per-recipe fact is asserted on the real `PlanRepository` output

- [x] **T-9** Extend `PlanRepository` to record `unmapped_requirements` per recipe
  - Type: impl
  - Covers: AC-13 (F-1); R-2 (fact stays within the plan feature)
  - Files: `SystemCode/remy/api/src/api/features/plan/repository.py`, `SystemCode/remy/api/src/api/features/plan/models.py` (`RequirementRef` dataclass; `Recipe` gains `unmapped_requirements`)
  - Done when: T-8 passes; the traversal is unchanged; the skip site identified in plan §0 records the missed `REQUIRES` edge into the recipe's `unmapped_requirements`; no p2-001 code change

### Group 5 — nutrition drop, cause model, three-level response (R-9 / C-3 / C-4 / C-5 / R-16 / R-17)

- [x] **T-10** Write failing tests: nutrition drop on tracked nutrients, goal-triggers-drop,
  untracked retention, cause precedence, per-recipe categorization
  - Type: test
  - Covers: AC-4, AC-4b, AC-4c, AC-5, AC-6, AC-7, AC-13
  - Files: `tests/features/plan/test_service_nutrition_drop.py` (`test_tracked_partial_nutrition_drops`, `test_drop_categorized_under_nutrient`, `test_goal_on_missing_nutrient_drops`, `test_untracked_partial_nutrition_retained`, `test_unmapped_cause_and_binding`), `tests/features/plan/test_causes.py` (`test_present_evidence_cause_distinct`, `test_multi_cause_precedence`)
  - Done when: the tests fail against the current service (which does not invoke the calculator or derive the per-recipe cause); AC-4/AC-4b/AC-4c pin the per-tracked-nutrient drop and its categorization; AC-5 pins untracked retention; AC-6/AC-7 pin cause distinctness and precedence `present-evidence-excludes → evidence-absent → unmapped`; AC-13 pins the `unmapped` cause and its binding-set naming

- [x] **T-11** Wire `inspect_candidates` into `PlanService.generate`; derive the per-recipe
  cause model; build the three-level response
  - Type: impl
  - Covers: AC-4, AC-4b, AC-4c, AC-5, AC-6, AC-7, AC-8a, AC-8b, AC-8c, AC-11, AC-13 (R-5, R-9, R-16, R-17); all interface rows
  - Files: `SystemCode/remy/api/src/api/features/plan/service.py`, `SystemCode/remy/api/src/api/features/plan/models.py` (per-recipe cause/outcome types), `SystemCode/remy/api/src/api/features/plan/schemas.py` (recipe-level outcome list, constraint-level list, `relaxed: bool`, `applied_tolerance_pct: int`, binding-constraint block; keep `status: complete|partial` per F-5; constraint-level record carries the `OfferRef`'s `listing_name` + `retailer`), `SystemCode/remy/api/src/api/features/plan/trace.py` (new `PlanTrace`; per-requirement resolved concept + offer, including the `OfferRef.food_key` audit identity)
  - Done when: T-10 passes; `PlanService.generate` calls `inspect_candidates` on the retained pool between filtering and solving; per-tracked-nutrient drops are applied per C-4; the per-recipe cause is derived per §4 (repository fact + p2-001 causes + p2-003's nutrition drops, combined per C-5 precedence); **the constraint-level record carries the `selected_offer` returned by `inspect_candidates` — `listing_name` + `retailer` in the user-facing response (AC-8c), `food_key` in `PlanTrace` (R-16)**; the response carries the three-level record and the `relaxed`/`applied_tolerance_pct` pair; no audit-only provenance in the user payload (AC-11); the `MISSING_PACKAGE_DATA` signal is not consumed (A-006 / C-1). **No plan-repository change is needed for offer data** — the offer comes from the calculator via `inspect_candidates`.

- [x] **T-12** Write failing tests: response contract at three levels; no audit provenance;
  relaxed label
  - Type: test
  - Covers: AC-8a, AC-8b, AC-8c, AC-11
  - Files: `tests/features/plan/test_response_contract.py` (`test_plan_level_record`, `test_recipe_level_record`, `test_constraint_level_record`, `test_no_audit_provenance_in_response`)
  - Done when: the tests fail against the current response schema; AC-8a/AC-8b/AC-8c pin each granularity; AC-11 asserts no `confidence`/`normalization_version`/`source_*`/`*_id` in the serialized user payload; the `relaxed` label and `applied_tolerance_pct` are present only when a widening was applied

### Group 6 — API doc correction (R-1)

- [x] **T-13** Update `API_doc.md` for the new `/plan` request and response shape
  - Type: impl
  - Covers: R-1; AC-9, AC-11
  - Files: `SystemCode/remy/api/docs/API_doc.md` (`/plan` section)
  - Done when: the doc documents `nutrient_tolerance_pct`, `relaxed`, `applied_tolerance_pct`, the binding-constraint block, and the three-level reasoning; the doc states the old structural-`partial` semantics is removed (F-5) and removes the structural-relaxation description; the doc's response example parses against the current `PlanResponse` schema

### Group 7 — integration tests

- [x] **T-14** Plan → calculator integration test
  - Type: integration
  - Covers: interface `CostNutritionService.inspect_candidates` → `PlanService.generate`; AC-4, AC-5, AC-13
  - Files: `tests/features/plan/test_plan_calculator_integration.py` (`test_plan_consumes_calculator_partial_nutrition`)
  - Done when: real calculator service + real plan service run together; the calculator repository (Neo4j) is mocked/faked, the solver runs for real; a candidate recipe missing a tracked nutrient is dropped by the plan because the real `inspect_candidates` reported it; **one explicit assertion that a `MISSING_PACKAGE_DATA` signal from the calculator is ignored by the plan** (pins A-006/C-1); the test also asserts the selected offer flows through the real plan → calculator path: a recipe with an eligible offer produces a constraint-level record carrying `listing_name` + `retailer`, and the `OfferRef.food_key` is present only in `PlanTrace`

- [x] **T-15** Plan repository → plan service integration test (extend existing)
  - Type: integration
  - Covers: interface `PlanRepository.fetch_candidates` → `PlanService.generate`; AC-8a/AC-8b/AC-8c, AC-13
  - Files: `tests/features/plan/test_service_integration.py` (extend)
  - Done when: the existing fake-driver flow asserts the new three-level record, the `relaxed` label, and the per-recipe `unmapped_requirements` fact survive the full path

### Group 8 — closing admin

- [x] **T-17** Record feature decisions
  - Type: admin
  - Covers: F-1..F-5 decisions; C-1..C-7 consequential flags; A-005 and A-006 citations; spec amendment AC-2
  - Files: `docs/sdd/features/p2-003-feasible-meal-plan-solving/decisions.md`
  - Done when: F-1 (unmapped fact sourced from the plan repository), F-2 (spec AC-2 amended to "individually-binding"), F-3 (reason discriminator, goal-triggers-drop), F-4 (`servings` for contract symmetry), F-5 (`status=partial` iff `relaxed`), C-1..C-7 and the AC-2 amendment are recorded; A-005 and A-006 referenced with their impact; no overrides; the r6 F-3 spec-sync note is recorded as a phase-review input: the spec's Q7 paragraph describes `inspect_candidates` as returning per-nutrient signals only — BD-2 extends it to also return the per-requirement `selected_offer` (for AC-8c's constraint-level record); additive, no AC contradicted; one line to add at the next spec touch ("…and the per-requirement selected offer for the constraint-level record.")

- [x] **T-18** Run the full API test suite and `sdd.py ci`
  - Type: verification
  - Covers: all ACs and interfaces
  - Files: (all above)
  - Done when: `cd remy/api && uv run --package remy-api pytest -q tests/features/plan tests/features/calculator` passes; sdd.json's check commands are re-confirmed to cover `src/api/features/plan` and `tests/features/plan` (T-1 established the coverage; this step re-confirms it hasn't drifted during implementation, and updates it if it has); `sdd.py ci p2-003-feasible-meal-plan-solving` reports `OVERALL: PASS`; the real-mart demonstration remains deferred under `docs/findings/data-prep-price-path.md` and is recorded as such
