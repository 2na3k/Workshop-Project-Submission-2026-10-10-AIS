# Proposal

## Problem

Planning meals according to personal constraints—such as nutrition targets, dietary restrictions,
ingredient availability, and budget—is difficult because required data is heterogeneous, imperfect,
and time-sensitive. Recipe requirements, generic nutrient profiles, and dated retail offers live in
separate schemas without shared entity keys, so linking a recipe requirement to a nutrient profile
and a purchasable offer requires normalization, mapping with recorded confidence, and preserved
provenance. Existing meal planning systems either address nutrition without pricing or prices
without dietary evidence, and none expose the full reasoning chain connecting a recipe requirement
to a purchasable, evaluable meal.

## Goals

* **G-1**: Users receive meal recommendations evaluated against explicit constraints, including
  carbohydrate/nutrient ranges, excluded allergens, halal or vegetarian preferences, and daily
  budget limits.

* **G-2**: Users receive explicit result explanations detailing which specific constraint or missing
  data point blocked or qualified a recipe recommendation.

* **G-3**: Meal cost calculations clearly distinguish whole-package retail purchase prices from the
  actual cost of consumed recipe ingredients.

* **G-4**: Recipe ingredients are linked to normalized nutrition profiles and dated retail offer
  prices while preserving provenance, source IDs, mapping confidence, and timestamp evidence.

* **G-5**: System performance and completeness are measurable separately across nutrition coverage,
  price availability, package unit conversions, dietary evidence, and overall recipe completeness.

* **G-6**: Every recommendation exposes the user-level reasoning chain as scoped in Q8: which
  normalized food concept each recipe requirement resolved to, which food/product candidate
  fulfilled it, which nutrition profile and offer were used, and which constraint evaluations
  passed.

* **G-7**: The data underlying recommendations is reproducible from source snapshots, quality-gated
  on entity counts and referential integrity, and queryable as a graph of recipes, food concepts,
  nutrition profiles, and retail offers.

## Explainability Stance

Recommendations must be explainable at three levels of granularity: the plan (the overall request),
the recipe (each candidate considered, including those that were dropped), and the constraint (each
specific requirement evaluated for a recipe).

Absent evidence is treated as a reason to drop a recipe from consideration, never as permission to
include it. The reason a recipe was dropped is reported distinctly depending on its cause:
"evidence is missing" is reported differently from "evidence is present and rules the recipe out."
This distinction is what makes G-2's explanations meaningful to a user.

The specific vocabulary and mapping used to express these levels in the API response are defined in
the spec. This section states the project-level stance; the spec states the contract.

## Non-goals

* Providing medical diagnosis, clinical dietary prescriptions, or health treatment advice.

* Issuing official halal certifications for food products or recipes.

* Supporting live inventory reservation, cart checkout, delivery scheduling, or guaranteed
  promotional retail prices.

* Achieving complete coverage of all grocery retailers, store SKUs, or recipe ingredients.

* Developing client applications for non-web platforms (tablets, mobile, etc.).

* Claiming that crawler data alone proves a weekly budget without a defined offer snapshot,
  compatible package basis, and policy for unavailable items.

## External Constraints

* **Lack of Public Retail API**: NTUC FairPrice lacks a public API, restricting retail price and
  product data collection to web crawling with rate and scroll limitations.

* **Heterogeneous Schemas**: Reference nutrition databases and retail grocery listings share no
  common entity identifiers, requiring text normalization and entity extraction to link records.

## Known Data Limitations

* **Geographic Reference Discrepancy**: Standard USDA FoodData Central collections lack
  Singapore-specific food items, creating potential domain gaps for local ingredients.

* **Temporal Degradation of Price Snapshots**: Retail pricing and offer data are point-in-time
  observations that degrade in accuracy over time.

## Behavioral Rules

These rules state policy in plain language. The response vocabulary used to encode each outcome
(drop / retain-with-warning / include, and their distinct causes) is defined in the spec.

* **Conservative Allergen Policy**: A recipe is evaluated against declared allergen evidence as
  follows. A declared severe allergen drops the recipe. A declared mild allergen retains the recipe
  with a user-visible warning on the offending ingredient. Undeclared or unknown allergen evidence
  drops the recipe, with the cause reported as evidence-absent rather than as non-compliance.
  Missing or unstated allergen data must never be treated as allergen-free. (source: §2, §4)

* **No Inferred Dietary Compliance**: For dietary requirements (halal, vegan, vegetarian), explicit
  compliance retains the recipe. Any other state — unknown, blank, or undeclared — drops the
  recipe, with the cause reported as evidence-absent rather than as non-compliance. Absent evidence
  is never treated as compliance. (source: §4)

* **Compatible Unit Basis Required**: Consumed ingredient cost is calculated only when package size
  and recipe quantity share a compatible unit basis. A product with an incompatible basis is not
  usable for cost; if no compatible product remains for a requirement, the cost for that
  requirement cannot be computed and the recipe is dropped from the eligible pool. (source: §4)

