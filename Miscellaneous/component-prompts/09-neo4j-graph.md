# Neo4j graph — requirements prompt

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

YOUR COMPONENT: NEO4J GRAPH
Repository location: SystemCode/docs/neo4j_db_design.md and SystemCode/remy/data-preparation/models/serving

REQUIREMENTS

Design the graph store consumed by the recommendation API and published by data preparation.

Neo4j owns the queryable recipe/food graph. Represent recipe requirements,
normalized concepts, candidate foods, and fulfillment evidence with stable
identifiers. Support efficient retrieval of recipes and their ingredient,
nutrition, pricing, and dietary evidence. Treat selected/best fulfillment as
a derived projection with provenance rather than a new source fact.

Inputs: validated graph projections from data preparation, including stable
identifiers, original ingredient occurrences, evidence references, source
snapshot identifiers, and mapping versions.
Outputs: query results for recipe retrieval, ingredient resolution, candidate
selection, nutrition calculation, and estimated cost.

Keep recipe requirements, food concepts, nutrition profiles, branded products,
and dated retail evidence distinct. Preserve unknown or absent evidence and
support API queries without inventing facts. Coordinate the schema and indexes
with the loader and API repositories; do not independently change their
contracts. Keep user accounts and Langfuse analytics in their own stores.

ACCEPTANCE CRITERIA

A loaded recipe can be traced through its original ingredient requirements to compatible food candidates and source evidence. API retrieval returns consistent identifiers and quantities; derived fulfillment remains attributable to its source projection.

VERIFICATION

Use commands from SystemCode/ unless a check specifies another directory.
Python checks must run through uv inside WSL as required by AGENTS.md; if WSL
or a required tool/data/service is unavailable, report the check as blocked.
Use existing checks first and add focused verification only for uncovered
requirements within the approved scope. Separate fixture-based checks from
live integrations. Record method/command, inputs, expected versus actual result,
and pass/fail/skipped/blocked/not-run status without exposing secrets.

1. Schema/identity queries: on the intended graph, inspect SHOW CONSTRAINTS and
   SHOW INDEXES; compare them with stable identifiers used by the loader and
   API repositories. Run a read-only duplicate check such as:
   MATCH (r:Recipe) WITH r.recipe_id AS id, count(*) AS n
   WHERE id IS NULL OR n > 1 RETURN id, n
   Repeat for food/concept keys and the declared relationship identities.
2. Traversal/provenance checks: query a known Recipe-REQUIRES->FoodConcept and
   Food-FULFILLS->FoodConcept path. Compare original ingredient occurrence,
   quantity/unit, food nutrition basis, mapping version, and snapshot/evidence
   references with the accepted source fixture. Verify derived
   BEST_FULFILLMENT edges point to eligible candidates with the right lineage.
3. Real loader regression: after confirming a disposable database through
   NEO4J_TEST_URI/NEO4J_TEST_USERNAME/NEO4J_TEST_PASSWORD, run:
   uv run --package remy-data-preparation pytest -q remy/data-preparation/tests/graph -m integration
   These fixtures clear the database. Never use the app, development, or
   production graph. Missing test credentials mean blocked/skipped, not passed.
4. Idempotence checks: load the same accepted fixture twice into that isolated
   graph. Compare node/relationship identities and canonical property values;
   require no duplicate occurrence/candidate links. Test rejected payloads
   separately and confirm no partial publication.
5. Query behavior/performance: execute the actual API repository queries against
   fixture data and compare typed rows with expected results. Use EXPLAIN to
   inspect plans, and PROFILE only for read-only queries in the test graph;
   record index use, row expansion, and timings without inventing a latency SLA.

DELIVERABLE

Provide a concise component specification covering responsibilities, owned
data, input/output contracts, dependencies, failure behavior, and acceptance
criteria. Identify the contracts needed from adjacent components and flag
unresolved requirements. If implementation is authorized, keep changes within
this component's ownership and report what was actually verified.
```
