# Decisions - Feasible meal-plan solving

## Decisions

### F-1 — Per-recipe unmapped facts come from the plan repository
- Date: 2026-10-09
- Decision: `PlanRepository.fetch_candidates` records each `REQUIRES` edge
  whose food concept or best fulfillment is missing as a per-recipe
  `RequirementRef`. `PlanService` reports the recipe as dropped with cause
  `unmapped`, retaining the requirement name for binding-constraint reporting.
- Affects: AC-13, R-17, the plan repository/service boundary.
- Source: Plan revision notes BD-2; plan Design §4.

### F-2 — AC-2 names individually binding constraints
- Date: 2026-10-09
- Decision: A hard infeasibility reports a deterministic set of constraints
  whose individual drop-out admits a plan. Constraint probes run in request
  order. The empty eligible pool is distinguished from a non-empty pool with
  no assignment by `no-recipes-survived` and `no-assignment` respectively.
- Affects: AC-2, AC-2b, AC-12, R-14.
- Source: Spec AC-2 revision; Amendment A-005; plan Design §2.

### F-3 — Goals track nutrition evidence; infeasibility reports a reason
- Date: 2026-10-09
- Decision: A nutrient is tracked when the request supplies either a limit or
  a goal. Missing evidence for either target drops the recipe for that nutrient.
  Hard infeasibility distinguishes an empty pool from an unsatisfied assignment.
- Affects: AC-4c, AC-5, AC-2b, R-9, R-14.
- Source: Spec Clarifications C-4; plan Design §§2–3.

### F-4 — `servings` remains on the calculator inspection contract
- Date: 2026-10-09
- Decision: `inspect_candidates(recipes, servings)` accepts the request's
  servings for interface symmetry. The method receives nutrient profiles and
  already-scaled requirement quantities; missingness itself is independent of
  servings.
- Affects: calculator/plan service interface, AC-4, AC-5.
- Source: Plan review F-4; Spec Clarification C-7.

### F-5 — `partial` means nutrient widening was applied
- Date: 2026-10-09
- Decision: A plan is `partial` exactly when the strict nutrient bounds were
  infeasible and the requested nutrient-bound widening produced a plan. The
  response also reports `relaxed` and `applied_tolerance_pct`. Structural
  relaxation no longer contributes to `partial`.
- Affects: AC-9, AC-14b, response compatibility, R-14.
- Source: Plan review F-5; Amendment A-005; Spec Clarification C-2.

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
