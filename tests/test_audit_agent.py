"""
Unit tests for app/agents/audit_agent.py

All tests use LLM_PROVIDER=stub (enforced via tests/conftest.py).
No network calls, no API keys required.
"""

import os
from pathlib import Path

import pytest

from app.agents import audit_agent
from app.agents.audit_agent import (
    _check_broken_links,
    _check_missing_sections,
    _check_version_consistency,
    _llm_audit_summary,
)
from app.models import AgentContext, AgentResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_context(tmp_path: Path, config: dict | None = None) -> AgentContext:
    """Build a minimal AgentContext pointing at tmp_path."""
    return AgentContext(
        repo_path=str(tmp_path),
        changed_files=[],
        git_diff="",
        config=config or {},
    )


# ---------------------------------------------------------------------------
# _check_broken_links
# ---------------------------------------------------------------------------

class TestCheckBrokenLinks:
    def test_detects_missing_local_file(self, tmp_path: Path):
        doc = tmp_path / "README.md"
        doc.write_text("See [guide](./missing_guide.md) for details.\n")
        issues = _check_broken_links(tmp_path, [doc])
        assert any("missing_guide.md" in i for i in issues), issues

    def test_passes_when_local_file_exists(self, tmp_path: Path):
        existing = tmp_path / "guide.md"
        existing.write_text("# Guide\n")
        doc = tmp_path / "README.md"
        doc.write_text("See [guide](./guide.md) for details.\n")
        issues = _check_broken_links(tmp_path, [doc])
        assert issues == [], issues

    def test_ignores_external_urls(self, tmp_path: Path):
        doc = tmp_path / "README.md"
        doc.write_text("See [IBM](https://ibm.com) for more.\n")
        issues = _check_broken_links(tmp_path, [doc])
        assert issues == [], issues

    def test_ignores_anchor_only_links(self, tmp_path: Path):
        doc = tmp_path / "README.md"
        doc.write_text("Jump to [section](#installation).\n")
        issues = _check_broken_links(tmp_path, [doc])
        assert issues == [], issues

    def test_returns_empty_for_no_links(self, tmp_path: Path):
        doc = tmp_path / "README.md"
        doc.write_text("# No links here.\n")
        issues = _check_broken_links(tmp_path, [doc])
        assert issues == []

    def test_detects_multiple_broken_links(self, tmp_path: Path):
        doc = tmp_path / "README.md"
        doc.write_text(
            "See [a](./a.md) and [b](./b.md).\n"
        )
        issues = _check_broken_links(tmp_path, [doc])
        assert len(issues) == 2

    def test_strips_anchor_from_local_path(self, tmp_path: Path):
        existing = tmp_path / "api.md"
        existing.write_text("# API\n")
        doc = tmp_path / "README.md"
        doc.write_text("See [api](./api.md#section) for details.\n")
        issues = _check_broken_links(tmp_path, [doc])
        assert issues == [], issues


# ---------------------------------------------------------------------------
# _check_version_consistency
# ---------------------------------------------------------------------------

class TestCheckVersionConsistency:
    def test_finds_mismatch_between_readme_and_changelog(self, tmp_path: Path):
        (tmp_path / "README.md").write_text("# My App v1.0.0\n")
        (tmp_path / "CHANGELOG.md").write_text("## v2.0.0\n")
        issues = _check_version_consistency(tmp_path)
        assert any("version mismatch" in i for i in issues), issues

    def test_no_issue_when_versions_match(self, tmp_path: Path):
        (tmp_path / "README.md").write_text("# My App v1.2.3\n")
        (tmp_path / "CHANGELOG.md").write_text("## v1.2.3\n")
        issues = _check_version_consistency(tmp_path)
        assert issues == [], issues

    def test_no_issue_when_no_versions_present(self, tmp_path: Path):
        (tmp_path / "README.md").write_text("# My App\nNo version here.\n")
        issues = _check_version_consistency(tmp_path)
        assert issues == []

    def test_detects_python_version_mismatch(self, tmp_path: Path):
        (tmp_path / "README.md").write_text("# My App v1.0.0\n")
        pkg = tmp_path / "myapp"
        pkg.mkdir()
        (pkg / "__init__.py").write_text('__version__ = "2.0.0"\n')
        issues = _check_version_consistency(tmp_path)
        assert any("version mismatch" in i for i in issues), issues

    def test_no_issue_with_matching_python_version(self, tmp_path: Path):
        (tmp_path / "README.md").write_text("# My App v1.5.0\n")
        pkg = tmp_path / "myapp"
        pkg.mkdir()
        (pkg / "__init__.py").write_text('__version__ = "1.5.0"\n')
        issues = _check_version_consistency(tmp_path)
        assert issues == [], issues


