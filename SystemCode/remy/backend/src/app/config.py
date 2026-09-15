from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass

from app.tokens import TokenConfig

_log = logging.getLogger(__name__)

HALF_DAY_SECONDS = 12 * 60 * 60
MIN_SECRET_BYTES = 32


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    cors_origins: tuple[str, ...]
    bloom_capacity: int
    bloom_error_rate: float
    tokens: TokenConfig


def _jwt_secret() -> str:
    secret = os.environ.get("REMY_JWT_SECRET", "").strip()
    if secret:
        # HS256 keys shorter than the 256-bit hash add no security beyond their
        # own length (RFC 7518 s3.2), and PyJWT warns about it.
        if len(secret.encode()) < MIN_SECRET_BYTES:
            _log.warning(
                "REMY_JWT_SECRET is only %d bytes. Use at least %d "
                "(`openssl rand -base64 48`).",
                len(secret.encode()),
                MIN_SECRET_BYTES,
            )
        return secret

    # No hardcoded fallback: a known signing key lets anyone mint a token for
    # any account. A fresh random key per process is safe, at the cost of
    # invalidating every issued token whenever the server restarts - fine for
    # development, which is the only place this branch should ever run.
    _log.warning(
        "REMY_JWT_SECRET is not set. Generated a random key for this process; "
        "all tokens become invalid when it restarts, and separate workers will "
        "reject each other's tokens. Set REMY_JWT_SECRET for anything real."
    )
    return secrets.token_urlsafe(48)


def load_settings() -> Settings:
    return Settings(
        database_url=os.environ.get(
            "REMY_DATABASE_URL",
            "postgresql://localhost:5432/remy_main",
        ),
        cors_origins=tuple(
            origin.strip()
            for origin in os.environ.get(
                "REMY_CORS_ORIGINS", "http://localhost:3000,http://localhost:3100"
            ).split(",")
            if origin.strip()
        ),
        # Sized for the expected number of accounts, not the current one: a
        # Bloom filter cannot be resized without rebuilding, and its false
        # positive rate climbs once it holds more than `capacity` items.
        bloom_capacity=int(os.environ.get("REMY_BLOOM_CAPACITY", "100000")),
        bloom_error_rate=float(os.environ.get("REMY_BLOOM_ERROR_RATE", "0.01")),
        tokens=TokenConfig(
            secret=_jwt_secret(),
            ttl_seconds=int(os.environ.get("REMY_JWT_TTL_SECONDS", HALF_DAY_SECONDS)),
            # 30 minutes: a token that is 11h30 into its 12h life renews.
            renew_within_seconds=int(
                os.environ.get("REMY_JWT_RENEW_WITHIN_SECONDS", 30 * 60)
            ),
            # How long after expiry a token can still be traded for a new one.
            # 0 disables it, so an expired token always means signing in again.
            expired_grace_seconds=int(
                os.environ.get("REMY_JWT_EXPIRED_GRACE_SECONDS", 7 * 24 * 60 * 60)
            ),
        ),
    )
