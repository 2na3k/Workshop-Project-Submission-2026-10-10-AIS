from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import load_settings
from app.routes import auth

settings = load_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
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


def run() -> None:
    """Entry point for `uv run remy-backend`."""
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
