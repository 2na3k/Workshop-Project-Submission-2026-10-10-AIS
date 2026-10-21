# Amendment proposal

status: approved
Proposed by: Kiro (specification agent), on behalf of the p2-003 spec review
Date: 2026-10-08

## Trigger
Spec-review blocker for p2-003-feasible-meal-plan-solving. Amended R-8 and
R-10 (A-002 and A-004, 2026-10-07) state that when a requirement has no
cost-eligible package, the requirement's cost cannot be computed and the
recipe must be dropped as evidence-absent. R-10's Check names a p2-003
fixture (`tests/features/plans/test_domain_solver.py`) for the recipe-level
drop. But p2-003's scope deliberately excludes cost and budget (no request
field for budget; the calculator's request does not carry `budget` per p2-002
C-4/Non-goals). If the recipe-level cost drop is not in p2-003's scope, R-8
and R-10 have no owner: the calculator emits the item-level signal, and no
layer drops the recipe. The constitution's check would have no path to
execute. Two resolutions are possible: (a) p2-003 consumes the calculator's
`MISSING_PACKAGE_DATA` signal and drops recipes (this conflicts with the
"cost out of scope" decision, and would drop most recipes since only about 6%
of edges are cost-eligible per the 2026-10-07 observation), or (b) R-8/R-10
are amended so the calculator's item-level signal is the sole cost
enforcement point in p2, with the recipe-level cost drop deferred to a later
budget feature. Option (b) is chosen.

## Current rule(s)
> **R-8 Non-fresh price offers are unavailable**
> - Rule: A retail price offer whose freshness signal is not positive must be
    >   treated as unavailable and must never be used, with or without a flag. The
    >   freshness signal is `freshness_status` on the `FULFILLS` edge; the positive
    >   value is `fresh`. Any other value (including `unknown`) is treated as
    >   unavailable. The freshness filter is applied at every layer that consumes
    >   the offer: the constraint-evidence-filtering layer (p2-001) filters the
    >   candidate pool it sees, and the cost calculation layer filters the packages
    >   it selects from, so that a non-fresh offer cannot reach cost output by any
    >   path. If no fresh offer exists for a requirement, the requirement's cost
    >   cannot be computed and the recipe must be dropped as evidence-absent. The
    >   check is a status comparison, not a timestamp comparison; a future
    >   timestamp-based freshness signal requires a further amendment and a
    >   producer that writes it.
> - Why: Q3; Behavioral Rule Price Snapshot Staleness; known temporal
    >   degradation of retail data; deployed `FULFILLS` schema carries a status, not
    >   a timestamp; the calculation API resolves ingredient names directly and
    >   therefore cannot rely on an upstream filter.
> - Check: Named test fixtures, at both layers. The filtering layer's fixture
    >   asserts an offer whose `freshness_status` is not `fresh` is excluded from
    >   the filtered pool. The calculator layer's fixture
    >   (`tests/features/calculator/test_domain_cost.py`) asserts a package whose
    >   `freshness_status` is not `fresh` is not selected, and that a requirement
    >   left with no fresh package carries the calculator's evidence-absent signal
    >   (`MISSING_PACKAGE_DATA`) with absent cost fields. The two layers are checked
    >   separately because they enforce the same rule at different boundaries.

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
> - Why: Q2; Behavioral Rule Compatible Unit Basis Required; deployed `FULFILLS`
    >   schema declares eligibility via `price_status`, `price_match_status`, and
    >   `price_basis`, not via `cost_basis_compatible`.
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

## Proposed change
Amend R-8 and R-10 so the calculator's item-level signal is the sole cost
enforcement point in p2, and the recipe-level cost drop is deferred to the
feature that owns budget evaluation. Replace the last two sentences of R-8's
rule and R-8's Check's second fixture, and the last paragraph of R-10's rule
and R-10's Check's second fixture.

> **R-8 (amended last two sentences of the rule):**
> "... If no fresh offer exists for a requirement, the requirement's cost
cannot be computed and the calculator reports the requirement with its
item-level evidence-absent signal. The recipe-level cost drop is owned by
p3-004-conversational-constraint-interface, which evaluates budget
constraints; until p3-004 ships the drop, the calculator's item-level signal
is the sole cost enforcement point. The check is a status comparison, not a
timestamp comparison; a future timestamp-based freshness signal requires a
further amendment and a producer that writes it."

> **R-8 (amended Check):**
> "... The calculator layer's fixture
> (`tests/features/calculator/test_domain_cost.py`) asserts a package whose
> `freshness_status` is not `fresh` is not selected, and that a requirement
> left with no fresh package carries the calculator's evidence-absent signal
> (`MISSING_PACKAGE_DATA`) with absent cost fields. **The recipe-level drop is
> asserted by the budget-owning feature's fixture once that feature ships; no
> p2-003 fixture asserts a recipe-level cost drop.**"

> **R-10 (amended last paragraph of the rule):**
> "... At the calculator layer, an ingredient whose resolved key has no
eligible package remains in the itemized result with null cost fields and
carries a `MISSING_PACKAGE_DATA` warning. The recipe-level cost drop is
owned by p3-004-conversational-constraint-interface; until p3-004 ships the
drop, the calculator's item-level signal is the sole cost enforcement point
in p2, and the recipe is not dropped for the absence of a cost-eligible
package."

> **R-10 (amended Check):**
> "... `tests/features/calculator/test_domain_cost.py` asserts a package whose
> `price_status` is not `estimated`, whose `price_match_status` is not
> `accepted`, or whose `price_basis` is not in the cost-convertible set, is
> excluded from cost; that a `package_volume` package is eligible and
> converted; and that a package with `cost_basis_compatible = FALSE` and an
> otherwise-convertible basis is eligible. **The recipe-level drop is asserted by p3-004's fixture once p3-004
ships; no p2 fixture asserts a recipe-level cost drop**"

## Impact
- **Completed features to re-check:** p2-002-cost-nutrition-calculation already
  emits the item-level `MISSING_PACKAGE_DATA` signal and does not perform a
  recipe-level drop; its behavior is unchanged. p2-001-constraint-evidence-
  filtering does not consume the calculator's cost signal; unchanged. No p1
  feature is affected.
- **In-flight features to re-check:** p2-003-feasible-meal-plan-solving — its
  spec asserts cost and budget out of scope and does not consume
  `MISSING_PACKAGE_DATA`. Once this amendment is approved the spec's C-1
  citation is valid and no spec edit is required.
- **Downstream:** p3-004-conversational-constraint-interface owns the
  recipe-level cost drop. When p3-004 ships, it either implements the drop
  (asserting R-8's and R-10's recipe-level check) or proposes a further
  amendment if the drop's shape must differ. The roadmap's p3-004 entry
  records the inherited obligation.
- **Behavioral change:** under the amended rule, a recipe with no cost-eligible
  package is retained in the plan pool (subject to the other constraints), and
  the calculator's item-level `MISSING_PACKAGE_DATA` signal is informational in
  p2. If a later budget feature ships, the recipe-level cost drop resumes under
  that feature's contract. No behavior in p2-002 or p2-003 changes as a result
  of this amendment.
- **No data migration required.**
- **Roadmap follow-up:** p2-003's entry is updated to remove the
  `MISSING_PACKAGE_DATA` input; p3-004's entry is updated to name the
  inherited recipe-level cost drop. The phase p2 exit criteria records the
  deferral across the p2→p3 boundary; the phase p3 entry names p3-004 as the
  owner.

## Version bump
1.5 -> 1.6

## Human decision
- Reviewer:
- Decision:
- Date:
