---
feature: p2-003-feasible-meal-plan-solving
---

# Spec - Feasible meal-plan solving

## Summary

This feature makes the existing meal-plan solver provable against the plan
feasibility and recipe-level drop contracts of the p2 reasoning core. Given a
requested planning horizon (`horizon_days × meals_per_day`), a pool of
candidate recipes, and the explicit nutrition, allergen, dietary, and freshness
constraints a user supplies, the solver returns a feasible plan when one can be
produced and refuses to return a plan when none can — naming the binding
constraint(s) in that refusal. A plan is never reported as unfeasible while a
producible plan exists.

Before solving, p2-003 performs the recipe-level drop that the calculator and
the constraint-evidence filter leave to it. It consumes the item-level
evidence-absent signal the cost/nutrition calculation (p2-002) emits for
nutrition — `PARTIAL_NUTRITION_DATA`, naming the canonical nutrients missing
from at least one contributing ingredient — and drops the affected recipe from
the eligible pool with an evidence-absent cause when the request tracks a
nutrient the recipe cannot evaluate. The drop is applied **per tracked
nutrient**: a recipe that is evidence-absent for any tracked nutrient is
excluded from the plan pool for that execution, and its exclusion is
categorized under that nutrient's constraint in the reasoning record. p2-003
also consumes p2-001's per-constraint candidate outcomes (retained / warned /
present-evidence-excludes / evidence-absent) and its unmapped-requirement
tracking, so drops carry a cause distinct from present-evidence exclusions and
from unmapped requirements.

The plan result carries the reasoning structure the downstream explanation
layer (p3) needs: plan-level feasibility outcome with named binding
constraints, recipe-level selection/drop outcomes with causes, and
constraint-level outcomes with resolved food concepts and selected offers.

The feature is a prove-and-fix change against pre-existing solver behavior. It
does not rebuild the solver, redesign the request/response files, or widen the
user-facing response with audit-only provenance.

**Cost and budget are out of scope for this feature.** The calculator's
item-level `MISSING_PACKAGE_DATA` signal does not trigger a recipe-level drop
here; the recipe-level cost drop is deferred to a later budget feature, and
R-8/R-10 are amended accordingly (see `## Clarifications` C-1).

## Traces to

- **G-1** — Users receive a weekly meal plan evaluated against explicit
  nutrition ranges, allergen/dietary constraints, and freshness; the solver
  produces that plan only when the requested horizon can be satisfied, and
  otherwise refuses with a named cause.
- **Roadmap phase p2 → p2-003-feasible-meal-plan-solving** *(partial)* —
  "Existing planning API. Remaining work: verify satisfiable returns a plan and
  unsatisfiable returns no plan with named binding constraints (R-14); confirm
  the plan result carries per-requirement outcomes, drop causes, selected
  offers, and resolved concepts so that p3 can explain without re-deriving.
  Additionally, per the amended R-9, p2-003 consumes p2-002's item-level
  nutrition evidence-absent signal as the recipe-level drop trigger; for
  `PARTIAL_NUTRITION_DATA` the drop applies per tracked nutrient."
- **Phase p2 outcome** — The reasoning core evaluates explicit constraints
  conservatively, computes distinct consumed and package costs, and returns a
  feasible meal plan only when the requested horizon can be satisfied.
- **Roadmap shared contract** — "Plan feasibility result with named binding
  constraints, reasoning structure sufficient for downstream explanation, and
  the recipe-level nutrition drop behavior consuming p2-002's item-level
  evidence-absent signal (per-nutrient for `PARTIAL_NUTRITION_DATA`)," shared
  with p2-001-constraint-evidence-filtering and
  p2-002-cost-nutrition-calculation.
