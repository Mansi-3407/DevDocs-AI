# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Project Overview
DevDocs-AI is a Python application that uses AI agents to auto-generate and audit documentation
(README, API docs, changelogs, tutorials, example validation) for software projects.

---

## Commands
<!-- TODO: Fill in once requirements.txt / pyproject.toml / Makefile exist -->

```bash
# Install dependencies (TODO: verify package manager)
pip install -r requirements.txt

# Run all tests
pytest tests/

# Run a single test file
pytest tests/test_api_agent.py

# Run a single test function
pytest tests/test_api_agent.py::test_function_name

# Lint (TODO: confirm linter — ruff, flake8, or pylint)
# ruff check .

# Type-check (TODO: confirm if mypy / pyright is used)
# mypy app/
```

---

## Architecture
```
orchestrator.py          # Top-level orchestrator entry point
app/
  main.py                # Application entry point
  cli.py                 # CLI interface
  agents/                # One module per documentation agent
    api_agent.py
    audit_agent.py
    changelog_agent.py
    example_validator.py
    readme_agent.py
    tutorial_agent.py
  utils/
    git_helper.py        # Git utilities shared by agents
bob/
  main_agent_setup.py    # Bob AI assistant setup for this repo
tests/
  test_<agent>.py        # 1:1 mirror of each agent module
  fixtures/
    sample_fastapi_app/  # Fixture project used by integration tests
docs/
  api/                   # Output directory for generated API docs
  migration/             # Output directory for migration guides
  tutorials/             # Output directory for generated tutorials
```

---

## Code Style
<!-- TODO: Add once linter/formatter config files are added (ruff.toml, .flake8, pyproject.toml) -->

Known conventions from directory structure:
- Each agent in `app/agents/` has a **1:1 test file** in `tests/` (e.g. `api_agent.py` → `test_api_agent.py`)
- `docs/` subdirectories are **output targets** for generated content — do not place hand-written docs there
- `tests/fixtures/sample_fastapi_app/` is the canonical fixture project for integration tests

---

## Environment Variables
<!-- TODO: Document required env vars once .env.example is populated -->
See `.env.example` for required environment variables.

---

## TODOs for future contributors
- [ ] Add `requirements.txt` or `pyproject.toml` with dependencies
- [ ] Add linter/formatter config (ruff, black, mypy, etc.) and document commands above
- [ ] Implement agent modules in `app/agents/`
- [ ] Populate `tests/fixtures/sample_fastapi_app/` with a minimal FastAPI project for integration tests
- [ ] Fill in `.env.example` with required API keys / config
- [ ] Implement `orchestrator.py` and document the agent execution flow
