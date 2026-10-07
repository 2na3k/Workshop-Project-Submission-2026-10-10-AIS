---
feature: p2-002-cost-nutrition-calculation
---

# Spec - Cost and nutrition calculation

## Summary

This feature makes the existing calculation capability provable against the
cost-and-nutrition contracts needed by the p2 reasoning core. For each resolved
recipe ingredient, the calculation reports nutrient contribution for the
requested quantity and serving count, and reports the cost of the consumed
quantity separately from the whole retail package purchase cost. Cost is
reported only when the ingredient's resolved key has at least one cost-eligible
package; eligibility is determined by the package's declared price evidence
and its freshness status. When multiple nutrition sources disagree, a single
deterministic precedence — the same ordering key the graph uses to derive
`BEST_FULFILLMENT` — selects the same value for the same inputs on every run.
Package selection for cost accepts any eligible package, including confidence
0, and ranks by lowest unit price with confidence as a later tie-break; there
is no confidence threshold. An ingredient with no eligible package stays in
the result with absent cost fields and a `MISSING_PACKAGE_DATA` warning, and
the summary cost totals are absent. Audit-only provenance (confidence, source
identity, mapping version) is retained in an internal execution trace and
never appears in the user-facing response.

The feature is a prove-and-fix change against pre-existing calculator behavior.
It does not broaden the user-facing response with audit-only provenance.

## Traces to

- **G-1** — Users receive meal recommendations evaluated against explicit
  nutrition ranges and daily budget limits; the calculation supplies the
  nutrient and cost values used for that evaluation.
- **G-3** — Meal cost calculations clearly distinguish whole-package retail
  purchase prices from the actual cost of consumed recipe ingredients.
- **Roadmap phase p2 → p2-002-cost-nutrition-calculation** *(partial)* —
  "Existing nutrient computation. Remaining work: verify separate cost fields
  (R-11); verify deterministic conflict precedence across runs (R-12); verify
  the no-floor selection with confidence recorded in the execution trace
  (R-13); verify cost eligibility (R-10)."
- **Phase p2 outcome** — The reasoning core evaluates explicit nutrition, unit,
  and budget constraints conservatively, computes distinct consumed and package
  costs, and returns a feasible meal plan only when the requested horizon can
  be satisfied.
- **Roadmap shared contract** — "Portion nutrient and consumed/package cost
  result contract; item-level evidence-absent signals (`MISSING_PACKAGE_DATA`,
  `PARTIAL_NUTRITION_DATA`) consumed by p2-003 as the recipe-level drop trigger
  (per-nutrient for partial nutrition)," shared with
  p2-001-constraint-evidence-filtering and p2-003-feasible-meal-plan-solving.
- **Constitutional rules:**
  - **R-1** (single schema, no dual support) — the calculator reads only the
    canonical `Food`/`FULFILLS` property names declared in the deployed graph
    design; the `confidence`/`mapping_confidence` naming drift is resolved in
    favour of the deployed `confidence`.
  - **R-2** (inward dependency direction) — the calculator does not import
    `api.features.plan` internals.
  - **R-5** (absent evidence drops, never includes) — the calculator reports
    absence at the item level; a non-evaluable nutrient's totals are null, not
    partial sums; the recipe-level drop is p2-003's.
  - **R-8** (non-fresh price offers are unavailable, per amended A-002) —
    freshness is enforced at every layer that consumes the offer. The
    calculator checks `freshness_status == "fresh"` on each candidate package
    and excludes non-fresh packages from cost selection; p2-001 also filters at
    its layer, so a non-fresh offer cannot reach cost output by any path.
  - **R-9** (nutrient constraints require a profile, per amended A-003) — a
    candidate with no nutrition profile contributes no value and is never
    treated as zero; the calculator emits `PARTIAL_NUTRITION_DATA`. A nutrient
    constraint is evaluable only when every contributing ingredient carries a
    non-null value for that nutrient; the recipe-level drop is p2-003's,
    applied per nutrient.
  - **R-10** (cost eligibility requires a convertible price basis, per amended
    A-004) — eligibility uses the package's declared `price_status`,
    `price_match_status`, `price_basis`, and a present, positive package
    amount; `cost_basis_compatible` is not the gate.
  - **R-11** (consumed cost is distinct from retail package price).
  - **R-12** (deterministic nutrient conflict precedence).
  - **R-13** (selection by best score, no confidence floor; confidence on the
    closed interval [0, 1] recorded in the execution trace). "Best score" is
    the AC-11 ordering (lowest unit price, then lowest retail package cost,
    then highest confidence, then lexicographic identity); there is no
    separate score field. Applies to package selection; the resolver's
    ambiguity margin is a separate mechanism (`## Clarifications` C-3).
  - **R-16** (user response excludes audit-only provenance).

