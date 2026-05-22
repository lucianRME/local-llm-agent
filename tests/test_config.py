from local_llm_agent.config import (
    DEFAULT_DOCUMENTS_DIR,
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_PROJECTS_DIR,
    load_settings,
)


def test_load_settings_uses_defaults(monkeypatch):
    monkeypatch.setattr("local_llm_agent.config.load_dotenv", lambda *_, **__: None)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("DOCUMENTS_DIR", raising=False)
    monkeypatch.delenv("PROJECTS_DIR", raising=False)

    settings = load_settings()

    assert settings.ollama_base_url == DEFAULT_OLLAMA_BASE_URL
    assert settings.ollama_model == DEFAULT_OLLAMA_MODEL
    assert settings.ollama_model == "llama3.2:3b"
    assert settings.documents_dir == DEFAULT_DOCUMENTS_DIR
    assert settings.projects_dir == DEFAULT_PROJECTS_DIR


def test_load_settings_uses_environment(monkeypatch):
    monkeypatch.setattr("local_llm_agent.config.load_dotenv", lambda *_, **__: None)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://example.test:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "custom-model")
    monkeypatch.setenv("DOCUMENTS_DIR", "custom/documents")
    monkeypatch.setenv("PROJECTS_DIR", "/tmp/projects")

    settings = load_settings()

    assert settings.ollama_base_url == "http://example.test:11434"
    assert settings.ollama_model == "custom-model"
    assert settings.documents_dir == "custom/documents"
    assert settings.projects_dir == "/tmp/projects"


def test_load_settings_loads_projects_dir_from_dotenv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PROJECTS_DIR", raising=False)
    (tmp_path / ".env").write_text(
        "PROJECTS_DIR=/tmp/dotenv-projects\n",
        encoding="utf-8",
    )

    settings = load_settings()

    assert settings.projects_dir == "/tmp/dotenv-projects"
