# Plan - Cost and nutrition calculation

## Approach

- **Chosen:** Prove-and-fix the existing calculator in place. Keep the current
  router/service/repository/domain layering; rewrite the three provably wrong
  mechanisms (cost eligibility + `package_volume`, per-nutrient conflict
  precedence, user/trace field split) against the deployed `FULFILLS` schema,
  add a `CalculationTrace` dataclass the router discards, and add a
  `MAX_REQUEST_INGREDIENTS` constant. One working context: the `calculator`
  feature package plus its tests.
- **Rejected:** Rewrite the calculator as a new feature package behind a new
  endpoint — rejected because the spec is a prove-and-fix against the deployed
  shape (R-1), AC-18 keeps the public field set, and a parallel package would
  duplicate the resolver/repository and risk a second vocabulary (R-1, R-3).

## Design

### §0 Baseline inventory (evidence-based)

Run on 2026-10-07 in WSL via `uv run --package remy-api pytest -q
remy/api/tests/features/calculator`. Code read at
`SystemCode/remy/api/src/api/features/calculator/*` and
`SystemCode/remy/domain/src/domain/*`. Schema read at
`SystemCode/docs/neo4j_db_design.md` (`EDGE_FULFILLS`).

- **`CostNutritionRepository.fetch_food_facts`** (`repository.py`): returns
  `dict[str, list[FoodFacts]]` — one `FoodFacts` **per accepted FULFILLS edge**,
  grouped by `canonical_key`. It does **not** raise on an empty result; it
  returns a `dict` and a missing key is simply absent. `QUERY_B` filters
  `FULFILLS {approval_status: 'accepted'}` in the `OPTIONAL MATCH`, so
  non-accepted edges never arrive and the service cannot distinguish
  "no accepted edge" from "no edge."
- **Repository property-name drift (R-1):** `QUERY_B` reads
  `ful.mapping_confidence AS confidence`. The deployed `FULFILLS` schema
  declares `confidence` (there is **no** `mapping_confidence`). This is an R-1
  violation to fix in place: read `ful.confidence AS confidence`.
- **Repository field gaps:** `QUERY_B` does **not** select
  `f.saturated_fat_g` or `f.cholesterol_mg`, and `NutrientProfile(...)` in
  `fetch_food_facts` omits both; they default to `None`. The deployed `Food`
  node carries nine canonical nutrients including both. `QUERY_B` also does not
  select `price_status`, `price_match_status`, `freshness_status`,
  `package_volume_ml`, `nutrition_rank`, `selection_priority`, or `food_key` —
  all required by eligibility/precedence and all present on the deployed edge.
- **Service consumption** (`service.py`): `food = facts.get(key)` then
  `food.nutrients`, `food.packages`, `food.canonical_name`. Because
  `fetch_food_facts` returns a **list** per key, `food` is a `list[FoodFacts]`
  and `.nutrients` would raise `AttributeError`. The current path only works
  when the grouping happens to carry one element and callers mock a single
  object; it has **no** per-nutrient selection and **no** accepted/unresolved
  distinction. This is a baseline defect to fix (service must select over the
  candidate list).
- **`select_package`** (`domain/cost.py`): ranking key is
  `(unit_price, count*price, -confidence, fdc_id, retailer, listing_name)` via
  `min(...)` — i.e. unit price → retail cost → confidence (desc) →
  lexicographic. Eligibility gate is
  `price_basis == "package_mass"` **AND** `cost_basis_compatible is True` AND
  `package_mass_g > 0` AND `package_price(...) is not None`
  (`package_price` requires `currency == "SGD"` and
  `reference_price_minor > 0`). **No** `price_status`, **no**
  `price_match_status`, **no** `freshness_status`, **no** `package_volume`
  path. Lexicographic tie-break uses `fdc_id` first, not
  `(food_key, retailer, listing_name)`.
  **Contradicts C-4/R-10:** `cost_basis_compatible` must not gate, and
  `package_volume` must be eligible. **Contradicts C-1/R-8:** no freshness
  check. **Contradicts AC-20:** no `price_status`/`price_match_status` check.
- **`consumed_cost`** (`domain/cost.py`): `price * grams / package_mass_g`;
  returns `None` when `package_mass_g` is falsy. No `package_volume → grams`
  conversion.
- **`domain.units.to_grams`** (`domain/units.py`): signature
  `to_grams(quantity, unit, *, grams_per_tbsp=None, grams_per_piece=None,
  density_g_per_ml=None) -> tuple[float, list[str]]`. Keyword args are
  **deprecated and ignored**. Warning code is `UNIT_ASSUMED_GRAMS` (non-mass
  units); mass units return `[]`. Raises `UnitConversionError` on unsupported
  unit, `DomainError` on non-finite/non-positive. The feature-local
  `domain/conversion.py` is a shim that re-raises `MissingConversionError` as
  `MissingUnitConversion` and other `DomainError` as `UnitConversionAppError`.
- **`schemas.py`** request: `CostNutritionRequest{servings: int (ge=1,le=1000),
  budget: float|None=None, ingredients: list[IngredientRequest]
  (min_length=1, max_length=100)}`; `IngredientRequest{name, quantity:
  PositiveFloat, unit: Literal["g","kg","ml","tbsp","pcs"]}` with `extra=forbid`.
  Response: `CostNutritionResponse{status:"success", servings, summary,
  itemized}`; `ItemizedCalculation` exposes `fdc_id` and `matched_package`
  (`retailer, package_title, package_price_sgd, package_amount_g,
  package_count`); `Nutrients` has 11 fields (9 canonical + `calcium_mg`,
  `iron_mg`). The `budget` field is present but out of scope (spec Non-goals).
  **Contradicts AC-18/C-5:** `fdc_id` and the extra `matched_package` fields
  must leave the user payload. The inline `max_length=100` is **not** a named
  `MAX_REQUEST_INGREDIENTS` constant (AC-19).
- **Error envelope (custom):** `app.exception_handler(AppError)` in `main.py`
  renders `core.errors.error_envelope` →
  `{"error": {"code", "message", "details":[{field,issue}], "timestamp"}}`.
  `RequestValidationError` → `{"error":{"code":"VALIDATION_ERROR", ...}}` at
  422. Calculator `AppError`s: `UNRESOLVABLE_INGREDIENT` (400),
  `AMBIGUOUS_INGREDIENT` (400), `MISSING_UNIT_CONVERSION` (400). This is a
  **custom** envelope, so the test strategy asserts it on a rejection AC.
- **T-2 `RetailSKU.__post_init__` interval check:** **removed** (commented out
  in `models.py`). Confidence is not interval-enforced — consistent with the
  spec's "records confidence as observed, applies no interval check."
- **`FoodFacts.observed_at`:** **present** (`models.py` field; `repository.py`
  reads `ful.observed_at`). The deployed `FULFILLS` edge has **no**
  `observed_at` column (freshness is `freshness_status`, a status not a
  timestamp). `observed_at` is therefore always `None` from the real graph;
  it is dead and is not used by cost selection. No behavior depends on it.
- **Pre-existing test failures (3), captured 2026-10-07:**
  - `test_domain_conversion.py::test_fixed_units_and_ml_warning` — asserts
    `to_grams(10,"ml") == (10, ["ML_ASSUMED_GRAMS"])`; code returns
    `["UNIT_ASSUMED_GRAMS"]`. Stale test (wrong warning code).
  - `test_domain_conversion.py::test_component_units_require_positive_facts` —
    asserts `to_grams(2,"tbsp",grams_per_tbsp=15) == (30,[])` and that `"pc"`
    raises; code ignores the kwarg and returns `(30, ["UNIT_ASSUMED_GRAMS"])`,
    and `"pc"` converts (does not raise). Stale test (old component-facts API).
  - `test_resolver.py::test_normalization_and_alias` — `resolve("oatmeal",
    ["rolled oats"])` now raises `AmbiguousIngredient` because the single-key
    candidate list defeats the alias path's `normalized_keys` membership.
    Stale test (alias requires the alias target to be in `canonical_keys`).
- **p2-001 freshness predicate** (`plan/filtering.py::_evaluate_freshness`):
  **timestamp-based when `offer_observed_at` is present** — it compares
  `now - observed <= timedelta(hours=24)` and only falls back to
  `freshness_status in {fresh,current}` when `offer_observed_at is None`. Under
  amended R-8 the signal is a **status**, not a timestamp. **Recorded as a
  p2-001 finding to route** (F-A below). The calculator's independent
  `freshness_status == "fresh"` check still satisfies R-8 at its own boundary,
  so this does not block p2-002.
- **p2-001 cost-eligibility predicate**
  (`plan/filtering.py::_evaluate_cost_basis`): uses
  `ingredient.cost_basis_compatible is True`. Under amended R-10,
  `cost_basis_compatible` is **not** the gate. **Recorded as a p2-001 finding
  to route** (F-B below). p2-002's own eligibility is corrected independently.

#### Per-AC status table

| AC | Status | Evidence |
|---|---|---|
| AC-1 scale nutrients, recipe total, per-serving | present | `domain.nutrients.scale_nutrients/sum_nutrients/per_serving` correct |
| AC-2 per-nutrient null when any ingredient missing + name nutrients | needs-fix | `sum_nutrients` nulls only when *all* missing; must null when *any* missing; warning does not name nutrients |
| AC-3 consumed vs retail distinct, sub-package | present | `consumed_cost` = P·Q/S; retail = count·P; distinct fields exist |
| AC-4 multi-package ceil(Q/S)·P | needs-fix | `count=max(1,ceil(grams/mass))`; no float tolerance; retail uses count·price (ok) but ceil tolerance unspecified |
| AC-5 ineligible excluded → MISSING_PACKAGE_DATA, summary absent | needs-fix | eligibility wrong (see §0); MISSING_PACKAGE_DATA emitted; summary absence logic present |
| AC-6 branded>generic per nutrient | absent | no source-kind precedence in service |
| AC-7 same-source tie-break (rank,priority,food_key) | absent | fields not selected; no precedence |
| AC-8 order-independent determinism | needs-fix | summation order fixed by list, but selection absent |
| AC-9 only accepted candidates usable | needs-fix | query filters accepted but service lacks unresolvable-when-none path |
| AC-10 single confidence-0 package selected + trace | needs-fix | no-floor select exists; no trace |
| AC-11 unit price→retail→confidence→lexicographic + runner-up trace | needs-fix | ranking close but lexicographic uses fdc_id; no trace; no volume unit price |
| AC-12 confidence 0 and 1 both valid | present | no floor; `-confidence` tie-break |
| AC-13 package_volume eligible + silent gram conversion | absent | no volume path |
| AC-14 UNIT_ASSUMED_GRAMS on nutrient non-mass unit | needs-fix | code emits it; message text differs; ok for nutrient path |
| AC-15 unsupported unit / non-finite quantity rejects whole request | present | `to_grams` raises → `MissingUnitConversion`/`UnitConversionAppError`; schema validates finite/positive |
| AC-16 unresolvable or no-accepted-candidate rejects | needs-fix | `UnresolvableIngredient` on empty candidates; no-accepted-edge path missing |
| AC-17 ambiguity reject (<0.86 or gap<0.05) | present | `resolver.resolve` enforces both |
| AC-18 user payload field set; provenance in trace | needs-fix | `fdc_id`+`matched_package` extras exposed; no trace |
| AC-19 servings/empty/over-limit rejected pre-calc via MAX_REQUEST_INGREDIENTS | needs-fix | servings ge=1 ok; list bounds inline, not a named constant |
| AC-20 individual eligibility conditions exclude | needs-fix | same as AC-5 eligibility defect |

### §1 Target design

**Repository (`repository.py`).** Correct `QUERY_B` to the deployed names and
select the full evidence contract per accepted edge: `ful.confidence AS
confidence` (drop `mapping_confidence`), add `f.saturated_fat_g`,
`f.cholesterol_mg`, `f.food_key AS food_key`, `ful.price_status`,
`ful.price_match_status`, `ful.freshness_status`, `ful.package_volume_ml`,
`ful.nutrition_rank`, `ful.selection_priority`. Keep returning
`dict[str, list[FoodFacts]]` (one `FoodFacts` per accepted edge); the service
selects across the list. Populate the nine canonical nutrients on
`NutrientProfile`. Remove the dead `observed_at` read (schema has no column).

**Models (`models.py`).** Extend `RetailSKU` with `price_status`,
`price_match_status`, `freshness_status`, `price_basis`, `package_volume_ml`,
`food_key`; extend `FoodFacts` candidate rows with `source_kind` (from
`nutrition_source`), `nutrition_rank`, `selection_priority`, `food_key`.
Confidence stays non-interval-checked (keep the `__post_init__` removed).

**Domain cost (`domain/cost.py`).** Rewrite eligibility to the C-4/R-10/R-8
rule: `price_status == "estimated"` AND `price_match_status == "accepted"` AND
`freshness_status == "fresh"` AND `price_basis in {"package_mass",
"package_volume"}` AND `currency == "SGD"` AND `reference_price_minor` present
and positive AND the basis amount present and positive (`package_mass_g` for
`package_mass`, `package_volume_ml` for `package_volume`).
`cost_basis_compatible` is **not** read. For `package_volume`, convert
`package_volume_ml` to grams via `domain.units.to_grams(amount, "ml")`
(silent; discard the warning). Unit price = `price / grams_amount` so volume
and mass rank like-with-like. Ranking: unit price → retail package cost →
`-confidence` → `(food_key, retailer, listing_name)` lexicographic. Retail
count = `ceil(Q / S)` with a small tolerance (`math.ceil(q/s - 1e-9)`,
clamped to `>= 1`) so a float artefact does not add a spurious package.
`consumed_cost` and `select_package` operate on the converted gram amount.

**Nutrient precedence (new `domain/nutrition_select.py` or extend
`domain/cost.py`).** Add `select_nutrient_value(candidates, field)` applying,
per nutrient, over accepted candidates with a non-null value for that field:
branded (`source_kind == "crawler_fdc_profile"`) over generic
(`fooddata_central` or any other/absent), then smallest
`(nutrition_rank, selection_priority, food_key)` with missing rank/priority
sorting last. Return the chosen value and the winning candidate (for the
trace). The service composes the per-ingredient `NutrientProfile` from
per-field winners (may mix sources). Summation nulls a nutrient's recipe and
per-serving total when **any** contributing ingredient lacks a non-null value
(fix `sum_nutrients` semantics or sum in the service with explicit null
propagation; §Numerics: summary = rounded sum of unrounded item values).

**Trace (`trace.py`, new).** `@dataclass CalculationTrace` with a list of
`IngredientTrace`, fields mirroring spec `## Execution trace`: resolved
`canonical_key`, resolver match type, resolver confidence; per-nutrient winner
(`source_kind, food_key, nutrition_rank, selection_priority, value`); chosen
package (`food_key, listing_name, retailer, confidence, price, package_count,
price_basis, freshness_status`); runner-up package identity + confidence;
observed `freshness_status`/`approval_status`; per-item warnings including the
`PARTIAL_NUTRITION_DATA` missing-nutrient list. `service.calculate` returns
`(response, trace)`; the router keeps returning only the response (no exposure
boundary — p3-001 owns that). `response_model=CostNutritionResponse` already
discards the trace.

**Service (`service.py`).** Resolve each ingredient to one canonical key;
reject with `UnresolvableIngredient` when no candidate **and** when the key has
no accepted candidate (AC-16). Build per-ingredient nutrients via per-field
precedence over the accepted candidate list; select the cost package via the
corrected `select_package`; emit `MISSING_PACKAGE_DATA` (no eligible package,
cost fields null, summary cost totals absent) and `PARTIAL_NUTRITION_DATA`
(naming the missing canonical nutrients among the nine). Assemble the AC-18
user payload (`ingredient`, `canonical_key`, offer `listing_name`+`retailer`,
distinct cost fields, nutrients DTO, warnings) and the parallel trace.

**Schemas (`schemas.py`).** `ItemizedCalculation`: drop `fdc_id`; replace
`matched_package` with `canonical_key: str` + a trimmed offer (`listing_name`,
`retailer`) — remove `package_title`/`package_price_sgd`/`package_amount_g`/
`package_count` from the user payload (they move to the trace). Add module
constant `MAX_REQUEST_INGREDIENTS` and use it in
`ingredients: list[...] = Field(min_length=1, max_length=MAX_REQUEST_INGREDIENTS)`.
`ItemWarning` keeps `{code, message}`; `PARTIAL_NUTRITION_DATA`'s message names
the missing nutrients. Keep `Nutrients` 11-field DTO (two extras always null);
keep `budget` out of use.

### §2 Decisions taken at plan stage (flagged for the reviewer)

- **D-1 `MAX_REQUEST_INGREDIENTS = 100`** — adopt the current inline
  `max_length=100` as the named constant. Spec (AC-19) requires a single
  declared constant but not a value; 100 preserves deployed behavior. Flagged
  for the reviewer to route if a different bound is wanted.
- **D-2 ceil tolerance `1e-9`** — `math.ceil(q/s - 1e-9)` clamped to `>= 1`.
  Spec permits "exact arithmetic or a small tolerance"; this is the tolerance
  choice. Flagged for the reviewer.
- **D-3 trace returned beside response as a tuple** — `calculate` returns
  `(CostNutritionResponse, CalculationTrace)`; the router returns the response
  only. Spec says the router discards the trace and p3-001 owns exposure; this
  is the mechanics, not a contract.

## Files to touch

- `SystemCode/remy/api/src/api/features/calculator/repository.py` — correct
  `confidence` name (R-1); select full evidence contract; nine nutrients;
  drop dead `observed_at`.
- `SystemCode/remy/api/src/api/features/calculator/models.py` — extend
  `RetailSKU` and `FoodFacts` candidate fields.
