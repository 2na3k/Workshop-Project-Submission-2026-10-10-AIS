---
feature: p2-001-constraint-evidence-filtering
---

# Spec - Constraint evidence filtering

## Summary

This feature makes the existing candidate-filtering logic provable against the
reasoning-safety rules that govern how a recipe requirement is evaluated against
a requested constraint. For each requested allergen, dietary, nutrient,
freshness, and unit-basis constraint, a candidate is retained only when the
evidence needed to evaluate that constraint is present and the constraint is
satisfied. When the evidence needed to evaluate a requested constraint is
missing, blank, or undeclared, the recipe is dropped and that drop is reported
as **evidence-absent**. When the evidence is present and rules the recipe out,
the recipe is dropped and that drop is reported as **present-evidence-excludes**.
These two causes are distinct in the output so a downstream consumer can tell
"we could not check" from "we checked and it failed."

The feature is a prove-and-fix change against pre-existing filtering code. The
current filtering path has the allergen, dietary, and freshness checks disabled,
so the conformance fixtures are expected to reveal non-conformant behavior that
this feature fixes. The feature does not redesign the reasoning shape, add new
constraint types, compute cost or nutrient totals, or solve meal plans; those
belong to p2-002 and p2-003.

## Traces to

- **G-1** — Remy models an explicit user request (a nutrient range, an excluded
  allergen, a halal/vegetarian preference, a freshness/budget constraint) as
  explicit constraints and evaluates candidates against them conservatively.
- **Roadmap phase p2 → p2-001-constraint-evidence-filtering** *(partial)* —
  "Existing filtering logic in the calculator API. Remaining work: write a
  fixture for each of R-5 through R-10 and either the fixtures pass or the code
  is fixed. The evidence-absent vs. present-exclusion distinction must be visible
  in the output."
- **Phase p2 outcome** — "The reasoning core evaluates explicit nutrition,
  allergen, dietary, freshness, unit, and budget constraints conservatively …"
- **Shared contract (roadmap feature table)** — "Candidate evaluation outcome
  and distinct evidence-absent/present-exclusion causes," shared with
  p2-002-cost-nutrition-calculation and p2-003-feasible-meal-plan-solving.
- **Constitutional rules:** **R-5** (absent evidence drops, never includes),
  **R-6** (severe allergen drops; mild allergen warns; undeclared drops as
  evidence-absent), **R-7** (no inferred dietary compliance), **R-8** (stale
  price offers are unavailable; no fresh offer drops as evidence-absent), **R-9**
  (nutrient constraints require a profile; profile-less is not zero), and **R-10**
  (compatible unit basis required for cost; no compatible product drops as
  evidence-absent).

## User-facing behavior

There is no direct end-user UI surface in this feature. The observable consumers
are the downstream calculation (p2-002), plan-solving (p2-003), and
explanation (p3) layers that read the candidate-evaluation outcome.

- A requirement whose candidate evidence satisfies every requested constraint is
  retained in the eligible pool.
- A requirement that lacks the evidence needed to evaluate a requested
  constraint causes its recipe to be dropped, and the drop carries an
  evidence-absent cause naming the constraint that could not be evaluated.
- A requirement with a declared **severe** allergen match causes its recipe to
  be dropped as a present-evidence exclusion.
- A requirement with a declared **mild** allergen match is retained, and the
  candidate-evaluation outcome carries a warning annotation attached to the
  identifier of the offending ingredient.
- A requirement with an undeclared or unknown allergen state causes its recipe
  to be dropped as evidence-absent.
- A requirement that requests halal, vegan, or vegetarian compliance is retained
  only on explicit compliant evidence; any unknown, blank, or undeclared state
  drops the recipe as evidence-absent.
- A nutrient constraint is evaluated only against a candidate that has a
  nutrition profile; a profile-less candidate neither satisfies the constraint
  nor contributes a zero, and a requirement with no profiled candidate drops as
  evidence-absent.
- A retail offer older than the freshness threshold (24 hours) is treated as
  unavailable and is never used; if no fresh offer exists for a requirement, the
  recipe drops as evidence-absent.
- Consumed-ingredient cost is evaluated only when package size and recipe
  quantity share a compatible unit basis; an incompatible-basis product is not
  used, and a requirement with no compatible product drops as evidence-absent.

## Acceptance criteria

- **AC-1** Given a requirement with an `unknown`, blank, or undeclared state for
  a requested constraint, when candidate filtering runs, then the recipe is
  dropped and the drop cause is reported as evidence-absent, naming the
  constraint that could not be evaluated; the recipe does not appear in the
  retained pool.

