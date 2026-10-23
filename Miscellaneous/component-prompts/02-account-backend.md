# Account and user-data backend — requirements prompt

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

YOUR COMPONENT: ACCOUNT AND USER-DATA BACKEND
Repository location: SystemCode/remy/backend

REQUIREMENTS

Build a FastAPI service backed by PostgreSQL that owns:
- Account registration, username availability, sign-in, session refresh,
  sign-out, and current-user lookup.
- Persisted dietary/cuisine/nutrient preferences.
- Saved meals and a user's meal-rating history.

Inputs: credentials, authenticated account requests, preference values, and
meal/rating payloads. Outputs: session cookies and account-scoped JSON results.

Normalize and validate usernames, hash passwords with Argon2id, and enforce
username uniqueness in the database. A Bloom filter may optimize availability
checks, but PostgreSQL remains authoritative. Authorize reads/writes against
the session owner. Persist signing configuration so a normal restart does not
invalidate every session. Keep the demo account explicitly public and separate
from any Langfuse administration account.

ACCEPTANCE CRITERIA

Registration and session flows work; preferences, saved meals, and ratings persist across restarts. An account cannot access another account's private records, and duplicate usernames are rejected consistently.

VERIFICATION

Use commands from SystemCode/ unless a check specifies another directory.
Python checks must run through uv inside WSL as required by AGENTS.md; if WSL
or a required tool/data/service is unavailable, report the check as blocked.
Use existing checks first and add focused verification only for uncovered
requirements within the approved scope. Separate fixture-based checks from
live integrations. Record method/command, inputs, expected versus actual result,
and pass/fail/skipped/blocked/not-run status without exposing secrets.

1. Existing unit regression: run:
   uv run --package remy-backend pytest -q remy/backend/tests
   Inspect test_tokens.py and test_bloom.py for the coverage actually provided;
   these unit checks do not establish live database or HTTP behavior.
2. HTTP/database integration: use FastAPI TestClient or an HTTP client with a
   cookie jar against an isolated PostgreSQL database. Check registration,
   case-normalized duplicate usernames, sign-in, /me, refresh, sign-out,
   preferences, saved meals, and ratings. Compare responses with stored rows.
3. Account isolation: create two test users and verify that each sees only
   their own preferences, saved meals, and history. Exercise missing, expired,
   and forged cookies; protected operations must reject unauthorized requests.
4. Credential/session checks: assert stored password hashes use Argon2id and
   verify them with the configured library. Exercise refresh-window boundaries,
   expiry, forged signatures, and unsigned tokens. Inspect Set-Cookie attributes
   against the configured local/production policy without logging token values.
5. Race and persistence checks: submit concurrent registrations for the same
   normalized username; require one account and a controlled conflict outcome.
   Force a Bloom-filter positive for an absent username to confirm the database
   decides availability. Restart the backend with stable configuration and
   verify a valid session and its persisted user data still work.

DELIVERABLE

Provide a concise component specification covering responsibilities, owned
data, input/output contracts, dependencies, failure behavior, and acceptance
criteria. Identify the contracts needed from adjacent components and flag
unresolved requirements. If implementation is authorized, keep changes within
this component's ownership and report what was actually verified.
```
