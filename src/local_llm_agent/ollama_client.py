"""Small Ollama API client."""

from __future__ import annotations

from dataclasses import dataclass

import requests


class OllamaError(RuntimeError):
    """Base error raised for Ollama client failures."""


class OllamaConnectionError(OllamaError):
    """Raised when the local Ollama server cannot be reached."""


class OllamaModelNotFoundError(OllamaError):
    """Raised when the configured Ollama model is not available locally."""


@dataclass
class OllamaClient:
    """Client for Ollama's local chat API."""

    base_url: str
    model: str
    timeout: int = 120

    def chat(self, message: str) -> str:
        """Send a user message to Ollama and return the assistant response."""

        url = f"{self.base_url.rstrip('/')}/api/chat"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": message}],
            "stream": False,
        }

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
        except requests.ConnectionError as exc:
            raise OllamaConnectionError(
                f"Could not connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running with `ollama serve`."
            ) from exc
        except requests.HTTPError as exc:
            response_text = response.text
            lower_response_text = response_text.lower()
            is_model_error = response.status_code == 404 or (
                "model" in lower_response_text
                and (
                    "not found" in lower_response_text
                    or "pull" in lower_response_text
                    or "invalid" in lower_response_text
                )
            )
            if is_model_error:
                raise OllamaModelNotFoundError(
                    f"Model '{self.model}' was not found locally. "
                    f"Run `ollama pull {self.model}` and try again."
                ) from exc
            raise OllamaError(f"Ollama request failed: {response_text}") from exc
        except requests.RequestException as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise OllamaError("Ollama returned an invalid JSON response.") from exc

        message_data = data.get("message", {})
        content = message_data.get("content")

        if not content:
            raise OllamaError("Ollama returned an empty response.")

        return content.strip()