## User-facing behavior

- A successful calculation returns nutrient values for each ingredient's
  consumed quantity, recipe-level nutrient totals, and nutrient totals divided
  by the requested number of servings. Missing values remain unknown rather
  than being represented as zero.
- A nutrient's recipe total and per-serving total are **null** when that
  nutrient is non-evaluable — that is, when any contributing ingredient lacks
  a non-null value for it. The partial sum is not exposed. This is the R-5
  posture: absent evidence must never be presented as a complete (or
  undercounted) value.
- A successful calculation exposes the consumed-ingredient cost and the
  whole-package retail purchase cost as separate values, both per ingredient
  and in the summary. The consumed cost reflects only the quantity used; the
  package cost reflects the package or packages that must be purchased.
- An ingredient with no cost-eligible package stays in the itemized result
  with no consumed cost, no retail package cost, and a `MISSING_PACKAGE_DATA`
  warning; the summary cost totals are absent; the response still succeeds. An
  ingredient with some canonical nutrients missing carries a
  `PARTIAL_NUTRITION_DATA` warning that names which of the nine canonical
  nutrients are missing. These warnings are the calculator's evidence-absent
  signals at the item level; recipe-level dropping is done by p2-003, not by
  this response. For `PARTIAL_NUTRITION_DATA`, p2-003 applies the drop per
  nutrient: a nutrient constraint is evaluable only when every contributing
  ingredient carries a non-null value for that nutrient. The warning's
  nutrient list and the item's null fields both carry the information p2-003
  needs to identify the affected nutrients.
- When conflicting nutrition evidence is available across the accepted
  candidates of one food concept, a single deterministic precedence selects
  the same value for the same inputs on every run. Branded product evidence
  (`source_kind == "crawler_fdc_profile"`) takes precedence over generic USDA
  evidence (`source_kind == "fooddata_central"`). Any other or absent source
  kind is treated as generic. Among same-source candidates, the candidate with
  the smallest `(nutrition_rank, selection_priority, food_key)` tuple wins,
  with missing ranks and priorities sorting last. This uses the same ordering
  key the graph uses to derive `BEST_FULFILLMENT`; the calculator applies it
  **per nutrient**, over the accepted subset that carries a non-null value for
  that nutrient. The winner per nutrient is recorded in the trace. The
  calculator may mix sources within one ingredient: calories may come from one
  Food and sodium from another.
- Only candidates whose `approval_status` is `accepted` are usable for
  nutrient or cost selection. A candidate with any other approval status is
  excluded from both. A food concept whose candidate set has no accepted edges
  is treated as unresolvable.
- A cost package is selectable whenever an eligible package record exists,
  including confidence 0. There is no minimum confidence threshold. The
  resolver first picks the canonical food key for the ingredient (rejecting the
  name as ambiguous if the top two string-score candidates are too close to
  call); package selection then ranks that key's eligible packages by lowest
  unit price (price per package mass; for a `package_volume` package the
  per-gram price is computed from the converted gram amount, so the ranking
  compares like with like), then lowest retail package cost, then highest
  confidence, then lexicographic identity (`food_key`, `retailer`,
  `listing_name`). This ordering is R-13's "best score"; there is no separate
  score field. The selected package's confidence and the resolver's
  chosen-candidate confidence are retained in the execution trace and not
  exposed in the user-facing response. A cheaper mislinked package outranks a
  more expensive correctly-linked one; this is the intended behavior of a
  no-floor price-ranked selection.
- A cost package is eligible when its `FULFILLS` edge declares all of:
  - `price_status == "estimated"`,
  - `price_match_status == "accepted"`,
  - `freshness_status == "fresh"`,
  - `price_basis` in a cost-convertible set (`package_mass` or
    `package_volume`),
  - `currency == "SGD"`,
  - `reference_price_minor` present and positive, and
  - a present, positive package amount: `package_mass_g` for `package_mass`,
    or `package_volume_ml` for `package_volume`.

  A `price_basis` of `package_volume` is converted to grams using the domain
  units converter; the conversion is silent (uses an assumed density; no
  user-visible warning). A `price_basis` of `package_unresolved`,
  `span_reference`, `nutrition_only`, or any other value is not eligible.
  `cost_basis_compatible` is **not** part of the eligibility rule. Freshness
  is checked by the calculator on every candidate package, independent of
  p2-001's filter. See `## Clarifications` C-1 and C-4.
