from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    cors_origins: tuple[str, ...]
    bloom_capacity: int
    bloom_error_rate: float


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
    )
