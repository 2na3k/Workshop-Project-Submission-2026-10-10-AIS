import json

from app.chat_contract import DoneEvent
from app.sse import serialize_event


def test_frame_shape():
    event = DoneEvent(event="done", status="complete", trace_id="trace-1")

    frame = serialize_event(event)

    assert frame.startswith("event: done\ndata: ")
    assert frame.endswith("\n\n")
    data = json.loads(frame.split("data: ", 1)[1].strip())
    assert data == event.model_dump(mode="json")
    assert "trace" not in data
