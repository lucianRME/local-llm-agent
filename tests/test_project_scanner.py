import pytest

from local_llm_agent.tools.project_scanner import ProjectScanner


def test_scanner_can_scan_temporary_projects_directory(tmp_path):
    project = tmp_path / "demo"
    project.mkdir()
    (project / "README.md").write_text("# Demo", encoding="utf-8")
    (project / "AGENTS.md").write_text("# Agent notes", encoding="utf-8")
    (project / "LICENSE").write_text("MIT", encoding="utf-8")
    (project / ".gitignore").write_text(".env\n", encoding="utf-8")
    (project / "requirements.txt").write_text("pytest", encoding="utf-8")
    (project / "app.py").write_text("print('hello')", encoding="utf-8")
    (project / "todo.py").write_text(
        "# TODO: add tests\n# FIXME: docs", encoding="utf-8"
    )
    tests_dir = project / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_app.py").write_text("", encoding="utf-8")
    workflows_dir = project / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "tests.yml").write_text("name: tests", encoding="utf-8")

    summaries = ProjectScanner(tmp_path).scan_projects()

    assert len(summaries) == 1
    assert summaries[0].name == "demo"
    assert summaries[0].relative_path == "demo"
    assert summaries[0].file_count == 8
    assert summaries[0].extensions == (".py", ".md", ".txt")
    assert summaries[0].has_readme is True
    assert summaries[0].has_tests is True
    assert summaries[0].has_agents is True
    assert summaries[0].has_license is True
    assert summaries[0].has_gitignore is True
    assert summaries[0].has_ci is True
    assert summaries[0].has_clear_structure is True
    assert summaries[0].dependency_files == ("requirements.txt",)
    assert summaries[0].todo_count == 2
    assert summaries[0].maturity_score == 100
    assert summaries[0].maturity_band == "promising"
    assert "README.md" in summaries[0].top_level_entries


def test_scanner_treats_immediate_child_folders_as_projects(tmp_path):
    alpha = tmp_path / "alpha"
    beta = tmp_path / "beta"
    nested = alpha / "nested-project"
    alpha.mkdir()
    beta.mkdir()
    nested.mkdir()
    (alpha / "main.py").write_text("", encoding="utf-8")
    (beta / "package.json").write_text("{}", encoding="utf-8")
    (nested / "README.md").write_text("# Nested", encoding="utf-8")

    summaries = ProjectScanner(tmp_path).scan_projects()

    assert [summary.name for summary in summaries] == ["alpha", "beta"]


def test_scanner_status_reports_configured_dir_and_project_names(tmp_path):
    (tmp_path / "alpha").mkdir()
    (tmp_path / "beta").mkdir()
    (tmp_path / ".github").mkdir()

    status = ProjectScanner(tmp_path).get_status()

    assert status.projects_dir == str(tmp_path)
    assert status.exists is True
    assert status.project_count == 2
    assert status.project_names == ("alpha", "beta")


def test_scanner_does_not_scan_outside_configured_root(tmp_path):
    projects_dir = tmp_path / "projects"
    outside_dir = tmp_path / "outside"
    projects_dir.mkdir()
    outside_dir.mkdir()
    (outside_dir / "secret.py").write_text("hidden = True", encoding="utf-8")
    (projects_dir / "outside-link").symlink_to(outside_dir, target_is_directory=True)

    summaries = ProjectScanner(projects_dir).scan_projects()

    assert summaries == []


def test_scanner_skips_secret_looking_files(tmp_path):
    project = tmp_path / "demo"
    project.mkdir()
    (project / "app.py").write_text("print('hello')", encoding="utf-8")
    (project / ".env").write_text("SECRET=value", encoding="utf-8")
    (project / "service.pem").write_text("private key", encoding="utf-8")
    (project / "api_token.txt").write_text("token", encoding="utf-8")
    (project / "credentials.json").write_text("{}", encoding="utf-8")

    summary = ProjectScanner(tmp_path).scan_projects()[0]

    assert summary.file_count == 1
    assert summary.extensions == (".py",)
    assert summary.skipped_files == 4


def test_scanner_ignores_noisy_folders(tmp_path):
    project = tmp_path / "demo"
    project.mkdir()
    (project / "app.py").write_text("", encoding="utf-8")
    node_modules = project / "node_modules"
    node_modules.mkdir()
    (node_modules / "package.js").write_text("", encoding="utf-8")
    git_dir = project / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("", encoding="utf-8")

    summary = ProjectScanner(tmp_path).scan_projects()[0]

    assert summary.file_count == 1
    assert summary.extensions == (".py",)


