# Application PostgreSQL — requirements prompt

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

YOUR COMPONENT: APPLICATION POSTGRESQL
Repository location: SystemCode/remy/backend/db.sql and SystemCode/remy/api/src/api/core/database.py

REQUIREMENTS

Design application persistence for the account backend and the checkpoint
integration used by the recommendation application.

Application PostgreSQL owns accounts, preferences, saved meals, ratings, and
the separate langgraph checkpoint schema where used. Preserve account/data
integrity and isolate user records. If an endpoint promises resumable runs,
its actual execution path must persist and restore the required state; the
existence of checkpoint tables alone is insufficient.

Inputs: backend account/user-data writes and checkpoint operations from the
application's configured persistence integration.
Outputs: authoritative account records, stored preferences, saved meals,
rating history, and checkpoint state where implemented.

Enforce username uniqueness and referential integrity. Store password hashes,
not plaintext credentials. Keep user-data access scoped to the authenticated
account through the owning backend. Preserve stored data across normal service
restarts. Keep application PostgreSQL distinct from Langfuse PostgreSQL.
Coordinate schema evolution with the services that own the corresponding data;
do not infer checkpoint/resume capability solely from database initialization.

ACCEPTANCE CRITERIA

Accounts, preferences, saved meals, and ratings retain their relationships across a normal restart. Duplicate identities and invalid references are rejected. Any advertised resumption behavior is demonstrated through the actual application path.

VERIFICATION

Use commands from SystemCode/ unless a check specifies another directory.
Python checks must run through uv inside WSL as required by AGENTS.md; if WSL
or a required tool/data/service is unavailable, report the check as blocked.
Use existing checks first and add focused verification only for uncovered
requirements within the approved scope. Separate fixture-based checks from
live integrations. Record method/command, inputs, expected versus actual result,
and pass/fail/skipped/blocked/not-run status without exposing secrets.

1. Schema inspection: use psql or the configured driver against an isolated
   application database. Inspect information_schema and pg_constraint for
   app_user, preference, saved_meal, meal_rating, their primary/foreign keys,
   and the langgraph schema where configured. Compare with backend/db.sql and
   runtime initialization; a schema-only check does not prove authorization.
2. Transactional integrity: in a disposable database, attempt duplicate
   normalized usernames, orphan user-data references, and duplicate logical
   saved-meal identities. Check the declared constraint/upsert behavior.
   Run reversible probes inside transactions and roll them back.
3. Service round trip: register two users through the backend, save distinct
   preferences/meals/ratings, then read through the same authenticated APIs.
   Compare with stored rows and confirm one account never receives the other's
   records. Verify password fields contain hashes and responses omit them.
4. Concurrency and durability: issue concurrent duplicate registrations or
   conflicting updates and assert the contract's conflict/update semantics.
   Restart services while retaining volumes and verify committed user data
   and sessions with stable signing configuration. Do not reset volumes.
5. Checkpoint semantics: inspect create_checkpointer and the actual request
   path. If resumable runs are exposed, interrupt a test run after a completed
   node, resume its ID, and use call counters/traces to prove completed work is
   not repeated. If the endpoint does not support this, report that limitation;
   the presence of langgraph tables is not a resumption test.

DELIVERABLE

Provide a concise component specification covering responsibilities, owned
data, input/output contracts, dependencies, failure behavior, and acceptance
criteria. Identify the contracts needed from adjacent components and flag
unresolved requirements. If implementation is authorized, keep changes within
this component's ownership and report what was actually verified.
```
