from __future__ import annotations

import asyncpg

from app.bloom import BloomFilter


async def create_pool(database_url: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(database_url, min_size=1, max_size=10)


async def load_bloom(pool: asyncpg.Pool, capacity: int, error_rate: float) -> BloomFilter:
    """Build the filter from every username currently in the table.

    Runs once at startup. The filter lives in process memory, so each worker
    keeps its own copy and rebuilds it on restart - there is nothing to
    invalidate and nothing to keep in sync beyond that.
    """
    bloom = BloomFilter(capacity=capacity, error_rate=error_rate)
    rows = await pool.fetch("SELECT username FROM app_user")
    for row in rows:
        bloom.add(row["username"])
    return bloom


async def user_exists(pool: asyncpg.Pool, username: str) -> bool:
    return await pool.fetchval(
        "SELECT EXISTS (SELECT 1 FROM app_user WHERE username = $1)", username
    )


async def insert_user(pool: asyncpg.Pool, username: str, password_hash: str) -> None:
    """Raises asyncpg.UniqueViolationError if the username was taken."""
    await pool.execute(
        "INSERT INTO app_user (username, password_hash) VALUES ($1, $2)",
        username,
        password_hash,
    )


async def fetch_password_hash(pool: asyncpg.Pool, username: str) -> str | None:
    return await pool.fetchval(
        "SELECT password_hash FROM app_user WHERE username = $1", username
    )


async def update_password_hash(pool: asyncpg.Pool, username: str, password_hash: str) -> None:
    await pool.execute(
        "UPDATE app_user SET password_hash = $1 WHERE username = $2",
        password_hash,
        username,
    )