def test_scanner_skips_binary_and_large_files(tmp_path):
    project = tmp_path / "demo"
    project.mkdir()
    (project / "app.py").write_text("", encoding="utf-8")
    (project / "image.bin").write_bytes(b"\x00\x01binary")
    (project / "large.txt").write_text("x" * 1_000_001, encoding="utf-8")

    summary = ProjectScanner(tmp_path).scan_projects()[0]

    assert summary.file_count == 1
    assert summary.extensions == (".py",)
    assert summary.skipped_files == 2


def test_resolve_project_path_blocks_traversal(tmp_path):
    scanner = ProjectScanner(tmp_path)

    with pytest.raises(ValueError, match="inside the projects directory"):
        scanner._resolve_project_path("../outside")


def test_scanner_classifies_learning_course_projects(tmp_path):
    project = tmp_path / "coursera-python-course"
    project.mkdir()
    (project / "README.md").write_text("# Course", encoding="utf-8")
    (project / "week1.py").write_text("", encoding="utf-8")

    summary = ProjectScanner(tmp_path).scan_projects()[0]

    assert summary.project_type == "learning_course"
    assert "course" in summary.classification_reason
    assert summary.maturity_band == "archive_or_ignore"


def test_scanner_classifies_interview_prep_projects(tmp_path):
    project = tmp_path / "leetcode-interview-prep"
    project.mkdir()
    (project / "README.md").write_text("# Practice", encoding="utf-8")
    (project / "solutions.py").write_text("", encoding="utf-8")

    summary = ProjectScanner(tmp_path).scan_projects()[0]

    assert summary.project_type == "interview_prep"
    assert "interview" in summary.classification_reason
    assert summary.maturity_band == "archive_or_ignore"


def test_scanner_classifies_app_like_repos_as_product_apps(tmp_path):
    project = tmp_path / "synapse-app"
    project.mkdir()
    (project / "README.md").write_text("# Synapse", encoding="utf-8")
    (project / "package.json").write_text("{}", encoding="utf-8")
    src_dir = project / "src"
    src_dir.mkdir()
    (src_dir / "index.ts").write_text("", encoding="utf-8")
    tests_dir = project / "tests"
    tests_dir.mkdir()
    (tests_dir / "app.test.ts").write_text("", encoding="utf-8")

    summary = ProjectScanner(tmp_path).scan_projects()[0]

    assert summary.project_type == "product_app"
    assert summary.has_clear_structure is True
    assert summary.maturity_band == "promising"


def test_scanner_detects_common_ci_configs(tmp_path):
    github_project = tmp_path / "github-ci"
    github_project.mkdir()
    workflows_dir = github_project / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "test.yaml").write_text("name: test", encoding="utf-8")
    gitlab_project = tmp_path / "gitlab-ci"
    gitlab_project.mkdir()
    (gitlab_project / ".gitlab-ci.yml").write_text("test: true", encoding="utf-8")

    summaries = ProjectScanner(tmp_path).scan_projects()

    assert [summary.has_ci for summary in summaries] == [True, True]


def test_scanner_calculates_maturity_score(tmp_path):
    project = tmp_path / "client-app"
    project.mkdir()
    (project / "README.md").write_text("# App", encoding="utf-8")
    (project / "AGENTS.md").write_text("# Instructions", encoding="utf-8")
    (project / "LICENSE").write_text("MIT", encoding="utf-8")
    (project / ".gitignore").write_text(".env\n", encoding="utf-8")
    (project / "pyproject.toml").write_text("[project]\nname='x'", encoding="utf-8")
    src_dir = project / "src"
    src_dir.mkdir()
    (src_dir / "app.py").write_text("# TODO one\n# TODO two\n", encoding="utf-8")
    tests_dir = project / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_app.py").write_text("", encoding="utf-8")
    workflows_dir = project / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "ci.yml").write_text("name: ci", encoding="utf-8")

    summary = ProjectScanner(tmp_path).scan_projects()[0]

    assert summary.maturity_score == 100
    assert summary.maturity_band == "strong"


def test_maturity_band_does_not_mark_learning_as_strong(tmp_path):
    project = tmp_path / "coursera-full-stack-course"
    project.mkdir()
    (project / "README.md").write_text("# Course", encoding="utf-8")
    (project / "AGENTS.md").write_text("# Instructions", encoding="utf-8")
    (project / "LICENSE").write_text("MIT", encoding="utf-8")
    (project / ".gitignore").write_text(".env\n", encoding="utf-8")
    (project / "package.json").write_text("{}", encoding="utf-8")
    (project / "src").mkdir()
    (project / "src" / "index.ts").write_text("", encoding="utf-8")
    (project / "tests").mkdir()
    (project / "tests" / "app.test.ts").write_text("", encoding="utf-8")
    workflows_dir = project / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "ci.yml").write_text("name: ci", encoding="utf-8")

    summary = ProjectScanner(tmp_path).scan_projects()[0]

    assert summary.project_type == "learning_course"
    assert summary.maturity_score == 100
    assert summary.maturity_band == "needs_cleanup"
