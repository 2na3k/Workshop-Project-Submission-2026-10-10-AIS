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

app = FastAPI(
    title="Remy API",
    version="0.1.0",
    description=(
        "Calculate nutrition profiles and ingredient costs in Singapore dollars. "
        "API base path: `/api/v1`. Requests and responses use `application/json`. "
        "Calculator errors use the shared `error` envelope with a code, message, "
        "field-level details, and an ISO 8601 timestamp."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=[{
        "name": "calculator",
        "description": "Nutrition totals, per-serving nutrition, and consumed versus retail package costs.",
    }],
    swagger_ui_parameters={"displayRequestDuration": True},
    lifespan=lifespan,
)
app.include_router(calculator_router, prefix="/api/v1/calculate", tags=["calculator"])


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code,
                        content=error_envelope(exc.code, exc.message,
                                               [ErrorDetail(**item) for item in exc.details]))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    details = [ErrorDetail(field=".".join(str(part) for part in error["loc"] if part != "body"),
                           issue=error["msg"])
               for error in exc.errors()]
    return JSONResponse(status_code=422,
                        content=error_envelope("VALIDATION_ERROR", "Request validation failed",
                                               details))


@app.exception_handler(Exception)
async def unexpected_error_handler(_: Request, exc: Exception):
    # Keep infrastructure details out of the public response. Logging is left to
    # the deployment's exception middleware; this handler guarantees the envelope.
    return JSONResponse(status_code=500,
                        content=error_envelope("INTERNAL_ERROR", "An unexpected error occurred"))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
