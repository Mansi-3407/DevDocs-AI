# Person 4 Implementation Plan — DevDocs AI

## Overview

Person 4 is responsible for:
1. Documentation Audit Agent (`app/agents/audit_agent.py`)
2. IBM Bob 2.0 integration (`bob/` — thin wrapper only)
3. Main orchestration (`orchestrator.py`)
4. Integration of agents from Person 1, 2, and 3
5. End-to-end testing and demo preparation

### Guiding Principles

- **All documentation analysis runs in Python.** Git operations, file analysis, link checking, version checking, and audit logic live in `app/`. Bob never touches these directly.
- **Bob is display-only.** `bob/` contains a single registered tool that calls `orchestrator.run()` and returns the result string. No audit, git, or LLM logic in `bob/`.
- **The LLM layer is stub-first.** `app/utils/llm_client.py` exposes one function. Only a `stub` implementation is written now. Real providers (OpenAI, WatsonX) are added later when a provider is actually chosen and configured.
- **Teammate-owned modules are not implemented.** Person 1, 2, and 3 own their agent files. Person 4 only defines the shared contract and adds interface-only stubs where needed to unblock the orchestrator. No functionality is added to teammate files.
- **The shared contract is defined first.** `app/models.py` is the first file created. Nothing else is implemented until teammates confirm the `AgentContext` / `AgentResult` contract.

### Component Ownership Boundaries

| Component | Owner | Person 4's Role |
|---|---|---|
| `app/models.py` | Person 4 | Define and share the contract |
| `app/utils/llm_client.py` | Person 4 | Stub + dispatch skeleton only |
| `app/utils/git_helper.py` | Person 1 | Add interface stub only if empty |
| `app/agents/audit_agent.py` | Person 4 | Full implementation |
| `app/agents/readme_agent.py` | Person 1 | No changes |
| `app/agents/api_agent.py` | Person 2 | No changes |
| `app/agents/example_validator.py` | Person 2 | No changes |
| `app/agents/tutorial_agent.py` | Person 3 | No changes |
| `app/agents/changelog_agent.py` | Person 3 | No changes |
| `orchestrator.py` | Person 4 | Full implementation |
| `bob/main_agent_setup.py` | Person 4 | Thin wrapper only |
| `tests/test_audit_agent.py` | Person 4 | Full implementation |
| `tests/test_e2e.py` | Person 4 | Full implementation |
| `tests/fixtures/sample_fastapi_app/` | Person 4 | Full demo fixture |

---

## Sub-Task 1 — Shared Agent Contract (`app/models.py`)

**Status:** [ ] pending

### Intent
Define the single shared data contract that all agents and the orchestrator exchange. This must be the first file created and shared with all teammates before any agent code is written. It prevents interface mismatch across all four team members.

### Expected Outcomes
- `app/models.py` exists with `AgentContext` and `AgentResult` dataclasses
- Status is a `Literal` type with four allowed values
- Module-level docstring documents the expected `run()` signature every agent must implement
- `app/__init__.py` exports the models
- Contract is shared with teammates before any agent implementation begins

### Todo List
1. Create `app/models.py` with:
   - `AgentContext` dataclass: `repo_path: str`, `changed_files: list[str]`, `git_diff: str`, `config: dict`
   - `AgentResult` dataclass: `agent_name: str`, `status: str`, `summary: str`, `output_files: list[str]`, `issues: list[str]`, `raw_output: dict`
   - `AgentStatus = Literal["success", "warning", "error", "skipped"]` type alias
   - Module docstring specifying the required agent function signature: `def run(context: AgentContext) -> AgentResult`
2. Add field-level docstrings explaining each field's purpose and expected content
3. Update `app/__init__.py` to re-export `AgentContext` and `AgentResult`

### Relevant Context
- All six `app/agents/` modules must eventually import from here
- `orchestrator.py` constructs `AgentContext` and consumes `list[AgentResult]`

---

## Sub-Task 2 — LLM Abstraction Layer (`app/utils/llm_client.py`)

**Status:** [ ] pending

### Intent
Create a provider-agnostic LLM utility that exposes a single `complete()` function. Only the `stub` provider is implemented now. Real provider implementations (OpenAI, WatsonX) are left as clearly marked `NotImplementedError` placeholders and will be filled in when a provider is chosen. This lets all tests and local development work without any API key.

