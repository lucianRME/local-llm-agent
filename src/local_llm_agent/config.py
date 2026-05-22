"""Application configuration loaded from environment variables."""

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2:3b"
DEFAULT_DOCUMENTS_DIR = "data/documents"
DEFAULT_PROJECTS_DIR = "data/projects"


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the local LLM agent."""

    ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL
    ollama_model: str = DEFAULT_OLLAMA_MODEL
    documents_dir: str = DEFAULT_DOCUMENTS_DIR
    projects_dir: str = DEFAULT_PROJECTS_DIR


def load_settings() -> Settings:
    """Load settings from `.env` and environment variables."""

    load_dotenv(dotenv_path=Path(".env"))

    return Settings(
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL),
        ollama_model=os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL),
        documents_dir=os.getenv("DOCUMENTS_DIR", DEFAULT_DOCUMENTS_DIR),
        projects_dir=os.getenv("PROJECTS_DIR", DEFAULT_PROJECTS_DIR),
    )