- Unit conversion for **nutrient** calculation using a non-mass assumption
  produces an explicit `UNIT_ASSUMED_GRAMS` warning so the user can distinguish
  an estimated nutrient amount from an exact mass conversion. The
  `package_volume` conversion used for **cost** is silent, as above; the
  `UNIT_ASSUMED_GRAMS` warning does not apply to cost.

## Acceptance criteria

- **AC-1** Given an ingredient with a validated nutrient profile per 100 grams,
  a positive consumed quantity, and a requested serving count, when calculation
  runs, then each available nutrient is scaled by consumed grams divided by
  100, the ingredient nutrient contribution is included in the recipe total,
  and the per-serving nutrient total is the recipe total divided by the
  requested serving count.

- **AC-2** Given a recipe with multiple ingredients and nutrient values that are
  missing for some tracked nutrients, when calculation runs, then for each of
  the nine canonical nutrients the recipe total and the per-serving total are
  computed only when **every** contributing ingredient carries a non-null
  value for that nutrient. A nutrient that is missing from any contributing
  ingredient has both its recipe total and its per-serving total set to
  `null` in the response — the partial sum is not exposed — and the item
  carries a `PARTIAL_NUTRITION_DATA` warning that names the affected
  nutrients. No missing value is treated as zero. The recipe-level consequence
  of a null nutrient total is p2-003's: the affected nutrient's constraint is
  evidence-absent for the recipe and the recipe is dropped for that constraint
  only.

- **AC-3** Given an eligible package with package price P, package amount S,
  and a consumed quantity Q where 0 < Q < S, when cost calculation runs, then
  the result exposes the consumed-ingredient cost equal to P × (Q / S) and the
  retail package purchase cost equal to P, as separate fields with distinct
  values.

- **AC-4** Given a consumed quantity requiring more than one package of an
  eligible package, when cost calculation runs, then the consumed cost is
  based on the quantity used while the retail purchase cost is based on the
  number of whole packages required (`ceil(Q / S) × P`), and neither value is
  substituted for the other in the item result or summary.

- **AC-5** Given a candidate package whose `FULFILLS` edge does not satisfy the
  eligibility rule (`price_status != "estimated"`, or
  `price_match_status != "accepted"`, or `freshness_status != "fresh"`, or
  `price_basis` not in `{package_mass, package_volume}`, or
  `currency != "SGD"`, or `reference_price_minor` missing/non-positive, or the
  package amount for the basis missing/non-positive), when cost eligibility is
  evaluated, then the package is excluded from cost calculation; and given
  that no eligible package remains for the ingredient, then the ingredient
  remains in the itemized result with absent consumed and retail package cost,
  carries a `MISSING_PACKAGE_DATA` warning, the summary consumed and retail
  totals are absent, and the response status remains success; no cost is
  inferred.

- **AC-6** Given generic USDA nutrition evidence and conflicting branded product
  nutrition evidence for the same nutrient among the accepted candidates, when
  the nutrient value is selected, then the branded product value is used
  consistently in the calculation; given only generic values with no
  conflicting branded value, then the generic value is used. A candidate whose
  `source_kind` is neither `crawler_fdc_profile` nor `fooddata_central` is
  treated as generic.

- **AC-7** Given two accepted candidates of the same source kind with
  conflicting non-null values for the same nutrient, when the nutrient value is
  selected, then the candidate with the smaller `nutrition_rank` wins; on equal
  `nutrition_rank`, the candidate with the smaller `selection_priority` wins;
  on equal `selection_priority`, the candidate with the lexicographically
  smaller `food_key` wins; a missing `nutrition_rank` or `selection_priority`
  sorts last. The ordering is applied per nutrient, over the subset of accepted
  candidates that carry a non-null value for that nutrient.

- **AC-8** Given the same conflicting nutrition inputs, when calculation is run
  more than once and the candidate inputs are presented in a different order,
  then the selected nutrient values and resulting totals are identical on
  every run. Selection and summation are functions of the evidence only, not
  of input order.

- **AC-9** Given a food concept whose candidate set contains only edges whose
  `approval_status` is not `accepted`, when calculation runs, then those
  candidates are excluded from both nutrient and cost selection; if no accepted
  candidate remains, the ingredient is treated as unresolvable under AC-16.
  Given a candidate set mixing accepted and non-accepted edges, then only the
  accepted edges participate in nutrient and cost selection.