- **AC-2** Given a requirement whose only candidate's evidence is absent for a
  requested constraint, when filtering runs, then no code path treats that
  absence as a passing, compliant, or zero value: the recipe is dropped rather
  than retained or scored as satisfying the constraint.

- **AC-3** Given a requested allergen that a candidate declares at **severe**
  severity, when allergen screening runs, then the recipe is dropped and the
  drop cause is reported as present-evidence-excludes (distinct from
  evidence-absent).

- **AC-4** Given a requested allergen that a candidate declares at **mild**
  severity, when allergen screening runs, then the recipe is retained and the
  candidate-evaluation outcome carries a warning annotation attached to the
  identifier of the specific offending ingredient; the warning is not attached
  to the recipe without an ingredient reference.

- **AC-5** Given a requested allergen for which a candidate's allergen evidence
  is undeclared or unknown, when allergen screening runs, then the recipe is
  dropped with an evidence-absent cause.

- **AC-6** Given a requested halal, vegan, or vegetarian constraint and a
  candidate whose compliance state is unknown, blank, or undeclared, when
  dietary screening runs, then the recipe is dropped with an evidence-absent
  cause; only an explicit compliant value retains the recipe.

- **AC-7** Given a requested nutrient constraint and a candidate with no
  nutrition profile, when the nutrient constraint is evaluated, then the
  candidate contributes no value (not zero) and does not satisfy the constraint;
  and given a requirement whose candidate set has no profiled candidate, the
  recipe is dropped with an evidence-absent cause.

- **AC-8** Given a requested freshness threshold of 24 hours and a retail offer
  whose age is greater than 24 hours, when offer evaluation runs, then the offer
  is excluded and is not used with or without a flag; an offer at exactly 24
  hours is treated as fresh (inclusive bound); and given a requirement with no
  offer at or under 24 hours old, the recipe is dropped with an evidence-absent
  cause.

- **AC-9** Given a requirement whose recipe quantity and a candidate product's
  package size do not share a compatible unit basis, when cost eligibility is
  evaluated, then that product is excluded from cost; and given a requirement
  left with no compatible product, the recipe is dropped with an evidence-absent
  cause.

- **AC-10** Given a candidate that satisfies every requested constraint with
  present, compliant evidence, when filtering runs, then the recipe is retained
  in the eligible pool and its candidate-evaluation outcome carries no drop
  cause (the cause field is null or absent, not a sentinel value).

- **AC-11** Given one recipe dropped for absent evidence and another dropped for
  present evidence that rules it out, when both outcomes are produced in the same
  run, then each outcome carries its own distinct cause and the two causes are
  not represented by the same value.

- **AC-12** Given a single recipe that is subject to both a present-evidence
  exclusion (e.g. a declared severe allergen) and an absent-evidence condition
  (e.g. an undeclared dietary state) in the same run, when filtering produces the
  recipe's outcome, then the reported cause is present-evidence-excludes — the
  present-evidence exclusion takes precedence over the absent-evidence drop.

- **AC-13** Given a user request that declares an allergen without a severity,
  when allergen screening runs, then the request is treated as a **severe**
  declaration and a matching candidate drops the recipe as present-evidence
  excludes.

## Edge cases & errors

- A requested allergen term that does not resolve to a known allergen key: this
  is an input error distinct from a drop; the request is rejected rather than
  silently passing or dropping candidates.
- A requested dietary code outside the supported set (halal, vegan, vegetarian):
  rejected as an input error, not treated as evidence-absent.
- A requested nutrient code the system does not track: rejected as an input
  error, not treated as a satisfied or absent constraint.
- A candidate with a severe allergen match **and** a separate absent-evidence
  constraint: the recipe is dropped with present-evidence-excludes as the
  reported cause, per AC-12; the absent-evidence condition is not silently
  discarded but is subordinate in the reported cause. A downstream consumer
  that needs both causes may inspect the outcome's per-constraint evaluations;
  the top-level cause carries the precedence rule.
- A mild allergen match on an ingredient whose offending-ingredient identity
  cannot be isolated: the outcome must still carry the warning with an
  ingredient identifier; a warning without an ingredient reference is invalid
  and must fail rather than be attached to the recipe as a whole.
- A nutrition profile that is present but partial (some tracked nutrients
  missing): a nutrient whose value is missing cannot be evaluated as satisfied
  and must not be read as zero; whether this drops the recipe depends on whether
  the specific requested nutrient is missing.
