# Decisions - Cost and nutrition calculation

## Decisions

### D-1 Defer real-mart integration until the data-preparation price path parses
- Date: 2026-10-06
- Context: The plan names the canonical graph evidence → calculator repository
  interface, but `docs/findings/data-prep-price-path.md` records that dbt fails
  before producing real marts because `stg_retail_listing.sql` references
  missing nodes.
- Decision: Verify the repository projection and calculator service with the
  existing canonical-row/fake-driver fixture now. Defer real-mart end-to-end
  verification until the data-preparation owner repairs the price path; do not
  treat fixture evidence as real-data pipeline evidence.
- Affects: Plan integration row for canonical graph evidence, Revision notes,
  AC-5/AC-13 service evidence.
- Source: `docs/findings/data-prep-price-path.md`; p2 phase posture proceeds
  with fixtures.

### D-2 Defer p2-003 consumer integration to the p2-003 implementation context
- Date: 2026-10-06
- Context: The approved specification names p2-003 as the downstream consumer
  of the portion nutrient and consumed/package cost result contract, but p2-003
  is not implemented in the current working context.
- Decision: Verify the calculator's producer-side contract and public response
  now, retain a named deferred integration row, and require p2-003 to run the
  real calculator producer through its own consumer when that feature is
  implemented. The deferral is explicit and is not a claim that the interface
  is already verified.
- Affects: Plan integration row for calculator result contract → p2-003,
  Revision notes, downstream task assignment after plan approval.
- Source: `docs/sdd/roadmap.md` p2 feature table and approved p2-002 spec.

### D-3 Cost is request-dependent; the condition is request.budget is not None
- Date: 2026-10-06
- Context: The spec's AC-5 says "when cost is required" without naming the
  condition. The approved plan interprets it as request-dependent: `budget`
  present → cost is required, and an ingredient with no compatible, usable
  cost evidence is an evidence-absent drop for the recipe; `budget` null →
  cost is computed opportunistically, and an ingredient without cost evidence
  is retained with cost marked absent, the calculation succeeding.
- Decision: The plan's reading stands. It does not contradict any AC, edge
  case, or non-goal; the input contract's reference to a request-supplied
  budget limit is consistent with it. It is new observable behavior defined
  at plan stage and must be confirmed at phase p2 review, because p2-003
  consumes the condition as part of the shared portion nutrient and cost
  result contract.
- Alternatives: Cost always required — rejected (makes the spec's "when cost
  is required" phrase meaningless and would drop nutrition-only requests that
  the request shape supports). Cost required based on a different request
  field — rejected (no other candidate field exists in the request schema).
- Affects: AC-5's two test rows; the shared result contract with p2-003.
- Source: Plan Design §3; plan-review round 2, first nit.

### D-4 Policy citations are agent-derived; human sign-off deferred to phase review
- Date: 2026-10-06
- Context: The p2-002 spec's `## Clarifications` records that no human was
  consulted; the R-12 precedence order (branded > newest crawl > lexicographic
  product ID) and the other cited proposal decisions were transcribed by the
  specification agent from the proposal's Resolved Questions. R-12's
  constitutional Check asserts against that exact order, so the citation is
  load-bearing.
- Decision: Proceed on the agent-derived citations. Record them for phase
  review, where a human confirms that the transcribed precedence order matches
  the intended policy. If any citation is wrong, the spec is amended, the plan
  re-reviewed, and the affected tests updated.
- Alternatives: Pause the feature pending human sign-off — rejected (the
  citations trace to the proposal's already-resolved questions; the risk is a
  transcription error, not an open policy). Sign off inline before tasks —
  rejected (adds a review cycle for a confirmation that the phase review is
  already designed to give).
- Affects: R-12's Check; the spec's Clarifications block; the feature's tests
  that assert the precedence order.
- Source: p2-002 spec `## Clarifications`; plan-review round 2, second nit.
