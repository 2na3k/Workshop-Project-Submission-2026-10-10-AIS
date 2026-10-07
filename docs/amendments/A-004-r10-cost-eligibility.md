# Amendment proposal

status: approved
Proposed by: Kiro (specification agent), on behalf of phase review for p2-002
Date: 2026-10-07

## Trigger
Phase-review finding routed to `constitution` from the p2-002 spec review. R-10
says "package size and recipe quantity share a compatible unit basis" and its
named check asserts "incompatible-basis products are excluded from cost." The
phrase reads as if the deployed graph declares a boolean compatibility flag
(`cost_basis_compatible`) that gates eligibility. The deployed schema does
carry `cost_basis_compatible`, but the p2-002 spec's C-4 establishes that this
flag is **not** the eligibility rule. The deployed eligibility rule is: a
package is cost-eligible when its `FULFILLS` edge declares
`price_status == "estimated"`, `price_match_status == "accepted"`, and
`price_basis` in `{package_mass, package_volume}`. `cost_basis_compatible` is
ignored — 63 edges with `cost_basis_compatible = FALSE` and
`price_basis = "package_mass"` are legitimately cost-eligible.

R-10's "drop as evidence-absent" language has the same layer confusion as R-9:
the calculator reports item-level absence; the drop is p2-003's.

## Current rule(s)
> **R-10 Compatible unit basis required for cost**
> - Rule: Consumed-ingredient cost must be computed only when package size and
    >   recipe quantity share a compatible unit basis. A product with an incompatible
    >   basis must not be used for cost; if no compatible product remains for a
    >   requirement, the recipe must be dropped as evidence-absent.
> - Why: Q2; Behavioral Rule Compatible Unit Basis Required.
> - Check: Named test fixture —
    >   `tests/features/calculator/test_domain_conversion.py` asserts incompatible-basis
    >   products are excluded from cost and that a requirement left with no compatible
    >   product drops with an evidence-absent cause.

## Proposed change

> **R-10 Cost eligibility requires a convertible price basis**
> - Rule: Consumed-ingredient cost must be computed only from a package whose
    >   `FULFILLS` edge declares all of:
    >   `price_status == "estimated"`, `price_match_status == "accepted"`, and a
    >   `price_basis` in the cost-convertible set (`package_mass` or
    >   `package_volume`). A `package_volume` price is converted to grams using the
    >   domain units converter. A `price_basis` of `package_unresolved`,
    >   `span_reference`, `nutrition_only`, or any other value is ineligible.
    >   `cost_basis_compatible` is **not** part of the eligibility rule; the flag
    >   is informational and may be false on eligible packages.
    >   At the calculator layer, an ingredient whose resolved key has no eligible
    >   package remains in the itemized result with null cost fields and carries a
    >   `MISSING_PACKAGE_DATA` warning. The recipe-level drop is **p2-003's**
    >   responsibility: when p2-003 determines that a requirement has no eligible
    >   package, the recipe is dropped from the eligible pool with an
    >   evidence-absent cause, reading the calculator's `MISSING_PACKAGE_DATA`
    >   signal as that evidence.
> - Why: Q2; Behavioral Rule Compatible Unit Basis Required; deployed
    >   `FULFILLS` schema declares eligibility via `price_status`,
    >   `price_match_status`, and `price_basis`, not via `cost_basis_compatible`.
> - Check: Named test fixtures, at both layers.
    >   `tests/features/calculator/test_domain_cost.py` asserts a package whose
    >   `price_status` is not `estimated`, whose `price_match_status` is not
    >   `accepted`, or whose `price_basis` is not in the cost-convertible set, is
    >   excluded from cost; that a `package_volume` package is eligible and
    >   converted; and that a package with `cost_basis_compatible = FALSE` and an
    >   otherwise-convertible basis is eligible.
    >   p2-003's fixture asserts that a requirement left with no eligible package
    >   drops with an evidence-absent cause, consuming the calculator's
    >   `MISSING_PACKAGE_DATA` signal.

## Impact
- **Completed features to re-check:** p2-001-constraint-evidence-filtering —
  its candidate hydration projects `cost_basis_compatible` from the canonical
  `FULFILLS` edge. If p2-001's filtering treats `cost_basis_compatible = FALSE`
  as ineligible, it is non-conformant with the amended rule and must be
  corrected. This is a p2-001 finding, not a p2-002 change; the amendment is
  the upstream trigger.
- **In-flight features to re-check:** p2-002-cost-nutrition-calculation — the
  spec's C-4 already assumes the amended rule. No spec change is required once
  this amendment is approved.
- **Downstream:** p2-003-feasible-meal-plan-solving owns the recipe-level drop
  under the amended rule. Its cost-feasibility checks must use the amended
  eligibility rule. p3-001, p3-002 — no impact.
- **Behavioral change:** under the amended rule, packages with
  `cost_basis_compatible = FALSE` and a convertible basis become cost-eligible.
  Per the 2026-10-07 price-stats distribution, this adds 63 `package_mass` rows
  to the eligible set. The `package_volume` rows (71) were already eligible
  under a "convert if possible" reading; the amendment makes that explicit. The
  `package_unresolved` rows (26) remain ineligible.
- **No data migration required.**
- **Coverage note:** under the amended rule, the calculator's cost coverage is
  approximately 607 of ~9,700 edges — 473 `package_mass` with
  `cost_basis_compatible = TRUE`, 63 `package_mass` with
  `cost_basis_compatible = FALSE`, and 71 `package_volume`, all with
  `price_status = "estimated"`, `price_match_status = "accepted"`, and
  `freshness_status = "fresh"`. This coverage is a data property, not a spec
  property.

## Version bump
1.3 -> 1.4

## Human decision
- Reviewer:
- Decision:
- Date:
