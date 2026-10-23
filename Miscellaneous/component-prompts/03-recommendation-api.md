# Recommendation API — requirements prompt

Copy the complete prompt below. It includes its own project context.

```text
Remy is a meal-planning application combining recipes, food nutrition,
Singapore grocery prices, and dietary evidence. Its web UI uses an account
backend for user data and a recommendation API for plans/calculations. A Python
chat application composes an in-process LangGraph workflow with those services.
Data preparation publishes source-backed recipe and food evidence to Neo4j.

Design and implement the component described below within the approved project
scope. Follow repository governing instructions and artifact ownership. Preserve
compatible interfaces with adjacent components; surface conflicts rather than
silently expanding scope or rewriting another component.

Ground results in available data. Keep missing evidence explicit. Do not invent
nutrition values, prices, ingredients, certifications, or successful constraint
checks. This is a requirements brief, not an assertion that the current code
already satisfies every requirement.

YOUR COMPONENT: RECOMMENDATION API
Repository location: SystemCode/remy/api

REQUIREMENTS

Build the FastAPI boundary for planning and ingredient calculations. Expose
versioned, validated contracts and structured errors with machine-readable
codes and useful field details.

Meal planner:
- Accept a planning horizon of 1–14 days, 1–6 meals per day, a positive serving
  count, allergies, supported dietary rules, and nutrient goals/minimums/maximums.
- Retrieve graph-backed recipe candidates; evaluate evidence and constraints;
  rank candidates; use the constraint solver to assemble the requested plan.
- Keep nutrient goals distinct from hard bounds. Only apply relaxations allowed
  by the approved rules, record them, and explain any resulting partial plan.
- Return recipe identifiers/titles, day and meal slots, scaled ingredients,
  instructions when available, nutrient aggregates, and validation outcomes.
- Distinguish no usable candidates, infeasible constraints, missing evidence,
  and dependency failures. Do not call a failed operation a completed plan.

Ingredient calculator:
- Accept ingredient names, quantities, units, and servings.
- Resolve names to food concepts and compatible nutrition/product candidates.
- Convert quantities using supported, evidenced conversion factors.
- Calculate nutrition totals and per-serving values, consumed cost, and retail
  package purchase cost in SGD. Keep those two cost meanings separate.
- Return itemized matches and warnings for ambiguous mappings, missing data,
  incompatible units, and unavailable pricing.

Inputs: structured requests and curated graph records. Outputs: typed plan,
calculation, validation, and error responses. Share domain arithmetic between
planner and calculator so identical portions produce consistent results.

ACCEPTANCE CRITERIA

A valid request produces graph-backed meal results or an explicit infeasible outcome. Planner and calculator agree on the same portion's nutrition. Invalid inputs, missing evidence, and dependency failures have clear typed responses.

VERIFICATION

Use commands from SystemCode/ unless a check specifies another directory.
Python checks must run through uv inside WSL as required by AGENTS.md; if WSL
or a required tool/data/service is unavailable, report the check as blocked.
Use existing checks first and add focused verification only for uncovered
requirements within the approved scope. Separate fixture-based checks from
live integrations. Record method/command, inputs, expected versus actual result,
and pass/fail/skipped/blocked/not-run status without exposing secrets.

1. Existing behavioral regression: run:
   uv run --package remy-api pytest -q remy/api/tests
   Inspect fixtures and supply isolated checkpoint/database dependencies where
   required. Cover the plan/calculator contract, filtering, tolerance, solver,
   cost/nutrition, and error tests; distinguish fake-driver from live tests.
2. Contract/boundary checks: use TestClient and the actual OpenAPI schemas.
   Exercise days 0/1/14/15, meals 0/1/6/7, invalid servings, duplicate/unknown
   codes, non-finite numbers, contradictory ranges, and unsupported units.
   Assert the documented status, error code, and field details for each case.
3. Independent numerical oracle: use explicitly synthetic fixture data with
   known per-100g nutrition and package prices. Recompute totals and per-serving
   values independently of production helpers. For 250 g of a food with
   100 kcal/100 g, expect 250 kcal total and 125 kcal per serving for two
   servings. A SGD 4 / 500 g package costs SGD 2 consumed and SGD 4 to buy.
4. Solver/evidence checks: use a small candidate set whose feasible plans can
   be enumerated independently. Verify the returned slots, quantities, stated
   constraints, allowed relaxations, and infeasible outcomes. Introduce missing
   allergen/dietary evidence, stale price evidence, and incompatible conversions;
   verify their defined outcomes rather than assuming missing means pass.
5. Cross-service check: pass the same ingredients/portions through planner and
   calculator and compare using the documented rounding tolerance and aggregate
   meaning. Run a real graph-backed request separately; a mocked repository
   test does not prove the deployed Cypher or loaded data is compatible.
6. Dependency failures: inject Neo4j errors, solver unavailability, and optional
   reranker failures. Check for controlled errors and truthful terminal stream
   events where streaming is used; health alone is not an integration pass.

DELIVERABLE

Provide a concise component specification covering responsibilities, owned
data, input/output contracts, dependencies, failure behavior, and acceptance
criteria. Identify the contracts needed from adjacent components and flag
unresolved requirements. If implementation is authorized, keep changes within
this component's ownership and report what was actually verified.
```
