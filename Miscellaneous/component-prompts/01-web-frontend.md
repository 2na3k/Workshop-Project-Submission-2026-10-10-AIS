# Web frontend — requirements prompt

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

YOUR COMPONENT: WEB FRONTEND
Repository location: SystemCode/remy/frontend

REQUIREMENTS

Build a Next.js/React interface with these user journeys:
- Sign up, sign in, try the public demo, and sign out.
- Set dietary preferences, cuisines, and preferred nutrients.
- Discover meals through a conversational request.
- Build a plan by choosing days, meals per day, servings, allergies, dietary
  restrictions, nutrient targets, and permitted nutrient tolerance.
- Inspect each meal's recipe, ingredients, instructions, and nutrition.
- Calculate an ingredient list's nutrition and estimated grocery cost.
- Save/remove meals and view like/dislike history.

Inputs: form values, natural-language messages, session state, and API results.
Outputs: validated requests and clear displays of plans, explanations, costs,
warnings, partial results, and errors.

Use the auth backend for account-related operations and the recommendation API
for planning, calculations, and chat. Keep HTTP-only session cookies managed by
the server. Read streamed chat events incrementally and handle an error event
even when the HTTP response started successfully. Preserve null/unknown values;
do not display unavailable prices or nutrients as zero. Show applied relaxations
and constraints that could not be evaluated. Keep the UI usable on mobile.

ACCEPTANCE CRITERIA

A user can sign in, save preferences, request a plan, inspect a meal, calculate an ingredient, save a meal, and rate it. Loading, missing data, partial results, stream failures, and signed-out states are visible.

VERIFICATION

Use commands from SystemCode/ unless a check specifies another directory.
Python checks must run through uv inside WSL as required by AGENTS.md; if WSL
or a required tool/data/service is unavailable, report the check as blocked.
Use existing checks first and add focused verification only for uncovered
requirements within the approved scope. Separate fixture-based checks from
live integrations. Record method/command, inputs, expected versus actual result,
and pass/fail/skipped/blocked/not-run status without exposing secrets.

1. Static and client checks: run these existing package scripts from SystemCode/:
   npm --prefix remy/frontend run lint
   npm --prefix remy/frontend test
   npm --prefix remy/frontend run build
   Separate lint/type/build failures from behavioral failures; a build alone
   does not prove that requests or user journeys work.
2. Client contract checks: use mocked fetch responses to exercise validation,
   null nutrients/prices, partial plans, and structured errors. For streaming
   clients, split SSE frames and UTF-8 characters across arbitrary chunks;
   verify keep-alives, terminal errors, and premature EOF are handled.
3. Browser integration: inspect tests/browser.e2e.mjs, configure its actual
   E2E_FRONTEND_URL/E2E_API_URL and service prerequisites, then run:
   npm --prefix remy/frontend run test:e2e
   Check its port and response-format assumptions against the current contract;
   do not alter the app just to satisfy a stale harness. Exercise calculator,
   saved meals, ratings, and chat separately if the harness omits them.
4. Session/network checks: inspect browser requests and cookies. Verify the
   session cookie is HttpOnly, credentialed CORS uses the intended origin, and
   auth and /api/v1 proxy requests reach the correct service. Log-out must
   prevent subsequent private requests; no token should enter browser storage.
5. Rendering/accessibility checks: inspect desktop and narrow mobile viewports,
   keyboard focus, field labels, and alert text. Compare displayed recipe IDs,
   serving quantities, nutrients, and costs against captured API responses;
   retain screenshots and console/network failures as evidence.

DELIVERABLE

Provide a concise component specification covering responsibilities, owned
data, input/output contracts, dependencies, failure behavior, and acceptance
criteria. Identify the contracts needed from adjacent components and flag
unresolved requirements. If implementation is authorized, keep changes within
this component's ownership and report what was actually verified.
```
