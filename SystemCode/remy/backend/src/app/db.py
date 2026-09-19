from __future__ import annotations

import json

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


async def save_preferences(
    pool: asyncpg.Pool,
    username: str,
    special_diet: str | None,
    cuisines: list[str],
    preferred_nutrient: str | None,
) -> None:
    """Replace this user's preferences outright with a single upsert.

    Cuisines live in one JSONB column as an array (cuisine JSONB in db.sql),
    so the whole preference set is written in one statement - there is no
    child table to keep in sync, and the chosen order is preserved as-is.
    """
    await pool.execute(
        """
        INSERT INTO preference (username, special_diet, cuisine, preferred_nutrient)
        VALUES ($1, $2, $3::jsonb, $4)
        ON CONFLICT (username) DO UPDATE
            SET special_diet = EXCLUDED.special_diet,
                cuisine = EXCLUDED.cuisine,
                preferred_nutrient = EXCLUDED.preferred_nutrient
        """,
        username,
        special_diet,
        json.dumps(cuisines),
        preferred_nutrient,
    )


async def fetch_preferences(pool: asyncpg.Pool, username: str) -> dict | None:
    row = await pool.fetchrow(
        "SELECT special_diet, cuisine, preferred_nutrient "
        "FROM preference WHERE username = $1",
        username,
    )
    if row is None:
        return None

    # asyncpg hands jsonb back as raw text, so decode it here; NULL means the
    # user never picked any cuisines and becomes an empty list.
    raw = row["cuisine"]
    cuisines = json.loads(raw) if raw is not None else []
    return {
        "special_diet": row["special_diet"],
        "preferred_nutrient": row["preferred_nutrient"],
        "cuisines": cuisines,
    }
