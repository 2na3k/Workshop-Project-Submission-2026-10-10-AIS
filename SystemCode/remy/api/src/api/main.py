from pathlib import Path

from dotenv import load_dotenv

SHARED_ENV_PATH = Path(__file__).resolve().parents[4] / ".env"
load_dotenv(SHARED_ENV_PATH)
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV_PATH)

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .core.database import lifespan
from .core.errors import ErrorDetail, error_envelope
from .core.exceptions import AppError
from .features.calculator.router import router as calculator_router
from .features.plan.router import router as plan_router


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_envelope(
            exc.code,
            exc.message,
            [ErrorDetail(**item) for item in exc.details],
        ),
    )


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        ErrorDetail(
            field=".".join(str(part) for part in error["loc"] if part != "body"),
            issue=error["msg"],
        )
        for error in exc.errors()
    ]
    if any("min cannot be greater than max" in error["msg"] for error in exc.errors()):
        return JSONResponse(
            status_code=400,
            content=error_envelope(
                "INVALID_NUTRIENT_RANGE",
                "Nutrient limit min cannot be greater than max",
                details,
            ),
        )
    return JSONResponse(
        status_code=422,
        content=error_envelope("VALIDATION_ERROR", "Request validation failed", details),
    )


async def unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=error_envelope("INTERNAL_ERROR", "An unexpected error occurred"),
    )


def health() -> dict[str, str]:
    return {"status": "ok"}


def create_app() -> FastAPI:
    application = FastAPI(title="Remy API", lifespan=lifespan)
    application.include_router(
        calculator_router, prefix="/api/v1/calculate", tags=["calculator"]
    )
    application.include_router(plan_router, prefix="/api/v1/plan", tags=["plan"])
    application.add_exception_handler(AppError, app_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    application.add_exception_handler(Exception, unexpected_error_handler)
    application.add_api_route("/health", health, methods=["GET"])
    return application


app = create_app()
