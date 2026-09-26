"""
Documentation Audit Agent — Person 4's primary deliverable.

Checks the repository documentation for:
  * Broken local markdown links
  * Version string inconsistencies across files
  * Missing required documentation sections

All three checks are pure Python (no LLM, no network).
The LLM is used only to generate the final human-readable summary via
app/utils/llm_client.complete(); it falls back gracefully when
LLM_PROVIDER=stub.

Public interface (matches the required agent contract):

    def run(context: AgentContext) -> AgentResult
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from app.models import AgentContext, AgentResult
from app.utils import llm_client

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AGENT_NAME = "audit_agent"

# Headings that every well-formed project README should contain.
DEFAULT_REQUIRED_SECTIONS = [
    "## Installation",
    "## Usage",
]

# Regex: match markdown inline links  [label](target)
_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")

# Regex: version strings such as v1.2.3 or 1.2.3
_VERSION_RE = re.compile(r"\bv?(\d+\.\d+\.\d+)\b")

# Python __version__ assignment: __version__ = "1.2.3"
_PY_VERSION_RE = re.compile(r'__version__\s*=\s*["\']([^"\']+)["\']')


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(context: AgentContext) -> AgentResult:
    """Audit documentation in the repository described by *context*.

    The orchestrator injects prior agent results via
    ``context.config["prior_results"]`` before calling this function.
    Those results are included in the raw_output for reference but the
    audit checks are performed independently against the filesystem.

    Args:
        context: Shared agent context (repo_path, config, etc.)

    Returns:
        AgentResult with status, summary, and a list of issue strings.
    """
    repo = Path(context.repo_path)
    required_sections: list[str] = context.config.get(
        "required_sections", DEFAULT_REQUIRED_SECTIONS
    )

    all_issues: list[str] = []

    # --- 1. Broken local links -----------------------------------------
    doc_files = _find_doc_files(repo)
    all_issues.extend(_check_broken_links(repo, doc_files))

    # --- 2. Version consistency ----------------------------------------
    all_issues.extend(_check_version_consistency(repo))

    # --- 3. Missing required sections ----------------------------------
    for doc_file in doc_files:
        try:
            content = doc_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(doc_file.relative_to(repo))
        all_issues.extend(_check_missing_sections(content, required_sections, rel))

    # --- 4. LLM narrative summary --------------------------------------
    summary = _llm_audit_summary(all_issues)

    status: str
    if not all_issues:
        status = "success"
    elif any("error" in i.lower() or "broken" in i.lower() for i in all_issues):
        status = "warning"
    else:
        status = "warning"

    prior: list = context.config.get("prior_results", [])

    return AgentResult(
        agent_name=AGENT_NAME,
        status=status,  # type: ignore[arg-type]
        summary=summary,
        output_files=[],
        issues=all_issues,
        raw_output={
            "issue_count": len(all_issues),
            "issues": all_issues,
            "prior_agent_results": [
                {"agent_name": r.agent_name, "status": r.status} for r in prior
            ],
        },
    )


# ---------------------------------------------------------------------------
# Internal check functions
# ---------------------------------------------------------------------------

def _find_doc_files(repo: Path) -> list[Path]:
    """Return all .md files in the repository root (non-recursive top-level)."""
    candidates = list(repo.glob("*.md")) + list(repo.glob("docs/**/*.md"))
    return [f for f in candidates if f.is_file()]


def _check_broken_links(repo: Path, doc_files: list[Path]) -> list[str]:
    """Scan markdown files for local links that point to non-existent files.

    External URLs (http/https/mailto) and anchor-only links (#section) are
    intentionally skipped — checking them would require network access.

    Returns a list of issue strings formatted as:
        "broken link: <target> in <relative-doc-path>"
    """
    issues: list[str] = []
    for doc_file in doc_files:
        try:
            content = doc_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel_doc = str(doc_file.relative_to(repo))
        for _label, target in _LINK_RE.findall(content):
            # Skip external URLs and pure anchors
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            # Strip anchor fragment from local paths (e.g. file.md#section)
            local_path = target.split("#")[0]
            if not local_path:
                continue
            resolved = (doc_file.parent / local_path).resolve()
            try:
                repo_resolved = repo.resolve()
            except OSError:
                repo_resolved = repo
            # Only flag paths inside the repo
            try:
                resolved.relative_to(repo_resolved)
            except ValueError:
                continue
            if not resolved.exists():
                issues.append(f"broken link: {target} in {rel_doc}")
    return issues


def _check_version_consistency(repo: Path) -> list[str]:
    """Compare version strings found across README, CHANGELOG, and Python files.

    Returns a list of issue strings formatted as:
        "version mismatch: <v1> in <file1> vs <v2> in <file2>"
    """
    found: dict[str, str] = {}  # filepath -> version string

    # Check README.md
    for name in ("README.md", "readme.md"):
        readme = repo / name
        if readme.exists():
            _extract_versions_from_text(readme, found, repo)

    # Check CHANGELOG.md
    for name in ("CHANGELOG.md", "changelog.md", "CHANGELOG", "CHANGES.md"):
        changelog = repo / name
        if changelog.exists():
            _extract_versions_from_text(changelog, found, repo)

    # Check Python files for __version__
    for py_file in repo.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = _PY_VERSION_RE.search(text)
        if m:
            rel = str(py_file.relative_to(repo))
            found[rel] = m.group(1)

    issues: list[str] = []
    versions = list(found.items())  # [(filepath, version), ...]
    for i in range(len(versions)):
        for j in range(i + 1, len(versions)):
            f1, v1 = versions[i]
            f2, v2 = versions[j]
            if v1 != v2:
                issues.append(f"version mismatch: {v1} in {f1} vs {v2} in {f2}")
    return issues


def _extract_versions_from_text(
    path: Path, found: dict[str, str], repo: Path
) -> None:
    """Extract the first version string from *path* into *found*."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    m = _VERSION_RE.search(text)
    if m:
        rel = str(path.relative_to(repo))
        found[rel] = m.group(1)


def _check_missing_sections(
    content: str, required: list[str], filename: str
) -> list[str]:
    """Check that *content* contains each heading listed in *required*.

    Matching is case-insensitive and ignores leading/trailing whitespace.

    Returns a list of issue strings formatted as:
        "missing section: <heading> in <filename>"
    """
    issues: list[str] = []
    content_lower = content.lower()
    for heading in required:
        if heading.lower().strip() not in content_lower:
            issues.append(f"missing section: {heading} in {filename}")
    return issues


def _llm_audit_summary(issues: list[str]) -> str:
    """Generate a human-readable summary of the audit findings via LLM.

    Uses the stub provider during tests/local dev (no API key required).
    If the LLM call itself fails for any reason, falls back to a plain
    text summary so the audit result is still useful.
    """
    if not issues:
        return "No documentation issues found."

    issue_list = "\n".join(f"- {i}" for i in issues)
    prompt = (
        f"The documentation audit found {len(issues)} issue(s):\n"
        f"{issue_list}\n\n"
        "Write a concise one-paragraph summary of these findings for a developer."
    )
    try:
        return llm_client.complete(prompt)
    except Exception:  # noqa: BLE001
        # Fallback: plain summary without LLM
        return (
            f"Audit complete. Found {len(issues)} issue(s): "
            + "; ".join(issues[:3])
            + ("..." if len(issues) > 3 else "")
        )