# ---------------------------------------------------------------------------
# _check_missing_sections
# ---------------------------------------------------------------------------

class TestCheckMissingSections:
    def test_reports_absent_heading(self):
        content = "# My App\n\nSome text.\n"
        issues = _check_missing_sections(content, ["## Installation"], "README.md")
        assert any("## Installation" in i for i in issues), issues

    def test_passes_when_heading_present(self):
        content = "# My App\n\n## Installation\n\nRun pip install.\n"
        issues = _check_missing_sections(content, ["## Installation"], "README.md")
        assert issues == []

    def test_case_insensitive_match(self):
        content = "# My App\n\n## installation\n\nRun pip install.\n"
        issues = _check_missing_sections(content, ["## Installation"], "README.md")
        assert issues == [], "Should match case-insensitively"

    def test_reports_multiple_missing_sections(self):
        content = "# My App\n"
        issues = _check_missing_sections(
            content, ["## Installation", "## Usage"], "README.md"
        )
        assert len(issues) == 2

    def test_empty_required_list_returns_no_issues(self):
        content = "# My App\n"
        issues = _check_missing_sections(content, [], "README.md")
        assert issues == []


# ---------------------------------------------------------------------------
# _llm_audit_summary (stub mode)
# ---------------------------------------------------------------------------

class TestLlmAuditSummary:
    def test_returns_string_with_no_issues(self):
        result = _llm_audit_summary([])
        assert isinstance(result, str)
        assert result  # non-empty

    def test_returns_string_with_issues(self):
        result = _llm_audit_summary(["broken link: ./a.md in README.md"])
        assert isinstance(result, str)
        assert result


# ---------------------------------------------------------------------------
# run() — full agent entry point
# ---------------------------------------------------------------------------

class TestRun:
    def test_returns_agent_result_instance(self, tmp_path: Path):
        (tmp_path / "README.md").write_text("# App\n\n## Installation\n\n## Usage\n")
        ctx = _make_context(tmp_path)
        result = audit_agent.run(ctx)
        assert isinstance(result, AgentResult)

    def test_agent_name_is_correct(self, tmp_path: Path):
        ctx = _make_context(tmp_path)
        result = audit_agent.run(ctx)
        assert result.agent_name == "audit_agent"

    def test_status_success_when_no_issues(self, tmp_path: Path):
        # README with all required sections and no broken links
        (tmp_path / "README.md").write_text(
            "# App v1.0.0\n\n## Installation\n\nRun pip install.\n\n## Usage\n\nRun app.\n"
        )
        ctx = _make_context(tmp_path, config={"required_sections": ["## Installation", "## Usage"]})
        result = audit_agent.run(ctx)
        assert result.status == "success"
        assert result.issues == []

    def test_status_warning_when_issues_found(self, tmp_path: Path):
        # README with a broken link
        (tmp_path / "README.md").write_text(
            "# App\n\nSee [guide](./missing.md).\n\n## Installation\n\n## Usage\n"
        )
        ctx = _make_context(tmp_path)
        result = audit_agent.run(ctx)
        assert result.status == "warning"
        assert any("missing.md" in i for i in result.issues)

    def test_raw_output_contains_issue_count(self, tmp_path: Path):
        ctx = _make_context(tmp_path)
        result = audit_agent.run(ctx)
        assert "issue_count" in result.raw_output
        assert result.raw_output["issue_count"] == len(result.issues)

    def test_prior_results_recorded_in_raw_output(self, tmp_path: Path):
        from app.models import AgentResult
        prior = [AgentResult(agent_name="readme_agent", status="skipped", summary="stub")]
        ctx = _make_context(tmp_path, config={"prior_results": prior})
        result = audit_agent.run(ctx)
        prior_names = [r["agent_name"] for r in result.raw_output["prior_agent_results"]]
        assert "readme_agent" in prior_names

    def test_custom_required_sections_respected(self, tmp_path: Path):
        (tmp_path / "README.md").write_text("# App\n\n## Quick Start\n\nHello.\n")
        ctx = _make_context(tmp_path, config={"required_sections": ["## Quick Start"]})
        result = audit_agent.run(ctx)
        assert not any("Quick Start" in i for i in result.issues)

    def test_missing_default_sections_detected(self, tmp_path: Path):
        (tmp_path / "README.md").write_text("# App\n\nJust a title.\n")
        ctx = _make_context(tmp_path)
        result = audit_agent.run(ctx)
        # Default required sections: ## Installation and ## Usage
        assert any("Installation" in i for i in result.issues)
