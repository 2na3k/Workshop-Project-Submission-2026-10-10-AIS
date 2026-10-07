# Decisions - Cost and nutrition calculation

## Decisions

### D-1 Request ingredient limit
- Date: 2026-10-07
- Status: adopted
- Decision: `MAX_REQUEST_INGREDIENTS` is 100, preserving the pre-existing inline
  request limit.
- Affects: AC-19, calculator request schema.
- Source: p2-002 plan, Design §2.

### D-2 Package count tolerance
- Date: 2026-10-07
- Status: adopted
- Decision: Compute the package count as `max(1, ceil(Q / S - 1e-9))` to avoid
  a spurious extra package from floating-point representation.
- Affects: AC-4, AC-11, package selection.
- Source: p2-002 plan, Design §2.

### D-3 Internal trace return
- Date: 2026-10-07
- Status: adopted
- Decision: `CostNutritionService.calculate` returns
  `(CostNutritionResponse, CalculationTrace)`. The calculator router unpacks
  the tuple and returns the response only; trace exposure remains p3-001's
  responsibility.
- Affects: AC-18, service/router interface.
- Source: p2-002 plan, Design §2.

### C-1 Freshness at both consuming layers
- Date: 2026-10-07
- Decision: The calculator selects a price package only when
  `freshness_status == "fresh"`; p2-001 applies its own filter. Freshness is a
  status comparison, not a timestamp calculation.
- Affects: R-8, AC-5, cost eligibility.
- Source: Spec clarification C-1.

### C-2 Item-level absence; recipe-level drop belongs to p2-003
- Date: 2026-10-07
- Decision: Emit `MISSING_PACKAGE_DATA` when no eligible package exists and
  `PARTIAL_NUTRITION_DATA` with the missing canonical nutrient names. Keep the
  item in the calculation response; p2-003 drops recipes for absent evidence,
  applying partial-nutrition drops per nutrient.
- Affects: R-5, R-9, AC-2, AC-5.
- Source: Spec clarification C-2.

### C-3 Resolver ambiguity is separate from confidence
- Date: 2026-10-07
- Decision: Keep the resolver's string-score rejection rules (top score below
  0.86 or top-two gap below 0.05). These do not impose a floor on
  `FULFILLS.confidence`; record resolver confidence in the internal trace.
- Affects: R-13, AC-17.
- Source: Spec clarification C-3.

### C-4 Cost package eligibility and volume conversion
- Date: 2026-10-07
- Decision: Require estimated price, accepted price match, fresh status, a
  `package_mass` or `package_volume` basis, SGD, a positive reference price,
  and a positive package amount for that basis. Convert package volume to grams
  through the domain unit converter without a user-visible warning.
  `cost_basis_compatible` is informational and does not gate selection.
- Affects: R-8, R-10, AC-5, AC-13, AC-20.
- Source: Spec clarification C-4.

### C-5 Public and audit field split
- Date: 2026-10-07
- Decision: The user response carries ingredient, canonical key, listing name,
  retailer, separate consumed and retail costs, nutrients, and warnings.
  Confidence, food/source identifiers, mapping versions, ranks, and approval
  status remain in the trace.
- Affects: R-16, AC-18.
- Source: Spec clarification C-5.

### C-6 Best-score ordering
- Date: 2026-10-07
- Decision: Rank eligible packages by lowest unit price, lowest retail package
  cost, highest confidence, then lexicographic `(food_key, retailer,
  listing_name)`.
- Affects: R-13, AC-11.
- Source: Spec clarification C-6.

### C-7 No-floor selection can choose a mislinked offer
- Date: 2026-10-07
- Decision: A lower-priced package may outrank a more expensive package even
  when its mapping confidence is lower. Retain runner-up identity and confidence
  in the trace to make the ranking auditable.
- Affects: R-13, AC-10, AC-11.
- Source: Spec clarification C-7.

### C-8 Nutrition precedence applies per nutrient
- Date: 2026-10-07
- Decision: Select each nutrient independently from accepted candidates that
  have a non-null value for that nutrient; record each winner in the trace.
- Affects: R-12, AC-6, AC-7, AC-8.
- Source: Spec clarification C-8.

### C-9 Cost coverage reflects the graph snapshot
- Date: 2026-10-07
- Decision: Cost availability is bounded by the graph's current offer snapshot
  (approximately 607 of 9,700 candidate edges were eligible in the
  2026-10-07 observation); freshness is not recomputed at request time.
- Affects: AC-5, AC-20; data coverage expectations.
- Source: Spec clarification C-9 and graph stats dated 2026-10-07.

### F-A/F-B — p2-001 follow-ups
- Date: 2026-10-07
- Status: open follow-ups routed to p2-001
- F-A: `plan/filtering.py::_evaluate_freshness` uses a 24-hour timestamp check
  when `offer_observed_at` exists; amended R-8 requires the `freshness_status`
  comparison. p2-001 owns the correction.
- F-B: `plan/filtering.py::_evaluate_cost_basis` gates on
  `cost_basis_compatible`; amended R-10 makes that flag informational.
  p2-001 owns the correction.
- Source: p2-002 plan, Design §0 and Revision notes F-A/F-B.

### F-C — Real data-preparation path deferred
- Date: 2026-10-07
- Status: deferred
- Decision: The real data-preparation marts to Neo4j demonstration is deferred
  because the dbt project does not parse, as documented in
  `docs/findings/data-prep-price-path.md`. Repository-to-service integration
  uses recorded `FULFILLS` rows and a mocked Neo4j driver; repository,
  calculator, and router code run for real.
- Source: p2-002 plan, Revision notes F-C; data-prep price-path finding.

### F-D — Response schema test location
- Date: 2026-10-07
- Status: phase-review note
- Decision: The R-16 response field-set assertion is located at
  `tests/features/calculator/test_response_schema.py` to keep it with the
  calculator feature. The constitution names `tests/api/test_response_schema.py`;
  this path divergence is recorded for phase review, with no amendment drafted.
- Source: p2-002 plan, Revision notes F-D.

### F-E — Router file added to T-20
- Date: 2026-10-07
- Status: resolved by plan revision
- Decision: The approved plan revision added `router.py` to T-20 so the router
  can unpack the service tuple and return only the public response.
- Source: p2-002 plan, Revision notes F-E.

## Overrides
None.
