# local-llm-agent

Privacy-first local LLM agent that runs on your machine using
[Ollama](https://ollama.com/). The first MVP is a simple CLI: ask a question,
send it to a local Ollama model, and print the answer without sending your
prompt to a cloud API.

The MVP can also include plain text or Markdown files from `data/documents/` as
local context and scan local coding projects as metadata-only summaries.

## Requirements

- Python 3.11+
- Ollama installed and running locally
- The default Ollama model pulled locally: `llama3.2:3b`

## Setup

Clone the repo, then create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python --version
```

Make sure the Python version is 3.11 or newer. Then install dependencies and
the local package:

```bash
pip install -r requirements.txt
pip install -e .
```

Create the local environment file:

```bash
cp .env.example .env
```

Make sure `OLLAMA_MODEL` in `.env` matches the exact model name shown by
`ollama list`.

## Ollama

Install Ollama from:

```text
https://ollama.com/download
```

Start Ollama with Homebrew services:

```bash
brew services start ollama
```

Pull the default model:

```bash
ollama pull llama3.2:3b
```

Confirm the installed model name:

```bash
ollama list
```

By default, the app connects to:

```text
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
DOCUMENTS_DIR=data/documents
PROJECTS_DIR=data/projects
```

## Local Coding Projects

By default, project scanning uses the safe repo-local directory
`data/projects`. To scan your real Mac coding workspace, create or update
`.env`:

```bash
cp .env.example .env
```

Set:

```text
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
PROJECTS_DIR=/Users/lucianirimie/Coding
```

If `ollama list` shows a different local model tag, set `OLLAMA_MODEL` to that
exact value.

Then run the CLI and ask:

```bash
local-llm-agent "Analyse my coding projects and find repeated patterns."
local-llm-agent "Which repositories look most portfolio-ready?"
local-llm-agent "Which projects need better tests or documentation?"
local-llm-agent "What should I standardise across my repos?"
```

The scanner treats each immediate child folder of `PROJECTS_DIR` as one
project. It ignores noisy folders such as `.git`, `.github`, `node_modules`, `.venv`,
`venv`, `__pycache__`, `dist`, `build`, `.next`, and `coverage`. It also skips
secret-looking files, binary files, and very large files.

By default, only project metadata and short summaries are sent to the local LLM,
not full source code.

### v0.4: project classification and maturity scoring

The project scanner now classifies each local repository before asking the
local model to judge portfolio readiness. By default, it still scans metadata
only: project names, top-level files and folders, language extensions,
dependency files, README/test/license/gitignore/AGENTS.md/CI presence, and
TODO/FIXME counts.

For each repository, the tool adds:

- a project type such as `product_app`, `portfolio_website`,
  `learning_course`, `interview_prep`, `documentation_site`,
  `library_or_tool`, `experiment_mvp`, `archive_or_personal`, or `unknown`
- a short classification reason
- a deterministic 0-100 maturity score
- a maturity band: `strong`, `promising`, `needs_cleanup`, or
  `archive_or_ignore`

The report prompt separates genuine portfolio/product candidates from learning,
interview-prep, archive, and personal folders so course work is not treated the
same as a product repo just because it has files. All analysis remains local:
there is no cloud API, GitHub API, command execution, vector database, or full
source-code reading by default.

## Local Documents

Create the local documents directory:

```bash
mkdir -p data/documents
```

Add a plain text or Markdown file:

```bash
cat > data/documents/project-notes.md <<'EOF'
# Project Notes

local-llm-agent is a privacy-first local LLM agent.
It uses Ollama on the user's machine.
EOF
```

Ask a question that can use the document context:

```bash
local-llm-agent "What does this project use?"
local-llm-agent "Summarize my project notes."
```

Supported files are `.txt` and `.md`. Unsupported files are ignored.

This is basic context injection: the app reads supported files from
`DOCUMENTS_DIR` and includes their contents in the prompt. It is not vector
search, embeddings, or full RAG yet.

## Run the CLI

Ask a question directly:

```bash
python -m local_llm_agent.cli "What is a local LLM?"
```

You can also use the installed console command:

```bash
local-llm-agent "What is a local LLM?"
```

Or start interactive mode:

```bash
local-llm-agent
```

Then type a question and press Enter. Use `exit`, `quit`, or `Ctrl+C` to leave.

## Run Tests

```bash
python -m pytest
```

The tests mock the Ollama client and do not require Ollama to be running.

## Troubleshooting

If the model gives a generic answer like "I cannot access your repositories",
check the project scanner startup summary printed by the CLI. It shows the
configured `PROJECTS_DIR`, whether that directory exists, how many immediate
child project folders were found, and their names.

On this machine, the correct example path is:

```text
PROJECTS_DIR=/Users/lucianirimie/Coding
```

Use uppercase `Coding`, not lowercase `coding`.

If no projects are found, update `.env`, then restart the CLI:

```bash
cp .env.example .env
```

Make sure `.env` contains the correct `PROJECTS_DIR`. The scanner only treats
immediate child folders under that directory as projects.

## MVP Scope

The current MVP is intentionally simple:

```text
CLI -> LocalAgent -> local tools -> OllamaClient -> local Ollama /api/chat
```

It supports asking one question from the CLI or using a minimal interactive
loop. If supported files exist in `DOCUMENTS_DIR`, they are added as local
context. If projects exist in `PROJECTS_DIR`, metadata-only summaries are added
as local context. Configuration comes from environment variables, with sensible
defaults for local Ollama, local documents, and repo-local project scanning.

## AGENTS.md

[AGENTS.md](AGENTS.md) documents contributor and agent instructions for this
repo. It captures the privacy-first rules, dependency expectations, testing
standards, and roadmap guardrails that future changes should follow.

## Not Included Yet

This repo intentionally does not include RAG, embeddings, LangGraph, FastAPI,
Streamlit, Docker, ChromaDB, hosted model providers, telemetry, analytics, or
remote logging. Those should only be added in later iterations when explicitly
scoped.

## Roadmap

- Add richer CLI options and conversation history
- Improve local document controls and context limits
- Add retrieval over local documents when explicitly scoped
- Add tool execution with safe approvals
- Add a desktop or web UI
- Add packaging and release automation
