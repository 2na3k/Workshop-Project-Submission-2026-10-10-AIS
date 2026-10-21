# Amendment proposal

status: approved
Proposed by: Kiro (specification agent), on behalf of phase review for p2-002
Date: 2026-10-07

## Trigger
Phase-review finding routed to `constitution` from the p2-002 spec review. R-8
says "a retail price offer past its freshness threshold" and its named check is
"parameterized over the spec threshold." The deployed schema carries no
timestamp on which a threshold could be evaluated: the `FULFILLS` edge
declares `freshness_status` as a two-value status (`fresh` / `unknown`), set at
load time. A status field cannot be "past a threshold." Additionally, the
calculation API resolves ingredient names directly and does not pass through
p2-001's filtering, so a "the calculator trusts its input" reading would let
non-fresh offers reach cost output. The rule must apply at every layer that
consumes the offer, and the check must be a status comparison, not a threshold.

## Current rule(s)
> **R-8 Stale price offers are unavailable**
> - Rule: A retail price offer past its freshness threshold must be treated as
    >   unavailable and must never be used, with or without a flag. If no fresh offer
    >   exists for a requirement, the recipe must be dropped as evidence-absent. The
    >   threshold value is set in the spec, not here.
> - Why: Q3; Behavioral Rule Price Snapshot Staleness; known temporal degradation of
    >   retail data.
> - Check: Named test fixture — `tests/features/calculator/test_domain_cost.py`
    >   parameterized over the spec threshold asserts an offer past the threshold is
    >   excluded and that no fresh offer drops the recipe with an evidence-absent cause.

## Proposed change

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

## Impact
- **Completed features to re-check:** p2-001-constraint-evidence-filtering —
  its freshness predicate must read `freshness_status`. The CHANGELOG entry
  currently says "offers older than 24 hours are excluded with inclusive
  24-hour boundary," which is timestamp language against a status field. If
  p2-001's implementation is timestamp-based, it is non-conformant with the
  amended rule. If it is status-based, only the CHANGELOG wording needs
  correcting. **The amended rule does not depend on p2-001 being correct:** the
  calculator enforces the same rule at its own boundary, so a p2-001 bug does
  not let non-fresh offers reach cost output.
- **In-flight features to re-check:** p2-002-cost-nutrition-calculation — its
  spec's C-1 must be revised. The spec currently says the calculator trusts its
  freshness-filtered input; the amended rule says the calculator checks
  `freshness_status == "fresh"` on each candidate package. The spec also needs
  to add the freshness check to the package-selection AC.
- **Downstream:** p2-003-feasible-meal-plan-solving consumes the shared cost
  result contract; the contract's freshness signal is status-based under the
  amended rule. p3-001, p3-002 — no impact.
- **Behavioral change:** non-fresh packages are excluded from cost selection at
  the calculator layer. Under the deployed data, the eligible set is bounded by
  `freshness_status == "fresh"` (the 2026-10-07 price-stats distribution shows
  all `estimated`/`accepted` rows already have `freshness_status = "fresh"`;
  the amendment makes the exclusion explicit for the 8,463 `unavailable` rows
  and any future non-fresh rows).
- **No data migration required.** The deployed graph already carries
  `freshness_status` on every edge.

## Version bump
1.1 -> 1.2

## Human decision
- Reviewer:
- Decision:
- Date:
