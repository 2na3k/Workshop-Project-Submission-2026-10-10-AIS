# Observability and optional evaluation — requirements prompt

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

YOUR COMPONENT: OBSERVABILITY AND OPTIONAL EVALUATION
Repository location: SystemCode/docker-compose.yml, SystemCode/remy/api/src/api/core, and SystemCode/remy/api/src/api/features/plan

REQUIREMENTS

Integrate Langfuse so a request can be followed across chat, workflow nodes,
planning/calculation operations, and LLM calls using correlated identifiers.
Capture outcomes, latency, model metadata, warnings, and evaluation scores when
available. Keep credentials and session tokens out of traces and client code.

Keep the infrastructure responsibilities explicit:
- langfuse-web: dashboard and ingestion/API surface.
- langfuse-worker: background trace/event processing.
- langfuse-postgres: Langfuse metadata, separate from application PostgreSQL.
- langfuse-clickhouse: trace and analytics storage.
- langfuse-redis: queue/cache support.
- langfuse-minio: S3-compatible event/media storage; the current implementation
  uses SeaweedFS despite the Compose service name.
- langfuse-gateway: the browser-facing gateway to the internal Langfuse service.

Support rule-based candidate ranking and the existing optional Jev reranker/
judge modes through explicit configuration. Distinguish ranking, which affects
selection, from judging, which evaluates results. Label automated scores as
automated evidence; do not present them as human assessments. Make disabled,
unconfigured, and failed integrations visible.

ACCEPTANCE CRITERIA

A real application request can be located in Langfuse and correlated with its workflow/service outcome. Optional ranker/judge modes have explicit status, and any reported automated score can be traced to its actual evaluation run.

VERIFICATION

Use commands from SystemCode/ unless a check specifies another directory.
Python checks must run through uv inside WSL as required by AGENTS.md; if WSL
or a required tool/data/service is unavailable, report the check as blocked.
Use existing checks first and add focused verification only for uncovered
requirements within the approved scope. Separate fixture-based checks from
live integrations. Record method/command, inputs, expected versus actual result,
and pass/fail/skipped/blocked/not-run status without exposing secrets.

1. Existing local regression: run:
   uv run --package remy-api pytest -q remy/api/tests/test_monitoring.py remy/api/tests/test_langfuse_gateway.py remy/api/tests/features/plan/test_jev.py remy/api/tests/features/plan/test_judge_eval.py
   Inspect fake transports and fixtures; these tests alone do not prove live
   Langfuse ingestion or Jev access.
2. Infrastructure/ingestion check: inspect Compose health and worker/store logs.
   Run scripts/check_langfuse.py through uv --package remy-api in WSL with its
   expected local configuration. It writes explicitly synthetic traces/scores;
   verify queryable ingestion and label the evidence as a wiring check only.
3. Real request correlation: make an actual chat/plan/calculator request,
   record its trace ID, flush observations where required, and poll Langfuse
   with a bounded timeout. Compare node/service spans, outcomes, model metadata,
   and latency with the request. A healthy dashboard is not sufficient.
4. Evaluation oracle: feed a small fixed relevance-label fixture to the metric
   functions and independently calculate nDCG@3, Precision@3, and pairwise
   accuracy, including tied grades/empty inputs under the defined policy.
   Check automated scores identify their judge/model and real evaluation run.
5. Mode/failure matrix: test rule ranking, Jev ranking, judge off, and judge on
   with absent keys, timeouts, and malformed provider responses. Assert the
   configured startup and request behavior for each; do not silently relabel
   rule output as Jev output or synthetic labels as human judgments.
6. Data hygiene: inspect representative observations, errors, and log records
   for leaked credentials, cookies, authorization headers, or raw secrets.
   Separately verify disabled/failed tracing is reported according to policy
   and does not produce a false claim that an evaluation was recorded.

DELIVERABLE

Provide a concise component specification covering responsibilities, owned
data, input/output contracts, dependencies, failure behavior, and acceptance
criteria. Identify the contracts needed from adjacent components and flag
unresolved requirements. If implementation is authorized, keep changes within
this component's ownership and report what was actually verified.
```
