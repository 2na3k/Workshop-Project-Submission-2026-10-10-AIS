# Decisions - Feasible meal-plan solving

## Decisions

### D-1 Per-recipe unmapped facts come from the plan repository
- Date: 2026-10-09
- Context: When food concepts or fulfillments are missing from the graph, candidate recipes cannot be fulfilled. AC-13 and R-17 require reporting drops with cause `unmapped` distinct from evidence-absent drops and preserving the requirement for binding-constraint identification.
- Decision: `PlanRepository.fetch_candidates` records each `REQUIRES` edge whose food concept or best fulfillment is missing as a per-recipe `RequirementRef`. `PlanService` reports the recipe as dropped with cause `unmapped`, retaining the requirement name for binding-constraint reporting.
- Alternatives: Synthesize fake offers with sentinel values (rejected: pollutes offer domain); report as evidence-absent (rejected: conflates missing graph mappings with missing nutritional evidence per R-5 and R-17).
- Affects: AC-13, R-17, the plan repository/service boundary.
- Source: Plan revision notes BD-2; plan Design §4; Task T-8.

### D-2 Binding constraints and reason discriminator on hard infeasibility
- Date: 2026-10-09
- Context: When a meal plan is infeasible, callers need to know which constraints caused the infeasibility. R-14 requires identifying the individually-binding constraints deterministically, and AC-2b requires distinguishing an empty candidate pool from an assignment failure.
- Decision: A hard infeasibility reports a deterministic set of constraints whose individual drop-out admits a plan. Constraint drop-out probes run in deterministic request order (`random_seed=0`, `num_search_workers=1`). The empty eligible pool is distinguished from a non-empty pool with no assignment by reason discriminator `no-recipes-survived` and `no-assignment` respectively.
- Alternatives: Report all failed constraints simultaneously (rejected: some constraints fail only in conjunction with others); run randomized constraint subsets (rejected: violates R-14 determinism); omit solver probing on infeasibility (rejected: fails AC-2 and AC-2b).
- Affects: AC-2, AC-2b, AC-12, R-14, solver and service layer.
- Source: Spec AC-2 revision; Amendment A-005; plan Design §2; Tasks T-4, T-5.

### D-3 Goals track nutrition evidence and trigger evidence-absent drops
- Date: 2026-10-09
- Context: Nutritional targets in requests can be specified as limits or goals. When nutrition data is missing, we must ensure recipes lacking data for tracked goals are not erroneously admitted.
- Decision: A nutrient is tracked when the request supplies either a limit (`min`/`max`) or a goal. Missing evidence for either target drops the recipe for that nutrient under AC-4.
- Alternatives: Only track nutrients with hard upper/lower bounds (rejected: admits recipes with unknown nutrient values against user goals, violating R-9); treat missing goal nutrients as zero (rejected: explicitly forbidden by R-5).
- Affects: AC-4c, AC-5, AC-2b, R-9, R-14.
- Source: Spec Clarifications C-4; plan Design §§2–3; Task T-10.

### D-4 Calculator candidate inspection interface symmetry and offer return
- Date: 2026-10-09
- Context: `CostNutritionService.inspect_candidates(recipes, servings)` was added for the plan service to inspect missing nutrients and retrieve selected package offers. Missingness of nutrients is independent of serving scale, but recipe ingredient scaling relies on servings.
- Decision: `inspect_candidates(recipes, servings)` accepts the request's servings parameter for interface symmetry. The method receives nutrient profiles and already-scaled requirement quantities, returning per-recipe `missing_nutrients` and per-requirement `selected_offer` for AC-8c's constraint-level record.
- Alternatives: Exclude servings from `inspect_candidates` (rejected: requires callers to scale quantities externally and breaks symmetry with other calculator service methods); let plan query repository directly (rejected: violates R-2 modularity by bypassing calculator service).
- Affects: AC-4, AC-5, AC-8c, calculator/plan service interface.
- Source: Plan review F-4; Spec Clarification C-7; Tasks T-6, T-7.

### D-5 Nutrient tolerance as sole solver relaxation and partial semantics
- Date: 2026-10-09
- Context: Legacy implementations allowed structural relaxations and round-robin fallbacks to mark plans as partial. Amendment A-005 and R-14 restrict solver relaxation strictly to uniform nutrient bound widening [0, 25]%.
- Decision: A plan is `partial` (and `relaxed: true`) exactly when strict nutrient bounds are infeasible and the requested nutrient tolerance [0, 25]% admits a feasible plan, recording `applied_tolerance_pct`. Structural relaxations and degraded fallbacks are removed.
- Alternatives: Retain structural relaxations (drop days, repeat meals) (rejected: forbidden by Amendment A-005 and R-14); widen goals or budget (rejected: violates R-14 permitted relaxation set).
- Affects: AC-9, AC-10, AC-14b, response compatibility, R-14.
- Source: Plan review F-5; Amendment A-005; Spec Clarification C-2; Tasks T-2, T-3.

## Consequential clarifications

- **C-1 — Cost and budget remain non-gating in p2-003.** The plan does not
  consume `MISSING_PACKAGE_DATA`; a missing offer does not drop a recipe.
  Recipe-level cost enforcement is deferred to p3-004. **A-006** amends R-8
  and R-10 to establish this boundary.
- **C-2 — Nutrient tolerance is the sole solver relaxation.** The strict solve
  runs first; only nutrient min/max bounds widen, uniformly by an integer
  percentage from 0 through 25. Goals and structural constraints are unchanged.
  **A-005** names the permitted relaxation set and prohibits structural
  relaxations.
- **C-3 — Incomplete tracked nutrition excludes the recipe.** A missing value
  for any tracked nutrient excludes the recipe globally for that execution and
  is categorized under the triggering nutrient constraint.
- **C-4 — Goals count as tracked nutrients.** A goal without a bound still
  triggers an evidence-absent drop when its nutrient is missing.
- **C-5 — Drop-cause precedence is deterministic.** The primary cause order is
  `present-evidence-excludes`, `evidence-absent`, then `unmapped`; the record
  retains all applicable causes.
- **C-6 — Solver unavailability is a hard failure.** No fallback plan or trace
  claiming feasibility is returned when OR-Tools is unavailable.
- **C-7 — Calculator inspection is a public integration point.** The plan calls
  the calculator service's `inspect_candidates` method. It consumes canonical
  nutrient signals and per-requirement selected offers; missing offers remain
  non-gating under C-1.

## Offer and provenance boundary

`inspect_candidates` selects an offer for each requirement using the
calculator's existing package-ranking and eligibility rules. The user-facing
constraint outcome contains only the resolved concept, listing name, retailer,
and warned conditions. `food_key` remains in `PlanTrace`; confidence,
normalization versions, and source identifiers remain out of the user payload.
The per-requirement offer extension is additive to the spec's Q7 paragraph and
does not contradict an acceptance criterion. Record this one-line sync at the
next spec touch: “and the per-requirement selected offer for the
constraint-level record.”

## Overrides

None.

## Verification deferral

The real-mart demonstration remains deferred under
`docs/findings/data-prep-price-path.md`, which records the data-preparation dbt
parse failure. p2-003's repository and plan/calculator integration coverage
uses fake Neo4j drivers and fixture rows; this does not claim real-mart
conformance.
