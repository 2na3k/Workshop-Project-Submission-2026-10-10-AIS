# Decisions - Cost and nutrition calculation

## Decisions

### D-1 Request ingredient limit
- Date: 2026-10-07
- Context: Spec AC-19 requires bounding the calculation request with a single declared constant `MAX_REQUEST_INGREDIENTS`, but does not prescribe the exact integer value.
- Decision: `MAX_REQUEST_INGREDIENTS` is set to 100, preserving the pre-existing inline request limit in `schemas.py`.
- Alternatives: Other upper bounds (e.g. 50 or 200) were rejected to preserve deployed behavior and prevent breaking existing callers.
- Affects: AC-19, calculator request schema.
- Source: p2-002 plan, Design §2 (task T-21).

### D-2 Package count tolerance
- Date: 2026-10-07
- Context: Floating-point division artefacts (e.g. `300.00000001 / 100` yielding `3.0000000001`) could cause `math.ceil` to compute an unnecessary extra package.
- Decision: Compute the package count as `max(1, ceil(Q / S - 1e-9))` to avoid a spurious extra package from floating-point representation.
- Alternatives: Strict `ceil(Q / S)` without tolerance (rejected due to float imprecision); decimal arithmetic (rejected for performance and consistency with float schema).
- Affects: AC-4, AC-11, package selection.
- Source: p2-002 plan, Design §2 (task T-11).

### D-3 Internal trace return
- Date: 2026-10-07
- Context: Spec AC-18 and R-16 require audit-only provenance (confidence, winner identity, ranks) to be retained in an internal trace while excluding them from the user-facing response.
- Decision: `CostNutritionService.calculate` returns `(CostNutritionResponse, CalculationTrace)`. The calculator router unpacks the tuple and returns the response only; trace exposure remains p3-001's responsibility.
- Alternatives: Storing trace in request state or global context (rejected: violates statelessness); passing a query parameter to conditionally expose trace in the public endpoint (rejected: violates R-16 and spec non-goals).
- Affects: AC-18, service/router interface.
- Source: p2-002 plan, Design §2 (tasks T-20, T-23).

### D-4 — `OfferRef` carries `confidence`, `source_snapshot_id`, `mapping_version`

- Date: 2026-10-17
- Status: adopted (reopen; resolves F-P3-1's upstream half)
- Context: p3-002's trace-side R-16 conformance check requires
  `confidence`, `source_snapshot_id`, and `mapping_version` on the trace.
  The calculator's `OfferRef` carried only `food_key`, `listing_name`,
  `retailer`, so the fields were unreachable downstream. All three live on
  the deployed `FULFILLS` edge and were already projected by the calculator's
  query.
- Decision: `OfferRef` gains `confidence: float | None`,
  `source_snapshot_id: str | None`, `mapping_version: str | None`.
  `CostNutritionService.inspect_candidates` populates them from the winning
  `FULFILLS` edge's `confidence`, `source_snapshot_id`, and `mapping_version`.
  `RetailSKU` carries them (with projection unchanged if already present).
- Alternatives: read `FoodConcept.normalization_version` instead of
  `FULFILLS.mapping_version` (rejected: the design doc's `FULFILLS` edge
  carries `mapping_version` for the offer's mapping; `FoodConcept` carries the
  vocabulary's normalization version, which is a different concept).
- Affects: `calculator/models.py` (`OfferRef`, `RetailSKU` if needed),
  `calculator/service.py` (`inspect_candidates`), `calculator/repository.py`
  (projection, if not already present).
- Source: p3-002 F-P3-1 resolution; p3-001's plan Revision notes.

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

### F-A — p2-001 freshness predicate: timestamp branch retained as latent
- Date: 2026-10-07; disposition updated 2026-10-08
- Status: resolved — retained as latent
- F-A: `plan/filtering.py::_evaluate_freshness` contains a timestamp branch
  (`now - offer_observed_at <= 24h`) that predates amended R-8. The branch is
  retained as a defensive fallback. `offer_observed_at` is not populated
  against the deployed schema (the `FULFILLS` edge carries `freshness_status`,
  not a timestamp), so the branch is unreachable in production and the
  effective rule matches amended R-8 (`freshness_status == "fresh"`).
- Consequence: if `offer_observed_at` is ever populated, the branch will fire
  with a rule amended R-8 forbids. The rule mismatch is dormant, not absent.
  A future schema change that adds a timestamp property should revisit this
  branch and either drop it or re-amend R-8.
- Affects: p2-001 `plan/filtering.py::_evaluate_freshness`; F-A's disposition.
  See p2-001's `decisions.md` for the p2-001-side record.
- Source: p2-002 plan, Design §0 and Revision notes F-A.

### F-B — p2-001 cost-basis predicate: behavioral, open
- Date: 2026-10-07
- Status: open follow-up routed to p2-001
- F-B: `plan/filtering.py::_evaluate_cost_basis` gates on
  `cost_basis_compatible is True`; amended R-10 makes that flag informational.
  Real data impact: ~63 `package_mass` rows with
  `cost_basis_compatible = FALSE` are legitimately cost-eligible and p2-001
  currently drops them. The fix is to replace the gate with
  `price_status == "estimated"` AND `price_match_status == "accepted"` AND
  `price_basis in {package_mass, package_volume}`. p2-001 owns the
  correction.
- Affects: p2-001 `plan/filtering.py::_evaluate_cost_basis`; p2-002's C-9
  coverage note (which will drift upward once p2-001 ships the fix).
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