- `SystemCode/remy/api/src/api/features/calculator/domain/cost.py` — eligibility
  (C-4/R-10/R-8/AC-20), `package_volume` conversion, ranking lexicographic key,
  ceil tolerance.
- `SystemCode/remy/api/src/api/features/calculator/domain/nutrition_select.py`
  *(new)* — per-nutrient precedence (R-12/AC-6/AC-7).
- `SystemCode/remy/api/src/api/features/calculator/domain/nutrition.py` — fix
  `sum_nutrients` null-when-any semantics (or move to service).
- `SystemCode/remy/api/src/api/features/calculator/trace.py` *(new)* —
  `CalculationTrace`/`IngredientTrace`.
- `SystemCode/remy/api/src/api/features/calculator/service.py` — selection,
  accepted/unresolvable path, warnings naming nutrients, trace assembly,
  AC-18 payload.
- `SystemCode/remy/api/src/api/features/calculator/schemas.py` — AC-18 field
  set, `MAX_REQUEST_INGREDIENTS`.
- `SystemCode/remy/api/docs/API_doc.md` — correct the response shape in the
  same change (R-1: documentation corrected, not carried in parallel).
- `SystemCode/remy/api/src/api/features/calculator/router.py` — unpack
  `service.calculate`'s `(response, trace)` return; return only the response;
  keep `response_model=CostNutritionResponse`. Do not add an exposure boundary
  for the trace (p3-001 owns that).
- Tests under `SystemCode/remy/api/tests/features/calculator/`:
  - **Existing, repaired/extended:**
    - `test_domain_cost.py` — R-8/R-11 named fixture; AC-3, AC-4, AC-5,
      AC-13, AC-20.
    - `test_domain_nutrition.py` — R-9/R-12 named fixture; AC-1, AC-2, AC-6,
      AC-7, AC-8.
    - `test_domain_conversion.py` — R-10 named fixture; AC-14, AC-15.
    - `test_resolver.py` — AC-17; repaired (pre-existing stale alias test).
  - **New:**
    - `test_mapping_selection.py` — R-13's named fixture; AC-9, AC-10, AC-11,
      AC-12.
    - `test_repository_integration.py` — repo→service interface; R-1/AC-5,
      AC-6, AC-7, AC-9, AC-13, AC-16, AC-20.
    - `test_service_errors.py` — AC-15, AC-16.
    - `test_response_schema.py` — AC-18, AC-19, custom error envelope. *(Path
      diverges from the constitution's R-16 named check
      `tests/api/test_response_schema.py`; see `## Revision notes` F-D.)*
    - `test_calculator_integration.py` — the three interface rows.
    - `test_api_doc_consistency.py` — R-1 doc-vs-schema check.

## Constitution alignment

- **R-1** — repository reads only `confidence` (deployed name); the stale
  `mapping_confidence` alias and the API doc are corrected in the same change.
- **R-2** — calculator does not import `api.features.plan` internals; the
  tests here that import `plan.filtering` are the p2-001 fixtures and are not
  part of p2-002's code paths (noted as a test-colocation smell, routed as a
  nit if the reviewer wants it moved).
- **R-5** — unresolved ingredient / no-accepted-candidate rejects; absent cost
  → null fields + `MISSING_PACKAGE_DATA`; non-evaluable nutrient → null totals,
  never zero.
- **R-8** — `select_package` excludes any package whose `freshness_status !=
  "fresh"`; status comparison, not time arithmetic.
- **R-9** — profile-less candidate contributes no value; `PARTIAL_NUTRITION_DATA`
  names the missing nutrients; a nutrient total is null unless every
  contributing ingredient has a value.
- **R-10** — eligibility uses `price_status`/`price_match_status`/`price_basis`
  + positive amount; `cost_basis_compatible` is not read.
- **R-11** — consumed cost (P·Q/S) and retail cost (ceil(Q/S)·P) are distinct
  fields, never conflated.
- **R-12** — single deterministic per-nutrient precedence, stable across runs
  and input order.
