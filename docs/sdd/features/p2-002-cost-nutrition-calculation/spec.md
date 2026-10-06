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
reported only when the recipe quantity and package amount use a compatible unit
basis. When multiple nutrition sources disagree, the declared deterministic
precedence selects the same value for the same inputs on every run. Candidate
selection accepts any existing mapping, including confidence 0, and chooses by
best score without a confidence floor while retaining confidence for the
execution trace.

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
  the closed-interval confidence and no-floor selection (R-13); verify
  unit-basis enforcement (R-10)."
- **Phase p2 outcome** — The reasoning core evaluates explicit nutrition, unit,
  and budget constraints conservatively, computes distinct consumed and package
  costs, and returns a feasible meal plan only when the requested horizon can
  be satisfied.
- **Roadmap shared contract** — "Portion nutrient and consumed/package cost
  result contract," shared with p2-001-constraint-evidence-filtering and
  p2-003-feasible-meal-plan-solving.
- **Constitutional rules:** **R-5** (absent evidence drops, never includes — at
  the calculation layer, an unresolved ingredient is rejected rather than
  producing zero nutrients or an inferred cost), **R-10** (compatible unit
  basis required for cost), **R-11** (consumed cost is distinct from retail
  package price), **R-12** (deterministic nutrient conflict precedence), and
  **R-13** (best-score selection with no confidence floor).

## User-facing behavior

- A successful calculation returns nutrient values for each ingredient's
  consumed quantity, recipe-level nutrient totals, and nutrient totals divided
  by the requested number of servings. Missing values remain unknown rather
  than being represented as zero.
- A successful calculation exposes the consumed-ingredient cost and the
  whole-package retail purchase cost as separate values, both per ingredient
  and in the summary. The consumed cost reflects only the quantity used; the
  package cost reflects the package or packages that must be purchased.
- A product whose package amount and recipe quantity do not have a compatible
  unit basis is not used for cost. If no compatible product remains for an
  ingredient, the cost cannot be computed and the eligible recipe is dropped
  as evidence-absent when cost is required.
- When conflicting nutrition evidence is available, branded product evidence
  takes precedence over generic USDA evidence. When only one source is
  present, that source is used. Between conflicting branded values, the most
  recently crawled offer wins; equal crawl timestamps are resolved by the
  lexicographically smaller product identifier.
- A candidate is selectable whenever a candidate record exists, including
  confidence 0. Selection is by best score, not by a minimum confidence
  threshold. The selected confidence is retained in the execution trace and
  is not exposed as an audit field in the user-facing response.
- Unit conversion using a non-mass assumption produces an explicit warning so
  the user can distinguish an estimated nutrient amount from an exact mass
  conversion.

## Acceptance criteria

- **AC-1** Given an ingredient with a validated nutrient profile per 100 grams,
  a positive consumed quantity, and a requested serving count, when calculation
  runs, then each available nutrient is scaled by consumed grams divided by
  100, the ingredient nutrient contribution is included in the recipe total,
  and the per-serving nutrient total is the recipe total divided by the
  requested serving count.

- **AC-2** Given a recipe with multiple ingredients and nutrient values that are
  missing for some tracked nutrients, when calculation runs, then available
  values are summed independently, a nutrient missing from every contributing
  ingredient remains unknown, and no missing value is treated as zero.

- **AC-3** Given a compatible product with package price P, package amount S,
  and a consumed quantity Q where 0 < Q < S, when cost calculation runs, then
  the result exposes the consumed-ingredient cost equal to P × (Q / S) and the
  retail package purchase cost equal to P, as separate fields with distinct
  values.

- **AC-4** Given a consumed quantity requiring more than one package of a
  compatible product, when cost calculation runs, then the consumed cost is
  based on the quantity used while the retail purchase cost is based on the
  number of whole packages required, and neither value is substituted for the
  other in the item result or summary.

- **AC-5** Given a candidate product whose package amount and recipe quantity do
  not share a compatible unit basis, when cost eligibility is evaluated, then
  the product is excluded from cost calculation; and given that no compatible
  product remains for the ingredient, when cost is required, then the recipe is
  dropped with an evidence-absent cause rather than receiving an inferred cost.

- **AC-6** Given generic USDA nutrition evidence and conflicting branded product
  nutrition evidence for the same nutrient, when the candidate's nutrient value
  is selected, then the branded product value is used consistently in the
  calculation; given only a generic USDA value with no conflicting branded
  value, then the generic value is used.

- **AC-7** Given two conflicting branded values for the same nutrient on offers
  with different crawl timestamps, when the nutrient value is selected, then
  the value from the more recently crawled offer is used; given equal crawl
  timestamps, then the value from the offer with the lexicographically smaller
  product identifier is used.

- **AC-8** Given the same conflicting nutrition inputs, when calculation is run
  more than once, then the selected nutrient values and resulting totals are
  identical on every run, including when the branded offers have equal crawl
  timestamps.

