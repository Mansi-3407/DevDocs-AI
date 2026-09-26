"""
End-to-end tests for the DevDocs AI pipeline.

Runs the full orchestrator against a copy of the demo fixture and asserts
that the audit agent detects the intentional documentation gaps.

All tests use LLM_PROVIDER=stub (enforced via tests/conftest.py).
No network calls, no API keys, no git history required.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import orchestrator
from app.models import AgentResult


# ---------------------------------------------------------------------------
# Fixture paths
# ---------------------------------------------------------------------------

_FIXTURE_V1 = Path(__file__).parent / "fixtures" / "sample_fastapi_app"
_FIXTURE_V2 = Path(__file__).parent / "fixtures" / "sample_fastapi_app_v2"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _copy_fixture(src: Path, dest: Path) -> Path:
    """Copy fixture directory into dest, return the copied path."""
    target = dest / src.name
    shutil.copytree(src, target)
    return target


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPipelineAgainstV2Fixture:
    """Run the full orchestrator against the v2 fixture (intentional gaps)."""

    def test_pipeline_returns_expected_keys(self, tmp_path: Path):
        repo = _copy_fixture(_FIXTURE_V2, tmp_path)
        result = orchestrator.run(repo_path=str(repo))
        assert set(result.keys()) == {"status", "results", "audit", "report"}

    def test_pipeline_completes_without_exception(self, tmp_path: Path):
        repo = _copy_fixture(_FIXTURE_V2, tmp_path)
        result = orchestrator.run(repo_path=str(repo))
        # Pipeline must always finish; no uncaught exceptions
        assert result is not None

    def test_audit_detects_version_mismatch(self, tmp_path: Path):
        """v2 fixture has __version__=2.0.0 but README/CHANGELOG say v1.0.0."""
        repo = _copy_fixture(_FIXTURE_V2, tmp_path)
        result = orchestrator.run(repo_path=str(repo))
        audit: AgentResult = result["audit"]
        version_issues = [i for i in audit.issues if "version mismatch" in i]
        assert version_issues, (
            f"Expected version mismatch issues, got: {audit.issues}"
        )

    def test_audit_result_is_agent_result(self, tmp_path: Path):
        repo = _copy_fixture(_FIXTURE_V2, tmp_path)
        result = orchestrator.run(repo_path=str(repo))
        assert isinstance(result["audit"], AgentResult)
        assert result["audit"].agent_name == "audit_agent"

    def test_content_agents_return_agent_results(self, tmp_path: Path):
        repo = _copy_fixture(_FIXTURE_V2, tmp_path)
        result = orchestrator.run(repo_path=str(repo))
        assert len(result["results"]) == 5
        for r in result["results"]:
            assert isinstance(r, AgentResult)
            assert r.status in ("success", "warning", "error", "skipped")

    def test_content_agents_reflect_current_implementation_status(
        self, tmp_path: Path
    ):
        """Implemented content agents succeed while the remaining stub stays skipped."""
        repo = _copy_fixture(_FIXTURE_V2, tmp_path)
        result = orchestrator.run(repo_path=str(repo))

        statuses = {r.agent_name: r.status for r in result["results"]}

        assert statuses["readme_agent"] == "skipped"
        assert statuses["api_agent"] == "success"
        assert statuses["example_validator"] == "success"
        assert statuses["tutorial_agent"] == "success"
        assert statuses["changelog_agent"] == "success"

    def test_report_is_non_empty_markdown_string(self, tmp_path: Path):
        repo = _copy_fixture(_FIXTURE_V2, tmp_path)
        result = orchestrator.run(repo_path=str(repo))
        report = result["report"]
        assert isinstance(report, str)
        assert "DevDocs AI" in report
        assert len(report) > 100

    def test_overall_status_reflects_audit_findings(self, tmp_path: Path):
        """v2 fixture has issues → overall status must be warning or error."""
        repo = _copy_fixture(_FIXTURE_V2, tmp_path)
        result = orchestrator.run(repo_path=str(repo))
        assert result["status"] in ("warning", "error"), (
            f"Expected warning/error with known gaps, got: {result['status']}"
        )


class TestPipelineAgainstV1Fixture:
    """Run the full orchestrator against the v1 fixture (clean baseline)."""

    def test_pipeline_completes_without_exception(self, tmp_path: Path):
        repo = _copy_fixture(_FIXTURE_V1, tmp_path)
        result = orchestrator.run(repo_path=str(repo))
        assert result is not None

    def test_no_version_mismatch_in_v1(self, tmp_path: Path):
        """v1 fixture has consistent v1.0.0 across all files."""
        repo = _copy_fixture(_FIXTURE_V1, tmp_path)
        result = orchestrator.run(repo_path=str(repo))
        audit: AgentResult = result["audit"]
        version_issues = [i for i in audit.issues if "version mismatch" in i]
        assert version_issues == [], (
            f"Unexpected version mismatch issues in v1 fixture: {version_issues}"
        )

    def test_v1_readme_has_required_sections(self, tmp_path: Path):
        """v1 README contains Installation and Usage — no missing-section issues in README."""
        repo = _copy_fixture(_FIXTURE_V1, tmp_path)
        result = orchestrator.run(
            repo_path=str(repo),
            config={"required_sections": ["## Installation", "## Usage"]},
        )
        audit: AgentResult = result["audit"]
        # Filter to README.md only — CHANGELOG.md is not expected to have
        # Installation/Usage sections, so only README misses count here.
        readme_section_issues = [
            i for i in audit.issues
            if "missing section" in i and "README.md" in i
        ]
        assert readme_section_issues == [], (
            f"Unexpected missing-section issues in v1 README: {readme_section_issues}"
        )


class TestOrchestratorResilience:
    """Verify the pipeline handles edge cases without crashing."""

    def test_empty_repo_does_not_crash(self, tmp_path: Path):
        """An empty directory with no markdown files completes cleanly."""
        result = orchestrator.run(repo_path=str(tmp_path))
        assert result["audit"].agent_name == "audit_agent"

    def test_prior_results_injected_into_audit(self, tmp_path: Path):
        """Audit agent receives prior content agent results in raw_output."""
        result = orchestrator.run(repo_path=str(tmp_path))
        prior = result["audit"].raw_output.get("prior_agent_results", [])
        agent_names = {r["agent_name"] for r in prior}
        # All five content agents must be present in prior_results
        expected = {
            "readme_agent", "api_agent", "example_validator",
            "tutorial_agent", "changelog_agent",
        }
        assert expected == agent_names, (
            f"Expected {expected}, got {agent_names}"
        )
