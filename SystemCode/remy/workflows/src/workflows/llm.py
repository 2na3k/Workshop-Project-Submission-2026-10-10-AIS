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
        "num_predict": 800,
        "timeout": 10,
        "max_retries": 0,
    },
    "google_genai": {
        "timeout": 60,
        "max_retries": 2,
    },
}


def _google_api_key() -> str | None:
    """AI Studio key: GEMINI_API_KEY first, then LangChain's own GOOGLE_API_KEY."""
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or None


def message_text(response: Any) -> str:
    """Plain text of a chat response.

    Gemini can return `content` as a list of parts (text plus thought
    signatures) instead of a string, so join only the text parts.
    """
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part if isinstance(part, str) else part.get("text", "")
            for part in content
            if isinstance(part, str) or (isinstance(part, dict) and part.get("type") == "text")
        )
    return str(content)


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

        if self.provider == "google_genai":
            key = _google_api_key()
            if key:
                params["api_key"] = key
            params["transport"] = "rest"

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
        if self.provider == "google_genai":
            return self._check_google()
        # Hosted providers have no cheap ping; failures are caught in invoke().
        return True

    def _check_google(self) -> bool:
        key = self._params.get("api_key") or _google_api_key()
        if not key:
            logger.warning(
                "No Google API key found. Set GEMINI_API_KEY (or GOOGLE_API_KEY) "
                "in the environment or .env."
            )
            return False
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
            response = self._client.invoke(prompt)
            # Normalize: if the content is a list (Gemini), flatten it to a string
            # so the JSON parser in workflows/nodes.py receives a string.
            if isinstance(getattr(response, "content", None), list):
                response.content = message_text(response)
            return response
        except Exception as exc:
            logger.warning(
                "LLM call failed (provider=%s, model=%s): %s: %s",
                self.provider, self.model, type(exc).__name__, exc,
            )
            raise


def main() -> None:
    import sys

    logging.basicConfig(level=logging.INFO)
    prompt = " ".join(sys.argv[1:]) or "Say hello in one short sentence."

    llm = ChatLLM()
    print(f"[{llm.provider}:{llm.model}] > {prompt}")

    response = llm.invoke(prompt)
    print(message_text(response))


if __name__ == "__main__":
    main()