### Expected Outcomes
- `app/utils/llm_client.py` exposes `complete(prompt: str, system: str = "") -> str`
- `LLM_PROVIDER=stub` returns deterministic canned text — no network calls, no API keys
- `LLM_PROVIDER=openai` and `LLM_PROVIDER=watsonx` raise `NotImplementedError` with a clear message indicating they are not yet implemented
- No provider SDK is imported at the top level — imports happen inside provider branches only
- `requirements.txt` lists only `gitpython>=3.1` and `pytest>=8.0` as immediate deps; provider SDKs are commented out

### Todo List
1. Create `app/utils/llm_client.py`:
   - Read `LLM_PROVIDER` from env (default: `"stub"`)
   - `stub` branch: return a fixed string like `"[stub] LLM output for: {prompt[:80]}"`
   - `openai` branch: `raise NotImplementedError("OpenAI provider not yet implemented")`
   - `watsonx` branch: `raise NotImplementedError("WatsonX provider not yet implemented")`
   - Default branch: `raise ValueError(f"Unknown LLM_PROVIDER: {provider}")`
2. Create `.env.example` documenting all future env vars with comments:
   - `LLM_PROVIDER=stub  # stub | openai | watsonx`
   - `OPENAI_API_KEY=`  (commented, not yet active)
   - `WATSONX_API_KEY=`, `WATSONX_PROJECT_ID=`, `WATSONX_MODEL_ID=`, `WATSONX_URL=`  (commented)
3. Create `requirements.txt`:
   - `gitpython>=3.1`
   - `pytest>=8.0`
   - Comment block for future provider deps: `# openai>=1.0`, `# ibm-watsonx-ai`

### Relevant Context
- `app/agents/audit_agent.py` (Sub-Task 4) — only consumer for now
- `.env.example` — sets expectations for all teammates

---

## Sub-Task 3 — Teammate Interface Stubs

**Status:** [ ] pending

### Intent
The orchestrator imports from `app/utils/git_helper.py` and will eventually import from all six agent modules. If any of these files are still empty when the orchestrator is written, the project cannot be imported or tested. This sub-task adds the minimum interface signatures — function signatures, type hints, and `TODO` comments — to teammate-owned files **only if they are still empty**. No logic is added, and no teammate functionality is implemented.

### Expected Outcomes
- `app/utils/git_helper.py` has at minimum two function stubs with correct signatures and `# TODO: implement (Person 1)` comments — only if Person 1 has not yet written anything
- Each of the five teammate agent files has a stub `run(context: AgentContext) -> AgentResult` function — only if the file is still empty
- Stubs return a minimal `AgentResult` with `status="skipped"` and `agent_name` set
- Orchestrator can import all modules without `ImportError` or `SyntaxError`

### Todo List
1. Check `app/utils/git_helper.py` — if empty, add:
   - `get_changed_files(repo_path: str, base_ref: str = "HEAD~1") -> list[str]`  with `# TODO: implement (Person 1)` and `return []`
   - `get_diff(repo_path: str, base_ref: str = "HEAD~1") -> str` with `# TODO: implement (Person 1)` and `return ""`
2. Check each of the five teammate agent files; for each that is still empty, add only:
   ```python
   from app.models import AgentContext, AgentResult
   # TODO: implement (Person X)
   def run(context: AgentContext) -> AgentResult:
       return AgentResult(agent_name="<name>", status="skipped", summary="Not yet implemented", output_files=[], issues=[], raw_output={})
   ```
3. Do **not** modify any teammate file that already has content
4. Leave a comment at the top of each stub file: `# Interface stub added by Person 4 — do not implement logic here`

### Relevant Context
- `app/utils/git_helper.py` — Person 1's module
- `app/agents/readme_agent.py` — Person 1
- `app/agents/api_agent.py`, `app/agents/example_validator.py` — Person 2
- `app/agents/tutorial_agent.py`, `app/agents/changelog_agent.py` — Person 3

---

## Sub-Task 4 — Documentation Audit Agent (`app/agents/audit_agent.py`)

**Status:** [ ] pending

