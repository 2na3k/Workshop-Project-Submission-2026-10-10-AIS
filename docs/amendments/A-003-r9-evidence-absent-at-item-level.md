# Amendment proposal

status: approved
Proposed by: Kiro (specification agent), on behalf of phase review for p2-002
Date: 2026-10-07

## Trigger
Phase-review finding routed to `constitution` from the p2-002 spec review. Two
problems in R-9:

1. R-9 says "the recipe must be dropped as evidence-absent" and its named check
   asserts "a requirement with no profiled candidate drops with an
   evidence-absent cause." The calculator — the layer named by the rule's own
   Check — has no recipe pool and no requirement pool to drop from. It processes
   one ingredient at a time. The drop is p2-003's (the plan solver's) action on
   the eligible pool.
2. R-9 as written permits a partial recipe to be evaluated: "a nutrient missing
   from every contributing ingredient remains unknown" (the p2-002 spec's
   reading) treats a per-nutrient total as evaluable when *some* ingredients
   contribute a value. An upper-bound constraint (sodium ≤ X, for example)
   would then pass on an undercounted total, which is exactly the R-5 failure
   the constitution forbids.

## Current rule(s)
> **R-9 Nutrient constraints require a profile**
> - Rule: A candidate with no nutrition profile must not satisfy any nutrient
    >   constraint it would serve and must not be treated as zero. If no candidate for a
    >   requirement has a profile, the nutrient constraint cannot be evaluated and the
    >   recipe must be dropped as evidence-absent.
> - Why: Behavioral Rule Missing Nutrition Profile.
> - Check: Named test fixture —
    >   `tests/features/calculator/test_domain_nutrition.py` asserts a profile-less
    >   candidate contributes no value (not zero) and that a requirement with no
    >   profiled candidate drops with an evidence-absent cause.

## Proposed change

> **R-9 Nutrient constraints require a profile**
> - Rule: A nutrient constraint is evaluable only when every contributing
    >   ingredient carries a non-null value for that nutrient. A candidate with no
    >   nutrition profile must not satisfy any nutrient constraint it would serve
    >   and must not be treated as zero. At the calculator layer, an ingredient
    >   whose resolved candidates carry no usable nutrient value remains in the
    >   itemized result with null nutrient fields (never zero) and carries a
    >   `PARTIAL_NUTRITION_DATA` warning. The recipe-level drop is **p2-003's**
    >   responsibility: for each nutrient independently, if any contributing
    >   ingredient lacks a value, the recipe is dropped from the eligible pool for
    >   that nutrient's constraint with an evidence-absent cause, reading the
    >   calculator's `PARTIAL_NUTRITION_DATA` signal as that evidence. A recipe may
    >   be evaluable for one nutrient and not another; the drop applies to the
    >   affected constraint, not the whole recipe.
> - Why: Behavioral Rule Missing Nutrition Profile; an upper-bound constraint
    >   evaluated against an undercounted total would pass on incomplete data,
    >   which is the failure R-5 forbids.
> - Check: Named test fixtures, at both layers.
    >   `tests/features/calculator/test_domain_nutrition.py` asserts a profile-less
    >   candidate contributes no value (not zero) and that the item carries
    >   `PARTIAL_NUTRITION_DATA`. p2-003's fixture asserts that for a nutrient whose
    >   contributing set is incomplete, the nutrient constraint is treated as
    >   evidence-absent and the recipe is dropped for that constraint only, while a
    >   nutrient whose contributing set is complete remains evaluable.

## Impact
- **Completed features to re-check:** none. No completed feature asserts the
  recipe-level drop at the calculator layer.
- **In-flight features to re-check:** p2-002-cost-nutrition-calculation — the
  spec's AC-2 must be strengthened. It currently says "a nutrient missing from
  every contributing ingredient remains unknown." Under the amended rule, a
  nutrient missing from **any** contributing ingredient makes the total
  non-evaluable for that nutrient. The spec also needs to note that
  `PARTIAL_NUTRITION_DATA` signals that the affected nutrient's total is
  untrustworthy, not merely that some field is null. p2-002's C-2 already
  assumes the "calculator reports absence; consumer drops" reading, but its
  scope needs the per-nutrient qualifier.
- **Downstream:** p2-003-feasible-meal-plan-solving owns the per-nutrient drop
  under the amended rule. Its plan must implement per-nutrient evaluability,
  not per-recipe. p3-002's three-level explanation reads the evidence-absent
  cause; the cause's scope is now per-nutrient, which the explanation layer
  must respect. No p3-002 change is required by this amendment, but its plan
  should be aware.
- **Behavioral change:** recipes with partially-missing nutrient data are no
  longer evaluable for the affected nutrient's constraints. Under the previous
  reading, they might have been evaluated on an undercounted total. The
  amendment makes the drop explicit and assigns it to p2-003.
- **No data migration required.**

## Version bump
1.2 -> 1.3

## Human decision
- Reviewer:
- Decision:
- Date:
