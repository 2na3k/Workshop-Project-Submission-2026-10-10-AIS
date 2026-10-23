# Data collection — requirements prompt

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

YOUR COMPONENT: DATA COLLECTION
Repository location: SystemCode/remy/data-crawler

REQUIREMENTS

Collect FairPrice product/listing evidence needed for ingredient fulfillment:
product identity, listing URL, description, package quantity/unit, price,
currency, and dietary/allergen claims when available.

Inputs: configured source pages/searches and existing unmatched ingredient or
product records. Outputs: landed source records for data preparation, including
source references and observation/snapshot metadata.

Keep extracted source facts separate from inferred mappings. Preserve missing
fields, identify duplicate captures, and make failed/partial collection visible.
Treat this as a batch data producer rather than an always-running web service.

ACCEPTANCE CRITERIA

A collection run produces attributable source records with capture metadata. Duplicate, missing, and failed captures can be identified, and downstream preparation can consume the output without assuming inferred values are source facts.

VERIFICATION

Use commands from SystemCode/ unless a check specifies another directory.
Python checks must run through uv inside WSL as required by AGENTS.md; if WSL
or a required tool/data/service is unavailable, report the check as blocked.
Use existing checks first and add focused verification only for uncovered
requirements within the approved scope. Separate fixture-based checks from
live integrations. Record method/command, inputs, expected versus actual result,
and pass/fail/skipped/blocked/not-run status without exposing secrets.

1. Parser fixtures: replay saved HTML/JSON fixtures covering normal products,
   missing prices, multi-packs, absent dietary claims, duplicate listings, and
   changed markup. Compare extracted values with explicit expected source
   facts, including currency, package units, URLs, and missing fields.
2. HTTP fault checks: stub the HTTP transport to return timeouts, 429, 5xx,
   empty pages, and malformed content. Verify implemented retry/timeout limits,
   partial-run reporting, and a visible failure when parsing no longer matches
   the page. Do not turn an empty extraction into a successful full catalogue.
3. Output contract checks: validate required fields, numeric price shape,
   source identity, timestamp format, and snapshot association in landed output.
   Repeated captures must follow the declared deduplication policy, preserving
   separate observations when their dates or offers differ.
4. Preparation handoff: feed a small captured fixture through the relevant
   staging model and compare row identity, price/package values, provenance,
   and nulls. Detect column or type drift before a full collection run.
5. Bounded live smoke: inspect the real script entrypoint and run a small,
   permitted source sample through uv --package remy-data-crawler in WSL.
   Compare several output records with their source pages and capture time.
   No crawler test suite or package __main__ entrypoint was observed when these
   prompts were prepared; recheck and report absent automation instead of
   claiming nonexistent tests passed. Keep fixture and live results separate.

DELIVERABLE

Provide a concise component specification covering responsibilities, owned
data, input/output contracts, dependencies, failure behavior, and acceptance
criteria. Identify the contracts needed from adjacent components and flag
unresolved requirements. If implementation is authorized, keep changes within
this component's ownership and report what was actually verified.
```
