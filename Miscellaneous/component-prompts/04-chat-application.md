# Conversational application — requirements prompt

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

YOUR COMPONENT: CONVERSATIONAL APPLICATION
Repository location: SystemCode/remy/app

REQUIREMENTS

Provide the Python application composition that adds /api/v1/chat to the
recommendation API. This package is separate from the Next.js frontend.

Accept a session identifier, a user message, and optional user context. Connect
the workflow to concrete planner/calculator services through explicit adapters.
Translate workflow output into the chat contract: metadata, text tokens,
plan updates, completion, and error events as applicable.

Preserve trace/session correlation, handle disconnects and downstream failures,
and expose the real terminal outcome. Keep HTTP/SSE handling here and reasoning
inside the workflow; avoid copying planner or nutrition logic into the route.

ACCEPTANCE CRITERIA

The chat route accepts its documented request, invokes the injected workflow/services, and emits correlated events with a truthful terminal outcome. A downstream failure is represented as an error, including after streaming begins.

VERIFICATION

Use commands from SystemCode/ unless a check specifies another directory.
Python checks must run through uv inside WSL as required by AGENTS.md; if WSL
or a required tool/data/service is unavailable, report the check as blocked.
Use existing checks first and add focused verification only for uncovered
requirements within the approved scope. Separate fixture-based checks from
live integrations. Record method/command, inputs, expected versus actual result,
and pass/fail/skipped/blocked/not-run status without exposing secrets.

1. Existing route/adapter regression: run:
   uv run --package remy-app pytest -q remy/app/tests
   Inspect the chat contract, plan adapter, application composition, SSE,
   response schema, and import-boundary tests. Use injected services and an
   isolated startup/checkpoint setup instead of relying on ambient databases.
2. Composition check: fetch /openapi.json from the served application and
   verify chat, planning, and calculator routes are all mounted. Confirm that
   the deployed ASGI target serves the composition rather than the API alone.
3. SSE protocol check: POST the actual chat schema with curl --no-buffer or
   an HTTP streaming client. Parse complete event/data frames, JSON payloads,
   and required identifiers. Check event order against the contract, incremental
   delivery, and the successful terminal event; HTTP 200 is insufficient.
4. Failure/lifecycle checks: inject extraction, planner, model timeout, and
   downstream exceptions before and after streaming starts. Assert a truthful
   error/terminal outcome, no success narrative after failure, and cancellation
   or cleanup of request work when the client disconnects.
5. Adapter/correlation checks: spy on planner/calculator calls and verify field,
   unit, serving, and ID translation. Compare plan_updated payloads with the
   returned plan and correlate metadata to the real trace. Concurrent sessions
   must not mix messages, plan updates, or terminal events.

DELIVERABLE

Provide a concise component specification covering responsibilities, owned
data, input/output contracts, dependencies, failure behavior, and acceptance
criteria. Identify the contracts needed from adjacent components and flag
unresolved requirements. If implementation is authorized, keep changes within
this component's ownership and report what was actually verified.
```