- A freshness threshold boundary: an offer at exactly 24 hours is treated as
  fresh (inclusive), per AC-8; evaluation must apply this deterministically.
- A unit basis that is convertible in principle but whose conversion data is
  absent for this candidate: treated as incompatible for cost, not assumed
  convertible.
- No candidate for a requirement resolves at all (empty candidate set): the
  requirement is unmappable; this is reported distinctly from a drop caused by a
  failed or absent constraint on a resolved candidate.
- All recipes drop for the same requested constraint: the result is an empty
  eligible pool with per-requirement causes, not an unhandled error.

## Non-goals

- Not computing portion nutrient contributions or consumed/package cost figures;
  that is p2-002. This feature decides eligibility and cost-usability, not the
  cost or nutrient values themselves.
- Not solving the meal plan or deciding feasibility across the horizon; that is
  p2-003.
- Not defining the user-facing explanation surface or the three-level
  explanation shape; that is p3-002's response contract.
- Not changing the canonical graph schema, mapping, or provenance model; that is
  p1-002.
- Not setting mapping-acceptance confidence thresholds or selection ranking;
  that is p2-002's R-13 scope.
- Not introducing new constraint categories beyond allergen, dietary, nutrient,
  freshness, and unit-basis.

## Interfaces & dependencies

- **Upstream dependency:** p1-002-provenance-graph-model supplies the canonical
  candidate evidence (allergen declarations, dietary flags, nutrition profiles,
  dated offers, package/unit data) that filtering reads. Per the roadmap's p2
  prerequisite note, `docs/findings/data-prep-price-path.md` must resolve before
  this feature can read the canonical marts against real data; until then the
  conformance fixtures exercise the filtering logic against fixtures.

- **Shared contract (candidate evaluation outcome):** this feature owns the
  candidate-evaluation outcome and the two distinct drop causes
  (evidence-absent, present-evidence-excludes). p2-002-cost-nutrition-calculation
  and p2-003-feasible-meal-plan-solving consume that outcome; the specific
  representation of the outcome and causes is a plan-stage decision subject to
  this spec and the constitution.

- **Rule inputs:** the behavior is governed by constitutional rules R-5 through
  R-10. The freshness threshold is **24 hours, inclusive** (an offer at exactly
  24 hours is fresh; anything older is stale). The reported drop cause follows
  a **fixed precedence: present-evidence-excludes over evidence-absent** when a
  single recipe is subject to both. Allergen severity comes from the **user's
  request**; an allergen declared without a severity is treated as **severe**.

- **Fixture ownership:** R-5, R-6, R-7 (allergen and dietary absent-evidence and
  present-exclusion) are owned by the dietary-domain fixture; R-8, R-9, R-10
  (freshness, profile-required, compatible-unit) are owned by the
  calculator-domain fixture. The plan names the concrete files. A rule's fixture
  lives in the domain that owns the rule, not in a cross-cutting "filtering"
  test file.

- **Verification contract:** the feature must provide independently runnable
  fixtures corresponding to R-5 through R-10 that assert the retain/drop/warn
  outcome and the distinct drop cause. Per the constitution's named checks, the
  dietary rules (R-5, R-6, R-7) are demonstrated by a dietary-domain fixture and
  the cost/nutrition/conversion rules (R-8, R-9, R-10) by calculator-domain
  fixtures; the plan stage names the concrete files.

- **Scope check:** the plan stage determines whether allergen, dietary,
  nutrient, freshness, and unit-basis evaluation fit one working context or
  should split; this spec does not prescribe that split.

## Open questions

None. All three questions (freshness threshold, cause precedence, allergen
severity source) are resolved in Interfaces & dependencies and reflected in the
acceptance criteria (AC-8, AC-12, AC-13).

## Clarifications

- Q1 → Freshness threshold is **24 hours, inclusive**: an offer exactly at 24
  hours is fresh; anything older is stale. Date: 2026-10-05. Who: Human.
- Q2 → When a single recipe is subject to both a present-evidence exclusion and
  an absent-evidence drop, the reported cause is **present-evidence-excludes**;
  the absent-evidence condition is subordinate in the top-level cause but
  retained in the outcome's per-constraint evaluations. Date: 2026-10-05.
  Who: Human.
- Q3 → Allergen severity comes from the **user's request**. An allergen declared
  without a severity is treated as **severe** (drop). Date: 2026-10-05.
  Who: Human.
