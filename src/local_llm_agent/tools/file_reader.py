"""Safe local document reader."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SUPPORTED_EXTENSIONS = {".txt", ".md"}


@dataclass(frozen=True)
class LocalDocument:
    """A supported local document loaded from disk."""

    name: str
    content: str


class LocalFileReader:
    """Read supported documents from one configured directory."""

    def __init__(self, documents_dir: str | Path) -> None:
        self.documents_dir = Path(documents_dir)

    def load_documents(self) -> list[LocalDocument]:
        """Load all supported documents from the configured directory."""

        if not self.documents_dir.exists() or not self.documents_dir.is_dir():
            return []

        documents: list[LocalDocument] = []

        for path in sorted(self.documents_dir.iterdir()):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            try:
                documents.append(self.read_document(path.name))
            except (OSError, ValueError):
                continue

        return documents

    def read_document(self, file_name: str) -> LocalDocument:
        """Read one supported document by name from the configured directory."""

        path = self._resolve_document_path(file_name)
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported document type: {path.suffix}")

        content = path.read_text(encoding="utf-8")
        return LocalDocument(name=path.name, content=content)

    def _resolve_document_path(self, file_name: str) -> Path:
        documents_root = self.documents_dir.resolve()
        path = (documents_root / file_name).resolve()

        if path.parent != documents_root:
            raise ValueError("Document path must stay inside the documents directory.")

        return path