- **AC-9** Given a requirement with exactly one existing candidate whose mapping
  confidence is 0, when candidate selection runs, then that candidate is
  selected rather than rejected for low confidence, and its confidence is
  recorded in the execution trace.

- **AC-10** Given a requirement with multiple existing candidates, when
  candidate selection runs, then the candidate with the best mapping score is
  selected regardless of whether another candidate has a higher confidence,
  and the selected candidate's confidence is recorded in the execution trace.

- **AC-11** Given candidate records whose mapping confidence values are at the
  endpoints 0 and 1, when selection runs, then both values are accepted as
  valid confidence values; given a value below 0 or above 1, then the candidate
  is rejected as invalid input rather than silently clamped or accepted.

- **AC-12** Given a known non-mass unit whose conversion uses an assumed gram
  equivalent, when nutrient calculation runs, then the calculated result is
  returned with a user-visible unit-assumption warning; given an unsupported
  unit or a non-positive, non-finite quantity, then calculation returns a
  validation/conversion error and does not produce a nutrient or cost value for
  that ingredient.

- **AC-13** Given a calculation request that cannot resolve an ingredient to any
  candidate, when calculation runs, then the request is rejected as unresolved
  rather than producing zero nutrients, an inferred cost, or a successful
  result. This is the calculation-layer expression of R-5's "absent evidence
  drops, never includes."

## Edge cases & errors

- A nutrition profile may be partial. A missing requested nutrient remains
  unknown and must not be replaced with zero; totals are unknown for that
  nutrient only when no contributing value exists.
- A recipe may use a fractional package quantity or require several whole
  packages. Consumed cost and retail purchase cost must remain distinct in both
  cases.
- A package with missing, non-positive, stale, non-SGD, or otherwise unusable
  price evidence is not a usable cost candidate. Freshness eligibility follows
  the p2-001 contract: the 24-hour boundary is inclusive and older offers are
  unavailable.
- A package with missing, non-positive, or incompatible amount information is
  excluded from cost rather than converted by an unsupported assumption.
- A candidate set may contain one low-confidence candidate or several tied
  scores. No confidence floor may discard the only existing candidate; ties
  must be resolved deterministically so repeated runs do not change the
  result.
- Nutrition sources may disagree, may contain equal timestamps, or may omit a
  tracked nutrient. The specified source and timestamp/product-ID precedence
  applies independently to each nutrient.
- Two branded offers carrying the same product identifier and the same crawl
  timestamp for the same nutrient are a data-integrity violation. The
  calculation must reject the conflicting evidence rather than silently
  choosing one, because the tie-break contract does not cover identical
  identities.
- A non-mass unit conversion is approximate and must be warned; an unsupported
  unit, invalid quantity, unresolved ingredient, or absent required evidence
  is an error or evidence-absent outcome, not an implicit zero.
- A request with zero or negative servings, no ingredients, or more ingredients
  than the supported request limit is invalid and must not be calculated.
- User-facing output must not expose mapping confidence, normalization version,
  source identifiers, or other audit-only provenance; those values belong only
  in the execution trace.

## Non-goals

- Solving the complete multi-day meal-plan feasibility problem; that belongs to
  p2-003.
- Implementing allergen or dietary evidence filtering; p2-001 owns those
  constraint evaluations, which this feature consumes.
- Refreshing, crawling, or guaranteeing live retail inventory or promotional
  prices.
- Providing medical, clinical, or individualized dietary advice.
- Designing a new storage schema, API file layout, or internal data structure.

## Interfaces & dependencies

- **Input contract:** the existing calculation request supplies servings and
  ingredient names, positive quantities, and supported units.
- **Evidence contract:** candidate resolution supplies normalized food
  candidates, nutrient evidence, package amount and price evidence, unit-basis
  compatibility, mapping score, confidence, crawl timestamp, and product
  identity as applicable.
- **Output contract:** the existing calculation response supplies itemized
  nutrient and cost results plus recipe totals and per-serving nutrients. The
  consumed-cost and retail-package-cost values remain distinct. User-facing
  output follows R-16; audit provenance is retained in the execution trace.
- **Upstream dependency:** p1-002-provenance-graph-model supplies the
  provenance-preserving canonical graph records and p2-001 supplies the
  conservative candidate-evaluation and freshness/unit-basis outcomes.
- **Downstream dependency:** p2-003 consumes the portion nutrient and
  consumed/package cost result contract for plan feasibility and explanation.
- **Runtime/data dependency:** real canonical marts remain subject to the
  tracked `data-preparation` price-path finding; until resolved, conformance
  evidence may use approved fixtures as allowed by the p2 phase posture.

## Open questions

There are no blocking open questions. The proposal resolves the applicable
policy questions: confidence threshold and selection (Q1), unit conversion for
cost (Q2), price freshness (Q3), and nutrient conflict precedence (Q7).

## Clarifications

No human clarification was requested for this specification. The proposal's
resolved decisions and the roadmap's p2 feature contract were used as the
binding inputs on 2026-10-06 by Kiro (specification agent).