- **Constitutional rules:**
  - **R-2** (inward dependency direction) — the solver reaches the calculator's
    item-level signals through the calculator service's public interface, not
    by importing its internals.
  - **R-3** (stack shape fixed) — the solver remains a constraint solver; any
    change to that shape requires an amendment.
  - **R-5** (absent evidence drops, never includes) — a recipe whose evidence
    is absent for a tracked constraint is dropped from the eligible pool with
    an evidence-absent cause, distinct from a present-evidence exclusion and
    from an unmapped requirement; absent evidence is never treated as passing,
    compliant, or zero. The `unmapped` cause is a top-level cause distinct from
    `evidence-absent` (see `## Clarifications` C-5).
  - **R-9** (nutrient constraints require a profile, per amended A-003) — the
    **recipe-level** drop for incomplete nutrition is p2-003's responsibility,
    applied per tracked nutrient. See `## Clarifications` C-1 for the
    tracking definition.
  - **R-10** (cost eligibility requires a convertible price basis, per amended
    A-004) — the cost-side recipe drop is **not** consumed in this feature (see
    `## Clarifications` C-1). R-8/R-10 are amended to make the calculator's
    item-level signal the sole enforcement point for cost in p2, with the
    recipe-level drop deferred.
  - **R-14** (feasibility floor names the binding constraint, per amendment
    A-005 — see `## Clarifications` C-2) — if, after filtering, dropping, and
    every permitted nutrient-tolerance relaxation, no set of retained recipes
    satisfies `horizon_days × meals_per_day`, no plan is produced and the
    response names the binding constraint(s); a plan is never returned as
    unfeasible while a producible plan exists. Only nutrient-bound widening is
    a permitted relaxation; structural relaxations are prohibited.
  - **R-16** (user response excludes audit-only provenance) — the reasoning
    structure p2-003 attaches for p3 keeps mapping confidence, normalization
    version, and source identifiers out of the user-facing payload, retaining
    them only in the execution trace.
  - **R-17** (three-level explanations with distinct drop causes) — the plan
    result exposes outcomes at plan, recipe, and constraint granularity,
    including dropped recipes, with evidence-absent drops reported distinctly
    from present-evidence exclusions and from unmapped requirements.

## User-facing behavior

- When the requested horizon can be satisfied by the recipes that survive
  filtering and dropping, the plan request returns a plan: recipe selections
  covering every `(day, meal)` slot of `horizon_days × meals_per_day`.
- When the horizon cannot be satisfied after filtering, dropping, and the
  permitted nutrient-tolerance relaxation, the request does not return a plan.
  It returns a feasibility failure that names the binding constraint(s) — a deterministic set of individually-binding constraints whose relaxation would admit a plan. The failure
  distinguishes "no recipes remained in the eligible pool" from "recipes
  remained but no assignment satisfies the horizon under the constraints." The
  named set is deterministic for identical inputs.
- A plan is never reported as unfeasible while a producible plan exists: if any
  assignment of eligible recipes satisfies the horizon and the (possibly
  relaxed) nutrient constraints, the solver returns it rather than failing.
