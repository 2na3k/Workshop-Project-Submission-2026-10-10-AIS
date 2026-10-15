# Amendment proposal

status: approved
Proposed by: Kiro (specification agent), on behalf of the p2-003 spec review
Date: 2026-10-08

## Trigger
Spec-review blocker for p2-003-feasible-meal-plan-solving. R-14 says a plan
must satisfy the request and otherwise name the binding constraint(s), and it
refers to "all permitted relaxations" without naming them. The existing
solver has a relaxation ladder (more recipe repeats, drop the no-consecutive
rule, widen nutrient max by 10%, loosen nutrient min by 10%) that predates
the constitution. Under the hierarchy, the constitution wins: the spec cannot
invent the permitted relaxation set. Two readings are possible — all existing
relaxations are permitted, or only nutrient-bound widening is — and they
produce different solver behavior. The relaxation set must be named in the
constitution.

## Current rule(s)
> **R-14 Feasibility floor names the binding constraint**
> - Rule: If, after filtering and all permitted relaxations, no set of retained
    >   recipes satisfies `horizon_days × meals_per_day`, the plan must not be produced
    >   and the response must name the binding constraint(s). A plan must never be
    >   returned as unfeasible while a producible plan exists.
> - Why: Proposal G-1; Behavioral Rule Plan Feasibility Floor.
> - Check: Named test fixture — `tests/features/plans/test_domain_solver.py`
    >   asserts (a) an infeasible request returns no plan with named binding
    >   constraint(s), and (b) a satisfiable request returns a plan rather than an
    >   unfeasible result.

## Proposed change
Replace the rule text and the check to name the permitted relaxation set, to
forbid structural relaxations, and to name the deterministic characterization
of a "binding constraint."

> **R-14 Feasibility floor names the binding constraint**
> - Rule: If, after filtering, dropping, and every permitted relaxation, no set
    >   of retained recipes satisfies `horizon_days × meals_per_day`, the plan must
    >   not be produced and the response must name the binding constraint(s) — a
    >   deterministic individually-binding set of constraints whose relaxation would admit a
    >   plan. A plan must never be returned as unfeasible while a producible plan
    >   exists. **Only nutrient-bound widening is a permitted relaxation: a
    >   nutrient `min` bound may be loosened downward and a nutrient `max` bound
    >   widened upward by a declared tolerance; the tolerance is applied to bounds,
    >   not to goals. Structural relaxations — allowing additional recipe repeats,
    >   or dropping the no-consecutive rule — are prohibited.** Cost and budget are
    >   out of scope for the feasibility floor; the feature that owns budget
    >   evaluation declares its own floor. If the solver cannot produce a plan
    >   within the permitted relaxation set, the response is a hard infeasibility
    >   failure naming the binding constraint(s); no structurally relaxed plan is
    >   returned.
> - Why: Proposal G-1; Behavioral Rule Plan Feasibility Floor; the existing
    >   solver's relaxation ladder predates the constitution and mixes nutrient and
    >   structural relaxations, which the R-14 floor must distinguish.
> - Check: Named test fixture — `tests/features/plans/test_domain_solver.py`
    >   asserts (a) an infeasible request returns no plan with a deterministic
    >   named binding constraint set; (b) a satisfiable request returns a plan
    >   rather than an unfeasible result; (c) a request satisfiable only under
    >   nutrient-bound widening returns a plan labeled relaxed and records the
    >   applied tolerance; (d) a request satisfiable only under a structural
    >   relaxation (additional repeats or dropped no-consecutive) returns a hard
    >   infeasibility failure, not a relaxed plan.

## Impact
- **Completed features to re-check:** p2-001-constraint-evidence-filtering
  consumes R-14 as a downstream rule; its own filtering does not implement a
  relaxation ladder, so no code change. p2-002-cost-nutrition-calculation does
  not touch the solver. p1 features are unaffected.
- **In-flight features to re-check:** p2-003-feasible-meal-plan-solving — its
  spec asserts this reading of R-14; once the amendment is approved the spec's
  AC-9/AC-10/AC-14/AC-14b are the amendment's checkable expression at the
  feature boundary. No spec edit is required; the spec already cites A-005.
- **Downstream:** p3-001, p3-002 consume p2-003's feasibility result and
  three-level reasoning structure; the amended rule's relaxation record and
  hard-infeasibility shape are the contract they consume. No p3 change is
  required by this amendment, but p3's specs should cite it.
- **Behavioral change:** under the amended rule, a request that the existing
  solver would satisfy only by allowing extra repeats or dropping the
  no-consecutive rule now returns a hard infeasibility failure. Requests
  satisfiable under nutrient-bound widening continue to return a plan, labeled
  relaxed. The relaxation set the constitution permits is now closed and
  named; future relaxations require further amendment.
- **No data migration required.**

## Version bump
1.4 -> 1.5

## Human decision
- Reviewer:
- Decision:
- Date:
