from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import load_settings
from app.middleware import JWTAuthMiddleware
from app.routes import auth

settings = load_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = settings
    app.state.pool = await db.create_pool(settings.database_url)
    # Built once, from the table, at startup. Each worker process keeps its own
    # copy in memory; a restart rebuilds it.
    app.state.bloom = await db.load_bloom(
        app.state.pool, settings.bloom_capacity, settings.bloom_error_rate
    )
    try:
        yield
    finally:
        await app.state.pool.close()


app = FastAPI(title="Remy Backend", version="0.1.0", lifespan=lifespan)

# Order matters: the last middleware added is the outermost. CORS must wrap the
# auth check so that a 401 still comes back with CORS headers - otherwise the
# browser reports an opaque network error instead of the real status.
app.add_middleware(JWTAuthMiddleware, config=settings.tokens)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, object]:
    return {"status": "ok", "bloom": app.state.bloom.stats}


@app.get("/me", tags=["account"])
async def me(request: Request) -> dict[str, str]:
    """Protected: reachable only through the JWT middleware, which puts the
    token's subject on request.state."""
    return {"username": request.state.username}


def run() -> None:
    """Entry point for `uv run remy-backend`."""
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