### Intent
Implement Person 4's primary feature: the Documentation Audit Agent. All audit logic runs in Python. The agent reads documentation files and the results from prior agents, then produces a structured list of issues and a plain-text summary. The LLM is used only for generating the human-readable summary; all detection logic is pure Python.

### Expected Outcomes
- `app/agents/audit_agent.py` implements `run(context: AgentContext) -> AgentResult`
- Three deterministic checks work with `LLM_PROVIDER=stub` (no API key needed):
  - Broken local markdown links
  - Version string inconsistencies across files
  - Missing required documentation sections
- LLM is called only for the final narrative summary (skipped gracefully if stub)
- `AgentResult.issues` contains structured strings for each detected problem
- `AgentResult.raw_output` contains the structured issue list for downstream consumers

### Todo List
1. Implement `run(context: AgentContext) -> AgentResult` in `app/agents/audit_agent.py`
2. Implement `_check_broken_links(repo_path: str, doc_files: list[str]) -> list[str]`:
   - Find all `[text](./relative/path)` patterns in each doc file
   - Check each local path against the filesystem
   - Return list of `"broken link: <path> in <file>"` strings
3. Implement `_check_version_consistency(repo_path: str) -> list[str]`:
   - Extract version strings (e.g. `v1.0.0`, `version = "1.0.0"`) from README, CHANGELOG, and any `__version__` in Python files
   - Return list of `"version mismatch: <v1> in <file1> vs <v2> in <file2>"` strings
4. Implement `_check_missing_sections(doc_content: str, required: list[str]) -> list[str]`:
   - Check for expected markdown headings (e.g. `## Installation`, `## Usage`)
   - Return list of `"missing section: <heading> in <file>"` strings
5. Implement `_llm_audit_summary(issues: list[str]) -> str`:
   - Call `llm_client.complete()` with the issue list
   - If `LLM_PROVIDER=stub`, a canned summary string is acceptable
6. Wire all into `run()`: collect all issues, call summary, return `AgentResult`

### Relevant Context
- `app/models.py` (Sub-Task 1) — `AgentContext`, `AgentResult`
- `app/utils/llm_client.py` (Sub-Task 2) — summary generation
- `tests/test_audit_agent.py` (Sub-Task 7) — unit tests for this module

---

## Sub-Task 5 — Main Orchestrator (`orchestrator.py`)

**Status:** [ ] pending

### Intent
Implement `orchestrator.py` as the central pipeline coordinator. It builds an `AgentContext` from git data, runs the five content agents in parallel, then runs the audit agent sequentially on their combined results, and returns a consolidated report dict. The orchestrator contains no LLM calls, no audit logic, and no git logic — it only coordinates.

### Expected Outcomes
- `orchestrator.py` exposes `run(repo_path: str, base_ref: str = "HEAD~1", config: dict | None = None) -> dict`
- Five content agents run in parallel via `concurrent.futures.ThreadPoolExecutor`
- Audit agent runs after all content agents complete, receiving their results via `context.config["prior_results"]`
- Any individual agent exception is caught and recorded as `status="error"` — pipeline always completes
- Return dict shape: `{"status": str, "results": list[AgentResult], "audit": AgentResult, "report": str}`
- The `report` value is a formatted markdown string summarizing all results

### Todo List
1. Implement `build_context(repo_path, base_ref, config) -> AgentContext`:
   - Call `git_helper.get_changed_files()` and `git_helper.get_diff()`
   - Construct and return `AgentContext`
2. Implement `_run_single_agent(agent_module, context) -> AgentResult`:
   - Wraps `agent_module.run(context)` in a try/except
   - On exception: returns `AgentResult(status="error", summary=str(e), ...)`
3. Implement `run_agents_parallel(context, agent_modules) -> list[AgentResult]`:
   - Uses `ThreadPoolExecutor` to call `_run_single_agent` for each agent
4. Implement `run_audit(context, prior_results) -> AgentResult`:
   - Injects `prior_results` into `context.config["prior_results"]`
   - Calls `audit_agent.run(context)`
5. Implement `format_report(results, audit_result) -> str`:
   - Produces a markdown string with a section per agent and an audit summary at the end
6. Implement the public `run()` entry point wiring all of the above together
7. Define the agent registry as an explicit list of imported modules (not dynamic discovery)

