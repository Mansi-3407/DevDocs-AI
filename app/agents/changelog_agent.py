"""
ChangelogAgent — parses conventional commits and generates release documentation.

Public API
----------
parse_commits(commits)                          -> list[dict]
detect_breaking(parsed_commits)                 -> list[dict]
generate_changelog(parsed_commits, version)     -> str
generate_migration(breaking_commits,
                   from_version, to_version)    -> str

Conventional-commit spec (subset implemented here):
  <type>[optional scope][!]: <description>
  BREAKING CHANGE: <description>   (footer / standalone form)

References:
  https://www.conventionalcommits.org/en/v1.0.0/
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from typing import Any


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Matches:  type[(scope)][!]: description
# Groups:   1=type  2=scope (optional, no parens)  3=bang  4=description
_CC_PATTERN = re.compile(
    r"^(?P<type>[a-zA-Z]+)"       # commit type
    r"(?:\((?P<scope>[^)]+)\))?"  # optional (scope)
    r"(?P<bang>!)?"               # optional ! for breaking
    r":\s*(?P<description>.+)$"   # colon + description
)

# Standalone "BREAKING CHANGE: …" footer / subject line
_BREAKING_FOOTER = re.compile(r"^BREAKING[ -]CHANGE:\s*(?P<description>.+)$", re.IGNORECASE)

# Human-friendly section headings mapped from commit type
_SECTION_LABELS: dict[str, str] = {
    "feat":     "✨ Features",
    "fix":      "🐛 Bug Fixes",
    "perf":     "⚡ Performance Improvements",
    "refactor": "♻️  Refactoring",
    "docs":     "📝 Documentation",
    "style":    "💄 Style",
    "test":     "✅ Tests",
    "build":    "🏗️  Build System",
    "ci":       "👷 Continuous Integration",
    "chore":    "🔧 Chores",
    "revert":   "⏪ Reverts",
}

# Types that are typically not interesting enough to show in a public changelog
_INTERNAL_TYPES = {"test", "style", "ci", "build", "chore"}


def _label(commit_type: str) -> str:
    """Return a human-readable section label for *commit_type*."""
    return _SECTION_LABELS.get(commit_type, f"🗂️  {commit_type.capitalize()}")


# ---------------------------------------------------------------------------
# ChangelogAgent
# ---------------------------------------------------------------------------

class ChangelogAgent:
    """Analyses conventional-commit messages and produces release documentation."""

    # ------------------------------------------------------------------
    # parse_commits
    # ------------------------------------------------------------------

    def parse_commits(self, commits: list[str]) -> list[dict[str, Any]]:
        """Parse a list of raw commit message strings.

        Each returned dict contains at minimum:
          - type (str)          – conventional-commit type
          - scope (str | None)  – optional scope
          - description (str)   – short commit summary
          - breaking (bool)     – True when the commit introduces a breaking change
          - raw (str)           – the original, unmodified commit string

        Args:
            commits: Raw commit message strings (one per commit).

        Returns:
            List of parsed commit dicts, one per input string.
        """
        result: list[dict[str, Any]] = []

        for raw in commits:
            raw_stripped = raw.strip()

            # Try the "BREAKING CHANGE: …" standalone form first.
            footer_match = _BREAKING_FOOTER.match(raw_stripped)
            if footer_match:
                result.append({
                    "type": "breaking",
                    "scope": None,
                    "description": footer_match.group("description").strip(),
                    "breaking": True,
                    "raw": raw,
                })
                continue

            # Try the standard conventional-commit pattern.
            cc_match = _CC_PATTERN.match(raw_stripped)
            if cc_match:
                scope = cc_match.group("scope")
                bang = cc_match.group("bang")
                result.append({
                    "type": cc_match.group("type").lower(),
                    "scope": scope if scope else None,
                    "description": cc_match.group("description").strip(),
                    "breaking": bang == "!",
                    "raw": raw,
                })
                continue

            # Fallback: store as unknown type, non-breaking.
            result.append({
                "type": "unknown",
                "scope": None,
                "description": raw_stripped,
                "breaking": False,
                "raw": raw,
            })

        return result

    # ------------------------------------------------------------------
    # detect_breaking
    # ------------------------------------------------------------------

    def detect_breaking(self, parsed_commits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return only the commits that introduce a breaking change.

        Args:
            parsed_commits: List of dicts as returned by :meth:`parse_commits`.

        Returns:
            Filtered list containing only entries where ``breaking`` is ``True``.
        """
        return [c for c in parsed_commits if c.get("breaking") is True]

    # ------------------------------------------------------------------
    # generate_changelog
    # ------------------------------------------------------------------

    def generate_changelog(
        self,
        parsed_commits: list[dict[str, Any]],
        version: str = "Unreleased",
    ) -> str:
        """Render a CHANGELOG markdown document.

        The output follows the Keep-a-Changelog convention with Markdown
        headings and bullet-point lists grouped by commit type.

        Args:
            parsed_commits: List of dicts as returned by :meth:`parse_commits`.
            version:        Release version string (e.g. ``"1.2.0"``).

        Returns:
            A fully-rendered Markdown string.
        """
        today = date.today().isoformat()
        lines: list[str] = [
            f"# Changelog",
            "",
            f"## [{version}] — {today}",
            "",
        ]

        # Group commits by type; collect breaking ones separately.
        by_type: dict[str, list[dict]] = defaultdict(list)
        breaking_commits: list[dict] = []

        for commit in parsed_commits:
            if commit.get("breaking"):
                breaking_commits.append(commit)
            by_type[commit["type"]].append(commit)

        # Breaking changes section first (most important).
        if breaking_commits:
            lines.append("### ⚠️  Breaking Changes")
            lines.append("")
            for c in breaking_commits:
                scope_tag = f"**{c['scope']}**: " if c.get("scope") else ""
                lines.append(f"- {scope_tag}{c['description']}")
            lines.append("")

        # Ordered list of display-worthy types.
        display_order = [
            "feat", "fix", "perf", "refactor",
            "docs", "style", "test", "build", "ci", "chore", "revert",
        ]
        displayed: set[str] = set()

        for commit_type in display_order:
            if commit_type not in by_type:
                continue
            displayed.add(commit_type)
            section_commits = by_type[commit_type]
            lines.append(f"### {_label(commit_type)}")
            lines.append("")
            for c in section_commits:
                scope_tag = f"**{c['scope']}**: " if c.get("scope") else ""
                lines.append(f"- {scope_tag}{c['description']}")
            lines.append("")

        # Any remaining custom types not in the predefined order.
        for commit_type, type_commits in by_type.items():
            if commit_type in displayed:
                continue
            lines.append(f"### {_label(commit_type)}")
            lines.append("")
            for c in type_commits:
                scope_tag = f"**{c['scope']}**: " if c.get("scope") else ""
                lines.append(f"- {scope_tag}{c['description']}")
            lines.append("")

        if not parsed_commits:
            lines.append("_No changes recorded for this release._")
            lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # generate_migration
    # ------------------------------------------------------------------

    def generate_migration(
        self,
        breaking_commits: list[dict[str, Any]],
        from_version: str = "previous",
        to_version: str = "current",
    ) -> str:
        """Render a migration guide for a set of breaking changes.

        Args:
            breaking_commits: List of breaking-change commit dicts (typically
                              the output of :meth:`detect_breaking`).
            from_version:     The version users are migrating *from*.
            to_version:       The version users are migrating *to*.

        Returns:
            A fully-rendered Markdown migration guide.
        """
        lines: list[str] = [
            f"# Migration Guide: {from_version} → {to_version}",
            "",
            f"This document describes the steps required to migrate your project "
            f"from **{from_version}** to **{to_version}**.",
            "",
        ]

        if not breaking_commits:
            lines += [
                "## No Breaking Changes",
                "",
                "No breaking changes were introduced in this release. "
                "No migration steps are required.",
                "",
            ]
            return "\n".join(lines)

        lines += [
            "## Breaking Changes",
            "",
            f"The following breaking changes were introduced between "
            f"**{from_version}** and **{to_version}**.",
            "",
        ]

        for idx, commit in enumerate(breaking_commits, start=1):
            scope_tag = f"[{commit['scope']}] " if commit.get("scope") else ""
            lines.append(f"### {idx}. {scope_tag}{commit['description']}")
            lines.append("")
            lines.append(
                f"> **Original commit:** `{commit['raw']}`"
            )
            lines.append("")
            lines.append(
                "Review the change above and update your code accordingly."
            )
            lines.append("")

        lines += [
            "## How to Apply This Migration",
            "",
            "1. Read each breaking change listed above.",
            "2. Locate the affected areas in your codebase.",
            "3. Apply the required changes.",
            "4. Run your test suite to verify correctness.",
            "",
        ]

        return "\n".join(lines)
