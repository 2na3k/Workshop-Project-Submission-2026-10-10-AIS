import pytest
from pydantic import ValidationError


def test_chat_request_requires_session_and_message():
    from app.chat_contract import ChatRequest

    request = ChatRequest(session_id="session-1", message="Plan meals")
    assert request.model_dump() == {
        "session_id": "session-1",
        "message": "Plan meals",
        "user_context": None,
    }
    assert ChatRequest(session_id="session-1", message="Plan meals", user_context={})

    with pytest.raises(ValidationError):
        ChatRequest(message="Plan meals")
    with pytest.raises(ValidationError):
        ChatRequest(session_id="session-1")
