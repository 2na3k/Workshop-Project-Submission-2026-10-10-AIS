from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import load_settings
from app.middleware import JWTAuthMiddleware
from app.routes import auth, preferences

settings = load_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = settings
    app.state.pool = await db.create_pool(settings.database_url)
    app.state.bloom = await db.load_bloom(
        app.state.pool, settings.bloom_capacity, settings.bloom_error_rate
    )
    try:
        yield
    finally:
        await app.state.pool.close()


app = FastAPI(title="Remy Backend", version="0.1.0", lifespan=lifespan)

app.add_middleware(JWTAuthMiddleware, config=settings.tokens)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(preferences.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, object]:
    return {"status": "ok", "bloom": app.state.bloom.stats}


@app.get("/me", tags=["account"])
async def me(request: Request) -> dict[str, str]:
    """Protected: reachable only through the JWT middleware, which puts the
    token's subject on request.state."""
    return {"username": request.state.username}


def run() -> None:
    """Entry point for `python src/main.py` and for the remy-backend script."""
    import uvicorn

    # Passed as a string rather than the app object because reload=True needs an
    # import path it can re-import in the worker process after each edit.
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)


# Without this, `python src/main.py` defines the app and exits without ever
# starting the server.
if __name__ == "__main__":
    run()