### Relevant Context
- `app/models.py` — `AgentContext`, `AgentResult`
- `app/utils/git_helper.py` — interface stubs from Sub-Task 3
- `app/agents/` — all six modules imported by name
- `concurrent.futures` — standard library, no additional dependency

---

## Sub-Task 6 — IBM Bob 2.0 Integration (`bob/`)

**Status:** [ ] pending

### Intent
Register `orchestrator.run()` as a single Bob tool. `bob/` contains no audit logic, no LLM calls, and no git operations. Its only job is to accept parameters from Bob, call the Python orchestrator, and return the report string. Keep `bob/` flat — no `agents/` or `prompts/` subdirectories.

### Expected Outcomes
- `bob/main_agent_setup.py` defines and registers exactly one tool: `run_devdocs_pipeline`
- The tool function calls `orchestrator.run()` and returns the `report` string from the result dict
- `bob/__init__.py` is updated to expose the setup function
- No business logic in `bob/` — all processing happens inside `orchestrator.run()`

### Todo List
1. Implement `bob/main_agent_setup.py`:
   - Import `orchestrator` from the project root
   - Define `run_devdocs_pipeline(repo_path: str, base_ref: str = "HEAD~1") -> str`
   - Function body: call `orchestrator.run(repo_path, base_ref)` and return `result["report"]`
   - Register the function as a Bob tool using the Bob 2.0 tool registration API
   - Write a clear docstring Bob will use as the tool description
2. Update `bob/__init__.py` to expose `run_devdocs_pipeline`
3. Add a usage example in `AGENTS.md` showing how to invoke the tool from Bob

### Relevant Context
- `orchestrator.py` (Sub-Task 5) — the only thing `bob/` calls
- Bob 2.0 tool registration API — check `bob/` for any existing registration patterns

---

## Sub-Task 7 — Unit Tests for Audit Agent

**Status:** [ ] pending

### Intent
Write unit tests for the audit agent's four internal functions and its `run()` entry point. All tests must pass with `LLM_PROVIDER=stub` — no network calls, no API keys. Tests use `pytest`'s `tmp_path` fixture to create isolated file system state.

### Expected Outcomes
- `tests/test_audit_agent.py` has at least five test functions
- `tests/conftest.py` sets `LLM_PROVIDER=stub` for all tests via a session-scoped fixture
- `pytest tests/test_audit_agent.py` passes with no API key configured

### Todo List
1. Create `tests/conftest.py` with a session-scoped autouse fixture that sets `os.environ["LLM_PROVIDER"] = "stub"`
2. Write `test_check_broken_links_detects_missing_file(tmp_path)`:
   - Create a markdown file with a link to a non-existent file
   - Assert the issue string is in the return value
3. Write `test_check_broken_links_passes_valid_links(tmp_path)`:
   - Create a markdown file with a link to an existing file
   - Assert return value is empty
4. Write `test_check_version_consistency_finds_mismatch(tmp_path)`:
   - Create a README with `v1.0.0` and a CHANGELOG with `v2.0.0`
   - Assert a mismatch issue is returned
5. Write `test_check_missing_sections_reports_absent_headings(tmp_path)`:
   - Create a markdown file without an `## Installation` section
   - Assert the missing section issue is returned
6. Write `test_run_returns_agent_result(tmp_path)`:
   - Create a minimal repo-like directory with a README
   - Call `audit_agent.run(context)` and assert result is an `AgentResult` with correct `agent_name`

### Relevant Context
- `app/agents/audit_agent.py` (Sub-Task 4) — module under test
- `app/models.py` (Sub-Task 1) — `AgentContext` for constructing test inputs

---

## Sub-Task 8 — Demo Fixture and E2E Test

**Status:** [ ] pending

### Intent
Build the hackathon demo scenario. The fixture project has a v1 and a v2 state representing a realistic code change. The demo script runs the full pipeline and shows how documentation gaps are detected. The E2E test automates the same scenario for repeatable validation.

### Expected Outcomes
- `tests/fixtures/sample_fastapi_app/` is a complete v1 FastAPI project with intentional documentation gaps in v2
- `demo.py` runs the full orchestrator pipeline against the fixture and prints a formatted report
- `tests/test_e2e.py` automates the demo scenario and asserts audit issues are detected
- Both demo and test work with `LLM_PROVIDER=stub`

