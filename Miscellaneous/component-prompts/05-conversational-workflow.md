# Conversational workflow — requirements prompt

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

YOUR COMPONENT: CONVERSATIONAL WORKFLOW
Repository location: SystemCode/remy/workflows

REQUIREMENTS

Build an in-process LangGraph workflow with three responsibilities:
- Extract Constraints: convert natural language into typed planning constraints.
  Distinguish stated values, defaults, unsupported requests, and unapplied
  constraints. Keep targets, hard limits, units, and serving counts distinct.
- Plan: call a planner port implemented by the application adapter. Preserve
  successful, infeasible, and failed outcomes plus supporting evidence.
- Generate Response: explain the actual plan and its limitations using the
  computed facts. Reference only returned recipes, ingredients, and values.

Inputs: user text/context and injected service/model interfaces. Outputs:
structured constraints, a typed outcome, an explanation, and a trace envelope.

Record node execution and LLM invocation metadata. Short-circuit failed stages;
do not generate a success narrative after extraction or planning fails. Treat
provider/model access as an integration dependency. Keep the workflow testable
with injected model and planner implementations.

ACCEPTANCE CRITERIA

A natural-language request becomes typed constraints, a planner outcome, and a grounded explanation. Unsupported constraints stay visible, failed stages stop the success path, and deterministic test doubles can exercise each node.

VERIFICATION

Use commands from SystemCode/ unless a check specifies another directory.
Python checks must run through uv inside WSL as required by AGENTS.md; if WSL
or a required tool/data/service is unavailable, report the check as blocked.
Use existing checks first and add focused verification only for uncovered
requirements within the approved scope. Separate fixture-based checks from
live integrations. Record method/command, inputs, expected versus actual result,
and pass/fail/skipped/blocked/not-run status without exposing secrets.

1. Existing deterministic regression: run:
   uv run --package remy-workflows pytest -q remy/workflows/tests
   Use the injected fake LLM/planner fixtures to exercise extraction, graph
   ordering, plan outcomes, generation, trace envelopes, and response schemas.
2. Extraction case matrix: table-test vague requests, explicit days/servings,
   weekly horizons, targets versus hard limits, tolerance, allergies, and
   unsupported constraints. Assert the exact typed values, defaults, and
   unapplied fields. Malformed model JSON and invalid ranges must fail clearly.
3. Execution-order check: use spies/call counters around each node and planner
   port. Require Extract Constraints -> Plan -> Generate Response on success.
   Extraction failure must not call the planner; planning failure must not
   produce a successful generation. Structured input should bypass extraction
   model calls where the contract specifies that behavior.
4. Grounding check: provide a fixed plan fact sheet and compare generated recipe
   IDs, ingredient references, quantities, nutrients, and drop causes with it.
   Inject invented IDs, unsupported success claims, and out-of-range numbers;
   verify the defined validation/failure behavior. Check that unverified or
   unevaluated constraints remain visible in the user-facing explanation.
5. Trace and live-model checks: assert node/outcome order, invocation counts,
   parsed constraints, and correlation fields in the trace envelope. Separately
   run a small fixed request set against the configured real provider/model,
   recording failures and constraint accuracy; fake-model success does not
   verify external model access or extraction quality.

DELIVERABLE

Provide a concise component specification covering responsibilities, owned
data, input/output contracts, dependencies, failure behavior, and acceptance
criteria. Identify the contracts needed from adjacent components and flag
unresolved requirements. If implementation is authorized, keep changes within
this component's ownership and report what was actually verified.
```