- **AC-10** Given an ingredient whose canonical food key resolves to exactly
  one eligible package whose confidence is 0, when package selection runs, then
  that package is selected rather than rejected for low confidence, and its
  confidence is recorded in the execution trace.

- **AC-11** Given an ingredient whose canonical food key resolves to multiple
  eligible packages, where one has the lower unit price and another has the
  higher confidence, when package selection runs, then the lower-unit-price
  package is selected; given equal unit price, then lower retail package cost,
  then higher confidence, then lexicographic (`food_key`, `retailer`,
  `listing_name`) order decides; the selected package's confidence and the
  runner-up's identity are recorded in the execution trace. **This ordering is
  R-13's "best score."** The spec does not declare a separate score field;
  R-13's named fixture should be read against this ordering. For a
  `package_volume` package, the per-gram unit price is computed from the
  converted gram amount, so the ranking compares like with like.

- **AC-12** Given package records whose confidence values are 0 and 1, when
  package selection runs, then both values are accepted as valid and neither is
  treated as a rejection.

- **AC-13** Given a package whose `price_basis` is `package_volume`, when cost
  eligibility is evaluated, then the package is eligible (subject to the other
  eligibility conditions) and the consumed cost is computed from the
  volume-to-gram conversion using the domain units converter. The conversion
  is silent (uses an assumed density; no user-visible warning); the price is
  the graph's declared `estimated` value.

- **AC-14** Given a known non-mass unit whose conversion uses an assumed gram
  equivalent, when **nutrient** calculation runs, then the calculated result is
  returned with a user-visible `UNIT_ASSUMED_GRAMS` warning. This warning does
  not apply to the cost path; the `package_volume` conversion used for cost is
  silent (AC-13).

- **AC-15** Given an unsupported unit or a non-positive, non-finite quantity,
  when calculation runs, then the request is rejected with a
  validation/conversion error and no response is assembled. No nutrient or
  cost value is produced for the affected ingredient, and the request fails as
  a whole (matching AC-16, AC-17, AC-19).

- **AC-16** Given a calculation request that cannot resolve an ingredient name
  to any canonical food key, or whose resolved food key has no accepted
  candidate, when calculation runs, then the request is rejected as unresolved
  rather than producing zero nutrients, an inferred cost, or a successful
  result. This is the calculation-layer expression of R-5's "absent evidence
  drops, never includes" at the pre-assembly resolver failure point; AC-5 is
  the same rule at the post-assembly item-level cost-absence point.

- **AC-17** Given an ingredient name whose top two canonical candidates have
  token scores below `0.86`, or whose top-two score gap is below `0.05`, when
  calculation runs, then the resolver rejects the name as ambiguous and the
  request is rejected. This is a resolver string-score mechanism, not a
  confidence threshold; R-13 concerns the `confidence` property on the
  `FULFILLS` edge and does not apply to this margin.

- **AC-18** Given a successful calculation, when the response is serialized,
  then the user-facing payload carries the resolved food concept
  (`canonical_key`), the chosen offer (`listing_name` and `retailer`), the
  per-ingredient nutrients, the distinct cost fields, and any item warnings;
  and it carries no `confidence`, no `food_key`, no `fdc_id`, no
  `listing_key`/`price_ref`, no `source_*`, no `normalization_version` or
  `mapping_version`, no `nutrition_rank` or `selection_priority`, and no
  `approval_status`. Those values are retained in the internal execution trace.
  The trace is not exposed by the current router; its exposure boundary is
  owned by a later feature (p3-001).

- **AC-19** Given a calculation request with zero or negative servings, an
  empty ingredient list, or an ingredient count above the supported request
  limit, when the request is received, then the request is rejected as invalid
  before calculation runs. The supported request limit is the constant
  `MAX_REQUEST_INGREDIENTS` (value to be confirmed by the plan's baseline
  inventory; the spec's requirement is that a single declared constant bounds
  the request).

- **AC-20** Given a package whose `price_status` is not `estimated` (for
  example `unavailable`), or whose `price_match_status` is not `accepted` (for
  example `estimated` or `unmatched`), or whose `currency` is not `SGD`, or
  whose `reference_price_minor` is missing or non-positive, or whose package
  amount for its `price_basis` is missing or non-positive, when cost
  eligibility is evaluated, then the package is excluded from cost
  calculation. These are the same eligibility conditions as AC-5, named
  individually for testability.

## Edge cases & errors

- A nutrient's recipe total and per-serving total are **null** when the
  nutrient is non-evaluable — that is, when any contributing ingredient lacks
  a non-null value for it. The partial sum is never exposed. The item carries
  `PARTIAL_NUTRITION_DATA` naming the affected nutrients. The recipe-level
  consequence is p2-003's per-nutrient drop.
