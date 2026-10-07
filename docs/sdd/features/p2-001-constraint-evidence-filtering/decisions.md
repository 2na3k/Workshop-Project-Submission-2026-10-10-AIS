# Decisions - Constraint evidence filtering

## Decisions

### D-1 Inclusive 24-hour freshness threshold
- Date: 2026-10-05
- Context: R-8 requires offers past the freshness threshold to be unavailable and drop recipes as evidence-absent, but the threshold duration and boundary behavior were left to spec.
- Decision: Set freshness threshold to exactly 24 hours inclusive: an offer observed within 24 hours (inclusive bound) is fresh; any offer older than 24 hours is stale and drops with cause `evidence-absent`.
- Alternatives: Exclusive 24-hour boundary (rejected — creates ambiguity at the boundary); calendar day / midnight cutoff (rejected — sensitive to local timezones and observation timing).
- Affects: AC-8, `api.features.plan.filtering._evaluate_freshness`, `tests/features/calculator/test_domain_cost.py`.
- Source: Spec Clarifications Q1; Plan Design §3; Task T-2.

### D-2 Cause precedence: present-evidence-excludes over evidence-absent
- Date: 2026-10-05
- Context: A single recipe may trigger both present-evidence exclusion (e.g. declared severe allergen) and absent evidence (e.g. undeclared dietary flag) during candidate filtering.
- Decision: Top-level cause reports `present-evidence-excludes` when both causes occur. Subordinate per-constraint evaluations remain intact on `CandidateOutcome.evaluations` so downstream explanation stages can inspect all causes.
- Alternatives: Report absent-evidence first (rejected — hides known fatal safety violations); merge into a compound string (rejected — violates two-cause contract in roadmap shared vocabulary); discard absent-evidence records (rejected — p3 explanation layer needs constraint-level evaluation history).
- Affects: AC-11, AC-12, `api.features.plan.filtering._top_cause`, `tests/features/plan/test_filtering.py`.
- Source: Spec Clarifications Q2; Plan Design §3; Task T-3.

### D-3 Allergen severity defaults to severe from request
- Date: 2026-10-05
- Context: R-6 distinguishes severe allergen (drop) from mild allergen (warn with ingredient reference), but incoming allergy requests may omit explicit severity declarations.
- Decision: Allergen severity is sourced from the user request (`AllergyRequest.severity`). When omitted, severity defaults conservatively to `severe`, dropping any candidate with matching allergen evidence as `present-evidence-excludes`.
- Alternatives: Default to mild (rejected — violates conservative allergen safety policy R-6); reject request as invalid when severity is missing (rejected — reduces API usability when users specify allergen code alone).
- Affects: AC-13, `api.features.plan.filtering._evaluate_allergens`, `tests/features/dietary/test_domain_rules.py`.
- Source: Spec Clarifications Q3; Plan Design §3; Task T-1.

### D-4 Internal outcome models encapsulate drop causes without widening user response schema
- Date: 2026-10-05
- Context: Downstream plan solver (p2-003) and explanation (p3) layers need structured evaluation outcomes, distinct drop causes, and unmapped requirement tracking, while R-16 prohibits leaking audit-only provenance into user responses.
- Decision: Return `FilterResult` containing typed `CandidateOutcome`, `ConstraintEvaluation`, and `IngredientWarning` objects from `filter_candidates` to `PlanService`, while keeping `PlanResponse` user-facing schema scoped to validated summary and meal selections. Unmapped candidate sets are tracked via `FilterResult.unmapped_requirements` rather than collapsing into candidate drop causes.
- Alternatives: Attach drop causes directly to public Pydantic response models (rejected by R-16); collapse empty candidate sets into `evidence-absent` drop causes (rejected — conflates unmappable concepts with candidate-level constraint evaluation).
- Affects: AC-10, AC-14, AC-16, R-16, R-17, `api.features.plan.models`, `api.features.plan.filtering`, `api.features.plan.service`.
- Source: Plan Design §4; Tasks T-3, T-5, T-6.

## Overrides
None.

## Open follow-ups

### F-A — Freshness predicate uses a timestamp
- Status: open follow-up
- Date: 2026-10-07
- Finding: `plan/filtering.py::_evaluate_freshness` applies a 24-hour timestamp
  comparison when `offer_observed_at` is present. Amended R-8 defines freshness
  by `freshness_status == "fresh"` and does not authorize timestamp comparison.
- Route: p2-001 implementation
- Source: p2-002 plan, Design §0 / Revision notes F-A.

### F-B — Cost eligibility gates on `cost_basis_compatible`
- Status: open follow-up
- Date: 2026-10-07
- Finding: `plan/filtering.py::_evaluate_cost_basis` requires
  `cost_basis_compatible is True`. Amended R-10 defines eligibility through
  `price_status`, `price_match_status`, and a convertible `price_basis`; the
  compatibility flag is informational.
- Route: p2-001 implementation
- Source: p2-002 plan, Design §0 / Revision notes F-B.
