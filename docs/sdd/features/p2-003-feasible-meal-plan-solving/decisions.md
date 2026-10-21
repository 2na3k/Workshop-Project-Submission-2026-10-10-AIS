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

### D-6 — `generate` returns `(PlanResponse, PlanTrace)`; response carries the three-level reasoning

- Date: 2026-10-15
- Status: adopted (reopen; prerequisite for p3-001)
- Context: p3-001's workflow adapter needs both the plan result and the
  three-level recipe/constraint reasoning. Before the reopen, `generate`
  returned only `PlanResponse`, and `recipe_outcomes`/`constraint_outcomes`
  were commented out on `PlanResponse` — the reasoning lived only in
  `PlanTrace`, reachable via the stateful `self.last_trace` side effect.
- Decision: `PlanService.generate` returns `tuple[PlanResponse, PlanTrace]`,
  matching `CostNutritionService.calculate`'s
  `tuple[CostNutritionResponse, CalculationTrace]` pattern. `PlanResponse`
  re-enables `recipe_outcomes` and `constraint_outcomes`. The router unpacks
  the tuple and serializes only the response; the trace is not exposed by the
  router (its exposure is p3-002's / p3-004's).
- Alternatives: keep the side-effect-only trace and have the adapter read
  `service.last_trace` (rejected: stateful, non-reentrant, fragile); a shared
  contract package (rejected: reopens p2-003 more than necessary).
- Affects: `plan/service.py`, `plan/schemas.py`, `plan/router.py`,
  `plan/tests/features/plan/`; the p3-001 workflow adapter (its
  workflow-owned port returns the tuple).
- Source: p3-001's spec C-7; the plan's Prerequisite P-1.

### D-7 — `ConstraintOutcomeResponse` carries `requirement_id`

- Date: 2026-10-16
- Status: adopted (reopen; prerequisite for p3-001's T-13)
- Context: p3-001's workflow adapter maps `RequirementOutcome` to a
  workflow-owned `RequirementOutcomeView` and requires the per-requirement
  identity (`requirement_id`, the `REQUIRES` edge's `occurrence_id`). The
  internal `RequirementOutcome` carries `requirement_id`, but the API-facing
  `ConstraintOutcomeResponse` DTO does not project it. The adapter cannot map
  the field losslessly without an API contract change.
- Decision: `ConstraintOutcomeResponse` gains
  `requirement_id: str | None = None`. `PlanService.generate` populates it
  from `RequirementOutcome.requirement_id` when building the response DTO.
  p2-003's response tests assert the field is present and populated for a
  representative plan.
- Alternatives: drop `requirement_id` from the workflow contract (rejected:
  weakens R-17's per-requirement identity and AC-11's check, and requires a
  spec amendment); use `requirement_text` as the identity (rejected: text is
  not guaranteed unique within a recipe and may be null).
- Affects: `plan/schemas.py`, `plan/service.py`, `plan/tests/features/plan/`;
  p3-001's workflow adapter (its `RequirementOutcomeView` mapping).
- Source: p3-001's plan BD-1 (2026-10-16); the adapter's AC-16 contract test.

### D-8 — `generate` returns infeasible as a response, not an exception

- Date: 2026-10-16
- Status: adopted (reopen; prerequisite for p3-001's infeasible-outcome path)
- Context: p3-001's workflow Plan node delegates to `PlanService.generate`
  through a workflow-owned port and reads `result.feasibility_outcome` to
  classify the outcome. Before the reopen, `generate` raised `PlanInfeasible`
  on infeasibility and stored the trace on `self.last_trace`. The workflow
  cannot read `last_trace` (the plan rules it out as a stateful side
  channel), so the real plan path could not produce an `infeasible` outcome
  with its reasoning trace. AC-6 and AC-15 were unsatisfiable through the
  workflow.
- Decision: `PlanService.generate` returns `(PlanResponse, PlanTrace)` on
  both feasible and infeasible outcomes; it never raises `PlanInfeasible`.
  `PlanResponse.feasibility_outcome`'s `Literal` is widened to
  `["plan-produced", "infeasible"]`. The infeasible response carries
  `binding_constraints`, `recipe_outcomes`, and `constraint_outcomes`; the
  trace carries the full reasoning. `solver_v2` still raises `PlanInfeasible`
  internally; the service catches it. `generate_v2` is updated consistently
  (with its existing commented-out response fields kept commented).
- Alternatives: have the workflow read `self.last_trace` after catching
  `PlanInfeasible` (rejected: stateful, non-reentrant, and the p3-001 plan
  forbids it); revise the p3-001 spec to drop the three-level reasoning from
  infeasible outcomes (rejected: R-17 requires three levels for feasible and
  infeasible outcomes; the spec amendment would be larger than the reopen).
- Affects: `plan/schemas.py` (Literal), `plan/service.py` (both catch sites
  return), the p2-003 response tests (new infeasible-return assertion), the
  p3-001 workflow Plan node (no change — it already branches on
  `feasibility_outcome`).
- Source: p3-001's plan BD-3 (2026-10-16); the workflow adapter's
  infeasible-outcome path.

### D-9 — `RequirementOutcome` carries the offer's provenance fields

- Date: 2026-10-17
- Status: adopted (reopen; resolves F-P3-1's middle half)
- Context: p3-002's trace-side R-16 conformance check requires the trace to
  carry `confidence`, `source_snapshot_id`, and `mapping_version`. p2-002's
  `OfferRef` now carries them, but `RequirementOutcome` (the trace record)
  did not project them — the trace could only reach them through
  `selected_offer.confidence` etc., which is awkward for the workflow's
  view model and the p3-002 mapper.
- Decision: `RequirementOutcome` gains `confidence: float | None = None`,
  `source_snapshot_id: str | None = None`,
  `mapping_version: str | None = None`. `PlanService.generate` populates
  them from the offer when the requirement is selected.
- Alternatives: reach through `selected_offer` in the workflow view and the
  p3-002 mapper (rejected: inconsistent flat/nested access; the workflow's
  `RequirementOutcomeView` would need a nested view model).
- Affects: `plan/models.py` (`RequirementOutcome`), `plan/service.py` (the
  selected-requirement construction). Response DTO
  (`ConstraintOutcomeResponse`) unchanged — R-16 keeps provenance trace-side.
- Source: p3-002 F-P3-1 resolution; p3-001's plan Revision notes.

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
