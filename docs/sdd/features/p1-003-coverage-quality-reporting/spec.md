---
feature: p1-003-coverage-quality-reporting
---

# Spec - Coverage and quality reporting

## Summary

This feature makes the completeness of the canonical meal-planning data
visible and reproducible. Every accepted build publishes a quality report with
five separate measures: nutrition coverage, price availability, package-unit
conversion coverage, dietary-evidence coverage, and whole-recipe completeness.

The report is calculated from the canonical recipe requirements, normalized food
concepts, food profiles, and fulfillment evidence. It exposes both the covered
count and denominator for each measure, together with a bounded percentage, so
an operator or downstream quality consumer can distinguish a genuinely complete
population from an empty or unavailable population. It reports gaps rather than
turning missing evidence into a pass, and it is tied to the same accepted source
snapshot and mart content used by the reproducibility and graph-quality
contracts.

The measures describe data readiness; they do not decide whether a recipe
satisfies a particular user's dietary, nutrition, cost, or freshness request.

## Traces to

- **G-5** — "Data quality and coverage are visible: users and operators can see
  which recipes have complete nutrition, price, dietary, and unit evidence
  rather than treating missing data as valid."
- **Roadmap phase p1 → p1-003-coverage-quality-reporting** *(new)* — publish
  separate nutrition, price, unit-conversion, dietary-evidence, and whole-recipe
  completeness measures, regenerated on every build.
- **Phase p1 outcome** — a reproducible, quality-gated canonical foundation is
  available for recipe requirements, normalized food concepts, nutrition
  profiles, products, and dated retail offers.
- **Phase p1 exit criterion** — the coverage report exposes separate
  measurements for nutrition, price availability, package-unit conversion,
  dietary evidence, and overall recipe completeness.
- **Constitutional rule R-15** — the data underlying recommendations is
  reproducible and quality-gated before it is queryable as a graph.
- **Constitutional rule R-5** — absent evidence is reported as a gap and is not
  treated as included or compliant.

## User-facing behavior

There is no direct end-user interface in this feature. The observable consumers
are the data-preparation operator, CI, graph-load admission, and downstream
services that need to know whether evidence is available.

- After a successful build, an operator can obtain one quality report associated
  with the exact accepted source snapshot and canonical mart build.
- The report shows separate nutrition, price, package-unit conversion,
  dietary-evidence, and whole-recipe measures; one dimension cannot be inferred
  from or substituted for another.
- For every dimension, the operator can see the covered population, total
  population, and percentage. A gap remains visible when evidence is absent.
- A downstream consumer can tell whether a low percentage is caused by missing
  evidence in one capability while another capability is present, without
  treating a nutrition-only or price-only candidate as complete.
- A build with missing, inconsistent, non-deterministic, or untraceable quality
  measures is rejected as an incomplete quality result rather than publishing a
  misleading report.

## Acceptance criteria

- **AC-1** Given an accepted build with the canonical recipe requirements,
  food profiles, and fulfillment evidence, when the build completes, then it
  publishes exactly one quality report associated with that build and exposes
  separate measures for nutrition coverage, price availability, package-unit
  conversion coverage, dietary-evidence coverage, and whole-recipe completeness.

- **AC-2** Given a quality report, when the nutrition measure is read, then it
  identifies its covered count, denominator, and percentage, where the covered
  population is the set of canonical ingredient requirements with usable
  nutrition evidence from at least one eligible fulfillment candidate, and the
  denominator is the set of canonical ingredient requirements in the build.

- **AC-3** Given a quality report, when the price-availability measure is read,
  then it identifies its covered count, denominator, and percentage, where the
  covered population is the set of canonical ingredient requirements with at
  least one available price offer or accepted price reference, and the
  denominator is the set of canonical ingredient requirements in the build.

- **AC-4** Given a quality report, when the package-unit-conversion measure is
  read, then it identifies its covered count, denominator, and percentage, where
  the covered population is the set of canonical ingredient requirements with
  at least one fulfillment candidate whose package and requirement quantities
  have a compatible unit basis, and the denominator is the set of canonical
  ingredient requirements in the build.

- **AC-5** Given a quality report, when the dietary-evidence measure is read,
  then it identifies its covered count, denominator, and percentage, where the
  covered population is the set of canonical ingredient requirements with at
  least one fulfillment candidate carrying explicit dietary evidence for the
  supported dietary screens, and the denominator is the set of canonical
  ingredient requirements in the build.

- **AC-6** Given a quality report, when whole-recipe completeness is read, then
  it identifies its covered recipe count, denominator, and percentage, where a
  recipe is covered only when every canonical ingredient requirement belonging
  to that recipe is covered by all four requirement-level measures in AC-2
  through AC-5, and the denominator is the set of canonical recipes in the
  build (distinct from the requirement-level denominators).

- **AC-7** Given a build with a requirement that has nutrition evidence but no
  available price offer, when the report is generated, then the requirement is
  counted as covered in the nutrition measure, not covered in the price measure,
  and is not represented as whole-recipe complete solely because nutrition
  evidence exists.

- **AC-8** Given a build with no canonical ingredient requirements, when the
  report is generated, then every requirement-level measure exposes a zero
  denominator and an explicit no-population result, and whole-recipe
  completeness exposes a zero recipe denominator; no undefined percentage,
  fabricated 100% value, or error-level pass is published.

- **AC-9** Given the same accepted source snapshot and canonical mart content,
  when the quality report is generated more than once, then **all five
  comparison points** — counts, denominators, percentages, dimension
  identities, and build association — are identical across runs. A test for
  this AC must compare all five, not only counts.

