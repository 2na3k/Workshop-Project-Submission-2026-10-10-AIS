# Shared domain — requirements prompt

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

YOUR COMPONENT: SHARED DOMAIN
Repository location: SystemCode/remy/domain

REQUIREMENTS

Provide pure, reusable logic for nutrient vocabulary, unit conversions, portion
scaling, nutrient aggregation, cost calculations, and constraint-check states.

Use one canonical nutrient mapping across components. Preserve the difference
between pass, fail, unknown, and not_requested. Unsupported conversions and
missing evidence must produce explicit outcomes. Keep this package free of
database, HTTP, UI, and LLM dependencies and avoid importing higher-level apps.

ACCEPTANCE CRITERIA

Equivalent quantities yield consistent portion and nutrient calculations across callers. Unknown values stay unknown, unsupported conversions have explicit results, and the package has no dependency on higher application layers.

VERIFICATION

Use commands from SystemCode/ unless a check specifies another directory.
Python checks must run through uv inside WSL as required by AGENTS.md; if WSL
or a required tool/data/service is unavailable, report the check as blocked.
Use existing checks first and add focused verification only for uncovered
requirements within the approved scope. Separate fixture-based checks from
live integrations. Record method/command, inputs, expected versus actual result,
and pass/fail/skipped/blocked/not-run status without exposing secrets.

1. Existing pure-function regression: run:
   uv run --package remy-domain pytest -q remy/domain/tests
   Inspect types, units, and nutrient tests and identify arithmetic/rule cases
   not covered by that suite.
2. Independent arithmetic checks: calculate expected values by hand from
   explicit fixtures. For 100 kcal and 10 g protein per 100 g, 250 g contributes
   250 kcal and 25 g protein; two equal servings contain half each. Compare
   domain outputs with these values using a documented numeric tolerance.
3. Algebraic/metamorphic checks: parameterize compatible unit equivalence,
   additive portion scaling, and sum-order independence within floating-point
   tolerance. Verify behavior at zero and invalid serving/quantity boundaries
   against each function's contract rather than assuming all accept zero.
4. Missingness/rule matrix: exercise zero separately from None and unknown.
   Check pass/fail/unknown/not_requested and unsupported conversions. Verify
   each aggregation function's declared null policy; summing known contributors
   and requiring every contributor are different contracts.
5. Dependency/vocabulary checks: verify one request-to-canonical mapping and run
   the configured import-linter through uv in WSL, for example:
   uv run --package remy-app lint-imports --config .importlinter
   Inspect imports for HTTP, database, or LLM dependencies as well; the configured
   higher-layer import contracts alone do not exclude every external I/O library.

DELIVERABLE

Provide a concise component specification covering responsibilities, owned
data, input/output contracts, dependencies, failure behavior, and acceptance
criteria. Identify the contracts needed from adjacent components and flag
unresolved requirements. If implementation is authorized, keep changes within
this component's ownership and report what was actually verified.
```
