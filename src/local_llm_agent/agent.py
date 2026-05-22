"""Agent interface for asking questions through a local LLM."""

from __future__ import annotations

from local_llm_agent.config import Settings, load_settings
from local_llm_agent.ollama_client import OllamaClient
from local_llm_agent.tools.file_reader import LocalDocument, LocalFileReader
from local_llm_agent.tools.project_scanner import (
    ProjectScanner,
    ProjectScanStatus,
    ProjectSummary,
)


class LocalAgent:
    """Simple local agent backed by an Ollama chat model."""

    def __init__(
        self,
        client: OllamaClient | None = None,
        settings: Settings | None = None,
        file_reader: LocalFileReader | None = None,
        project_scanner: ProjectScanner | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.client = client or OllamaClient(
            base_url=self.settings.ollama_base_url,
            model=self.settings.ollama_model,
        )
        self.file_reader = file_reader or LocalFileReader(self.settings.documents_dir)
        self.project_scanner = project_scanner or ProjectScanner(
            self.settings.projects_dir
        )

    def ask(self, question: str) -> str:
        """Ask the local model a question and return its response."""

        cleaned_question = question.strip()
        if not cleaned_question:
            raise ValueError("Question cannot be empty.")

        documents = self.file_reader.load_documents()
        projects = self.project_scanner.scan_projects()
        if not documents and not projects:
            if self._is_project_question(cleaned_question):
                return (
                    "No local projects were found under "
                    f"PROJECTS_DIR={self.settings.projects_dir}. "
                    "Check your .env configuration."
                )
            return self.client.chat(cleaned_question)

        return self.client.chat(
            self._build_context_prompt(cleaned_question, documents, projects)
        )

    def get_project_scan_status(self) -> ProjectScanStatus:
        """Return configured project scanner status for CLI startup output."""

        return self.project_scanner.get_status()

    def _build_context_prompt(
        self,
        question: str,
        documents: list[LocalDocument],
        projects: list[ProjectSummary],
    ) -> str:
        context_sections: list[str] = []
        if projects:
            context_sections.append(self._build_project_report_instructions())
            project_context = "\n\n".join(
                project.to_prompt_context() for project in projects
            )
            context_sections.append(
                "Local project metadata summaries:\n"
                f"{project_context}\n\n"
                "These summaries include repository metadata only, not full source code."
            )

        if documents:
            context_sections.append(self._build_document_context(documents))

        context = "\n\n---\n\n".join(context_sections)

        prompt_intro = "Use the local context below to answer the user's question. "
        if projects:
            prompt_intro += (
                "You have been provided with metadata scanned from the user's local "
                "repositories. Do not say you cannot access the repositories. Base "
                "your analysis on the provided project summaries. "
            )

        return (
            prompt_intro
            + (
                "Answer only from the provided context where possible. If the context "
                "does not contain the answer, say that the local context does not "
                "provide enough information.\n\n"
                f"Local context:\n{context}\n\n"
                f"Question: {question}"
            )
        )

    def _build_project_report_instructions(self) -> str:
        return (
            "Project analysis report requirements:\n"
            "A. Repositories found\n"
            "- List each repository with a one-line summary based on its metadata.\n\n"
            "B. Repeated patterns\n"
            "- Identify patterns across the scanned repositories. Do not give generic advice.\n\n"
            "C. Portfolio readiness\n"
            "- Classify each repository as one of: strong, promising, needs cleanup, archive/ignore.\n\n"
            "D. Common gaps\n"
            "- Cover tests, README quality, CI, packaging, environment setup, and "
            "security/privacy documentation where the metadata supports it.\n\n"
            "E. Recommended standard template\n"
            "- Suggest what every serious repository should include.\n\n"
            "F. Next 5 actions\n"
            "- Give concrete, prioritised actions for this user.\n\n"
            "Rules:\n"
            "- Do not say \"I cannot access your repositories\" because scanned local "
            "metadata has already been provided.\n"
            "- Do not suggest generic tools such as SonarQube, ESLint, or Git unless "
            "they are directly relevant to the scanned metadata."
        )

    def _build_document_context(self, documents: list[LocalDocument]) -> str:
        context_sections = ["Local document context:"]
        for document in documents:
            context_sections.append(
                f"File: {document.name}\n"
                f"Content:\n{document.content.strip()}"
            )

        return "\n\n".join(context_sections)

    def _is_project_question(self, question: str) -> bool:
        lower_question = question.lower()
        project_terms = {
            "repo",
            "repos",
            "repositories",
            "repository",
            "project",
            "projects",
            "coding",
            "portfolio-ready",
            "standardise",
            "standardize",
        }
        return any(term in lower_question for term in project_terms)
