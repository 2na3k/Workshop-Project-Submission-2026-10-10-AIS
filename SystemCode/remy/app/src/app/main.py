"""FastAPI composition root for the conversational application.

This module is the served ASGI target. It composes the API app
(``api.main.create_app``) with the chat router. Services are not
constructed here: ``api.core.database.lifespan`` sets
``app.state.neo4j_driver`` on startup, and the ``/chat`` handler
builds the plan/calculator services from that driver per request.
Explicit ``plan_service`` / ``calculator_service`` arguments are
accepted for test injection only.
"""

from typing import Any

from api.main import create_app as create_api_app
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.chat_router import router as chat_router


def create_app(
    *,
    plan_service: Any | None = None,
    calculator_service: Any | None = None,
) -> FastAPI:
    application = create_api_app()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3100", "http://127.0.0.1:3100"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if plan_service is not None:
        application.state.plan_service = plan_service
    if calculator_service is not None:
        application.state.calculator_service = calculator_service
    application.include_router(chat_router, prefix="/api/v1", tags=["chat"])
    return application


app = create_app()
