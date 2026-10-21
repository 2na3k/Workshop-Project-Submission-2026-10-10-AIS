## Fix plan — p3-004 app composition (BD-1)

---

### Preconditions (agent must verify first)

```bash
grep -n "def " SystemCode/remy/app/src/app/composition.py
grep -n "class PlanServiceAdapter\|def __init__\|def generate" SystemCode/remy/app/src/app/plan_adapter.py
grep -n "def create_app\|@app.exception_handler\|@app.get\|^app = " SystemCode/remy/api/src/api/main.py
grep -n "plan_service\|calculator_service\|neo4j_driver\|def chat" SystemCode/remy/app/src/app/chat_router.py
```

Record the actual function/attribute names before editing. If any name differs from what the code blocks below assume, use the real name — do not invent.

---

### 1. `SystemCode/remy/api/src/api/main.py`

**Change:** module-level setup → `create_app()` factory, keeping `app = create_app()`. Handlers become plain functions.

Replace the entire file with (adjust imports only if the existing file imports different names — do not add or remove imports beyond what the decorators used):

```python
from pathlib import Path

from dotenv import load_dotenv

SHARED_ENV_PATH = Path(__file__).resolve().parents[4] / ".env"
load_dotenv(SHARED_ENV_PATH)
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV_PATH)

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .core.database import lifespan
from .core.errors import ErrorDetail, error_envelope
from .core.exceptions import AppError
from .features.calculator.router import router as calculator_router
from .features.plan.router import router as plan_router


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_envelope(
            exc.code,
            exc.message,
            [ErrorDetail(**item) for item in exc.details],
        ),
    )


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        ErrorDetail(
            field=".".join(str(part) for part in error["loc"] if part != "body"),
            issue=error["msg"],
        )
        for error in exc.errors()
    ]
    if any("min cannot be greater than max" in error["msg"] for error in exc.errors()):
        return JSONResponse(
            status_code=400,
            content=error_envelope(
                "INVALID_NUTRIENT_RANGE",
                "Nutrient limit min cannot be greater than max",
                details,
            ),
        )
    return JSONResponse(
        status_code=422,
        content=error_envelope("VALIDATION_ERROR", "Request validation failed", details),
    )


async def unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=error_envelope("INTERNAL_ERROR", "An unexpected error occurred"),
    )


def health() -> dict[str, str]:
    return {"status": "ok"}


def create_app() -> FastAPI:
    application = FastAPI(title="Remy API", lifespan=lifespan)
    application.include_router(
        calculator_router, prefix="/api/v1/calculate", tags=["calculator"]
    )
    application.include_router(plan_router, prefix="/api/v1/plan", tags=["plan"])
    application.add_exception_handler(AppError, app_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    application.add_exception_handler(Exception, unexpected_error_handler)
    application.add_api_route("/health", health, methods=["GET"])
    return application


app = create_app()
```

**Done when:** `python -c "from api.main import app, create_app; create_app()"` works; existing API tests still pass.

---

### 2. `SystemCode/remy/app/src/app/main.py`

**Change:** replace the standalone `FastAPI(...)` app with a composition of `api.main.create_app()` + `chat_router`. Do **not** build services at import time; services are built per request from `app.state.neo4j_driver`.

Replace the entire file with:

```python
"""FastAPI composition root for the conversational application.

This module is the served ASGI target. It composes the API app
(``api.main.create_app``) with the chat router. Services are not
constructed here: ``api.core.database.lifespan`` sets
``app.state.neo4j_driver`` on startup, and the ``/chat`` handler
builds the plan/calculator services from that driver per request.
Explicit ``plan_service`` / ``calculator_service`` arguments are
accepted for test injection only.
"""

from typing import Any

from api.main import create_app as create_api_app
from fastapi import FastAPI

from app.chat_router import router as chat_router


def create_app(
    *,
    plan_service: Any | None = None,
    calculator_service: Any | None = None,
) -> FastAPI:
    application = create_api_app()
    if plan_service is not None:
        application.state.plan_service = plan_service
    if calculator_service is not None:
        application.state.calculator_service = calculator_service
    application.include_router(chat_router, prefix="/api/v1", tags=["chat"])
    return application


app = create_app()
```

**Done when:** `python -c "from app.main import app; print([r.path for r in app.routes])"` lists `/api/v1/calculate/...`, `/api/v1/plan/...`, `/api/v1/chat`, `/health`.

---

### 3. `SystemCode/remy/app/src/app/chat_router.py`

**Change:** resolve services from `request.app.state` (injected) or from `request.app.state.neo4j_driver` via the existing `composition.create_*` builders. Use the real builder names discovered in the precondition grep; the block below assumes `create_plan_service(driver)` and `create_calculator_service(driver)` — rename if different.

At the top of the handler (or the helper it calls), insert:

```python
from fastapi import Request
from app import composition


def _resolve_services(request: Request) -> tuple[Any, Any]:
    driver = request.app.state.neo4j_driver
    plan_service = getattr(request.app.state, "plan_service", None) \
        or composition.create_plan_service(driver)
    calculator_service = getattr(request.app.state, "calculator_service", None) \
        or composition.create_calculator_service(driver)
    return plan_service, calculator_service
```

Replace the existing place where `plan_service` / `calculator_service` are read (currently they were probably read from `app.state` directly or built inline). Call `_resolve_services(request)` at the start of the `/chat` handler and use the returned pair for the workflow invocation and the cost projection.

Do **not** change any other behavior in `chat_router.py` (event order, SSE framing, cost branch, error handling).

**Done when:** the module imports cleanly; `pytest SystemCode/remy/app/tests/api/test_chat_endpoint.py -q` passes (with the fixture change in step 4).

---

### 4. `SystemCode/remy/app/tests/api/test_chat_endpoint.py`

**Change:** fix the app construction so T-13 uses real `PlanServiceAdapter` + real `PlanService` via `create_app(plan_service=..., calculator_service=...)`. Locate the line:

```python
plan_service = PlanService(PlanRepository(Driver()))
```

Replace with (using the real `PlanServiceAdapter` constructor discovered in the precondition grep):

```python
from app.main import create_app
from app.plan_adapter import PlanServiceAdapter

plan_service = PlanServiceAdapter(PlanService(PlanRepository(Driver())))
calculator_service = CostNutritionService(CostNutritionRepository(Driver()))
app = create_app(plan_service=plan_service, calculator_service=calculator_service)
client = TestClient(app)
```

Apply the same pattern to every test in the file that constructs a `TestClient`. `Driver()` / `CostNutritionRepository(...)` fakes remain (repo is faked; `PlanService` and `PlanServiceAdapter` are real — this is F-2).

**Done when:** `test_cost_intent_turn_drops_uncosted_recipe_end_to_end` passes and its fixture uses the `create_app(plan_service=..., calculator_service=...)` path (grep the test file for `create_app(` to confirm).

---

### 5. `SystemCode/remy/app/tests/api/test_composition.py` (new)

**Change:** add the F-3 test proving one composed app serves all four routes and uses the standard `error` envelope on `/chat`.

```python
"""F-3: the composed app serves api + chat with the shared error envelope."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_health_served_unprefixed(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_calculate_route_mounted(client):
    r = client.post("/api/v1/calculate", json={})
    assert r.status_code != 404


def test_plan_route_mounted(client):
    r = client.post("/api/v1/plan", json={})
    assert r.status_code != 404


def test_chat_route_mounted(client):
    r = client.post("/api/v1/chat", json={})
    assert r.status_code != 404


def test_chat_workflow_failure_uses_error_envelope(client, monkeypatch):
    """A raised exception in the chat handler must emit the standard error
    SSE event (AC-17), not FastAPI's default 500 body."""
    from app import chat_router

    def boom(*args, **kwargs):
        raise RuntimeError("forced")

    monkeypatch.setattr(chat_router, "_resolve_services", boom)
    with client.stream("POST", "/api/v1/chat",
                       json={"session_id": "s", "message": "hi"}) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        body = "".join(r.iter_text())
    assert "event: error" in body
```

Adjust `_resolve_services` name if step 3 names the helper differently. If `/chat` returns 422 for a missing-body request before streaming, change the failing test to post a valid `ChatRequest` body `{"session_id": "s", "message": "hi"}`.

**Done when:** `pytest SystemCode/remy/app/tests/api/test_composition.py -q` passes.

---

### 6. `SystemCode/remy/api/docs/API_doc.md`

**Change:** add one line under §3 (`POST /api/v1/chat`):

> **Served entrypoint:** `app.main:app`. The chat endpoint is mounted on the composed app; `api.main:app` remains for API-only deployments and does **not** include `/api/v1/chat`.

---

### 7. `docs/sdd/features/p3-004-conversational-constraint-interface/plan.md`

**Change:** append to `## Revision notes`:

```markdown
- **BD-1** — plan §1 "constructs the FastAPI app" was realized as a
  parallel `Remy Chat` app that bypassed the API's error envelope,
  `/health`, and router mounting. Corrected: `app/main.py` now
  composes `api.main.create_app()` + `chat_router`; services are
  resolved per request from `app.state.neo4j_driver` via the existing
  `app.composition` builders. **Served entrypoint:** `app.main:app`.
  `api.main:app` remains for back-compat and is not the deployment
  target. Date, commit.
```

Do not edit `## Tasks` wording or checkboxes; do not edit spec/review/constitution.

---

### 8. Verification (agent runs, pastes output)

```bash
uv run lint-imports
pytest SystemCode/remy/api/tests -q
pytest SystemCode/remy/app/tests -q
pytest SystemCode/remy/workflows/tests -q
python -c "from app.main import app; print(sorted(r.path for r in app.routes))"
sdd.py check p3-004-conversational-constraint-interface
sdd.py ci p3-004-conversational-constraint-interface
```

Expected:
- `lint-imports` → 4 kept, 0 broken.
- All tests green.
- Route listing contains `/api/v1/chat`, `/api/v1/calculate...`, `/api/v1/plan...`, `/health`.
- `sdd.py ci` → `PASS`.

---

### Commit

One commit:

```
fix(p3-004): compose api + chat into one served app (BD-1)

- api.main: extract create_app(); handlers as plain functions
- app.main: compose api.main.create_app() + chat_router (served entrypoint)
- chat_router: resolve services from app.state.neo4j_driver per request
- test_chat_endpoint: inject real PlanServiceAdapter via create_app(...)
- add test_composition (F-3): four routes + shared error envelope
- API_doc: name served entrypoint
- plan: record BD-1
```

---

### Do not

- Create new `build_*` helpers — `app/composition.py` already has them; call the existing names.
- Add `plan_service`/`calculator_service` construction at import time in `app/main.py` — the driver does not exist before lifespan.
- Change router prefixes or the SSE handler logic.
- Touch `filtering.py`, `PlanService.generate`, `from_trace_envelope`, or any p3-002 contract model.
- Reopen plan-review or edit the spec.
- Weaken tests.
