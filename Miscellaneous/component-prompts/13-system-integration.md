# System integration — requirements prompt

Use this prompt to define the contracts between components after their briefs.

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

YOUR SCOPE: CROSS-COMPONENT REQUIREMENTS AND INTERFACES

Define how the frontend, account backend, recommendation API, chat application,
workflow, shared domain, collection/preparation jobs, data stores, and observability
work together. Focus on responsibilities and contracts, rather than installation
or deployment commands. Do not duplicate logic owned by individual components.

HOW THE COMPONENTS WORK TOGETHER

Data path:
Recipe/FoodData Central/FairPrice inputs -> collection and landed snapshots ->
dbt transformations in DuckDB/DuckLake -> validated graph projection -> Neo4j.

User-data path:
Browser -> Next.js frontend -> account backend -> application PostgreSQL.

Structured recommendation path:
Frontend -> recommendation API -> Neo4j + shared domain logic + solver ->
structured plan/calculation -> frontend.

Conversational path:
Frontend -> Python chat application -> Extract Constraints -> Plan adapter ->
recommendation services -> Generate Response -> streamed frontend updates.

Observability path:
Application/workflow/service observations -> Langfuse -> correlated inspection
and optional evaluation. These components must share request/trace identifiers.

ACCEPTANCE OF THE INTEGRATED DESIGN

Demonstrate one coherent journey: sign in, save preferences, request a meal plan,
receive graph-backed recipes with explanations, calculate an ingredient's
nutrition/cost, save a meal, and record a rating. The conversational explanation
and structured result must agree. Show a trace for the request and a clear
failure/unknown result when required data or a dependency is unavailable.

VERIFICATION

Use commands from SystemCode/ unless a check specifies another directory.
Python checks must run through uv inside WSL as required by AGENTS.md; if WSL
or a required tool/data/service is unavailable, report the check as blocked.
Use existing checks first and add focused verification only for uncovered
requirements within the approved scope. Separate fixture-based checks from
live integrations. Record method/command, inputs, expected versus actual result,
and pass/fail/skipped/blocked/not-run status without exposing secrets.

1. Contract checks: inspect the served OpenAPI schemas and compare frontend,
   account, chat, workflow-adapter, and recommendation payloads at each boundary.
   Validate IDs, nutrient/unit vocabulary, serving scaling, nullability,
   structured errors, and actual JSON/SSE response formats.
2. Layer regression: run the applicable backend, API, app, workflow, domain,
   and preparation suites plus frontend unit/build checks from the component
   prompts. Keep results separate by layer and fixture type; mocked integration
   tests cannot substitute for live service/data checks.
3. Real user journey: with an isolated nonprod stack and accepted graph data,
   use Playwright or an HTTP client plus browser to sign up/sign in, persist
   preferences, request a one-day plan, inspect ingredients, calculate a known
   quantity, save a meal, rate it, sign out, and sign back in. Assert database
   persistence and account isolation, not just rendered success messages.
4. End-to-end consistency: trace one known recipe requirement from the accepted
   source/mart through Neo4j, API output, calculator totals, chat explanation,
   and rendered UI. Recompute expected quantities/nutrients/cost independently
   and compare using documented rounding and aggregation policies.
5. Failure matrix: in test fixtures or isolated services, exercise missing
   graph evidence, invalid constraints, database unavailability, LLM timeout,
   optional Jev failure, and a truncated/error SSE stream. Assert truthful
   error/unknown/partial outcomes and no fabricated success or cross-user data.
6. Correlation/durability: find the real request in Langfuse and compare spans
   and outcome with the HTTP/SSE result. Restart services without deleting data
   and repeat a persisted-data read. Only claim checkpoint recovery after
   interruption/resumption is demonstrated through an implemented endpoint.
7. Repeatable evidence: inspect/configure the existing frontend browser harness
   before using it, including ports, response format, graph data, and Langfuse
   prerequisites. Record screenshots, redacted HTTP/SSE samples, query results,
   trace IDs, and elapsed times. Report observed timings without inventing
   performance thresholds or treating missing live checks as passes.

DELIVERABLE

Produce a component dependency map and a boundary-contract table identifying
caller, owner, request/input, response/output, identifiers, units, nullability,
and error behavior. Align session handling, nutrient vocabulary, serving scale,
recipe/ingredient IDs, source provenance, streaming outcomes, and trace correlation.
Distinguish application user-data storage, analytical build storage, the serving
graph, and Langfuse's own infrastructure. Identify unresolved compatibility gaps
and give acceptance criteria for the integrated user journey.
```