* **Price Snapshot Staleness**: Retail price offers older than 24 hours are treated as unavailable.
  A stale offer is never used, even with a flag; if no fresh offer exists for a requirement, the
  cost for that requirement cannot be computed and the recipe is dropped. This mirrors the
  Conservative Allergen Policy's safe-by-default posture: unverifiable is treated as unavailable.
  (source: §2, §3)

* **Nutrient Conflict Precedence**: When generic USDA values and crawled branded product values
  disagree, branded product values take precedence. When two branded product values disagree for
  the same nutrient, the value from the most recently crawled offer is used; if the offers have
  identical crawl timestamps, the value from the offer with the lexicographically smaller product
  ID is used. (source: §3, §5)

* **Missing Nutrition Profile**: A candidate with no nutrition profile does not satisfy any
  nutrient constraint it would serve. It is not treated as zero. If all candidates for a
  requirement lack a profile, that requirement's nutrient constraint cannot be evaluated and the
  recipe is dropped from the eligible pool. (source: §3, §4)

* **Mapping Acceptance Floor**: There is no minimum confidence threshold. A recipe requirement is
  unmappable only when no candidate exists. Confidence is expressed on a closed interval from 0 (no
  signal) to 1 (exact normalized match); a candidate is selectable when a candidate record
  exists, regardless of its confidence value. Selection among candidates is by best score. This
  prioritizes coverage over precision — a low-confidence mapping yields a nutrient or price value
  with its confidence recorded in the execution trace so the weakness is visible. (source: §3)

* **Plan Feasibility Floor**: After candidate filtering and all permitted relaxations, if no set of
  retained recipes can satisfy the requested horizon_days × meals_per_day, the plan cannot be
  produced and the response names the binding constraint (s) that caused the failure so the user
  can adjust the request. An unfeasible plan is never returned while a producible plan exists.
  (source: §3, §4)

## Resolved Questions

All eight open questions from the review session have been resolved. Decisions below are binding on
the constitution stage. Response vocabulary referenced below is defined in the spec.

* **Q1 — Mapping confidence threshold**: No threshold. Selection is by best score among all
  existing candidates; a requirement is unmappable only when the candidate set is empty.
  Confidence is on a closed [0, 1] interval. Resolved 2026-10-02. (→ Behavioral Rule: Mapping
  Acceptance Floor)

* **Q2 — Budget when unit conversion is impossible**: Exclude the product from cost calculation.
  If no compatible product remains for a requirement, the cost cannot be computed and the recipe is
  dropped from the eligible pool. Resolved 2026-10-02. (→ Behavioral Rule: Compatible Unit Basis
  Required)

* **Q3 — Price snapshot age threshold**: 24 hours. Offers older than this are treated as
  unavailable, never silently used and never used with a flag. If no fresh offer exists, the cost
  cannot be computed and the recipe is dropped. Resolved 2026-10-02. (→ Behavioral Rule: Price
  Snapshot Staleness)

* **Q4 — Mild vs. severe allergen exclusion**: A declared severe allergen drops the recipe. A
  declared mild allergen retains the recipe with a user-visible warning flag on the offending
  ingredient. Undeclared allergen evidence drops the recipe, with the cause reported as
  evidence-absent. Resolved 2026-10-02. (→ Behavioral Rule: Conservative Allergen Policy)

* **Q5 — Unknown allergen evidence**: The recipe is dropped, with the cause reported as
  evidence-absent rather than as non-compliance. Undeclared is treated as unsafe-by-default.
  Resolved 2026-10-02. (→ Behavioral Rule: Conservative Allergen Policy)

* **Q6 — Unknown dietary compliance**: The recipe is dropped, with the cause reported as
  evidence-absent. Absent evidence is never treated as compliance, though the reported reason
  distinguishes absent evidence from declared non-compliance. Resolved 2026-10-02. (→ Behavioral
  Rule: No Inferred Dietary Compliance)

* **Q7 — USDA vs. branded nutrient conflict**: Branded product values take precedence when
  available. When two branded values conflict, the more recently crawled offer wins; on tie, the
  lexicographically smaller product ID wins. Resolved 2026-10-02. (→ Behavioral Rule: Nutrient
  Conflict Precedence)

* **Q8 — Provenance exposure level**: User-facing response exposes only what is needed to explain a
  recommendation — resolved food concept, chosen offer, constraint outcome per requirement, and
  any warned conditions. Mapping confidence, normalization version, and source IDs are retained in
  the execution trace for debugging and audit but not returned to the user. Resolved 2026-10-02.
  (Not a checkable rule; recorded as intent. G-6 is scoped accordingly.)

## Source material

* [final_proposal_1_v2.md](../../final_proposal_1_v2.md)
