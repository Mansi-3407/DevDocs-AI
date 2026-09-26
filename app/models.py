"""
Shared data contract for all DevDocs AI agents.

Every agent module in app/agents/ must expose exactly one public function
with the following signature:

    def run(context: AgentContext) -> AgentResult: ...

AgentContext carries all inputs the agent needs (repo location, git data,
per-run config).  AgentResult carries everything the orchestrator and the
audit agent need to understand what the agent did and found.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# ---------------------------------------------------------------------------
# Status type
# ---------------------------------------------------------------------------

AgentStatus = Literal["success", "warning", "error", "skipped"]


# ---------------------------------------------------------------------------
# Input contract
# ---------------------------------------------------------------------------

@dataclass
class AgentContext:
    """All information an agent needs to perform its work.

    Attributes:
        repo_path:     Absolute or relative path to the root of the repository
                       being analysed.
        changed_files: List of file paths (relative to repo_path) that have
                       changed since base_ref.  Empty list means "analyse the
                       whole repo".
        git_diff:      Raw unified-diff string produced by git.  Empty string
                       when git data is unavailable (e.g. stub mode).
        config:        Arbitrary per-run configuration dict.  Well-known keys:
                         "prior_results" – list[AgentResult] injected by the
                           orchestrator before the audit agent runs.
                         "required_sections" – list[str] of markdown headings
                           the audit agent checks for.
                       Agents must treat unknown keys as optional / ignored.
    """

    repo_path: str
    changed_files: list[str] = field(default_factory=list)
    git_diff: str = ""
    config: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------

@dataclass
class AgentResult:
    """Structured result returned by every agent.

    Attributes:
        agent_name:   Machine-readable name of the agent (e.g. "audit_agent").
        status:       One of "success", "warning", "error", "skipped".
        summary:      Single human-readable sentence describing the outcome.
        output_files: Paths of files written or updated by the agent.
        issues:       Structured issue strings, one per problem found.
                      Format convention: "<category>: <detail> in <location>"
                      Example: "broken link: ./missing.md in README.md"
        raw_output:   Agent-specific structured data for downstream consumers
                      (e.g. the audit agent reads prior agents' raw_output).
    """

    agent_name: str
    status: AgentStatus = "success"
    summary: str = ""
    output_files: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    raw_output: dict = field(default_factory=dict)
