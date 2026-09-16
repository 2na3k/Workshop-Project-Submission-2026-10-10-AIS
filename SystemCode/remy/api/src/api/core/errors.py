from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    field: str | None = None
    issue: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)
    timestamp: datetime


class ErrorEnvelope(BaseModel):
    error: ErrorBody


def error_envelope(code: str, message: str, details: list[ErrorDetail] | None = None) -> dict:
    return {"error": {"code": code, "message": message,
                       "details": [d.model_dump() for d in (details or [])],
                       "timestamp": datetime.now(timezone.utc).isoformat()}}
