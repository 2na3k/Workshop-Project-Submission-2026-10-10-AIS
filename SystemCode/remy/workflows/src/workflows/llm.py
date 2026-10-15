"""Small configurable LangChain chat-model wrapper."""

from __future__ import annotations

import os
from typing import Any


class ChatLLM:
    def __init__(self, model: str | None = None, provider: str | None = None) -> None:
        self.model = model or os.getenv("REMY_LLM_MODEL", "llama3.2")
        self.provider = provider or os.getenv("REMY_LLM_PROVIDER", "ollama")
        from langchain.chat_models import init_chat_model

        self._client = init_chat_model(self.model, model_provider=self.provider)

    def invoke(self, prompt: str) -> Any:
        return self._client.invoke(prompt)