- `PARTIAL_NUTRITION_DATA` is scoped to the nine canonical nutrients
  (`calories_kcal`, `protein_g`, `carbs_g`, `fat_g`, `saturated_fat_g`,
  `fiber_g`, `sugar_g`, `sodium_mg`, `cholesterol_mg`). The deprecated
  `Nutrients` DTO's extra fields (`calcium_mg`, `iron_mg`) have no canonical
  source and are always null; their nullness does not trigger the warning.
- A recipe may use a fractional package quantity or require several whole
  packages. Consumed cost and retail purchase cost must remain distinct in both
  cases. The retail cost uses `ceil(Q / S) × P`. The ceiling is computed with
  exact arithmetic or a small tolerance so a float artefact (for example
  `Q / S = 3.0000000001`) does not add a spurious package. Plan stage names
  the tolerance or the exact-arithmetic approach.
- A package is cost-eligible only when its `FULFILLS` edge declares all of:
  `price_status == "estimated"`, `price_match_status == "accepted"`,
  `freshness_status == "fresh"`, `price_basis` in
  `{package_mass, package_volume}`, `currency == "SGD"`, a present positive
  `reference_price_minor`, and a present positive package amount for the
  basis (`package_mass_g` for `package_mass`; `package_volume_ml` for
  `package_volume`). A `package_volume` price is converted to grams via the
  domain units converter, silently (uses an assumed density; no user-visible
  warning). `package_unresolved`, `span_reference`, `nutrition_only`, and any
  other `price_basis` are ineligible. `cost_basis_compatible` is not part of
  the eligibility rule.
- Freshness is enforced at two layers. p2-001 filters the candidate pool it
  sees by `freshness_status`. The calculator independently checks
  `freshness_status == "fresh"` on every candidate package and excludes
  non-fresh packages from cost selection, so that a non-fresh offer cannot
  reach cost output by any path. The check is a status comparison, not time
  arithmetic; the deployed graph carries no crawl timestamp, and freshness is
  set at load time.
- A resolved canonical key's package set may contain one low-confidence package
  or several packages tied on unit price. No confidence threshold may discard
  the only eligible package; ties resolve through the ranking order in AC-11 so
  repeated runs do not change the result. A cheaper mislinked package
  outranks a more expensive correctly-linked one — this is intended.
- A candidate whose `approval_status` is not `accepted` is not usable for
  nutrient or cost selection, regardless of source. A food concept whose
  candidate set has no accepted edges is treated as unresolved under AC-16.
- Nutrition sources may disagree, may contain missing ranks, or may omit a
  tracked nutrient. The precedence in AC-6/AC-7 applies independently to each
  nutrient, over the accepted subset that carries a value for that nutrient.
  The winner per nutrient is recorded in the trace; the calculator may select
  calories from one Food and sodium from another within the same ingredient.
- Confidence outside the closed interval [0, 1] is not asserted to be rejected
  in this feature. The calculator records confidence as observed and applies no
  interval enforcement.
- A non-mass unit conversion for nutrients is approximate and must be warned
  (`UNIT_ASSUMED_GRAMS`); an unsupported unit, invalid quantity, unresolved
  ingredient, or absent required evidence is an error or evidence-absent
  outcome, not an implicit zero. An invalid unit or quantity rejects the whole
  request (AC-15).
- A request with zero or negative servings, no ingredients, or more ingredients
  than the supported request limit is invalid and must not be calculated.
- User-facing output must not expose mapping confidence, normalization version,
  source identifiers, product identity, or other audit-only provenance; those
  values belong only in the execution trace.

## Numerics

- **Currency:** all SGD values are computed as floats and rounded to two
  decimal places at the response boundary.
- **Nutrients:** nutrient values are computed as floats at full precision
  internally and rounded at the response boundary to the precision declared by
  the domain types.
- **Summary rounding:** the summary totals are the **rounded sum of unrounded
  item values** — items are summed at full precision, and the summary is
  rounded once at the response boundary. The summary is not the sum of the
  rounded item values; that would compound per-item rounding error.
- **Non-evaluable nutrients:** when any contributing ingredient lacks a
  value for a nutrient, that nutrient's recipe total and per-serving total are
  set to `null`. No partial sum is exposed.
- **Whole-package retail cost:** `ceil(Q / S) × P`, where the ceiling is on the
  package count and is computed with exact arithmetic or a small tolerance so
  a float artefact does not add a spurious package.
