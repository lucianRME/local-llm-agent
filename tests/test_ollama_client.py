import requests

from local_llm_agent.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaError,
    OllamaModelNotFoundError,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self.payload = payload or {}
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def json(self):
        return self.payload


class InvalidJsonResponse(FakeResponse):
    def json(self):
        raise ValueError("invalid json")


def test_chat_posts_to_ollama_chat_endpoint(monkeypatch):
    calls = []

    def fake_post(url, json, timeout):
        calls.append({"url": url, "json": json, "timeout": timeout})
        return FakeResponse(payload={"message": {"content": " Hello! "}})

    monkeypatch.setattr("local_llm_agent.ollama_client.requests.post", fake_post)
    client = OllamaClient(base_url="http://localhost:11434/", model="llama3.2:3b")

    answer = client.chat("Hi")

    assert answer == "Hello!"
    assert calls == [
        {
            "url": "http://localhost:11434/api/chat",
            "json": {
                "model": "llama3.2:3b",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": False,
            },
            "timeout": 120,
        }
    ]


def test_chat_raises_clear_connection_error(monkeypatch):
    def fake_post(url, json, timeout):
        raise requests.ConnectionError("Connection refused")

    monkeypatch.setattr("local_llm_agent.ollama_client.requests.post", fake_post)
    client = OllamaClient(base_url="http://localhost:11434", model="llama3.2:3b")

    try:
        client.chat("Hi")
    except OllamaConnectionError as exc:
        assert "Make sure Ollama is running" in str(exc)
    else:
        raise AssertionError("Expected OllamaConnectionError")


def test_chat_raises_clear_missing_model_error(monkeypatch):
    def fake_post(url, json, timeout):
        return FakeResponse(status_code=404, text="model not found")

    monkeypatch.setattr("local_llm_agent.ollama_client.requests.post", fake_post)
    client = OllamaClient(base_url="http://localhost:11434", model="llama3.2:3b")

    try:
        client.chat("Hi")
    except OllamaModelNotFoundError as exc:
        assert "ollama pull llama3.2:3b" in str(exc)
    else:
        raise AssertionError("Expected OllamaModelNotFoundError")


def test_chat_raises_clear_invalid_model_error(monkeypatch):
    def fake_post(url, json, timeout):
        return FakeResponse(status_code=400, text="invalid model name")

    monkeypatch.setattr("local_llm_agent.ollama_client.requests.post", fake_post)
    client = OllamaClient(base_url="http://localhost:11434", model="bad model")

    try:
        client.chat("Hi")
    except OllamaModelNotFoundError as exc:
        assert "ollama pull bad model" in str(exc)
    else:
        raise AssertionError("Expected OllamaModelNotFoundError")


def test_chat_raises_error_for_invalid_json(monkeypatch):
    def fake_post(url, json, timeout):
        return InvalidJsonResponse()

    monkeypatch.setattr("local_llm_agent.ollama_client.requests.post", fake_post)
    client = OllamaClient(base_url="http://localhost:11434", model="llama3.2:3b")

    try:
        client.chat("Hi")
    except OllamaError as exc:
        assert "invalid JSON response" in str(exc)
    else:
        raise AssertionError("Expected OllamaError")


def test_chat_raises_error_for_empty_response(monkeypatch):
    def fake_post(url, json, timeout):
        return FakeResponse(payload={"message": {"content": ""}})

    monkeypatch.setattr("local_llm_agent.ollama_client.requests.post", fake_post)
    client = OllamaClient(base_url="http://localhost:11434", model="llama3.2:3b")

    try:
        client.chat("Hi")
    except OllamaError as exc:
        assert "empty response" in str(exc)
    else:
        raise AssertionError("Expected OllamaError")
