"""Safe local project scanner."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


IGNORED_DIRS = {
    ".git",
    ".github",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    ".next",
    "coverage",
}
SECRET_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_dsa",
    "credentials.json",
}
SECRET_NAME_PARTS = {"secret", "token", "credential", "password"}
SECRET_SUFFIXES = {".pem", ".key"}
MAX_FILE_SIZE_BYTES = 1_000_000
READ_ME_NAMES = {"readme", "readme.md", "readme.txt"}
LICENSE_NAMES = {"license", "license.md", "license.txt"}
DEPENDENCY_FILE_NAMES = {
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "poetry.lock",
    "pipfile",
    "cargo.toml",
    "go.mod",
    "gemfile",
}
CI_FILE_NAMES = {
    ".gitlab-ci.yml",
    ".travis.yml",
    "azure-pipelines.yml",
    "bitbucket-pipelines.yml",
    "circle.yml",
    "jenkinsfile",
}
SOURCE_ENTRY_NAMES = {
    "app",
    "apps",
    "cli",
    "cmd",
    "lib",
    "package",
    "packages",
    "server",
    "src",
}
APP_ENTRY_NAMES = {
    "app.py",
    "main.py",
    "index.html",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
}
TEXT_EXTENSIONS = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".rs",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}


@dataclass(frozen=True)
class ProjectSummary:
    """Metadata-only summary for one local project."""

    name: str
    path: str
    relative_path: str
    file_count: int
    extensions: tuple[str, ...]
    has_readme: bool
    has_tests: bool
    has_agents: bool
    has_license: bool
    has_gitignore: bool
    has_ci: bool
    has_clear_structure: bool
    dependency_files: tuple[str, ...]
    todo_count: int
    top_level_entries: tuple[str, ...]
    project_type: str
    classification_reason: str
    maturity_score: int
    maturity_band: str
    skipped_files: int

    def to_prompt_context(self) -> str:
        """Return a short metadata summary safe to include in an LLM prompt."""

        extensions = ", ".join(self.extensions) if self.extensions else "none"
        dependency_files = (
            ", ".join(self.dependency_files) if self.dependency_files else "none"
        )
        top_level_entries = (
            ", ".join(self.top_level_entries) if self.top_level_entries else "none"
        )
        return (
            f"Project: {self.name}\n"
            f"Relative path: {self.relative_path}\n"
            f"Total file count: {self.file_count}\n"
            f"Main language extensions: {extensions}\n"
            f"README present: {self._yes_no(self.has_readme)}\n"
            f"Tests present: {self._yes_no(self.has_tests)}\n"
            f"AGENTS.md present: {self._yes_no(self.has_agents)}\n"
            f"License present: {self._yes_no(self.has_license)}\n"
            f".gitignore present: {self._yes_no(self.has_gitignore)}\n"
            f"CI config present: {self._yes_no(self.has_ci)}\n"
            f"Clear app/source structure: {self._yes_no(self.has_clear_structure)}\n"
            f"Dependency files: {dependency_files}\n"
            f"TODO/FIXME count: {self.todo_count}\n"
            f"Notable top-level files/folders: {top_level_entries}\n"
            f"Project type: {self.project_type}\n"
            f"Classification reason: {self.classification_reason}\n"
            f"Maturity score: {self.maturity_score}\n"
            f"Maturity band: {self.maturity_band}\n"
            f"Skipped files: {self.skipped_files}"
        )

    def _yes_no(self, value: bool) -> str:
        return "yes" if value else "no"


@dataclass(frozen=True)
class ProjectScanStatus:
    """Startup/debug status for the configured projects directory."""

    projects_dir: str
    exists: bool
    project_count: int
    project_names: tuple[str, ...]


class ProjectScanner:
    """Scan immediate child projects under one configured root directory."""

    def __init__(self, projects_dir: str | Path) -> None:
        self.projects_dir = Path(projects_dir)

    def scan_projects(self) -> list[ProjectSummary]:
        """Return metadata summaries for immediate child project directories."""

        if not self.projects_dir.exists() or not self.projects_dir.is_dir():
            return []

        projects_root = self.projects_dir.resolve()
        summaries: list[ProjectSummary] = []

        for project_path in sorted(projects_root.iterdir()):
            if not project_path.is_dir() or project_path.name in IGNORED_DIRS:
                continue

            try:
                resolved_project_path = self._resolve_project_path(project_path.name)
            except ValueError:
                continue

            summaries.append(self._summarize_project(resolved_project_path))

        return summaries

    def get_status(self) -> ProjectScanStatus:
        """Return visible scanner status without reading source contents."""

        projects_dir = str(self.projects_dir)
        if not self.projects_dir.exists() or not self.projects_dir.is_dir():
            return ProjectScanStatus(
                projects_dir=projects_dir,
                exists=False,
                project_count=0,
                project_names=(),
            )

        projects_root = self.projects_dir.resolve()
        project_names = []
        for project_path in sorted(projects_root.iterdir()):
            if not project_path.is_dir() or project_path.name in IGNORED_DIRS:
                continue
            try:
                self._resolve_project_path(project_path.name)
            except ValueError:
                continue
            project_names.append(project_path.name)

        return ProjectScanStatus(
            projects_dir=projects_dir,
            exists=True,
            project_count=len(project_names),
            project_names=tuple(project_names),
        )

    def _resolve_project_path(self, project_name: str) -> Path:
        projects_root = self.projects_dir.resolve()
        project_path = (projects_root / project_name).resolve()

        if project_path.parent != projects_root:
            raise ValueError("Project path must stay inside the projects directory.")

        return project_path

    def _summarize_project(self, project_path: Path) -> ProjectSummary:
        file_count = 0
        skipped_files = 0
        extensions: set[str] = set()
        extension_counts: Counter[str] = Counter()
        has_readme = False
        has_tests = False
        has_agents = False
        has_license = False
        has_gitignore = False
        has_ci = self._has_ci_config(project_path)
        dependency_files: set[str] = set()
        todo_count = 0
        top_level_entries = self._top_level_entries(project_path)
        has_clear_structure = self._has_clear_structure(top_level_entries)

        for path in self._iter_project_files(project_path):
            if self._should_skip_file(path):
                skipped_files += 1
                continue

            file_count += 1
            if path.suffix:
                extensions.add(path.suffix.lower())
                extension_counts[path.suffix.lower()] += 1

            lower_name = path.name.lower()
            lower_parts = {part.lower() for part in path.parts}
            if lower_name in READ_ME_NAMES:
                has_readme = True
            if "tests" in lower_parts or lower_name.startswith("test_"):
                has_tests = True
            if lower_name == "agents.md":
                has_agents = True
            if lower_name in LICENSE_NAMES:
                has_license = True
            if lower_name == ".gitignore":
                has_gitignore = True
            if lower_name in DEPENDENCY_FILE_NAMES:
                dependency_files.add(path.name)
            todo_count += self._count_todos(path)

        project_type, classification_reason = self._classify_project(
            project_path.name,
            has_readme=has_readme,
            has_tests=has_tests,
            has_clear_structure=has_clear_structure,
            dependency_files=dependency_files,
            extensions=extension_counts,
            top_level_entries=top_level_entries,
        )
        maturity_score = self._calculate_maturity_score(
            has_readme=has_readme,
            has_tests=has_tests,
            has_dependency_files=bool(dependency_files),
            has_license=has_license,
            has_gitignore=has_gitignore,
            has_agents=has_agents,
            has_clear_structure=has_clear_structure,
            todo_count=todo_count,
            has_ci=has_ci,
        )
        maturity_band = self._maturity_band(project_type, maturity_score)

        return ProjectSummary(
            name=project_path.name,
            path=str(project_path),
            relative_path=str(project_path.relative_to(self.projects_dir.resolve())),
            file_count=file_count,
            extensions=tuple(
                extension
                for extension, _ in extension_counts.most_common(8)
            )
            or tuple(sorted(extensions)),
            has_readme=has_readme,
            has_tests=has_tests,
            has_agents=has_agents,
            has_license=has_license,
            has_gitignore=has_gitignore,
            has_ci=has_ci,
            has_clear_structure=has_clear_structure,
            dependency_files=tuple(sorted(dependency_files)),
            todo_count=todo_count,
            top_level_entries=top_level_entries,
            project_type=project_type,
            classification_reason=classification_reason,
            maturity_score=maturity_score,
            maturity_band=maturity_band,
            skipped_files=skipped_files,
        )

    def _top_level_entries(self, project_path: Path) -> tuple[str, ...]:
        entries = []
        for path in sorted(project_path.iterdir()):
            if path.name in IGNORED_DIRS or self._is_secret_name(path.name):
                continue
            entries.append(path.name)
            if len(entries) >= 12:
                break
        return tuple(entries)

    def _iter_project_files(self, project_path: Path):
        for path in project_path.rglob("*"):
            if any(part in IGNORED_DIRS for part in path.parts):
                continue
            if path.is_file():
                yield path

    def _should_skip_file(self, path: Path) -> bool:
        if self._is_secret_name(path.name):
            return True

        try:
            if not path.resolve().is_relative_to(self.projects_dir.resolve()):
                return True
        except OSError:
            return True

        try:
            if path.stat().st_size > MAX_FILE_SIZE_BYTES:
                return True
            return self._looks_binary(path)
        except OSError:
            return True

    def _is_secret_name(self, name: str) -> bool:
        lower_name = name.lower()
        suffix = Path(name).suffix.lower()

        if lower_name in SECRET_FILE_NAMES:
            return True

        if suffix in SECRET_SUFFIXES:
            return True
        if any(part in lower_name for part in SECRET_NAME_PARTS):
            return True
        return False

    def _count_todos(self, path: Path) -> int:
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            return 0
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return 0

        upper_text = text.upper()
        return upper_text.count("TODO") + upper_text.count("FIXME")

    def _has_ci_config(self, project_path: Path) -> bool:
        workflows_dir = project_path / ".github" / "workflows"
        if workflows_dir.is_dir():
            for path in workflows_dir.iterdir():
                if path.is_file() and path.suffix.lower() in {".yml", ".yaml"}:
                    return True

        for path in project_path.iterdir():
            if path.is_file() and path.name.lower() in CI_FILE_NAMES:
                return True

        circle_config = project_path / ".circleci" / "config.yml"
        return circle_config.is_file()

    def _has_clear_structure(self, top_level_entries: tuple[str, ...]) -> bool:
        lower_entries = {entry.lower() for entry in top_level_entries}
        return bool(lower_entries & SOURCE_ENTRY_NAMES) or bool(
            lower_entries & APP_ENTRY_NAMES
        )

    def _classify_project(
        self,
        name: str,
        *,
        has_readme: bool,
        has_tests: bool,
        has_clear_structure: bool,
        dependency_files: set[str],
        extensions: Counter[str],
        top_level_entries: tuple[str, ...],
    ) -> tuple[str, str]:
        lower_name = name.lower()
        lower_entries = {entry.lower() for entry in top_level_entries}
        text = " ".join([lower_name, *lower_entries])

        if self._has_any_hint(
            text,
            {
                "coursera",
                "course",
                "tutorial",
                "lesson",
                "bootcamp",
                "udemy",
                "codecademy",
                "freecodecamp",
                "learning",
                "exercise",
                "assignment",
            },
        ):
            return (
                "learning_course",
                "Project name or top-level structure suggests course or practice "
                "material rather than a deployable product.",
            )

        if self._has_any_hint(
            text,
            {
                "interview",
                "leetcode",
                "hackerrank",
                "codewars",
                "dsa",
                "algorithm",
                "algorithms",
                "prep",
                "coding-challenge",
            },
        ):
            return (
                "interview_prep",
                "Project name or structure suggests interview preparation or "
                "algorithm practice.",
            )

        if self._has_any_hint(text, {"archive", "old", "personal", "scratch"}):
            return (
                "archive_or_personal",
                "Project naming suggests archived, personal, or scratch material.",
            )

        if self._has_any_hint(text, {"docs", "documentation", "mkdocs", "book"}):
            return (
                "documentation_site",
                "Project metadata emphasizes documentation content or docs-oriented "
                "structure.",
            )

        website_hints = {"portfolio", "website", "homepage", "site"}
        if self._has_any_hint(text, website_hints) and self._has_web_extension(
            extensions
        ):
            return (
                "portfolio_website",
                "Project name and web files indicate a personal or portfolio website.",
            )

        if self._has_any_hint(text, {"demo", "prototype", "mvp", "experiment"}):
            return (
                "experiment_mvp",
                "Project naming suggests an experiment, demo, prototype, or MVP.",
            )

        app_hints = {
            "app",
            "application",
            "portal",
            "dashboard",
            "forge",
            "synapse",
        }
        if (
            self._has_any_hint(text, app_hints)
            or ("src" in lower_entries and bool(dependency_files))
            or ("app" in lower_entries and bool(dependency_files))
        ):
            return (
                "product_app",
                "Project metadata indicates an app-like repository with deployable "
                "product structure.",
            )

        if self._has_any_hint(text, {"lib", "library", "package", "tool", "cli"}):
            return (
                "library_or_tool",
                "Project name or folders indicate a reusable library, package, CLI, "
                "or developer tool.",
            )

        if has_clear_structure and (has_readme or has_tests or dependency_files):
            return (
                "experiment_mvp",
                "Project has some app or source structure but not enough naming "
                "metadata to classify as a product.",
            )

        return (
            "unknown",
            "Available metadata is not specific enough to classify the project "
            "confidently.",
        )

    def _has_any_hint(self, text: str, hints: set[str]) -> bool:
        text_tokens = set(re.findall(r"[a-z0-9]+", text))
        for hint in hints:
            hint_tokens = re.findall(r"[a-z0-9]+", hint)
            if hint_tokens and all(token in text_tokens for token in hint_tokens):
                return True
        return False

    def _has_web_extension(self, extensions: Counter[str]) -> bool:
        return any(
            extension in extensions
            for extension in {".html", ".css", ".js", ".ts", ".tsx"}
        )

    def _calculate_maturity_score(
        self,
        *,
        has_readme: bool,
        has_tests: bool,
        has_dependency_files: bool,
        has_license: bool,
        has_gitignore: bool,
        has_agents: bool,
        has_clear_structure: bool,
        todo_count: int,
        has_ci: bool,
    ) -> int:
        score = 0
        if has_readme:
            score += 15
        if has_tests:
            score += 20
        if has_dependency_files:
            score += 10
        if has_license:
            score += 10
        if has_gitignore:
            score += 5
        if has_agents:
            score += 10
        if has_clear_structure:
            score += 10
        if todo_count <= 2:
            score += 10
        if has_ci:
            score += 10
        return min(score, 100)

    def _maturity_band(self, project_type: str, score: int) -> str:
        if project_type == "archive_or_personal":
            return "archive_or_ignore"

        if project_type in {"learning_course", "interview_prep"}:
            return "needs_cleanup" if score >= 50 else "archive_or_ignore"

        if project_type == "experiment_mvp":
            if score >= 70:
                return "promising"
            if score >= 35:
                return "needs_cleanup"
            return "archive_or_ignore"

        if project_type == "unknown":
            if score >= 70:
                return "promising"
            if score >= 40:
                return "needs_cleanup"
            return "archive_or_ignore"

        if score >= 80:
            return "strong"
        if score >= 55:
            return "promising"
        if score >= 30:
            return "needs_cleanup"
        return "archive_or_ignore"

    def _looks_binary(self, path: Path) -> bool:
        try:
            sample = path.read_bytes()[:1024]
        except OSError:
            return True

        return b"\x00" in sample