- **Consumed cost:** `P × (Q / S)`, not rounded until the response boundary.
- **Sum stability:** the recipe totals and per-serving totals are computed in a
  fixed summation order over the ingredient list, so AC-8 holds on floats.
  Repeated runs over the same input produce bit-identical totals.

## Execution trace

The internal `CalculationTrace` is returned beside the response and is not
exposed by the current router. It carries, per ingredient:

- Resolved canonical key, resolver match type, and resolver confidence.
- Per-nutrient winner: `source_kind`, `food_key`, `nutrition_rank`,
  `selection_priority`, and the chosen value.
- Chosen package: `food_key`, `listing_name`, `retailer`, `confidence`,
  `price`, package count, `price_basis`, and `freshness_status`.
- Runner-up package identity and confidence, for auditability of the ranking.
- `freshness_status` and `approval_status` as observed on the input edge.
- Per-item warnings (`PARTIAL_NUTRITION_DATA`, `MISSING_PACKAGE_DATA`,
  `UNIT_ASSUMED_GRAMS`) with ingredient scope; for `PARTIAL_NUTRITION_DATA`,
  the list of missing canonical nutrients.

The trace does not appear in the serialized user response.

## Non-goals

- Solving the complete multi-day meal-plan feasibility problem or evaluating
  the request's `budget`; those belong to p2-003. The `budget` field is not
  part of the calculation request in this feature.
- Implementing allergen or dietary evidence filtering; p2-001 owns those
  constraint evaluations, which this feature consumes.
- Implementing the recipe-level drop; p2-003 owns it. The calculator reports
  item-level absence and p2-003 acts on the signal.
- Refreshing, crawling, or guaranteeing live retail inventory or promotional
  prices.
- Providing medical, clinical, or individualized dietary advice.
- Designing a new storage schema, API file layout, or internal data structure.
- Changing the public nutrient field set; the deprecated `Nutrients` response
  DTO is retained for backward compatibility.
- Enforcing confidence intervals; the calculator records confidence as
  observed and applies no interval check.

## Interfaces & dependencies

