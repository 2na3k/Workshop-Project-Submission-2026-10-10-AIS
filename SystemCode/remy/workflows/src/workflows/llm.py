"""Small configurable LangChain chat-model wrapper."""

from __future__ import annotations

import os
from typing import Any


class ChatLLM:
    def __init__(self, model: str | None = None, provider: str | None = None) -> None:
        self.model = model or os.getenv("REMY_LLM_MODEL", "llama3.2:3b")
        self.provider = provider or os.getenv("REMY_LLM_PROVIDER", "ollama")
        self.base_url = os.getenv("REMY_LLM_BASE_URL", "http://localhost:11434")
        self.temperature = float(os.getenv("REMY_LLM_TEMPERATURE", "0.0"))
        from langchain.chat_models import init_chat_model

        self._client = init_chat_model(
            self.model,
            base_url=self.base_url,
            model_provider=self.provider,
            temperature=self.temperature,
            keep_alive="1h"
        )

    def invoke(self, prompt: str) -> Any:
        return self._client.invoke(prompt)
