from local_llm_agent import cli
from local_llm_agent.cli import expand_question_shortcut, run_once
from local_llm_agent.config import Settings
from local_llm_agent.ollama_client import OllamaConnectionError
from local_llm_agent.tools.project_scanner import ProjectScanStatus


class FakeAgent:
    def __init__(self, response="Test answer", error=None):
        self.response = response
        self.error = error
        self.questions = []
        self.settings = Settings(
            ollama_base_url="http://localhost:11434",
            ollama_model="llama3.2:3b",
            projects_dir="/tmp/projects",
        )

    def ask(self, question: str) -> str:
        self.questions.append(question)
        if self.error:
            raise self.error
        return self.response

    def get_project_scan_status(self):
        return ProjectScanStatus(
            projects_dir="/tmp/projects",
            exists=True,
            project_count=2,
            project_names=("alpha", "beta"),
        )


def test_run_once_prints_answer(capsys):
    agent = FakeAgent(response="Local answer")

    exit_code = run_once(agent, "What is local?")

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == "Local answer\n"
    assert captured.err == ""
    assert agent.questions == ["What is local?"]


def test_expand_question_shortcut_for_local_repo_analysis():
    expanded = expand_question_shortcut("analyze my local repos")

    assert expanded == (
        "Analyse the scanned local repository metadata and produce a "
        "portfolio-readiness report with repeated patterns, common gaps, "
        "and next actions."
    )


def test_run_once_prints_errors_to_stderr(capsys):
    agent = FakeAgent(error=OllamaConnectionError("Ollama is not running"))

    exit_code = run_once(agent, "Hello?")

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == "Error: Ollama is not running\n"


def test_main_smoke_with_question(monkeypatch, capsys):
    class FakeLocalAgent:
        settings = Settings(
            ollama_base_url="http://localhost:11434",
            ollama_model="llama3.2:3b",
            projects_dir="/tmp/projects",
        )

        def ask(self, question: str) -> str:
            return f"answer to {question}"

        def get_project_scan_status(self):
            return ProjectScanStatus(
                projects_dir="/tmp/projects",
                exists=True,
                project_count=1,
                project_names=("portfolio",),
            )

    monkeypatch.setattr("sys.argv", ["local-llm-agent", "What", "now?"])
    monkeypatch.setattr(cli, "LocalAgent", FakeLocalAgent)

    exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == "answer to What now?\n"
    assert "OLLAMA_BASE_URL=http://localhost:11434" in captured.err
    assert "OLLAMA_MODEL=llama3.2:3b" in captured.err
    assert "PROJECTS_DIR=/tmp/projects" in captured.err
    assert "PROJECTS_DIR_EXISTS=True" in captured.err
    assert "projects=1" in captured.err
    assert "names=portfolio" in captured.err


def test_startup_summary_shows_project_scan_status(capsys):
    cli.print_startup_summary(FakeAgent())

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "OLLAMA_BASE_URL=http://localhost:11434" in captured.err
    assert "OLLAMA_MODEL=llama3.2:3b" in captured.err
    assert "PROJECTS_DIR=/tmp/projects" in captured.err
    assert "PROJECTS_DIR_EXISTS=True" in captured.err
    assert "projects=2" in captured.err
    assert "names=alpha, beta" in captured.err