- **AC-10** Given a quality report, when its source/build association and counts
  are compared with the reproducibility and graph-quality contracts, then the
  report references the same accepted source snapshot and canonical mart
  content, its denominators do not exceed the corresponding canonical
  populations, and every reported percentage is the covered count divided by
  the denominator when that denominator is non-zero.

- **AC-11** Given a build whose required source snapshot, canonical mart, or
  quality input is missing, unreadable, internally inconsistent, or cannot
  produce one of the five measures, when quality reporting runs, then it fails
  non-zero and publishes no accepted quality report for that build.

- **AC-12** Given a build containing absent nutrition, price, conversion, or
  dietary evidence, when quality reporting runs, then the affected population
  is reported as uncovered with a distinct gap count and is never counted as
  covered by a null, blank, unknown, or inferred value.

- **AC-13** Given a quality report, when its dimensions are enumerated, then it
  exposes exactly the five named measures — nutrition coverage, price
  availability, package-unit conversion coverage, dietary-evidence coverage,
  and whole-recipe completeness — and no others; the report's build association
  names the source snapshot identity and mart content checksum it measures.

## Edge cases & errors

- A requirement has multiple fulfillment candidates and only some provide a
  capability: count the requirement once for that capability if at least one
  eligible candidate provides it; do not inflate counts by candidate count.
- A candidate has nutrition and price data but an incompatible package basis:
  it may contribute to nutrition and price measures but not package-unit
  conversion, and it cannot by itself make its recipe whole-recipe complete.
- A price reference exists without a currently usable offer: price availability
  follows the accepted price-evidence status, while package-unit conversion
  remains uncovered unless a compatible package basis is present.
- Dietary evidence is unknown, blank, or inferred only from absence of a
  concern: report it as uncovered rather than as explicit compliance.
- A recipe has an optional or alternative requirement: the report uses the
  canonical requirement population emitted by the accepted build and applies
  the same rule consistently; it does not silently remove hard-to-measure
  requirements to improve coverage.
- A source snapshot has zero rows for one canonical relation: report the
  resulting zero denominator or gap explicitly and fail only if the accepted
  build contract says that relation must be non-empty.
- A count is negative, a covered count exceeds its denominator, a percentage is
  outside [0, 1] (or its documented percentage equivalent), or a dimension is
  duplicated: reject the report as internally invalid.
- Source snapshot identity or mart content changes between metric computation
  and report publication: reject the report rather than associating metrics
  with the wrong build.
- A build is reproducible in content but its observation timestamp differs: the
  report remains tied to the new observation, while deterministic content
  measures remain unchanged.

## Non-goals

- Not closing data gaps, imputing missing nutrition or dietary evidence, or
  increasing coverage percentages through fallback inference.
- Not changing recipe mappings, fulfillment selection, graph schema, or
  provenance behavior delivered by p1-002.
- Not deciding whether a candidate passes a user's nutrition, allergen, halal,
  vegetarian, budget, freshness, or meal-plan constraints; later reasoning
  features own those decisions.
- Not setting a universal minimum coverage threshold or rejecting a build merely
  because a descriptive percentage is low; this feature reports gaps, while
  admission/reproducibility integrity failures remain quality-gate failures.
- Not exposing audit-only source IDs, mapping confidence, or normalization
  details in an end-user recommendation response.
- Not replacing the source snapshot manifest or mart content checksums owned by
  p1-001.

## Interfaces & dependencies

- **Depends on:** p1-001-reproducible-source-pipeline for the accepted source
  snapshot identity, observation facts, and deterministic canonical mart
  content; p1-002-provenance-graph-model for the canonical graph/mart contract,
  linking directions, and accepted relationship evidence.

- **Test infrastructure dependency:** p1-001b-test-infrastructure (closed
  2026-10-04) provides the fixture pattern for constructing controlled inputs.
  The coverage measures can be demonstrated against fixture marts; a
  demonstration against real marts requires the p1-001 O-1 seed restoration and
  is a follow-up, not a prerequisite for this feature's ACs.

- **Shares the contract** "Coverage dimensions and graph quality manifest" with
  p1-001 and p1-002. The report consumes their accepted build facts and adds
  coverage measurements; it does not redefine source identity, mart content
  checksums, edge provenance, or graph admission semantics.

- **Input contract:** the report is calculated only from the canonical build's
  recipe requirements, food/nutrition profiles, fulfillment candidates, price
  evidence, unit-basis evidence, dietary evidence, and recipe identities. A
  report must be traceable to the exact source snapshot and canonical mart
  content it measures.

- **Output contract:** consumers receive five named dimensions, each with a
  covered count, denominator, percentage or explicit no-population result, and
  enough build association to compare it with the reproducibility manifest and
  graph quality result. The report distinguishes requirement-level measures
  from recipe-level whole-recipe completeness.

- **Regeneration contract:** every accepted build regenerates the report from
  that build's canonical content. A prior report is not reused when its source
  snapshot or mart content differs.

- **Verification contract:** the feature must provide deterministic fixture
  coverage for each dimension, missing-evidence cases, zero denominators,
  cross-dimension independence, and alignment with the accepted reproducibility
  and graph-quality facts.

## Open questions

_No blocking questions remain for specification. Coverage is descriptive and
has no universal minimum threshold; implementation-level representation and
execution choices belong in the plan._

## Clarifications

_No clarifications recorded; no human clarification was required._
