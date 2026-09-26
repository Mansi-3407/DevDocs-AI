# AGENTS.md — Ask Mode

This file provides guidance to agents answering questions about this repository.

## Non-Obvious Context

- All source files (`app/`, `bob/`, `orchestrator.py`, `tests/`) are currently **empty stubs** — do not assume any implementation exists
- `docs/api/`, `docs/migration/`, `docs/tutorials/` are **output directories** for AI-generated content, not hand-written documentation
- `bob/main_agent_setup.py` is the Bob AI assistant configuration for the repo itself (meta-level), distinct from the app's own agents in `app/agents/`
- No `requirements.txt`, `pyproject.toml`, or any config files exist yet — dependency information is unknown