- Before solving, each candidate recipe is screened for evidence-absent
  conditions:
  - A recipe with a requirement that maps to no food concept (p2-001's
    unmapped-requirement outcome) is dropped with a distinct `unmapped` cause.
  - A recipe whose contributing set is incomplete for a nutrient the request
    tracks (the calculator's `PARTIAL_NUTRITION_DATA`) is dropped for that
    nutrient's constraint as `evidence-absent`. If any tracked nutrient
    triggers a drop for a recipe, the recipe is excluded from the plan pool for
    that execution; the exclusion is categorized under the affected nutrient's
    constraint in the reasoning record. A nutrient is "tracked" when the
    request supplies a `limit` (`min`/`max`) or a `goal` for it (see
    `## Clarifications` C-4).
  - A recipe already excluded by p2-001 for present evidence (declared severe
    allergen, dietary non-compliance, or a nutrient limit the recipe's known
    values exceed) is dropped with a `present-evidence-excludes` cause. This
    cause is distinct from `evidence-absent` and from `unmapped`.
- When multiple causes apply to the same recipe, the top-level cause follows
  p2-001's precedence: `present-evidence-excludes` ahead of `evidence-absent`
  ahead of `unmapped`. All applicable causes remain distinguishable in the
  recipe-level reasoning record.
- The plan result carries, at three granularities:
  - **Plan level:** whether a plan was produced, and if not, the named binding
    constraint(s); the applied nutrient-tolerance relaxation, if any.
  - **Recipe level:** for each candidate, whether it was selected, retained but
    unselected, or dropped, and the drop cause (`evidence-absent` /
    `present-evidence-excludes` / `unmapped`) when dropped.
  - **Constraint/requirement level:** per requirement, the constraint outcome,
    the resolved food concept, the selected offer, and any warnings.
- A plan produced under a nutrient-tolerance relaxation is labeled as a relaxed
  plan and records the applied tolerance. The tolerance applies only to
  nutrient `min`/`max` bounds; it does not apply to goals.
- When the constraint solver is unavailable at runtime, the request fails hard;
  no degraded plan is produced (see `## Clarifications` C-6).
- The user-facing plan response exposes only the resolved food concept, the
  chosen offer, the per-requirement constraint outcome, warned conditions, the
  selected recipes, the named binding constraints when infeasible, the relaxed
  label and applied tolerance when applicable. It does not expose mapping
  confidence, normalization version, or source identifiers; those remain in
  the execution trace.

## Acceptance criteria

- **AC-1** Given a request whose horizon is `horizon_days × meals_per_day` and a
  pool of eligible recipes from which at least one assignment satisfies the
  horizon and all requested constraints, when the plan is solved, then a plan
  is returned that fills every `(day, meal)` slot, rather than a feasibility
  failure.

- **AC-2** Given a request whose horizon cannot be satisfied by any assignment
  of the eligible recipes under the requested constraints and under every
  permitted nutrient-tolerance relaxation, when the plan is solved, then no plan is returned and the response names the binding constraint(s) — a deterministic set of individually-binding constraints, each relaxation of which (in isolation) admits a plan. When the failure is driven by a nutrient bound exceeding the permitted `nutrient_tolerance_pct`, the specific binding nutrient constraint(s) are included in the named set.

- **AC-3** Given a request for which a producible plan exists, when the plan is
  solved, then the response is never a feasibility failure — the existence of a
  satisfying assignment guarantees a returned plan. (The R-14 "never unfeasible
  while producible" direction, paired with AC-2.)

- **AC-4** Given a request that tracks a nutrient and a candidate recipe the
  calculator reports with `PARTIAL_NUTRITION_DATA` naming that nutrient as
  missing from at least one contributing ingredient, when the eligible pool is
  built, then the recipe is dropped from the plan pool for that execution with
  an `evidence-absent` cause. The drop is triggered by any single tracked
  nutrient's evidence-absence.

- **AC-4b** Given a recipe dropped under AC-4, when the reasoning record is
  produced, then the exclusion is categorized under the affected nutrient's
  constraint and the record explicitly names which nutrient triggered the drop.

- **AC-5** Given a candidate recipe the calculator reports with
  `PARTIAL_NUTRITION_DATA` for a nutrient the request does **not** track, when
  the eligible pool is built, then the recipe is not dropped on account of that
  nutrient.

- **AC-6** Given a candidate recipe already excluded by p2-001 for present
  evidence (for example a declared severe allergen), when the eligible pool is
  built, then the recipe is dropped with a `present-evidence-excludes` cause,
  and this cause is distinct in the result from `evidence-absent` and from
  `unmapped`.

- **AC-7** Given a recipe to which multiple drop causes apply (for example both
  an evidence-absent condition and a present-evidence exclusion), when the drop
  cause is reported, then the top-level cause follows the precedence
  `present-evidence-excludes` → `evidence-absent` → `unmapped`, and all
  applicable causes remain distinguishable in the recipe-level reasoning
  record.

- **AC-8a** Given a successful plan, when the plan result is produced, then the
  plan-level record carries the feasibility outcome (plan produced) and, if a
  nutrient-tolerance relaxation was applied, the applied tolerance value and
  the relaxed label.

- **AC-8b** Given any plan result — successful or infeasible — when the
  recipe-level record is produced, then each candidate recipe carries its
  outcome (selected / retained-unselected / dropped) and, when dropped, its
  drop cause (`evidence-absent` / `present-evidence-excludes` / `unmapped`).

- **AC-8c** Given a successful plan, when the constraint-level record is
  produced, then each selected requirement carries its resolved food concept,
  the selected offer, and any warned conditions.

- **AC-9** Given a request whose nutrient bounds cannot be satisfied exactly
  but can be satisfied under the permitted nutrient-tolerance widening
  (`nutrient_tolerance_pct`), when the plan is solved, then the plan is
  returned, labeled as relaxed, and the result records the applied tolerance
  value. Only nutrient `min`/`max` bounds are widened — `min' = min × (1 −
  p/100)`, `max' = max × (1 + p/100)` — and goals are not widened. Structural
  relaxations (additional recipe repeats, dropping the no-consecutive rule) are
  not applied.

- **AC-10** Given a request whose nutrient bounds cannot be satisfied even under
  the permitted nutrient-tolerance widening, when the plan is solved, then no
  plan is returned, and the response is a hard infeasibility failure naming the
  binding nutrient constraint(s); no structurally degraded plan is produced.

- **AC-11** Given any plan result — successful, relaxed, or infeasible — when
  the user-facing response is serialized, then it carries no mapping
  confidence, no normalization version, and no source identifiers; those
  values appear only in the execution trace. (R-16.)

- **AC-12** Given the same request and the same candidate pool, when the plan
  is solved more than once, then the returned plan (or the infeasibility
  result and its named binding constraints) is identical across runs —
  selection and feasibility reporting are deterministic functions of the
  inputs.

- **AC-13** Given a candidate recipe whose requirement maps to no food concept
  (p2-001's unmapped-requirement outcome), when the eligible pool is built,
  then the recipe is dropped with the `unmapped` cause; if that recipe's
  exclusion is the cause of infeasibility, the named binding constraint
  identifies the unmapped requirement.

- **AC-14** Given a request with `nutrient_tolerance_pct` present and outside
  the closed interval `[0, 25]`, when the request is received, then it is
  rejected with `422 Unprocessable Entity` (or `400 Bad Request` if rejected by
  a business-logic validator) before the solver runs; the solver is not
  invoked. A non-integer value (for example a string or float) is rejected by
  schema validation at the same boundary.

- **AC-14b** Given a request with `nutrient_tolerance_pct` absent, when the
  plan is solved, then the tolerance defaults to `0` (no nutrient-bound
  widening); given a request with `nutrient_tolerance_pct = 0`, no widening is
  applied.

- **AC-15** Given a request received while the constraint solver is
  unavailable, when the plan is solved, then the request fails with an
  explicit error (no `200 OK` plan response) and no plan or partial result is
  produced; no degraded fallback is returned, and no trace record claims
  feasibility.

## Edge cases & errors

- The eligible pool is empty after filtering and dropping. The response is a
  feasibility failure whose named binding constraint identifies that no recipe
  survived, distinct from the case where recipes survived but no assignment
  satisfies the horizon.
- A recipe is dropped because it is evidence-absent for one tracked nutrient
  but is complete for every other tracked nutrient. It is excluded from the
  plan pool for that execution; the reasoning record categorizes the exclusion
  under the affected nutrient's constraint.
- A requested nutrient is one for which the canonical graph carries no value
  for any candidate (for example calcium or iron, which the calculator reports
  as always-null). Every candidate is evidence-absent for that nutrient; the
  response is a feasibility failure naming that nutrient's constraint as
  binding, not a silently empty plan.
- A `min = 0` or `max = 0` bound is not widened by a non-zero tolerance:
  percent widening of zero stays zero. Only strictly positive bounds expand.
- A user sets `nutrient_tolerance_pct = 0` and the request otherwise could only
  be satisfied by widening: the response is a hard infeasibility failure, not a
  silently widened plan.
- A user sets `nutrient_tolerance_pct` above `25`: the request is rejected at
  the request-validation boundary (AC-14).
- A `goal` on a nutrient is a soft target optimized by the solver; it does not
  trigger R-14 infeasibility, and it is not widened by
  `nutrient_tolerance_pct`. A `goal` on a nutrient whose value is
  evidence-absent still counts as "tracked" for the drop under AC-4
  (`## Clarifications` C-4).
- Multiple causes apply to the same recipe. The recipe is dropped; the
  top-level cause follows the precedence `present-evidence-excludes` →
  `evidence-absent` → `unmapped`; all applicable causes are retained at the
  recipe level.
- The request supplies no nutrient constraints and no goals. No recipe is
  dropped for nutrition evidence-absence; feasibility depends on whether enough
  recipes exist to fill the horizon.
- The constraint solver is unavailable at runtime. The request fails with an
  explicit error; no degraded fallback is returned.
- A candidate recipe has a requirement that maps to no food concept. The
  recipe is dropped with the `unmapped` cause; if that drop is the cause of
  infeasibility, the named binding constraint identifies the unmapped
  requirement.
- A recipe is passed to the solver with the same servings value the request
  supplies; recipe quantities are scaled by that value.

## Non-goals

- Re-deriving or restating the per-ingredient cost and nutrient *values*;
  those are p2-002's output, which this feature consumes.
- Evaluating cost or budget constraints. Budget is out of scope for this
  feature; the calculator's `MISSING_PACKAGE_DATA` signal does not trigger a
  drop or an infeasibility response here. Cost-based constraint evaluation is
  deferred to a later budget feature, and R-8/R-10 are amended accordingly
  (`## Clarifications` C-1).
- Implementing the per-constraint candidate evaluation (allergen, dietary,
  nutrient, freshness, unit-basis); p2-001 owns that, and p2-003 consumes its
  outcomes.
- Producing the final user-facing explanation text or response contract;
  p3-002 owns the explainable response contract. p2-003 provides the reasoning
  structure p3 consumes.
- Designing a new storage schema, request/response file layout, solver module
  structure, or internal data types.
- Refreshing, crawling, or guaranteeing live retail inventory or promotional
  prices.
- Providing medical, clinical, or individualized dietary advice.
- Changing the solver *shape* (the constraint-solver approach fixed by R-3);
  any such change requires a constitutional amendment.

## Interfaces & dependencies

- **Input contract:** the existing plan request supplies `horizon_days`,
  `meals_per_day`, `servings`, the optional constraint lists (allergies,
  dietary, nutrients), and the new optional `nutrient_tolerance_pct: int`
  field (closed interval `[0, 25]`, default `0`; out-of-range requests rejected
  at the request-validation boundary). Budget and cost are out of scope.
- **Recipe quantity source:** recipe ingredient quantities come from the
  canonical graph's `REQUIRES` edges; p2-003 uses the request's `servings`
  value to scale recipe quantities, matching p2-002's scaling contract.
- **Upstream dependencies:**
  - **p2-001-constraint-evidence-filtering** supplies the per-constraint
    candidate outcomes (retained / warned / present-evidence-excludes /
    evidence-absent) with their precedence, and the unmapped-requirement
    tracking that p2-003 consumes.
  - **p2-002-cost-nutrition-calculation** supplies the portion nutrient result
    contract and the item-level `PARTIAL_NUTRITION_DATA` signal (naming the
    missing canonical nutrients) that is p2-003's recipe-level drop trigger.
    The calculator's `MISSING_PACKAGE_DATA` signal is not consumed by this
    feature.
  - **Integration mechanism (Q7):** `PlanService.generate` invokes a public
    method on the calculator's service boundary — **`inspect_candidates`**
    (new, added as part of p2-003's scope) — during the candidate-recipe
    filtering phase. The method accepts a bulk set of candidate recipes (each
    with ingredient quantities in grams and the request's servings value) and
    returns per-recipe, per-nutrient item-level signals
    (`PARTIAL_NUTRITION_DATA` with the missing nutrient names, or a
    no-signal result). The returned signals are evaluated and recorded in the
    p2-003 trace before the solver runs. The invocation goes through the
    calculator's public service interface, not its internals (R-2).
- **Trace boundary:** p2-003 produces a **plan-level trace separate from
  p2-002's `CalculationTrace`.** The plan-level trace records the per-recipe
  drop outcome and cause, references the calculator's per-nutrient signal
  (without embedding the calculator's trace), the plan-level feasibility
  outcome, and the applied tolerance. The user-facing payload excludes
  audit-only provenance (R-16); the trace carries it. The exact shape of the
  trace and the reasoning structure is the plan stage's to design; the
  contract is that a plan-level trace exists, is separate from p2-002's, and
  carries the reasoning the p3 layers consume.
- **Output contract:** the plan result exposes a feasibility outcome (plan or
  named-binding-constraint failure), the selected recipes per slot, the
  applied nutrient-tolerance relaxation and relaxed label when applicable, and
  the three-level reasoning structure (plan / recipe / constraint). The
  user-facing payload excludes audit-only provenance (R-16).
- **Downstream dependency:** p3-001 and p3-002 consume p2-003's feasibility
  result and three-level reasoning structure to deliver and explain the
  recommendation without re-deriving the reasoning.
- **Runtime/data dependency:** real canonical marts remain subject to the
  tracked `data-prep-price-path` finding
  (`docs/findings/data-prep-price-path.md`); until it resolves, conformance
  evidence may use approved fixtures, per the p2 phase posture.

## Open questions

None blocking. All Q1..Q7 resolved and recorded under `## Clarifications` as
C-1..C-7.

## Clarifications

- **C-1 (Q6 + blocker 1) — Cost and budget are out of scope; R-8/R-10
  amended.** Budget and cost are out of scope for p2-003. The calculator's
  `MISSING_PACKAGE_DATA` signal does not trigger a recipe-level drop here.
  R-8/R-10 are amended so that the calculator's item-level signal is the sole
  cost enforcement point in p2; the recipe-level cost drop is deferred to a
  later budget feature. (2026-10-08, human.) **Consequential — flag for
  `decisions.md` at close. Requires constitution amendment A-006 (or next in
  sequence) drafting.**
- **C-2 (Q4 + blocker 2) — Nutrient-bound widening is the only permitted
  relaxation.** `nutrient_tolerance_pct` is an integer in the closed interval
  `[0, 25]`, default `0`. Applied to nutrient `min` and `max` bounds
  one-sidedly: `min' = min × (1 − p/100)`, `max' = max × (1 + p/100)`; percent
  widening of zero stays zero. Goals are not widened. Structural relaxations
  (additional recipe repeats, dropping the no-consecutive rule) are prohibited.
  When widening is insufficient, the response is a hard infeasibility failure
  naming the binding nutrient constraint(s). Out-of-range values are rejected
  at the request-validation boundary. Cost is excluded. (2026-10-08, human.)
  **Consequential — flag for `decisions.md` at close. Requires constitution
  amendment A-005 (or next in sequence) drafting, naming the permitted
  relaxation set.**
- **C-3 (Q2 + blocker 1) — Per-nutrient drop is globally excluding with
  constraint-scoped reporting.** If a candidate recipe is evidence-absent for
  a tracked nutrient, the recipe is globally excluded from the plan pool for
  that execution. The exclusion is categorized under the affected nutrient's
  constraint in the reasoning record, and the record names which nutrient
  triggered the drop. If the request does not track that nutrient, the recipe
  remains fully eligible (AC-5). (2026-10-08, human.) **Consequential — flag
  for `decisions.md` at close.**
- **C-4 (Q1 + blocker 4) — "Tracked" includes goals.** A nutrient is tracked
  when the request supplies a `limit` (`min`/`max`) **or** a `goal` for it. A
  goal on an evidence-absent nutrient triggers the AC-4 drop, because the
  solver would otherwise optimize toward an unknown value. (2026-10-08,
  human.) **Consequential — flag for `decisions.md` at close.**
- **C-5 (Q3 + should-fix) — `unmapped` is a top-level cause.** `unmapped` is
  its own top-level drop cause, distinct from `evidence-absent` and from
  `present-evidence-excludes`. Precedence when multiple apply:
  `present-evidence-excludes` → `evidence-absent` → `unmapped`. All applicable
  causes remain in the recipe-level record. (2026-10-08, human.)
  **Consequential — flag for `decisions.md` at close.**
- **C-6 (Q5 + should-fix) — Solver unavailable = hard failure.** If the
  constraint solver is unavailable at runtime, the request fails with an
  explicit error; no `200 OK` plan response, no partial result, no degraded
  fallback, and no trace record claiming feasibility. (2026-10-08, human.)
  **Consequential — flag for `decisions.md` at close.**
- **C-7 (Q7 + blocker 3) — Integration is in scope; new public service method
  `inspect_candidates`.** `PlanService.generate` invokes a new public method on
  the calculator's service boundary — `inspect_candidates` — during candidate
  filtering. The method accepts a bulk set of candidate recipes (with
  ingredient quantities and the request's servings value) and returns
  per-recipe, per-nutrient item-level signals. The method is added as part of
  p2-003's scope, using p2-002's existing internal pieces. Wiring the
  cross-service integration is in scope for this feature. (2026-10-08, human.)
  **Consequential — flag for `decisions.md` at close.**
- **Note (C-2 confirmation):** `nutrient_tolerance_pct` is a single global
  percentage applied uniformly to all tracked nutrient bounds in the request.
  Per-nutrient overrides are out of scope for the MVP. (2026-10-08, human.)
- **Note (trace boundary):** p2-003's trace is separate from p2-002's
  `CalculationTrace`. The plan-level trace references the calculator's
  per-ingredient signals but does not embed the calculator's trace.
  (2026-10-08, human.)
- **Note (default tolerance):** `nutrient_tolerance_pct` defaults to `0`
  (strict). A user who wants relaxation must set the field explicitly. A plan
  produced under any non-zero tolerance is labeled as relaxed in the response
  (AC-9). (2026-10-08, human.)