### Todo List
1. Create `tests/fixtures/sample_fastapi_app/` v1 state:
   - `main.py` — minimal FastAPI app with `GET /items` and `POST /items`
   - `README.md` — documents only v1 endpoints
   - `CHANGELOG.md` — single `v1.0.0` entry
   - `requirements.txt` — `fastapi`, `uvicorn`
2. Create `tests/fixtures/sample_fastapi_app_v2/` simulating a code change with intentional gaps:
   - `main.py` — adds `DELETE /items/{id}` endpoint
   - `README.md` — unchanged from v1 (intentional gap: new endpoint not documented)
   - `CHANGELOG.md` — no new entry (intentional gap)
3. Create `demo.py` at project root:
   - Print a banner describing the demo scenario
   - Call `orchestrator.run()` pointing at the v2 fixture directory
   - Print the formatted report
   - Falls back gracefully if `LLM_PROVIDER` is not set (defaults to `stub`)
4. Create `tests/test_e2e.py`:
   - `test_full_pipeline_detects_documentation_gaps(tmp_path)` — copies v2 fixture to `tmp_path`, runs orchestrator, asserts `audit_result.issues` is non-empty

### Relevant Context
- `orchestrator.py` (Sub-Task 5) — entry point for demo and E2E
- `app/agents/audit_agent.py` (Sub-Task 4) — must detect the intentional gaps

---

## Sub-Task 9 — Integration of Person 1/2/3 Agents

**Status:** [ ] pending

### Intent
Once teammates push their implementations, verify each agent conforms to `run(context: AgentContext) -> AgentResult`, register them in the orchestrator, and confirm the full pipeline works. If a teammate's signature differs, an adapter wrapper is added inside `orchestrator.py` — no teammate file is modified.

### Expected Outcomes
- All six agents registered in orchestrator's parallel pool (audit agent excluded)
- Interface mismatches resolved via adapter in `orchestrator.py`, not by editing teammate files
- `pytest tests/` passes with all agents integrated

### Todo List
1. Once each teammate pushes code, read their agent file
2. Verify the `run()` signature matches `run(context: AgentContext) -> AgentResult`
3. If signature differs, add a local adapter function in `orchestrator.py` (not in the agent file)
4. Run `pytest tests/` and resolve any import errors
5. Update `AGENTS.md` with any non-obvious coupling discovered during integration

### Relevant Context
- `app/agents/readme_agent.py` (Person 1)
- `app/agents/api_agent.py`, `app/agents/example_validator.py` (Person 2)
- `app/agents/tutorial_agent.py`, `app/agents/changelog_agent.py` (Person 3)

---

## Dependency / Execution Order

```
Sub-Task 1 — models           (no dependencies)
    │
    ├── Sub-Task 2 — llm_client + requirements.txt + .env.example
    │
    ├── Sub-Task 3 — teammate interface stubs
    │       (can run in parallel with Sub-Task 2)
    │
    └── Sub-Task 4 — audit_agent
            (depends on Sub-Task 1 + 2)
                │
                └── Sub-Task 5 — orchestrator
                        (depends on Sub-Task 1 + 3 + 4)
                                │
                                ├── Sub-Task 6 — Bob integration
                                ├── Sub-Task 7 — audit unit tests
                                └── Sub-Task 8 — demo + E2E
                                        │
                                        └── Sub-Task 9 — P1/2/3 integration
                                                (last, waits for teammates)
```

---

## Key Integration Risks

| Risk | Mitigation |
|---|---|
| P1/2/3 implement incompatible `run()` signatures | Define Sub-Task 1 first; share `app/models.py` with all teammates immediately |
| git_helper not ready when orchestrator is written | Sub-Task 3 adds typed stubs that return empty values — orchestrator compiles and runs |
| LLM provider unavailable in CI / local dev | `LLM_PROVIDER=stub` is the default; no test or demo requires a real API key |
| Bob integration API is unknown | `bob/` only calls `orchestrator.run()` — even if Bob's registration API changes, the impact is confined to one file |
| P1/2/3 code appears and conflicts with stubs | Sub-Task 3 stubs carry a comment marking them as removable; teammates' real code takes precedence |
| E2E test is slow or flaky | E2E test uses `tmp_path` and `stub` LLM — fully deterministic, no network, no git required |
