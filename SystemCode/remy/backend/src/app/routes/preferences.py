from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app import db
from app.schemas import PreferencesIn, PreferencesOut

router = APIRouter(prefix="/preferences", tags=["preferences"])

# No path is public here, so the JWT middleware has already validated the token
# and left its subject on request.state.username. That is the account these
# endpoints act on - a user cannot read or write anyone else's preferences,
# because the username never comes from the request body.


@router.put("", response_model=PreferencesOut)
async def save(body: PreferencesIn, request: Request) -> PreferencesOut:
    """Write the whole preference set. Called at the end of the cold start and
    whenever the preferences page is saved."""
    username = request.state.username
    await db.save_preferences(
        request.app.state.pool,
        username,
        body.special_diet,
        body.cuisines,
        body.preferred_nutrient,
    )
    return PreferencesOut(username=username, **body.model_dump())


@router.get("", response_model=PreferencesOut)
async def read(request: Request) -> PreferencesOut:
    username = request.state.username
    stored = await db.fetch_preferences(request.app.state.pool, username)
    if stored is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="No preferences saved yet.",
        )
    return PreferencesOut(username=username, **stored)
