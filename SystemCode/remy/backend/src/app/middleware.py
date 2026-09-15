from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.tokens import TokenConfig, TokenError, username_of

# Reachable without a token. Everything else needs one.
PUBLIC_PATHS = frozenset(
    {
        "/health",
        "/auth/signup",
        "/auth/signin",
        # Refresh reads the token itself, including expired ones, so it has to
        # sit outside a check that rejects expired tokens.
        "/auth/refresh",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
)

PUBLIC_PREFIXES = ("/auth/available/",)


def _is_public(path: str) -> bool:
    return path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Requires a valid, unexpired bearer token on every non-public route.

    On success the subject is left at `request.state.username` so handlers do
    not have to decode the token a second time.
    """

    def __init__(self, app, config: TokenConfig) -> None:
        super().__init__(app)
        self._config = config

    async def dispatch(self, request: Request, call_next):
        # CORS preflight carries no Authorization header by design; CORSMiddleware
        # answers it before this runs, but allowing it here keeps the middleware
        # correct regardless of ordering.
        if request.method == "OPTIONS" or _is_public(request.url.path):
            return await call_next(request)

        header = request.headers.get("Authorization", "")
        scheme, _, token = header.partition(" ")

        if scheme.lower() != "bearer" or not token:
            return _unauthorized("Missing bearer token.")

        try:
            request.state.username = username_of(token, self._config)
        except TokenError as error:
            return _unauthorized(str(error))

        return await call_next(request)


def _unauthorized(detail: str) -> JSONResponse:
    return JSONResponse(
        {"detail": detail},
        status_code=401,
        headers={"WWW-Authenticate": "Bearer"},
    )
