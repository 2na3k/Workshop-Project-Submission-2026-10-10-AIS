# Remy API + local Langfuse

## Docker: one command

From `SystemCode/`, with production Neo4j credentials already in `.env.prod`:

```sh
make up-prod API_PORT=8003 FRONTEND_PORT=3100 BACKEND_PORT=8010
```

This generates private backend credentials once, starts **Langfuse web + worker,
passwordless gateway, PostgreSQL, ClickHouse, Redis, and MinIO**, waits for dashboard health, then builds
and starts the real frontend, auth/preferences backend, and API against production Neo4j. It does not start a local Neo4j or
change your production credentials. Subsequent runs reuse the credentials and data.

- **Application: `http://localhost:3100`** (the merged Next.js frontend, not a placeholder)
- API: `http://localhost:8003/docs`
- Dashboard: `http://localhost:<LANGFUSE_PORT>` from `.env.langfuse`
- **No login/password prompt**: the localhost gateway establishes the operator session internally.
- On the current machine the dashboard is **http://localhost:3032**; default port
  3031 was occupied. Change `LANGFUSE_PORT` in the private file if needed, then rerun.

`.env.langfuse` is gitignored, mode **0600**, and contains generated passwords, API
keys, and the reviewer token. No known/default passwords are committed. The official
headless initialization creates the Remy organization, project, and admin account.
Signup is disabled; dashboard access is bound to localhost only. The gateway blocks
foreign Host/Origin headers, cross-site API requests, and framing. All local users
can use the operator dashboard: **never expose this gateway publicly**. The native
web service, backend databases, Redis, and MinIO are not published to host ports.
Backend credentials remain private; removing the human login prompt does not remove
server authentication. The gateway supports HTTP/streamed responses (not WebSockets)
and caps request bodies at 16 MiB. Do not remove/rotate this private
file while retaining database volumes; headless initialization does not overwrite
existing accounts, project keys, or infrastructure passwords.

The API automatically uses `http://langfuse-web:3000`, enables tracing and local
ranking snapshots, and gets matching project keys. It needs **no manual Langfuse
settings in `.env.prod`**. Selected Neo4j/runtime settings still come from `.env.prod`.
The shared local monitoring stack survives switching API environment; trace
`environment` identifies `prod` versus `nonprod`.

Other commands:

```sh
make up                         # .env.nonprod + local Neo4j + Langfuse + API
make langfuse DBT_TARGET=prod    # dashboard/worker only
make logs DBT_TARGET=prod
make down DBT_TARGET=prod        # stop; retain volumes
```

Raw Compose equivalent after initialization (local secrets loaded last):

```sh
uv run --frozen --package remy-api python scripts/init_langfuse.py
DBT_TARGET=prod API_PORT=8003 docker compose \
  --env-file .env.prod --env-file .env.langfuse up -d --build --wait langfuse-gateway langfuse-worker
DBT_TARGET=prod API_PORT=8003 docker compose \
  --env-file .env.prod --env-file .env.langfuse up -d --build --wait frontend
```

Named volumes retain Langfuse databases/event storage and local evaluation snapshots.
`docker compose down -v` **deletes that data**. This is a localhost deployment using
production food data, not a public production monitoring deployment. Public hosting
requires HTTPS/reverse proxy, access restrictions, backups, and a retention policy.
JSON traces/scores are supported; browser media uploads/downloads are not exposed.

## Workflow and the three metrics (slides 18–19)

1. `POST /api/v1/plan` creates a `meal-plan` trace with nested retrieval, filtering,
   ranking, solving, and response spans. Record durations, sanitized failure types,
   candidate counts, empty retrievals, plan status, and relaxation count.
2. Save the successful ranking snapshot in SQLite. The response includes
   `trace_id` and `evaluation_id`; these are nullable outside Docker when disabled
   or unavailable. All tracing/storage failures leave meal planning available.
3. A protected endpoint presents the original request and shuffled candidates,
   without ranking scores/order, plan order, trace link, or previous judgments.
4. A reviewer grades every candidate **0–3**. Persist the grades and computed
   metrics before queueing scores on the original Langfuse trace.

**Metrics evaluate `rank_candidates` before the solver, not the final meal-slot
order.** The evaluation pool is its bounded output (up to 300 recipes), not every
recipe in Neo4j. Compare ranking methods on the same pool/grading protocol; these
metrics do not measure retrieval recall. Candidate nutrients are per-recipe values
before scaling by requested servings.

| Langfuse score | Definition |
| --- | --- |
| `nDCG@3` | Top-three DCG uses `(2^grade - 1) / log2(rank + 1)`, divided by ideal top-three DCG from the **whole graded pool**. All-zero ideal returns 0. |
| `Precision@3` | Number of top-three recipes graded **≥2**, divided by **3**. Missing positions in shorter lists count as not relevant. |
| `pairwise_accuracy` | Fraction of unequal-grade pairs in the whole ranking with the better recipe first. Exclude ties. No comparable pairs returns `null` locally and emits no Langfuse score. |

Set `REMY_DATA_VERSION` and `LANGFUSE_RELEASE` in the selected API env file to label
data/code versions. Root `meal-plan` durations support p50/p95 **planner** latency;
do not mix nested stages into percentiles. HTTP validation/serialization and network
round-trip time are outside that measurement.

## Collect actual human judgments

Create a plan, then copy its `evaluation_id`:

```sh
curl -fS http://localhost:8003/api/v1/plan \
  -H 'Content-Type: application/json' \
  -d '{"horizon_days":1,"meals_per_day":3}'

# Copy REMY_EVALUATION_TOKEN from private .env.langfuse; do not put it in a browser app.
export REVIEWER_TOKEN='your-local-reviewer-token'
export EVALUATION_ID='evaluation_id-from-plan-response'
curl -fS "http://localhost:8003/api/v1/evaluations/$EVALUATION_ID" \
  -H "Authorization: Bearer $REVIEWER_TOKEN" > candidates.json
```

Use a consistent rubric: **0** unsuitable, **1** marginal, **2** relevant, **3** highly
relevant to the request. Grade blind, independently of the returned plan and Langfuse
ranking trace. Put one integer grade per returned ID in `human-grades.json`:

```json
{"grades":{"actual-recipe-id-1":3,"actual-recipe-id-2":2,"actual-recipe-id-3":0}}
```

Replace the example IDs and grade the **entire** recorded pool, not just three
recipes. Missing/unknown IDs, floats, booleans, grades outside 0–3, and duplicate
ranking IDs are rejected.

```sh
curl -fS "http://localhost:8003/api/v1/evaluations/$EVALUATION_ID/grades" \
  -H "Authorization: Bearer $REVIEWER_TOKEN" \
  -H 'Content-Type: application/json' --data-binary @human-grades.json
```

Response: `metrics`, `trace_id`, and `langfuse_scores_queued`. Human score metadata
contains `judge=human`, evaluation ID, and metric version `v1`. Grades are immutable;
repeat the same request to retry publication with stable score IDs. Changed grades
return 409. `queued=true` is SDK acceptance, not remote delivery confirmation; verify
in Langfuse and retry after an outage. No clicks/saves or LLM labels are passed off
as human judgments. A snapshot made without a trace cannot later publish to one.

## Verification

```sh
# Unit checks: no Docker, Neo4j, or real Langfuse credentials needed.
uv run --frozen --package remy-api python -m unittest discover \
  -s remy/api/tests -p test_monitoring.py
uv run --frozen --package remy-api python -m unittest discover \
  -s scripts -p test_init_langfuse.py
uv run --frozen --package remy-api python -m unittest discover \
  -s remy/api/tests -p test_langfuse_gateway.py
uv lock --check

# Live Docker check: verifies project auth, trace export, worker processing,
# and all three persisted metrics through the public Langfuse API.
uv run --frozen --package remy-api python scripts/check_langfuse.py
```

The live check creates a clearly labeled **synthetic fixture** trace in environment
`integration-test`; its scores are not human evaluations or production quality claims.
A real planner request was also verified: HTTP 200, all six observations present in
local Langfuse, and the protected blind-grading endpoint working. Its actual human
grades remain pending. Passwordless dashboard access was verified from a fresh HTTP
client without supplying credentials or cookies; foreign Host/Origin requests are blocked.

The merged frontend's real Chromium E2E passes: signup, saved preferences, logout/login,
streamed planning through the frontend proxy, all six Langfuse spans, and protected
candidate review. Evidence: `SystemCode/target/e2e/meal-plan.png` and `result.json`.
Frontend unit tests: **22 passed**; lint clean; production npm audit clean after the
Next.js 16.4.0 security patch. API/domain suite: **34 passed, 4 pre-existing conversion
failures**. The PR fixed the former oatmeal-alias failure. Architecture lint is blocked by the
existing `.importlinter` file's invalid `[[contracts]]` syntax. Those are unchanged.

## Privacy and limitations

Raw dietary/allergy requests, recipe instructions, and raw exception messages are
not sent to Langfuse. Export only structural settings/constraint counts, versions,
recipe/plan/evaluation IDs, counts/statuses, and aggregate scores. Actual constraints
and candidate details are stored in protected local SQLite for review; protect its
volume/backups and grading files, and apply retention. SQLite is intentionally
single-deployment; use shared PostgreSQL before scaling API replicas.

Ranking evaluation does not establish dietary safety. Existing allergen/dietary
checks now screen known conflicts per recipe in `filtering.py`. Restricted requests
run normally; unknown evidence remains eligible for best-effort suggestions and is
explicitly marked `unverified`, never `passed`. Both plan and chat UIs warn that these
results are not guaranteed allergy-safe or diet-compliant. No blanket 503 guard remains. No LLM/LangGraph rebuild, token-cost tracking,
automatic grading, click/save tracking, or grading UI is added.

For non-Docker API use, tracing still defaults off. Configure the optional Cloud or
self-hosted settings from `.env.example`, then run:

```sh
uv run --env-file .env.prod --package remy-api uvicorn api.main:app --reload
```
