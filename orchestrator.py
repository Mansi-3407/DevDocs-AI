"""
DevDocs AI — Main Orchestrator

Entry point:

    result = orchestrator.run(repo_path, base_ref="HEAD~1", config=None)

The orchestrator:
  1. Builds an AgentContext from git data (via app/utils/git_helper).
  2. Runs the five content agents in parallel via ThreadPoolExecutor.
  3. Runs the audit agent sequentially after all content agents finish,
     injecting their results via context.config["prior_results"].
  4. Returns a consolidated result dict including a markdown report string.

Design constraints
------------------
* No LLM calls here — all intelligence lives inside individual agents.
* No audit logic here — that belongs to audit_agent.
* No git logic here — that belongs to git_helper.
* One failing agent never crashes the pipeline; it is recorded as "error".
* If a teammate agent is not yet implemented it returns status="skipped",
  which the orchestrator accepts and passes through without error.
"""

from __future__ import annotations

import types
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.models import AgentContext, AgentResult
from app.utils import git_helper

# ---------------------------------------------------------------------------
# Agent registry — all content agents (audit agent is separate)
# ---------------------------------------------------------------------------
# Import each agent module.  Teammate stubs return status="skipped" until
# their real implementations are merged.

from app.agents import (  # noqa: E402
    readme_agent,
    api_agent,
    example_validator,
    tutorial_agent,
    changelog_agent,
)
from app.agents import audit_agent  # runs last, after content agents

# Ordered list of content agents to run in parallel.
_CONTENT_AGENTS: list[types.ModuleType] = [
    readme_agent,
    api_agent,
    example_validator,
    tutorial_agent,
    changelog_agent,
]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(
    repo_path: str,
    base_ref: str = "HEAD~1",
    config: dict | None = None,
) -> dict:
    """Run the full DevDocs AI documentation pipeline.

    Args:
        repo_path: Path to the repository root to analyse.
        base_ref:  Git ref to diff against (default: one commit back).
        config:    Optional extra configuration forwarded to AgentContext.
                   Recognised keys:
                     "required_sections" — list[str] for audit agent.

    Returns:
        A dict with keys:
          "status"  — overall pipeline status string
          "results" — list[AgentResult] from the five content agents
          "audit"   — AgentResult from the audit agent
          "report"  — formatted markdown report string
    """
    cfg = dict(config) if config else {}

    # Step 1 — build shared context
    context = _build_context(repo_path, base_ref, cfg)

    # Step 2 — run content agents in parallel
    content_results = _run_agents_parallel(context, _CONTENT_AGENTS)

    # Step 3 — run audit agent with prior results injected
    audit_result = _run_audit(context, content_results)

    # Step 4 — compile report
    report = _format_report(content_results, audit_result)

    overall = _overall_status(content_results, audit_result)

    return {
        "status": overall,
        "results": content_results,
        "audit": audit_result,
        "report": report,
    }


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------

def _build_context(repo_path: str, base_ref: str, config: dict) -> AgentContext:
    """Construct the AgentContext from git data."""
    changed_files = git_helper.get_changed_files(repo_path, base_ref)
    git_diff = git_helper.get_diff(repo_path, base_ref)
    return AgentContext(
        repo_path=repo_path,
        changed_files=changed_files,
        git_diff=git_diff,
        config=config,
    )


def _run_single_agent(
    agent_module: types.ModuleType, context: AgentContext
) -> AgentResult:
    """Run an agent module through its supported interface."""
    try:
        module_name = getattr(agent_module, "__name__", str(agent_module))
        agent_name = module_name.split(".")[-1]

        if agent_name == "api_agent":
            target_files = list(Path(context.repo_path).rglob("*.py"))

            if not target_files:
                raise FileNotFoundError(
                    f"No Python files found in repository: {context.repo_path}"
                )

            result = agent_module.APIAgent().run(str(target_files[0]))

        elif agent_name == "example_validator":
            result = agent_module.ExampleValidator().run(context.repo_path)

        else:
            return agent_module.run(context)

        return AgentResult(
            agent_name=agent_name,
            status=result.get("status", "error"),
            summary=f"{agent_name} completed with status {result.get('status', 'error')}.",
            output_files=[],
            issues=result.get("errors", []),
            raw_output=result,
        )

    except Exception as exc:  # noqa: BLE001
        module_name = getattr(agent_module, "__name__", str(agent_module))
        agent_name = module_name.split(".")[-1]
        return AgentResult(
            agent_name=agent_name,
            status="error",
            summary=f"Agent raised an exception: {exc}",
            output_files=[],
            issues=[f"agent exception: {exc}"],
            raw_output={"exception": str(exc)},
        )


def _run_agents_parallel(
    context: AgentContext,
    agent_modules: list[types.ModuleType],
) -> list[AgentResult]:
    """Run multiple agents concurrently, preserving input order in results."""
    results: list[AgentResult | None] = [None] * len(agent_modules)

    with ThreadPoolExecutor(max_workers=len(agent_modules)) as executor:
        future_to_index = {
            executor.submit(_run_single_agent, mod, context): idx
            for idx, mod in enumerate(agent_modules)
        }
        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            results[idx] = future.result()

    # Replace any unexpected None with an error result (should never happen)
    return [
        r if r is not None else AgentResult(
            agent_name="unknown",
            status="error",
            summary="Agent returned no result.",
        )
        for r in results
    ]


def _run_audit(
    context: AgentContext, prior_results: list[AgentResult]
) -> AgentResult:
    """Run the audit agent after all content agents, injecting their results."""
    # Inject prior results — audit agent reads them from config
    audit_context = AgentContext(
        repo_path=context.repo_path,
        changed_files=context.changed_files,
        git_diff=context.git_diff,
        config={**context.config, "prior_results": prior_results},
    )
    return _run_single_agent(audit_agent, audit_context)


def _format_report(
    content_results: list[AgentResult], audit_result: AgentResult
) -> str:
    """Build a markdown-formatted summary report of the full pipeline run."""
    lines: list[str] = [
        "# DevDocs AI -- Pipeline Report",
        "",
        "## Content Agents",
        "",
    ]

    for result in content_results:
        icon = _status_icon(result.status)
        lines.append(f"### {icon} {result.agent_name}")
        lines.append(f"**Status:** {result.status}")
        if result.summary:
            lines.append(f"**Summary:** {result.summary}")
        if result.output_files:
            lines.append("**Output files:**")
            for f in result.output_files:
                lines.append(f"  - {f}")
        if result.issues:
            lines.append("**Issues:**")
            for issue in result.issues:
                lines.append(f"  - {issue}")
        lines.append("")

    lines += [
        "---",
        "",
        "## Documentation Audit",
        "",
        f"**Status:** {audit_result.status}",
    ]
    if audit_result.summary:
        lines.append(f"**Summary:** {audit_result.summary}")
    if audit_result.issues:
        lines.append("")
        lines.append("**Issues found:**")
        for issue in audit_result.issues:
            lines.append(f"  - {issue}")
    else:
        lines.append("")
        lines.append("_No documentation issues detected._")

    lines += ["", "---", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _status_icon(status: str) -> str:
    return {
        "success": "[OK]",
        "warning": "[WARN]",
        "error": "[ERR]",
        "skipped": "[SKIP]",
    }.get(status, "[?]")


def _overall_status(
    content_results: list[AgentResult], audit_result: AgentResult
) -> str:
    all_statuses = [r.status for r in content_results] + [audit_result.status]
    if "error" in all_statuses:
        return "error"
    if "warning" in all_statuses:
        return "warning"
    if all(s == "skipped" for s in all_statuses):
        return "skipped"
    return "success"
