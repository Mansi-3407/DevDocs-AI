# AGENTS.md — Agent (Coding) Mode

This file provides guidance to agents when writing or modifying code in this repository.

## Non-Obvious Coding Rules

- Each agent module in `app/agents/` **must** have a corresponding test file in `tests/test_<agent_name>.py` — create both together
- `app/utils/git_helper.py` is the shared utility for all git operations; do not inline git calls inside agent modules
- `bob/main_agent_setup.py` configures the Bob AI assistant for this repo — update it when adding new agents or tools
- `tests/fixtures/sample_fastapi_app/` is currently empty (`.gitkeep` only); populate it when writing integration tests for any agent that processes a real project

## TODOs Before Implementing
- [ ] Confirm dependency management (`requirements.txt` vs `pyproject.toml`) before adding imports
- [ ] Confirm test runner options (pytest markers, async support) before writing tests
- [ ] Confirm env var names from `.env.example` before referencing `os.environ` in agents