- **Input contract:** the existing calculation request supplies servings and
  ingredient names, positive quantities, and supported units. The request does
  not carry `budget`; budget evaluation belongs to p2-003. Ingredient count is
  bounded by the declared request-limit constant `MAX_REQUEST_INGREDIENTS`
  (value confirmed by the plan's baseline inventory).
- **Evidence contract:** candidate resolution supplies normalized food
  candidates, nutrient evidence, package amount and price evidence, and the
  canonical `FULFILLS` properties the eligibility and precedence rules use:
  `confidence`, `price_status`, `price_match_status`, `price_basis`,
  `freshness_status`, `reference_price_minor`, `currency`, `package_mass_g`,
  `package_volume_ml`, `package_count`, `approval_status`, `nutrition_rank`,
  `selection_priority`, `food_key`, `listing_name`, `retailer`, and
  `source_kind` (from `nutrition_source`). There is no `mapping_confidence`;
  the deployed property is `confidence`.
- **Output contract:** the existing calculation response supplies itemized
  nutrient and cost results plus recipe totals and per-serving nutrients. The
  consumed-cost and retail-package-cost values remain distinct. A nutrient's
  recipe total and per-serving total are **null** when the nutrient is
  non-evaluable. The user-facing payload carries the resolved food concept
  (`canonical_key`) and the chosen offer (`listing_name`, `retailer`); it
  excludes audit-only provenance. Audit provenance is retained in an internal
  execution trace returned beside the response. When an ingredient has no
  eligible cost evidence, the item remains in `itemized` with
  `consumed_cost_sgd` and `retail_package_cost_sgd` absent and a
  `MISSING_PACKAGE_DATA` warning; the summary cost totals are absent whenever
  any item lacks cost; `status` remains `"success"`. This is distinct from
  AC-16, where an unresolvable ingredient fails the request before any
  response is assembled.
- **Response DTO:** the public `Nutrients` class is retained for backward
  compatibility. It declares eleven fields; the canonical `Food` node carries
  nine, and the two extras (`calcium_mg`, `iron_mg`) have no canonical source
  in the deployed graph. They remain in the DTO but are always null. The
  canonical internal type is `NutrientProfile`, carrying the nine fields
  present on the canonical `Food` node. `Nutrients` is a serialization shape at
  the response boundary, not a parallel vocabulary; the two types refer to the
  same nine fields at different layers. `PARTIAL_NUTRITION_DATA` is scoped to
  the nine canonical nutrients; the two always-null extras do not trigger it.
  Any constraint requiring calcium or iron is evidence-absent at the
  calculation layer, because the canonical graph carries no value. No public
  field-set change is made by this feature.
- **Selection:** the resolver picks one canonical food key per ingredient using
  exact, alias, or fuzzy string matching; it rejects the name as ambiguous when
  the top score is below `0.86` or the top-two gap is below `0.05`. Nutrient
  selection runs per nutrient over the accepted candidates that carry a
  non-null value: branded over generic; within same source kind, the smallest
  `(nutrition_rank, selection_priority, food_key)` tuple wins, with missing
  ranks and priorities sorting last. Cost package selection, within the
  resolved key, ranks eligible packages by lowest unit price, then lowest
  retail package cost, then highest confidence, then lexicographic identity
  (`food_key`, `retailer`, `listing_name`). For a `package_volume` package, the
  per-gram unit price is computed from the converted gram amount. This ordering
  is R-13's "best score"; there is no separate score field. There is no
  confidence threshold.
- **Upstream dependency:** p1-002-provenance-graph-model supplies the
  provenance-preserving canonical graph records; p2-001 supplies the
  conservative candidate-evaluation and the freshness filter. The calculator
  also enforces the freshness rule at its own boundary, so a p2-001 defect
  cannot let a non-fresh offer reach cost output. The graph's whole-Food
  selection ordering (used to derive `BEST_FULFILLMENT`) is the reference for
  the nutrient-selection ordering in AC-7; the calculator applies it per
  nutrient.
- **Downstream dependency:** p2-003 consumes the portion nutrient and
  consumed/package cost result contract for plan feasibility and explanation.
  p2-003 reads the calculator's item-level evidence-absent signals
  (`MISSING_PACKAGE_DATA`, `PARTIAL_NUTRITION_DATA`) as the recipe-level drop
  trigger; for `PARTIAL_NUTRITION_DATA` the drop is per nutrient, because a
  nutrient total is evaluable only when every contributing ingredient carries
  a non-null value for that nutrient. The warning names the affected
  nutrients, so p2-003 does not need to re-derive them from the null fields
  alone (though the null fields are consistent with the warning).
- **Runtime/data dependency:** real canonical marts remain subject to the
  tracked `data-preparation` price-path finding; until resolved, conformance
  evidence may use approved fixtures as allowed by the p2 phase posture.
- **Coverage note (for the phase review):** under the AC-20 eligibility rule,
  the 2026-10-07 price-stats distribution yields approximately 607 eligible
  packages out of ~9,700 candidate edges (about 6%). The eligible set is
  `package_mass` and `package_volume` rows with `estimated` status, `accepted`
  match, and `fresh` freshness. `freshness_status` is set at load time, not
  recomputed at request time; the coverage figure is bounded by the current
  graph snapshot.

## Open questions

All calculation-layer policy questions for this feature are resolved. The
proposal's Q1–Q7 remain the binding upstream decisions; the feature's own
clarifications are recorded below as C-1..C-9.

## Clarifications

- **C-1 (freshness is enforced at both layers).** The calculator checks
  `freshness_status == "fresh"` on every candidate package and excludes
  non-fresh packages from cost selection. p2-001 also filters at its layer.
  A non-fresh offer cannot reach cost output by any path. The check is a
  status comparison, not time arithmetic; the deployed graph carries no crawl
  timestamp, and freshness is set at load time. (2026-10-07, human, per
  amended R-8.)
  **Consequential — flag for `decisions.md` at close.**
- **C-2 (item-level evidence-absent; p2-003 drops).** The calculator reports
  absence at the item level via `MISSING_PACKAGE_DATA` (no eligible cost
  package) and `PARTIAL_NUTRITION_DATA` (missing canonical nutrients; the
  warning names them). The calculator does not drop a recipe; it has no recipe
  pool. **p2-003** is the drop owner: it reads the calculator's item-level
  signals as the recipe-level drop trigger. For `PARTIAL_NUTRITION_DATA`, the
  drop is per nutrient — a nutrient constraint is evaluable only when every
  contributing ingredient carries a non-null value for that nutrient, and the
  non-evaluable nutrient's totals are null in the response (no partial sum).
  (2026-10-07, human, per amended R-9 and R-10.)
  **Consequential — flag for `decisions.md` at close.**
- **C-3 (resolver ambiguity is a reading of R-13, not a carve-out).** The
  resolver's ambiguity rejection (top score < `0.86` or top-two gap < `0.05`)
  is a string-score mechanism over `_token_score`, not a confidence threshold
  over the `FULFILLS.confidence` property. R-13 concerns the latter; the
  ambiguity rejection is a deliberate exception that does not conflict with
  R-13's scope. The resolver's chosen-candidate confidence is recorded in the
  trace. AC-17 is therefore not in R-13's scope. (2026-10-07, human.)
  **Consequential — flag for `decisions.md` at close.**
- **C-4 (cost eligibility).** A package is cost-eligible when its `FULFILLS`
  edge declares all of: `price_status == "estimated"`,
  `price_match_status == "accepted"`, `freshness_status == "fresh"`,
  `price_basis` in `{package_mass, package_volume}`, `currency == "SGD"`,
  `reference_price_minor` present and positive, and a present positive package
  amount for the basis (`package_mass_g` for `package_mass`;
  `package_volume_ml` for `package_volume`). A `package_volume` price is
  converted to grams via the domain units converter, **silently** — the
  conversion uses an assumed density with no user-visible warning. The
  `UNIT_ASSUMED_GRAMS` warning does not apply to this cost conversion.
  `cost_basis_compatible` is **not** part of the eligibility rule.
  `package_unresolved`, `span_reference`, `nutrition_only`, and any other
  `price_basis` are ineligible. (2026-10-07, human, per amended R-10.)
  **Consequential — flag for `decisions.md` at close.**
- **C-5 (response field split).** The user-facing item result carries the
  ingredient, the resolved `canonical_key`, the chosen offer (`listing_name`,
  `retailer`), the distinct cost fields, the nutrients DTO, and item warnings.
  It excludes `confidence`, `food_key`, `fdc_id`, `listing_key`, `price_ref`,
  `source_*`, `normalization_version`, `mapping_version`, `nutrition_rank`,
  `selection_priority`, and `approval_status`. Those values are retained in the
  trace. (2026-10-07, human, approving the review's field split.)
  **Consequential — flag for `decisions.md` at close.**
- **C-6 (R-13 "best score").** R-13's "best score" is the AC-11 ordering:
  lowest unit price, then lowest retail package cost, then highest confidence,
  then lexicographic identity (`food_key`, `retailer`, `listing_name`). The
  spec declares no separate score field. R-13's named fixture
  (`tests/features/calculator/test_mapping_selection.py` per the constitution)
  should assert against this ordering. (2026-10-07, human, resolving the
  review's "map best score" item.)
  **Consequential — flag for `decisions.md` at close.**
- **C-7 (no-floor ranking can prefer a cheaper mislinked package).** With no
  confidence floor and unit price ranked before confidence, a cheaper package
  whose mapping is mislinked can outrank a correctly-linked but more expensive
  package. This is intended. The runner-up's identity and confidence are
  recorded in the trace so the ranking is auditable. (2026-10-07, human.)
  **Consequential — flag for `decisions.md` at close.**
- **C-8 (per-nutrient selection may mix sources).** The calculator's
  nutrient-selection precedence is applied per nutrient, over the accepted
  subset that carries a non-null value for that nutrient. Within one
  ingredient, calories may come from one Food and sodium from another. The
  winner per nutrient is recorded in the trace. (2026-10-07, human.)
  **Consequential — flag for `decisions.md` at close.**
- **C-9 (cost coverage is bounded by the graph snapshot).** Under the amended
  eligibility rule, approximately 6% of candidate edges are cost-eligible
  (≈607 of ~9,700 per the 2026-10-07 stats). `freshness_status` is set at load
  time, not recomputed at request time, so the eligible set is bounded by the
  current graph snapshot. This is a data property, not a spec property.
  (2026-10-07, human.)
  **Consequential — flag for `decisions.md` at close.**
- **Note (2026-10-07, Kiro).** The `confidence` vs `mapping_confidence` naming
  drift is resolved in favour of the deployed property `confidence`. There is
  no `mapping_confidence` in the graph. Any documentation still naming
  `mapping_confidence` is corrected in the same change (R-1).
- **Note (2026-10-07, Kiro).** The previously proposed
  `ConflictingNutritionEvidence` error is not reachable through the deployed
  graph: `food_key` is unique per `Food` and terminates the tie-break chain.
  The exception is not an acceptance criterion in this feature.
- **Note (2026-10-07, Kiro).** The proposal's Q1–Q7 are the upstream policy
  resolutions. This feature's clarifications are numbered C-1..C-9 to avoid
  collision.
- **Note (2026-10-07, Kiro).** The roadmap's dependency column for p2-002
  now lists p2-001; the roadmap entry also names the item-level signal
  contract consumed by p2-003 and the per-nutrient drop scope.