- **R-13** — no confidence floor; selection by the AC-11 ordering ("best
  score"); confidence recorded in the trace. R-13's named fixture
  (`tests/features/calculator/test_mapping_selection.py`) is **created by this
  feature**; the tests assert the ordering, the no-floor behaviour, and the
  trace record.
- **R-16** — user payload excludes `confidence`, `food_key`, `fdc_id`,
  `source_*`, versions, ranks, `approval_status`; those live in the trace. The
  feature's R-16 test lives at
  `tests/features/calculator/test_response_schema.py`, **not** at the
  constitution's named check path `tests/api/test_response_schema.py`. The
  divergence is recorded (Revision notes F-D) and routed as a constitution
  correction; the assertion is otherwise the same as R-16's check.

## Test strategy

Error envelope: the code uses a **custom** envelope
`{"error":{code,message,details,timestamp}}` (`core.errors.error_envelope`).
AC-15/AC-16/AC-17/AC-19 rejection tests assert the custom envelope on at least
one case (AC-19 row below).

| AC | Test type | Test location / name | Notes |
|---|---|---|---|
| AC-1 | unit | `test_domain_nutrition.py::test_scale_total_per_serving` | scale by g/100, recipe total, per-serving = total/servings |
| AC-2 | unit | `test_domain_nutrition.py::test_nutrient_null_when_any_missing_and_warning_names` | any-missing → null total + per-serving; warning lists missing nutrients; no zero |
| AC-3 | unit | `test_domain_cost.py::test_consumed_vs_retail_distinct_sub_package` | P·Q/S vs P, distinct values |
| AC-4 | unit | `test_domain_cost.py::test_multi_package_ceil` | consumed=Q-based, retail=ceil(Q/S)·P; float artefact adds no package |
| AC-5 | unit | `test_domain_cost.py::test_ineligible_excluded_missing_package_warning` | ineligible edge excluded; MISSING_PACKAGE_DATA; summary totals absent; status success |
| AC-6 | unit | `test_domain_nutrition.py::test_branded_over_generic` | branded wins per nutrient; generic-only uses generic; unknown source → generic |
| AC-7 | unit | `test_domain_nutrition.py::test_same_source_tie_break` | rank→priority→food_key; missing rank/priority sort last; per nutrient |
| AC-8 | unit | `test_domain_nutrition.py::test_order_independent_determinism` | shuffled inputs → identical selections and totals, run twice |
| AC-9 | unit | `test_mapping_selection.py::test_only_accepted_candidates_usable` | non-accepted excluded from nutrient+cost; no accepted → unresolvable (AC-16) |
| AC-10 | unit | `test_mapping_selection.py::test_single_confidence_zero_selected_trace` | confidence-0 sole package selected; confidence in trace |
| AC-11 | unit | `test_mapping_selection.py::test_ranking_order_and_runner_up_trace` | unit price→retail→confidence→lexicographic; runner-up in trace; volume unit price compares like-with-like |
| AC-12 | unit | `test_mapping_selection.py::test_confidence_zero_and_one_valid` | both accepted, neither rejected |
| AC-13 | unit | `test_domain_cost.py::test_package_volume_eligible_and_converted` | volume eligible; gram conversion via units; silent (no UNIT_ASSUMED_GRAMS); price is declared estimated |
| AC-14 | unit | `test_domain_conversion.py::test_nutrient_non_mass_unit_warns` | nutrient non-mass unit → UNIT_ASSUMED_GRAMS; not on cost path |
| AC-15 | unit+api | `test_service_errors.py::test_unsupported_unit_and_nonfinite_reject` | to_grams raises → request fails as a whole; no response assembled |
| AC-16 | unit+api | `test_service_errors.py::test_unresolvable_and_no_accepted_reject` | unresolved name / no accepted candidate → rejection, not zero/inferred |
| AC-17 | unit | `test_resolver.py::test_ambiguous_rejects_low_score_and_small_gap` | score<0.86 or gap<0.05 rejects |
| AC-18 | api | `test_response_schema.py::test_user_payload_field_set` | payload has canonical_key, listing_name, retailer, costs, nutrients, warnings; excludes confidence/food_key/fdc_id/source_*/versions/ranks/approval_status; trace carries them |
| AC-19 | api | `test_response_schema.py::test_invalid_request_rejected_custom_envelope` | servings<1 / empty / >MAX_REQUEST_INGREDIENTS rejected pre-calc; asserts custom `{"error":{code,...}}` envelope |
| AC-20 | unit | `test_domain_cost.py::test_each_eligibility_condition_excludes` | each of price_status/price_match_status/currency/reference_price_minor/amount individually excludes |

## Integration per interface

The plan names three producer→consumer boundaries: repository→service (graph
evidence to calculation), service→router/response (calculation to serialized
user payload), and service→trace (calculation to the internal trace the router
discards). The repository's producer is the Neo4j driver.

| Interface (producer → consumer) | Test type | Test location / name | Notes |
|---|---|---|---|
| `CostNutritionRepository.fetch_food_facts` → `CostNutritionService.calculate` | integration | `test_calculator_integration.py::test_repo_output_feeds_service_selection` | Real `select_package`/precedence/service run; the **Neo4j driver is mocked** to replay recorded `FULFILLS` rows (approved fixture per p2 posture; the data-prep price path is blocked — finding `data-prep-price-path.md`). The repository and service code run for real; only the driver is a stub. Asserts selection + warnings on the real service output. |
| `CostNutritionService.calculate` → `calculator_router` (`CostNutritionResponse` serialization) | integration | `test_calculator_integration.py::test_service_output_serializes_user_payload` | FastAPI `TestClient` POSTs to `/api/v1/calculate/cost-and-nutrition` with the repository dependency overridden by a fixture-backed stub; the **router + service + schemas run for real**; asserts the AC-18 serialized key set and the custom error envelope on a rejection. |
| `CostNutritionService.calculate` → `CalculationTrace` | integration | `test_calculator_integration.py::test_service_populates_trace_discarded_by_router` | Real service returns `(response, trace)`; asserts the trace carries per-nutrient winners, chosen+runner-up package, and the response (via router) carries none of it. Trace is an in-process object, no external dependency. |

Deferral: the end-to-end path from the **real** data-preparation marts through
the Neo4j load is blocked by `docs/findings/data-prep-price-path.md` (the dbt
project does not parse). Per the p2 phase posture, repository→service evidence
uses an **approved recorded-row fixture** with a mocked driver; the code under
test (repository query-shaping, service, domain selection, router, schemas)
runs for real. Recorded in `## Revision notes` (F-C) and to be recorded in
`decisions.md` at close.

## Risks & mitigations

- **R1 Hidden consumers of the old field set** (`fdc_id`, `matched_package`
  extras). Mitigation: `grep` the api/workflows packages for those field names
  before editing; AC-18 test pins the new set; API doc corrected in the same
  change (R-1).
- **R2 `sum_nutrients` null semantics change** could affect p2-003's reading
  of the signal. Mitigation: AC-2 test pins "null when any missing"; the
  warning names the nutrients so p2-003 does not re-derive them.
- **R3 `package_volume` conversion density assumption** differs from any
  real-mart expectation. Mitigation: conversion is silent by spec (C-4/AC-13);
  AC-13 test pins eligibility + conversion; coverage is a data property (C-9).
- **R4 Mocked-driver integration diverges from real graph** (finding blocks
  real marts). Mitigation: fixtures are recorded from the deployed `FULFILLS`
  property set (schema-verified in §0); deferral recorded; real path reruns
  when the finding is resolved.
- **R5 p2-001 findings (F-A timestamp freshness, F-B cost_basis_compatible)**
  are out of p2-002's edit scope (R-2, ownership). Mitigation: routed as
  findings, not edited here; the calculator's independent checks satisfy R-8
  and R-10 regardless of p2-001's state.

## Scope check

Fits one working context: yes. The change is confined to the `calculator`
feature package and its tests, plus an in-place correction of the API doc
(R-1). The two p2-001 defects are routed as findings, not edited. The real
end-to-end data path is a recorded deferral, not work in this context.

## Revision notes

- **F-A (route: p2-001)** — `plan/filtering.py::_evaluate_freshness` is
  timestamp-based (`now - offer_observed_at <= 24h`) when `offer_observed_at`
  is present; amended R-8 makes freshness a status comparison. p2-001 owns the
  fix. p2-002's independent `freshness_status == "fresh"` check satisfies R-8
  at the calculator boundary meanwhile.
- **F-B (route: p2-001)** — `plan/filtering.py::_evaluate_cost_basis` gates on
  `cost_basis_compatible is True`; amended R-10 says that flag is not the gate.
  p2-001 owns the fix.
- **F-C (deferral)** — real data-prep marts → Neo4j load is blocked by
  `data-prep-price-path.md`; repository→service integration uses an approved
  recorded-row fixture with a mocked driver. To be recorded in `decisions.md`
  at close.
- **D-1/D-2/D-3** — plan-stage defaults (`MAX_REQUEST_INGREDIENTS = 100`; ceil
  tolerance `1e-9`; trace returned as a tuple) recorded in Design §2 and
  flagged for the reviewer to route if any is wrong.
- **R-1 doc correction** — the API doc still names `mapping_confidence`
  indirectly (via `confidence`) and shows `fdc_id`/`matched_package` extras;
  corrected in the same change, not carried in parallel.
- **F-D (route: constitution)** — R-16's named check path is
  `tests/api/test_response_schema.py`; this feature places its equivalent test
  at `tests/features/calculator/test_response_schema.py` to keep it local to
  the calculator package (MVP colocation). The assertion matches R-16's check:
  serialize a representative response and assert the allowed key set, failing
  on `confidence`, `normalization_version`, and `source_*`/`*_id` fields. The
  constitution's check path should be corrected to the feature-local location
  (or R-16 should name both), via amendment. Recorded for phase review.
- **F-E (route: plan; resolved by this revision)** — T-20 originally listed
  only `service.py` and `trace.py` as editable files while its done-when
  required the router to discard the trace. The existing router returns
  `service.calculate()` directly, so after T-20's tuple-return change the
  response would fail serialization against `response_model=CostNutritionResponse`.
  This was a fold error: the earlier task review merged "T-27 Confirm router
  discards trace" into T-20's done-when but dropped `router.py` from T-20's
  `Files:`. This revision restores `router.py` to T-20's `Files:`, adds
  `router.py` to `## Files to touch`, and sharpens T-20's done-when to name
  the router unpack explicitly. No behavioral or AC-coverage change.

## Tasks

### Group 0 — pre-task admin

- [x] **T-1** Verify rule IDs and AC numbers against the approved artifacts before writing code
  - Type: admin
  - Covers: F-1
  - Files: `docs/sdd/features/p2-002-cost-nutrition-calculation/plan.md` (Design §0, Constitution alignment) — edit only if a citation is wrong
  - Done when: every cited rule (R-1, R-2, R-5, R-8, R-9, R-10, R-11, R-12, R-13, R-16) and every AC (AC-1..AC-20) is confirmed present in the current approved `constitution.md` and `spec.md`; any mismatch is corrected in the plan before proceeding

- [x] **T-2** File p2-001 findings F-A and F-B as open follow-ups
  - Type: admin
  - Covers: F-2 (routed findings)
  - Files: `docs/sdd/features/p2-001-constraint-evidence-filtering/decisions.md`
  - Done when: F-A (p2-001 freshness predicate is timestamp-based; amended R-8 is status-based) and F-B (p2-001 uses `cost_basis_compatible`; amended R-10 does not) are recorded as new decision entries with status "open follow-up"; no code change to p2-001

### Group 1 — stale test repairs

- [x] **T-3** Repair stale `ml` warning-code test
  - Type: test
  - Covers: AC-14
  - Files: `SystemCode/remy/api/tests/features/calculator/test_domain_conversion.py` (`test_fixed_units_and_ml_warning`)
  - Done when: test asserts `to_grams(10, "ml") == (10, ["UNIT_ASSUMED_GRAMS"])`; passes against current `domain.units`

- [x] **T-4** Repair stale component-unit test
  - Type: test
  - Covers: AC-14
  - Files: `SystemCode/remy/api/tests/features/calculator/test_domain_conversion.py` (`test_component_units_require_positive_facts`)
  - Done when: test asserts `to_grams(2, "tbsp") == (30, ["UNIT_ASSUMED_GRAMS"])` (deprecated kwargs removed), and `pc` converts without raising; passes

- [x] **T-5** Repair stale resolver alias test
  - Type: test
  - Covers: AC-17
  - Files: `SystemCode/remy/api/tests/features/calculator/test_resolver.py` (`test_normalization_and_alias`)
  - Done when: test either includes the alias target in `canonical_keys` or asserts `AmbiguousIngredient` per AC-17's margin; passes against current `resolver.resolve`

### Group 2 — repository canonicalisation (R-1) and evidence contract

- [x] **T-6** Write failing test: `QUERY_B` reads deployed property names and full evidence contract
  - Type: test
  - Covers: AC-5, AC-6, AC-7, AC-9, AC-13, AC-16, AC-20 (R-1); interface repo→service
  - Files: `SystemCode/remy/api/tests/features/calculator/test_repository_integration.py` (`test_query_b_reads_deployed_names_and_full_contract`)
  - Done when: with a mocked driver replaying recorded `FULFILLS` rows, the returned row-shape exposes `confidence` (not `mapping_confidence`), `price_status`, `price_match_status`, `freshness_status`, `price_basis`, `package_mass_g`, `package_volume_ml`, `nutrition_rank`, `selection_priority`, `food_key`, and the nine canonical nutrients (including `saturated_fat_g`, `cholesterol_mg`); a missing key yields an empty list, distinguishing "no accepted edge" from "no key"; fails on the current repository. Assert on returned row shape, not on SQL text.

- [x] **T-7** Fix `QUERY_B` and `fetch_food_facts` to the canonical shape
  - Type: impl
  - Covers: AC-5, AC-6, AC-7, AC-9, AC-13, AC-16, AC-20 (R-1); interface repo→service
  - Files: `SystemCode/remy/api/src/api/features/calculator/repository.py`
  - Done when: T-6 passes; `observed_at` read removed; `mapping_confidence` alias removed; nine canonical nutrients populated on `NutrientProfile`; full evidence contract projected; a missing key returns an empty list

### Group 3 — domain cost (eligibility, ranking, volume, ceil)

- [x] **T-8** Write failing tests: eligibility exclusion and `MISSING_PACKAGE_DATA`
  - Type: test
  - Covers: AC-5, AC-20
  - Files: `SystemCode/remy/api/tests/features/calculator/test_domain_cost.py` (`test_ineligible_excluded_missing_package_warning`, `test_each_eligibility_condition_excludes`)
  - Done when: ineligible edge (any of `price_status`/`price_match_status`/`freshness_status`/`price_basis`/`currency`/amount) is excluded; no eligible package → `MISSING_PACKAGE_DATA` with null cost fields and absent summary totals; each condition excludes independently; fails on the current `select_package`

- [x] **T-9** Write failing test: `package_volume` eligibility, silent conversion, and no user-visible warning
  - Type: test
  - Covers: AC-13, AC-11 (volume unit-price clause), AC-14 (cost-path non-applicability)
  - Files: `SystemCode/remy/api/tests/features/calculator/test_domain_cost.py` (`test_package_volume_eligible_and_converted_silently`)
  - Done when: volume basis is eligible; grams come from `to_grams(amount, "ml")`; no user-visible warning is emitted (the `UNIT_ASSUMED_GRAMS` warning is not present on the cost path); unit price compares like-with-like against mass packages; fails on the current `select_package`

- [x] **T-10** Write failing tests: consumed vs retail and multi-package ceil
  - Type: test
  - Covers: AC-3, AC-4
  - Files: `SystemCode/remy/api/tests/features/calculator/test_domain_cost.py` (`test_consumed_vs_retail_distinct_sub_package`, `test_multi_package_ceil`)
  - Done when: consumed = P·Q/S and retail = P are distinct; multi-package retail = `ceil(Q/S)·P`; a float artefact (`Q/S = 3.0000000001`) adds no spurious package

- [x] **T-11** Rewrite `select_package` eligibility, ranking, and ceil
  - Type: impl
  - Covers: AC-3, AC-4, AC-5, AC-11, AC-13, AC-20 (R-8, R-10, R-11, R-13)
  - Files: `SystemCode/remy/api/src/api/features/calculator/domain/cost.py`
  - Done when: T-8, T-9, T-10 pass; eligibility is the C-4/R-10/R-8 rule; `cost_basis_compatible` not read; `package_volume` converted silently via `domain.units.to_grams`; lexicographic key is `(food_key, retailer, listing_name)`; ceil uses `math.ceil(q/s - 1e-9)` clamped to `≥ 1`

### Group 4 — per-nutrient precedence (R-12)

- [x] **T-12** Write failing tests: branded-over-generic and same-source tie-break
  - Type: test
  - Covers: AC-6, AC-7
  - Files: `SystemCode/remy/api/tests/features/calculator/test_domain_nutrition.py` (`test_branded_over_generic`, `test_same_source_tie_break`)
  - Done when: branded wins per nutrient; unknown source treated as generic; tie-break is `nutrition_rank` asc → `selection_priority` asc → `food_key` asc, nulls last, applied per nutrient; fails against the current code

- [x] **T-13** Write failing tests: order-independent determinism, null-when-any, and baseline scaling (AC-1, AC-2, AC-8)
  - Type: test
  - Covers: AC-1, AC-2, AC-8
  - Files: `SystemCode/remy/api/tests/features/calculator/test_domain_nutrition.py` (`test_order_independent_determinism`, `test_nutrient_null_when_any_missing_and_warning_names`, `test_scale_total_per_serving`)
  - Done when: shuffled inputs give identical selections and totals, twice; a nutrient missing from any contributing ingredient nulls that nutrient's recipe and per-serving total; `PARTIAL_NUTRITION_DATA` names the missing canonical nutrients; no zero-fill; `test_scale_total_per_serving` formalizes AC-1 (scale by g/100, recipe total, per-serving = total/servings) — this one passes immediately; the others fail against the current code

- [x] **T-14** Add per-nutrient selection and fix `sum_nutrients` semantics
  - Type: impl
  - Covers: AC-1, AC-2, AC-6, AC-7, AC-8 (R-9, R-12)
  - Files: `SystemCode/remy/api/src/api/features/calculator/domain/nutrition_select.py` (new), `SystemCode/remy/api/src/api/features/calculator/domain/nutrition.py`
  - Done when: T-12, T-13 pass; `select_nutrient_value(candidates, field)` applies the precedence per nutrient; `sum_nutrients` nulls a nutrient's total when any contributing ingredient lacks a value; summary uses the §Numerics rounding rule

### Group 5 — cost selection behaviour (R-13, trace)

- [x] **T-15** Create R-13 fixture and write accepted-candidates test
  - Type: test
  - Covers: AC-9, AC-16
  - Files: `SystemCode/remy/api/tests/features/calculator/test_mapping_selection.py` (new; R-13's named fixture)
  - Done when: file created with header docstring citing R-13; `test_only_accepted_candidates_usable` asserts non-accepted edges are excluded from nutrient and cost selection, and none-accepted resolves to unresolvable (AC-16); fails against the current code

- [x] **T-16** Append confidence-0 selection and ranking tests to R-13 fixture
  - Type: test
  - Covers: AC-10, AC-11, AC-12
  - Files: `SystemCode/remy/api/tests/features/calculator/test_mapping_selection.py`
  - Done when: `test_single_confidence_zero_selected_trace` asserts a sole confidence-0 package is selected and its confidence is in the trace; `test_ranking_order_and_runner_up_trace` asserts unit price → retail → confidence → lex with the runner-up in the trace; `test_confidence_zero_and_one_valid` asserts both accepted (passes immediately — no floor exists; not labelled a failing test)

### Group 6 — service orchestration, trace, payload

- [x] **T-17** Write failing tests: rejection paths (unit, unresolved, invalid request)
  - Type: test
  - Covers: AC-15, AC-16, AC-19
  - Files: `SystemCode/remy/api/tests/features/calculator/test_service_errors.py` (`test_unsupported_unit_and_nonfinite_reject`, `test_unresolvable_and_no_accepted_reject`)
  - Done when: `to_grams` raising rejects the whole request; unresolved name / no accepted candidate rejects; the custom error envelope (`{"error": {code, message, details, timestamp}}`) is asserted; fails against the current service

- [x] **T-18** Create R-16 assertion at feature-local path; write payload and invalid-request tests
  - Type: test
  - Covers: AC-18, AC-19; interface service→router
  - Files: `SystemCode/remy/api/tests/features/calculator/test_response_schema.py` (new; R-16 assertion at the feature-local path)
  - Done when: `test_user_payload_field_set` asserts the payload carries `canonical_key`, `listing_name`, `retailer`, costs, nutrients, warnings, and excludes `confidence`/`food_key`/`fdc_id`/`source_*`/versions/ranks/`approval_status`; `test_invalid_request_rejected_custom_envelope` asserts servings<1 / empty / `> MAX_REQUEST_INGREDIENTS` rejected pre-calc with the custom envelope; both fail against the current code

- [x] **T-19** Write failing test: nutrient non-mass unit warns
  - Type: test
  - Covers: AC-14 (nutrient path)
  - Files: `SystemCode/remy/api/tests/features/calculator/test_domain_conversion.py` (`test_nutrient_non_mass_unit_warns`)
  - Done when: nutrient non-mass unit emits `UNIT_ASSUMED_GRAMS`; passes or fails per current behavior, with intended behavior asserted

- [x] **T-20** Rewrite `service.calculate` for selection, warnings, payload, and trace
  - Type: impl
  - Covers: AC-1..AC-13, AC-16, AC-18 (R-5, R-8, R-9, R-10, R-11, R-12, R-13, R-16); all interface rows
  - Files: `SystemCode/remy/api/src/api/features/calculator/service.py`, `SystemCode/remy/api/src/api/features/calculator/trace.py` (new — `CalculationTrace` and `IngredientTrace`), `SystemCode/remy/api/src/api/features/calculator/router.py`
  - Done when: candidate-list selection; rejection on no accepted; per-nutrient profile via precedence; cost selection via corrected `select_package`; `MISSING_PACKAGE_DATA` and `PARTIAL_NUTRITION_DATA` (naming missing nutrients) emitted; AC-18 payload and parallel trace assembled; `calculate` returns `(CostNutritionResponse, CalculationTrace)`; **the router unpacks the tuple and returns only the response (keeping `response_model=CostNutritionResponse`)**; the trace is not serialized — verified by T-18's serialization test

- [x] **T-21** Update schemas: field set, `MAX_REQUEST_INGREDIENTS`
  - Type: impl
  - Covers: AC-18, AC-19; interface service→router
  - Files: `SystemCode/remy/api/src/api/features/calculator/schemas.py`
  - Done when: `ItemizedCalculation` drops `fdc_id` and the extra `matched_package` fields, adds `canonical_key` and `listing_name`/`retailer`; module constant `MAX_REQUEST_INGREDIENTS = 100` exists and is used in `Field(max_length=…)`; `ItemWarning` keeps `{code, message}`; `PARTIAL_NUTRITION_DATA` message names missing nutrients; `Nutrients` 11-field DTO retained

### Group 7 — API doc correction (R-1)

- [x] **T-22** Correct API doc response example
  - Type: impl
  - Covers: AC-18 (R-1)
  - Files: `SystemCode/remy/api/docs/API_doc.md` (`/cost-and-nutrition` section)
  - Done when: example removes `fdc_id`; trims `matched_package` to `listing_name`+`retailer`; shows `canonical_key`; shows `warnings` with `PARTIAL_NUTRITION_DATA` naming missing nutrients; a grep-level manual review confirms the doc and `CostNutritionResponse` agree (no regression test — doc consistency is not MVP scope)

### Group 8 — integration test (one, end-to-end)

- [ ] **T-23** Service → router end-to-end integration test (single, absorbs repo→service and trace-discard assertions)
  - Type: integration
  - Covers: interface repo→service, service→router, service→trace; AC-5, AC-6, AC-7, AC-9, AC-10, AC-11, AC-13, AC-16, AC-18, AC-19, AC-20
  - Files: `SystemCode/remy/api/tests/features/calculator/test_calculator_integration.py` (`test_end_to_end_repo_to_serialized_payload`)
  - Done when: the repository runs against a mocked driver replaying recorded `FULFILLS` rows; the real service selects (per-nutrient precedence + cost eligibility); the real `CalculationTrace` is populated with per-nutrient winners and chosen/runner-up package; the FastAPI `TestClient` POSTs to `/api/v1/calculate/cost-and-nutrition`; the serialized body matches AC-18's key set and carries none of the trace; a rejection case asserts the custom error envelope

### Group 9 — closing admin

- [ ] **T-24** Record feature decisions and deferrals
  - Type: admin
  - Covers: F-C; D-1/D-2/D-3; C-1..C-9 consequential flags; R-16 test-path divergence note
  - Files: `docs/sdd/features/p2-002-cost-nutrition-calculation/decisions.md`
  - Done when: F-C (mocked-driver deferral for the data-prep path) and D-1/D-2/D-3 are recorded; the spec's C-1..C-9 are transcribed as decisions; F-A and F-B referenced with routing; a one-line note records that the R-16 test lives at the feature-local path (divergence from the constitution's named check, for phase-review awareness — no amendment drafted)

- [ ] **T-25** Run the full API test suite and `sdd.py ci`
  - Type: verification
  - Covers: all ACs and interfaces
  - Files: (all above)
  - Done when: `pytest` passes for the API package; `sdd.py ci p2-002-cost-nutrition-calculation` reports `OVERALL: PASS`; the real-mart demonstration remains deferred under `docs/findings/data-prep-price-path.md` and is recorded as such
