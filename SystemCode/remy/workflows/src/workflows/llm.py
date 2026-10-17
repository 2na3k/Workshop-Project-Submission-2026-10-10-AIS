"""Small configurable LangChain chat-model wrapper."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

_PROVIDER_DEFAULTS: dict[str, dict[str, Any]] = {
    "ollama": {
        "base_url": os.getenv("REMY_LLM_BASE_URL", "http://localhost:11434"),
        "keep_alive": "1h",
    },
}


class ChatLLM:
    def __init__(
            self,
            model: str | None = None,
            provider: str | None = None,
            check: bool = True,
            **kwargs: Any,
    ) -> None:
        self.provider: str = provider or os.getenv("REMY_LLM_PROVIDER") or "ollama"
        self.model: str = model or os.getenv("REMY_LLM_MODEL") or "llama3.2:3b"

        params: dict[str, Any] = {"temperature": 0}
        params.update(_PROVIDER_DEFAULTS.get(self.provider, {}))
        params.update(kwargs)
        self._params = params

        from langchain.chat_models import init_chat_model

        self._client = init_chat_model(
            self.model,
            model_provider=self.provider,
            **params
        )

        if check:
            self.check_connection()

    def check_connection(self) -> bool:
        """Warn (never raise) if the provider looks unreachable. Returns True if OK."""
        if self.provider == "ollama":
            return self._check_ollama()
        # Hosted providers have no cheap ping; failures are caught in invoke().
        return True

    def _check_ollama(self) -> bool:
        base_url = self._params["base_url"].rstrip("/")
        try:
            with urllib.request.urlopen(f"{base_url}/api/tags", timeout=2) as r:
                names = {m["name"] for m in json.load(r).get("models", [])}
        except (urllib.error.URLError, TimeoutError, OSError):
            logger.warning(
                "Ollama is not reachable at %s. Start it with `ollama serve` "
                "or set REMY_LLM_BASE_URL.",
                base_url,
            )
            return False

        wanted: str = self.model if ":" in self.model else f"{self.model}:latest"
        if wanted not in names:
            logger.warning(
                "Ollama is running but model '%s' is not pulled. "
                "Run `ollama pull %s`. Available: %s",
                self.model, self.model, sorted(names) or "none",
            )
            return False
        return True

    def invoke(self, prompt: str) -> Any:
        try:
            return self._client.invoke(prompt)
        except Exception as exc:
            logger.warning(
                "LLM call failed (provider=%s, model=%s): %s: %s",
                self.provider, self.model, type(exc).__name__, exc,
            )
            raise
