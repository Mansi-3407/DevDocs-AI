# AGENTS.md — Plan Mode

This file provides guidance to agents planning or designing features in this repository.

## Non-Obvious Architectural Context

- The `orchestrator.py` at the root is the intended top-level coordinator — all agent invocations should route through it, not through `app/main.py` directly
- Agent modules in `app/agents/` are designed as one-agent-per-doc-type; keep that 1:1 mapping when adding new documentation types
- `app/utils/git_helper.py` is the only shared utility layer; plan additional shared logic there rather than in individual agents
- `docs/` subdirectories are write-only output targets for generated artifacts — no architecture should treat them as a source of truth
- The fixture project at `tests/fixtures/sample_fastapi_app/` implies integration testing against a real project structure is the intended test strategy (not just unit mocks)

## Open Architectural Questions (TODO)
- How agents are composed and sequenced in `orchestrator.py` (not yet implemented)
- Whether agents run synchronously, async, or in parallel
- How env/config is injected into agents (`.env.example` is empty)
