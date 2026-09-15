from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Header, HTTPException, Request, status

from app import db, security, tokens
from app.schemas import (
    AvailabilityOut,
    Credentials,
    RefreshOut,
    SessionOut,
    UsernameIn,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _session(username: str, request: Request) -> SessionOut:
    token = tokens.issue(username, request.app.state.settings.tokens)
    return SessionOut(
        username=username, access_token=token.value, expires_at=token.expires_at
    )


@router.post("/signup", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def signup(body: Credentials, request: Request) -> SessionOut:
    pool = request.app.state.pool
    bloom = request.app.state.bloom

    # The Bloom filter's job. A miss is definitive, so most sign ups with a
    # fresh username skip the existence query and go straight to the insert.
    # A hit is only probable, so it has to be confirmed.
    if body.username in bloom and await db.user_exists(pool, body.username):
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="That username is already taken."
        )

    password_hash = security.hash_password(body.password)

    try:
        await db.insert_user(pool, body.username, password_hash)
    except asyncpg.UniqueViolationError:
        # The filter is an optimisation, never the authority: two requests can
        # both pass the check above and race to insert. The primary key settles it.
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="That username is already taken."
        ) from None

    bloom.add(body.username)
    return _session(body.username, request)


@router.post("/signin", response_model=SessionOut)
async def signin(body: Credentials, request: Request) -> SessionOut:
    pool = request.app.state.pool

    # Deliberately no Bloom filter here. It could answer "certainly not
    # registered" without touching the database, but that fast path would be
    # visibly quicker than a wrong password and would turn the endpoint into a
    # username enumeration oracle.
    password_hash = await db.fetch_password_hash(pool, body.username)

    if password_hash is None:
        security.waste_time()
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password."
        )

    if not security.verify_password(password_hash, body.password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password."
        )

    # Transparently upgrade hashes written under older cost parameters.
    if security.needs_rehash(password_hash):
        await db.update_password_hash(
            pool, body.username, security.hash_password(body.password)
        )

    return _session(body.username, request)


@router.post("/refresh", response_model=RefreshOut)
async def refresh(
    request: Request, authorization: str = Header(default="")
) -> RefreshOut:
    """Trade a near-expiry or recently expired token for a fresh one.

    Public by design: it must accept tokens the auth middleware would reject,
    because an expired token is exactly the case it exists to handle. The
    signature is still verified, so an expired token cannot be forged.
    """
    scheme, _, presented = authorization.partition(" ")
    if scheme.lower() != "bearer" or not presented:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token, minted = tokens.renew(presented, request.app.state.settings.tokens)
    except tokens.TokenError as error:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    return RefreshOut(
        access_token=token.value, expires_at=token.expires_at, refreshed=minted
    )


@router.post("/available", response_model=AvailabilityOut)
async def availability(body: UsernameIn, request: Request) -> AvailabilityOut:
    """Live check for the sign up form, answered from memory where possible.

    POST with the name in the body rather than GET /available/{username}: a
    username in the path lands in access logs, browser history and referrer
    headers, which is more exposure than a availability probe deserves. Pydantic
    validates and lowercases it, so a malformed name is a 422 before any lookup.
    """
    candidate = body.username
    bloom = request.app.state.bloom

    if candidate not in bloom:
        return AvailabilityOut(
            username=candidate, available=True, answered_by_filter=True
        )

    taken = await db.user_exists(request.app.state.pool, candidate)
    return AvailabilityOut(
        username=candidate, available=not taken, answered_by_filter=False
    )
