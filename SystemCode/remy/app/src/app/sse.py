"""Serialize the fixed chat event vocabulary as Server-Sent Events frames."""

from pydantic import BaseModel

from app.chat_contract import (
    DoneEvent,
    ErrorEvent,
    MetadataEvent,
    PlanUpdatedEvent,
    TokenEvent,
)

_EVENT_TYPES = (MetadataEvent, TokenEvent, PlanUpdatedEvent, ErrorEvent, DoneEvent)


def serialize_event(event: BaseModel) -> str:
    if not isinstance(event, _EVENT_TYPES):
        raise TypeError("event must be one of the five chat event models")
    return f"event: {event.event}\ndata: {event.model_dump_json()}\n\n"
