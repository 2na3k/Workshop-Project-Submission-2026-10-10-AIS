"""FastAPI composition root for the conversational application."""

from typing import Any

from api.core.database import lifespan
from fastapi import FastAPI

from app.chat_router import router as chat_router


def create_app(plan_service: Any | None = None) -> FastAPI:
    application = FastAPI(title="Remy Chat", lifespan=lifespan)
    application.state.plan_service = plan_service
    application.state.calculator_service = None
    application.include_router(chat_router, prefix="/api/v1", tags=["chat"])
    return application


app = create_app()
