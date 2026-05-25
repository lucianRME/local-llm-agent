import pytest

from local_llm_agent.agent import LocalAgent
from local_llm_agent.config import Settings
from local_llm_agent.tools.file_reader import LocalDocument
from local_llm_agent.tools.project_scanner import ProjectScanStatus
from local_llm_agent.tools.project_scanner import ProjectSummary


class FakeOllamaClient:
    def __init__(self, response="Test answer"):
        self.response = response
        self.messages = []

    def chat(self, message: str) -> str:
        self.messages.append(message)
        return self.response


class FakeFileReader:
    def __init__(self, documents=None):
        self.documents = documents or []

    def load_documents(self):
        return self.documents


class FakeProjectScanner:
    def __init__(self, projects=None):
        self.projects = projects or []

    def scan_projects(self):
        return self.projects

    def get_status(self):
        return ProjectScanStatus(
            projects_dir="data/projects",
            exists=True,
            project_count=len(self.projects),
            project_names=tuple(project.name for project in self.projects),
        )


def test_agent_asks_client_and_returns_answer():
    client = FakeOllamaClient(response="Hello from local model")
    agent = LocalAgent(
        client=client,
        settings=Settings(),
        file_reader=FakeFileReader(),
        project_scanner=FakeProjectScanner(),
    )

    answer = agent.ask("  What can you do?  ")

    assert answer == "Hello from local model"
    assert client.messages == ["What can you do?"]


def test_agent_rejects_empty_question():
    agent = LocalAgent(
        client=FakeOllamaClient(),
        settings=Settings(),
        file_reader=FakeFileReader(),
        project_scanner=FakeProjectScanner(),
    )

    with pytest.raises(ValueError, match="Question cannot be empty"):
        agent.ask("   ")


def test_agent_includes_document_context_when_available():
    client = FakeOllamaClient(response="Document answer")
    file_reader = FakeFileReader(
        documents=[
            LocalDocument(name="notes.txt", content="The project uses Ollama."),
            LocalDocument(name="plan.md", content="# Plan\nKeep it local."),
        ]
    )
    agent = LocalAgent(
        client=client,
        settings=Settings(),
        file_reader=file_reader,
        project_scanner=FakeProjectScanner(),
    )

    answer = agent.ask("What does the project use?")

    assert answer == "Document answer"
    prompt = client.messages[0]
    assert "Use the local context below" in prompt
    assert "File: notes.txt" in prompt
    assert "The project uses Ollama." in prompt
    assert "File: plan.md" in prompt
    assert "Question: What does the project use?" in prompt


def test_agent_falls_back_when_no_documents_exist():
    client = FakeOllamaClient(response="Normal answer")
    agent = LocalAgent(
        client=client,
        settings=Settings(),
        file_reader=FakeFileReader(documents=[]),
        project_scanner=FakeProjectScanner(),
    )

    answer = agent.ask("What is local?")

    assert answer == "Normal answer"
    assert client.messages == ["What is local?"]


def test_agent_includes_project_metadata_when_available():
    client = FakeOllamaClient(response="Project answer")
    project_scanner = FakeProjectScanner(
        projects=[
            ProjectSummary(
                name="portfolio-app",
                path="/safe/projects/portfolio-app",
                relative_path="portfolio-app",
                file_count=12,
                extensions=(".md", ".py"),
                has_readme=True,
                has_tests=False,
                has_agents=True,
                has_license=False,
                has_gitignore=True,
                has_ci=True,
                has_clear_structure=True,
                dependency_files=("requirements.txt",),
                todo_count=3,
                top_level_entries=("README.md", "src", "tests"),
                project_type="product_app",
                classification_reason="Project metadata indicates an app-like repository.",
                maturity_score=65,
                maturity_band="promising",
                skipped_files=2,
            )
        ]
    )
    agent = LocalAgent(
        client=client,
        settings=Settings(),
        file_reader=FakeFileReader(),
        project_scanner=project_scanner,
    )

    answer = agent.ask("Which projects need tests?")

    assert answer == "Project answer"
    prompt = client.messages[0]
    assert "Local project metadata summaries:" in prompt
    assert "Project: portfolio-app" in prompt
    assert "Relative path: portfolio-app" in prompt
    assert "Tests present: no" in prompt
    assert "AGENTS.md present: yes" in prompt
    assert "License present: no" in prompt
    assert ".gitignore present: yes" in prompt
    assert "CI config present: yes" in prompt
    assert "Clear app/source structure: yes" in prompt
    assert "Dependency files: requirements.txt" in prompt
    assert "TODO/FIXME count: 3" in prompt
    assert "Notable top-level files/folders: README.md, src, tests" in prompt
    assert "Project type: product_app" in prompt
    assert "Classification reason: Project metadata indicates an app-like repository." in prompt
    assert "Maturity score: 65" in prompt
    assert "Maturity band: promising" in prompt
    assert "not full source code" in prompt
    assert "Do not say you cannot access the repositories" in prompt
    assert "Question: Which projects need tests?" in prompt


def test_project_prompt_includes_requested_report_sections_and_categories():
    client = FakeOllamaClient(response="Project answer")
    project_scanner = FakeProjectScanner(
        projects=[
            ProjectSummary(
                name="client-portal",
                path="/safe/projects/client-portal",
                relative_path="client-portal",
                file_count=20,
                extensions=(".ts", ".tsx"),
                has_readme=True,
                has_tests=True,
                has_agents=False,
                has_license=True,
                has_gitignore=True,
                has_ci=False,
                has_clear_structure=True,
                dependency_files=("package.json",),
                todo_count=0,
                top_level_entries=("README.md", "package.json", "src"),
                project_type="product_app",
                classification_reason="Project metadata indicates an app-like repository.",
                maturity_score=65,
                maturity_band="promising",
                skipped_files=0,
            )
        ]
    )
    agent = LocalAgent(
        client=client,
        settings=Settings(),
        file_reader=FakeFileReader(),
        project_scanner=project_scanner,
    )

    agent.ask("Analyse my repositories")

    prompt = client.messages[0]
    assert "Project: client-portal" in prompt
    assert "Project type: product_app" in prompt
    assert "Maturity score: 65" in prompt
    assert "Maturity band: promising" in prompt
    assert "A. Repository inventory" in prompt
    assert "B. Strongest portfolio candidates" in prompt
    assert "C. Supporting/learning repos" in prompt
    assert "D. Repeated patterns across serious repos" in prompt
    assert "E. Common gaps by priority" in prompt
    assert "F. Recommended next 5 actions" in prompt
    assert "learning_course, interview_prep, archive_or_personal, or unknown" in prompt
    assert "Learning and interview-prep repos" in prompt
    assert "Do not say \"I cannot access your repositories\"" in prompt
    assert "Do not suggest generic tools such as SonarQube, ESLint, or Git" in prompt


def test_agent_does_not_call_ollama_when_project_question_has_no_projects():
    client = FakeOllamaClient(response="Should not be used")
    agent = LocalAgent(
        client=client,
        settings=Settings(projects_dir="/missing/projects"),
        file_reader=FakeFileReader(),
        project_scanner=FakeProjectScanner(),
    )

    answer = agent.ask("Analyze my local repos")

    assert answer == (
        "No local projects were found under PROJECTS_DIR=/missing/projects. "
        "Check your .env configuration."
    )
    assert client.messages == []
