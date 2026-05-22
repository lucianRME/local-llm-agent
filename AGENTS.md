# AGENTS.md

## Project Purpose

`local-llm-agent` is a privacy-first local LLM agent for running simple agent
workflows on the user's machine with Ollama. The current MVP is intentionally
small: a command-line interface sends a user question to `LocalAgent`, which can
optionally include local `.txt` and `.md` documents plus metadata-only coding
project summaries as context before calling the local Ollama chat API and
printing the response.

The project should remain local-first. User prompts, local documents, logs, and
configuration should stay on the user's machine unless a future contributor is
explicitly asked to add a remote integration.

## Current MVP Scope

The current architecture is:

```text
CLI -> LocalAgent -> local tools -> OllamaClient -> local Ollama /api/chat
```

In scope for this stage:

- Loading Ollama settings from environment variables
- Calling a local Ollama model
- Reading `.txt` and `.md` documents from the configured documents directory
- Scanning immediate child project folders as metadata-only summaries
- Clear CLI output and error messages
- Focused unit tests that do not require Ollama to be running

Out of scope for this stage:

- RAG
- LangGraph
- FastAPI
- Streamlit
- Docker
- ChromaDB or other vector databases
- Embeddings or vector search
- Remote model providers

## Coding Standards

- Use Python 3.11+.
- Prefer small, testable modules with clear responsibilities.
- Keep functions and classes simple until real complexity requires abstraction.
- Use explicit imports from `local_llm_agent`.
- Keep command-line behavior predictable: answers go to stdout, errors go to
  stderr, and failures return non-zero exit codes.
- Avoid broad rewrites when a focused change will solve the problem.

## Testing Expectations

- Add or update tests for every behavior change.
- Tests must run with:

```bash
python -m pytest
```

- Tests must not require Ollama to be installed, running, or connected.
- Mock network calls and the Ollama client where needed.
- Cover default configuration, environment overrides, agent behavior, local
  file and project scanning, client request payloads, error handling, and CLI
  smoke behavior.

## Privacy-First Rules

- Do not send user data to cloud APIs.
- Do not add external API calls unless explicitly requested.
- Do not introduce hidden telemetry, analytics, remote logging, crash reporting,
  or usage tracking.
- Local files must never be uploaded externally.
- Only read local documents from the configured documents directory.
- Only scan local projects from the configured projects directory.
- Send project metadata summaries to the LLM by default, not full source code.
- Never commit secrets, `.env` files, local documents, transcripts, prompts, or
  user data.
- Treat local files and prompts as private by default.

## Dependency Rules

- Keep dependencies minimal.
- Do not add frameworks or infrastructure before the MVP needs them.
- Prefer the Python standard library when it is sufficient.
- Before adding a dependency, justify why the current code cannot stay simple
  without it.

## What Contributors Should Avoid

- Do not add RAG, embeddings, vector search, web servers, desktop UIs, or
  orchestration frameworks in this MVP.
- Do not route prompts to hosted model APIs.
- Do not add background services, schedulers, daemons, or network listeners
  without explicit scope approval.
- Do not silently collect, persist, or upload user prompts or responses.
- Do not commit generated caches, virtual environments, or local runtime files.

## Roadmap Guardrails

Future iterations may add conversation history, local file workflows, retrieval,
tool execution, or a UI. Each addition should preserve the privacy-first model,
be opt-in, and include tests. When adding capabilities that touch local files or
external processes, prefer explicit user approval and narrow permissions over
automatic behavior.
