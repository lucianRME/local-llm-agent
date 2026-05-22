"""Command-line interface for the local LLM agent."""

from __future__ import annotations

import argparse
import sys

from local_llm_agent.agent import LocalAgent
from local_llm_agent.ollama_client import (
    OllamaConnectionError,
    OllamaError,
    OllamaModelNotFoundError,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Ask a local Ollama model a question.",
    )
    parser.add_argument(
        "question",
        nargs="*",
        help="Question to ask. If omitted, interactive mode starts.",
    )
    return parser


def print_error(error: Exception) -> None:
    """Print user-friendly CLI errors."""

    if isinstance(error, OllamaConnectionError):
        print(f"Error: {error}", file=sys.stderr)
        return

    if isinstance(error, OllamaModelNotFoundError):
        print(f"Error: {error}", file=sys.stderr)
        return

    if isinstance(error, OllamaError):
        print(f"Error: {error}", file=sys.stderr)
        return

    print(f"Error: {error}", file=sys.stderr)


def run_once(agent: LocalAgent, question: str) -> int:
    """Ask one question and print the answer."""

    try:
        answer = agent.ask(expand_question_shortcut(question))
    except (ValueError, OllamaError) as exc:
        print_error(exc)
        return 1

    print(answer)
    return 0


def expand_question_shortcut(question: str) -> str:
    """Expand common shorthand questions into more useful analysis requests."""

    if question.strip().lower() == "analyze my local repos":
        return (
            "Analyse the scanned local repository metadata and produce a "
            "portfolio-readiness report with repeated patterns, common gaps, "
            "and next actions."
        )

    return question


def run_interactive(agent: LocalAgent) -> int:
    """Start an interactive question-answer loop."""

    print("local-llm-agent", flush=True)
    print_startup_summary(agent)
    print("Type a question, or use 'exit' or 'quit' to leave.", flush=True)

    while True:
        try:
            question = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if question.lower() in {"exit", "quit"}:
            return 0

        if not question:
            continue

        run_once(agent, question)


def main() -> int:
    """CLI entry point."""

    args = build_parser().parse_args()
    agent = LocalAgent()
    if args.question:
        print_startup_summary(agent)
        return run_once(agent, " ".join(args.question))

    return run_interactive(agent)


def print_startup_summary(agent: LocalAgent) -> None:
    """Print resolved runtime settings for debugging configuration."""

    get_status = getattr(agent, "get_project_scan_status", None)
    if get_status is None:
        return

    status = get_status()
    settings = getattr(agent, "settings", None)
    ollama_base_url = getattr(settings, "ollama_base_url", "unknown")
    ollama_model = getattr(settings, "ollama_model", "unknown")
    names = ", ".join(status.project_names) if status.project_names else "none"
    print(
        "Startup config: "
        f"OLLAMA_BASE_URL={ollama_base_url}; "
        f"OLLAMA_MODEL={ollama_model}; "
        f"PROJECTS_DIR={status.projects_dir}; "
        f"PROJECTS_DIR_EXISTS={status.exists}; "
        f"projects={status.project_count}; "
        f"names={names}",
        file=sys.stderr,
        flush=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
