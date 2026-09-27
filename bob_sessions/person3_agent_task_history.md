# Please inspect `tests/test_changelog_agent.py` and completely implement `app/agents/changelog_agent.py` so that all the tests in `tests/test_changelog_agent.py` pass.

Requirements:
1. Implement the ChangelogAgent class with methods for parsing conventional commits, detecting breaking changes, generating CHANGELOG markdown, and generating migration guides.
2. Strictly follow all class and method signatures expected by `tests/test_changelog_agent.py`.
3. Provide complete, production-ready Python code without placeholders.

---

**Status:** active  **Date:** 2026-09-26

---

### 👤 User

Please inspect `tests/test_changelog_agent.py` and completely implement `app/agents/changelog_agent.py` so that all the tests in `tests/test_changelog_agent.py` pass.

Requirements:
1. Implement the ChangelogAgent class with methods for parsing conventional commits, detecting breaking changes, generating CHANGELOG markdown, and generating migration guides.
2. Strictly follow all class and method signatures expected by `tests/test_changelog_agent.py`.
3. Provide complete, production-ready Python code without placeholders.

---

### 🤖 Assistant

> 🔧 called: read_file, list_files

Let me start by reading the test file to understand exactly what's expected.

> 🔧 **read_file** — tests/test_changelog_agent.py

> 🔧 **list_files** — .

### 🤖 Assistant

> 🔧 called: read_file, read_file, read_file, read_file

The test file is empty. Let me look at the existing changelog agent, PRD, other test files for context, and the README.

> 🔧 **read_file** — tests/test_tutorial_agent.py

> 🔧 **read_file** — PRD.md

> 🔧 **read_file** — tests/test_api_agent.py

> 🔧 **read_file** — app/agents/changelog_agent.py

### 🤖 Assistant

> 🔧 called: read_file, read_file, read_file, read_file

All files are empty. Let me check the other test files and existing agent implementations for patterns.

> 🔧 **read_file** — tests/test_audit_agent.py

> 🔧 **read_file** — tests/test_readme_agent.py

> 🔧 **read_file** — app/agents/tutorial_agent.py

> 🔧 **read_file** — app/agents/api_agent.py

### 🤖 Assistant

> 🔧 called: read_file, read_file, read_file, read_file



> 🔧 **read_file** — app/main.py

> 🔧 **read_file** — app/agents/audit_agent.py

> 🔧 **read_file** — README.md

> 🔧 **read_file** — app/utils/git_helper.py

### 🤖 Assistant

> 🔧 called: read_file, read_file, read_file, read_file

The test file is empty and so is the existing `changelog_agent.py`. Based on the requirement, I need to:
1. Write comprehensive tests in `tests/test_changelog_agent.py` for a `ChangelogAgent`
2. Implement `app/agents/changelog_agent.py` so all those tests pass

Let me check the CHANGELOG.md and any other existing agent for patterns:

> 🔧 **read_file** — CHANGELOG.md

> 🔧 **read_file** — app/agents/readme_agent.py

> 🔧 **read_file** — app/agents/example_validator.py

> 🔧 **read_file** — orchestrator.py

### 🤖 Assistant

> 🔧 called: update_todo_list

Every file is empty. The entire project is a blank slate. I need to design both the test file and the implementation from scratch, based on the README description. Let me plan everything carefully.

> 🔧 **update_todo_list** — 
[-] Design and write tests/test_changelog_agent.py with comprehensive test coverage
[ ] Implement app/agents/changelog_agent.py to pass all tests
[ ] Run the test suite to verify all tests pass


### 🤖 Assistant

> 🔧 called: write_file

Now I'll write both files. The test file first, then the implementation.

> 🔧 **write_file** — tests/test_changelog_agent.py

### 🤖 Assistant

> 🔧 called: update_todo_list

Now implement the agent:

> 🔧 **update_todo_list** — 
[x] Design and write tests/test_changelog_agent.py with comprehensive test coverage
[-] Implement app/agents/changelog_agent.py to pass all tests
[ ] Run the test suite to verify all tests pass


### 🤖 Assistant

> 🔧 called: write_file



> 🔧 **write_file** — app/agents/changelog_agent.py

### 🤖 Assistant

> 🔧 called: execute_command

Now run the tests:

> 🔧 **execute_command** — python -m pytest tests/test_changelog_agent.py -v 2>&1

### 🤖 Assistant

> 🔧 called: execute_command



> 🔧 **execute_command** — pip install pytest --quiet 2>&1; python -m pytest tests/test_changelog_agent.py -v 2>&1

### 🤖 Assistant

> 🔧 called: update_todo_list

**53/53 tests pass.**

> 🔧 **update_todo_list** — 
[x] Design and write tests/test_changelog_agent.py with comprehensive test coverage
[x] Implement app/agents/changelog_agent.py to pass all tests
[x] Run the test suite to verify all tests pass


### 🤖 Assistant

All 53 tests pass. Here's a summary of what was built:

---

### [`tests/test_changelog_agent.py`](tests/test_changelog_agent.py) — 53 tests across 4 classes

| Class | Tests | What it covers |
|---|---|---|
| `TestParseCommits` | 22 | Type parsing, scope, breaking flags (`!` and `BREAKING CHANGE:`), raw preservation, empty input, unknown types |
| `TestDetectBreaking` | 9 | Filter accuracy, no false-positives, multiple breaking changes, empty input |
| `TestGenerateChangelog` | 12 | Version in output, section headings, breaking section present/absent, date format, empty commits |
| `TestGenerateMigration` | 10 | From/to version injection, breaking descriptions listed, no-changes note, full end-to-end pipeline |

---

### [`app/agents/changelog_agent.py`](app/agents/changelog_agent.py) — `ChangelogAgent`

Four public methods:

- **[`parse_commits(commits)`](app/agents/changelog_agent.py:72)** — Parses raw conventional-commit strings using two regex patterns: one for the standard `type[(scope)][!]: description` form and one for standalone `BREAKING CHANGE: …` footers. Returns a list of dicts with `type`, `scope`, `description`, `breaking`, and `raw` keys.

- **[`detect_breaking(parsed_commits)`](app/agents/changelog_agent.py:117)** — Filters the parsed list to only entries where `breaking is True`.

- **[`generate_changelog(parsed_commits, version)`](app/agents/changelog_agent.py:131)** — Renders a Keep-a-Changelog-style Markdown document. Commits are grouped by type into labelled sections (Features, Bug Fixes, etc.) with a prominent ⚠️ Breaking Changes section at the top when applicable. Includes a `YYYY-MM-DD` datestamp.

- **[`generate_migration(breaking_commits, from_version, to_version)`](app/agents/changelog_agent.py:186)** — Renders a Markdown migration guide listing each breaking change with its original commit string, a note for developers to act on, and a step-by-step "How to Apply" section. Returns a clean "No Breaking Changes" note when given an empty list.

---

### 👤 User

Please inspect `tests/test_tutorial_agent.py` and completely implement `app/agents/tutorial_agent.py` so that all the tests in `tests/test_tutorial_agent.py` pass.

Requirements:
1. Implement the TutorialAgent class with methods for detecting new features from code/diffs, generating step-by-step tutorials, code examples, and troubleshooting sections.
2. Strictly follow all class and method signatures expected by `tests/test_tutorial_agent.py`.
3. Provide complete, production-ready Python code without placeholders.

---

### 🤖 Assistant

> 🔧 called: read_file, read_file

Let me read the test file and existing agent to understand the current state.

> 🔧 **read_file** — tests/test_tutorial_agent.py

> 🔧 **read_file** — app/agents/tutorial_agent.py

### 🤖 Assistant

> 🔧 called: read_file, read_file, read_file

Both are empty. Let me gather full context before designing anything.

> 🔧 **read_file** — app/agents/changelog_agent.py

> 🔧 **read_file** — tests/test_changelog_agent.py

> 🔧 **read_file** — README.md

### 🤖 Assistant

> 🔧 called: update_todo_list

I have everything I need. Now I'll plan the full design carefully before writing a single line.

The `TutorialAgent` needs:
1. **`detect_features(diff_or_code)`** — extract feature signals from raw diff/code text → `list[dict]`
2. **`generate_tutorial(feature, …)`** — generate a step-by-step tutorial markdown for one feature → `str`
3. **`generate_code_example(feature, …)`** — generate a fenced code example snippet → `str`
4. **`generate_troubleshooting(feature, …)`** — generate a troubleshooting section → `str`

I'll write both files in parallel now.

> 🔧 **update_todo_list** — 
[-] Design and write tests/test_tutorial_agent.py with comprehensive test coverage
[ ] Implement app/agents/tutorial_agent.py to pass all tests
[ ] Run the test suite to verify all tests pass


### 🤖 Assistant

> 🔧 called: update_todo_list



> 🔧 **update_todo_list** — 
[x] Design and write tests/test_changelog_agent.py with comprehensive test coverage
[x] Implement app/agents/changelog_agent.py to pass all tests
[x] Run the test suite to verify all tests pass (changelog)
[-] Design and write tests/test_tutorial_agent.py with comprehensive test coverage
[ ] Implement app/agents/tutorial_agent.py to pass all tests
[ ] Run the test suite to verify all tutorial tests pass


### 🤖 Assistant

> 🔧 called: update_todo_list



> 🔧 **update_todo_list** — 
[x] Design and write tests/test_changelog_agent.py with comprehensive test coverage
[x] Implement app/agents/changelog_agent.py to pass all tests
[x] Run the test suite to verify all tests pass
[-] Design and write tests/test_tutorial_agent.py with comprehensive test coverage
[ ] Implement app/agents/tutorial_agent.py to pass all tests
[ ] Run the test suite to verify all tutorial tests pass


### 🤖 Assistant

> 🔧 called: write_file

Now write the test file — comprehensive coverage of all four methods and the full pipeline:

> 🔧 **write_file** — tests/test_tutorial_agent.py

### 🤖 Assistant

> 🔧 called: update_todo_list

Good. Now implement the agent:

> 🔧 **update_todo_list** — 
[x] Design and write tests/test_changelog_agent.py with comprehensive test coverage
[x] Implement app/agents/changelog_agent.py to pass all tests
[x] Run the test suite to verify all tests pass
[x] Design and write tests/test_tutorial_agent.py with comprehensive test coverage
[-] Implement app/agents/tutorial_agent.py to pass all tests
[ ] Run the test suite to verify all tutorial tests pass


### 🤖 Assistant

> 🔧 called: write_file



> 🔧 **write_file** — """
TutorialAgent — analyses code diffs / source files and generates developer documentation.

Public API
----------
detect_features(diff_or_code)                               -> list[dict]
generate_tutorial(feature, *, title, language)              -> str
generate_code_example(feature, *, language, context)        -> str
generate_troubleshooting(feature, *, known_issues)          -> str

Terminology
-----------
*feature*   – a dict with keys ``name``, ``kind`` ("function" | "class" | "method"),
              and ``description``.  Produced by :meth:`detect_features` or supplied
              directly by the caller.

Detection strategy
------------------
The detector works purely with static text analysis (no AST / no external tools) so
that it runs everywhere without additional dependencies:

1. If the text looks like a unified diff (contains ``+++`` / ``---`` / ``@@`` markers),
   only lines that start with ``+`` (additions) are considered, and leading ``+``
   characters are stripped before pattern matching.
2. Class definitions (``class Foo``) and top-level / module-level function definitions
   (``def foo``) that are *not* dunder methods are extracted.
3. Each extracted symbol is enriched with its inline docstring (if present on the
   immediately following ``+`` line or plain next line).
"""

from __future__ import annotations

import re
import textwrap
from typing import Any


# ---------------------------------------------------------------------------
# Internal regex patterns
# ---------------------------------------------------------------------------

# Detects a unified-diff file header
_IS_DIFF = re.compile(r"^(?:diff --git|---|\+\+\+|@@)", re.MULTILINE)

# Matches a class definition line (possibly indented in a diff "+" line)
_CLASS_DEF = re.compile(r"^(?P<indent>\s*)class\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?:\s*[\(:])")

# Matches a function / method definition line
_FUNC_DEF = re.compile(r"^(?P<indent>\s*)def\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(")

# Matches a docstring opener
_DOCSTRING = re.compile(r'^\s*(?:\"\"\"(?P<text>[^\"]*)|\'\'\'(?P<text2>[^\']*))')

# Dunder names we ignore (they aren't "new features" worth documenting)
_DUNDER = re.compile(r"^__[a-z_]+__$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_diff_prefix(lines: list[str]) -> list[str]:
    """Return only added lines with the leading ``+`` removed."""
    result = []
    for line in lines:
        if line.startswith("++") or line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("+"):
            result.append(line[1:])
    return result


def _is_diff_text(text: str) -> bool:
    return bool(_IS_DIFF.search(text))


def _extract_features(lines: list[str]) -> list[dict[str, Any]]:
    """Walk *lines* and return feature dicts for every class / top-level function found."""
    features: list[dict[str, Any]] = []
    seen: set[str] = set()
    n = len(lines)

    for i, line in enumerate(lines):
        class_m = _CLASS_DEF.match(line)
        func_m = _FUNC_DEF.match(line)

        if class_m:
            name = class_m.group("name")
            if name in seen:
                continue
            seen.add(name)
            description = _peek_docstring(lines, i + 1) or f"The {name} class."
            features.append({"name": name, "kind": "class", "description": description})

        elif func_m:
            name = func_m.group("name")
            indent = func_m.group("indent")
            if name in seen or _DUNDER.match(name):
                continue
            # Determine kind: method if indented (inside a class body), else function
            kind = "method" if indent else "function"
            seen.add(name)
            description = _peek_docstring(lines, i + 1) or f"The {name} {kind}."
            features.append({"name": name, "kind": kind, "description": description})

    return features


def _peek_docstring(lines: list[str], start: int) -> str:
    """Return the first docstring text found at or after *start*, or ``""``."""
    for j in range(start, min(start + 3, len(lines))):
        m = _DOCSTRING.match(lines[j])
        if m:
            text = (m.group("text") or m.group("text2") or "").strip()
            if text:
                return text
    return ""


def _fence(code: str, language: str = "") -> str:
    """Wrap *code* in a Markdown fenced block."""
    return f"```{language}\n{code.rstrip()}\n```"


def _function_call_example(name: str, description: str) -> str:
    """Produce a minimal realistic Python call for a function."""
    return f"result = {name}()"


def _class_usage_example(name: str) -> str:
    """Produce a minimal realistic Python instantiation for a class."""
    return f"instance = {name}()\n# use instance methods as needed"


# ---------------------------------------------------------------------------
# TutorialAgent
# ---------------------------------------------------------------------------

class TutorialAgent:
    """Generates developer tutorials and documentation from code changes."""

    # ------------------------------------------------------------------
    # detect_features
    # ------------------------------------------------------------------

    def detect_features(self, diff_or_code: str) -> list[dict[str, Any]]:
        """Extract feature signals (functions, classes) from a diff or source file.

        The method handles both unified-diff format and plain source code.
        For diffs only *added* lines (``+``) are considered; removed lines (``-``)
        are silently ignored so that deleted symbols are not reported as new features.

        Args:
            diff_or_code: A unified diff string or raw Python source code.

        Returns:
            List of feature dicts, each with keys ``name``, ``kind``, and
            ``description``.  Returns ``[]`` for empty or whitespace-only input.
        """
        if not diff_or_code or not diff_or_code.strip():
            return []

        raw_lines = diff_or_code.splitlines()

        if _is_diff_text(diff_or_code):
            lines = _strip_diff_prefix(raw_lines)
        else:
            lines = raw_lines

        return _extract_features(lines)

    # ------------------------------------------------------------------
    # generate_tutorial
    # ------------------------------------------------------------------

    def generate_tutorial(
        self,
        feature: dict[str, Any],
        *,
        title: str | None = None,
        language: str = "python",
    ) -> str:
        """Render a step-by-step tutorial Markdown document for *feature*.

        Args:
            feature:  Feature dict with at minimum ``name``, ``kind``, and
                      ``description`` keys.
            title:    Optional custom heading.  Defaults to
                      ``"How to use <name>"``.
            language: Programming-language hint used in fenced code blocks.
                      Defaults to ``"python"``.

        Returns:
            A fully-rendered Markdown string starting with a ``#`` heading.
        """
        name        = feature["name"]
        kind        = feature.get("kind", "function")
        description = feature.get("description", f"The {name} {kind}.")
        heading     = title or f"How to use `{name}`"
        lang        = language or "python"

        if kind == "class":
            usage_code = (
                f"# Instantiate the class\n"
                f"obj = {name}()\n\n"
                f"# Call a method\n"
                f"# obj.method()"
            )
            step_body = (
                f"Create an instance of `{name}` and call its methods as shown above."
            )
        else:
            usage_code = (
                f"# Import or locate {name} in your module\n"
                f"# from your_module import {name}\n\n"
                f"# Call the {kind}\n"
                f"result = {name}()"
            )
            step_body = (
                f"Import `{name}` from the appropriate module and invoke it "
                f"with the required arguments."
            )

        lines = [
            f"# {heading}",
            "",
            "## Overview",
            "",
            f"This tutorial explains how to use **`{name}`** ({kind}) in your project.",
            "",
            f"{description}",
            "",
            "## Prerequisites",
            "",
            f"Before you begin, ensure the following requirements are met:",
            "",
            f"- Python 3.8 or higher is installed.",
            f"- The module containing `{name}` is available in your environment.",
            f"- Required dependencies are installed (`pip install -r requirements.txt`).",
            "",
            "## Step 1 — Import",
            "",
            f"Import `{name}` into your script or module:",
            "",
            _fence(f"from your_module import {name}", lang),
            "",
            "## Step 2 — Usage",
            "",
            step_body,
            "",
            _fence(usage_code, lang),
            "",
            "## Step 3 — Verify",
            "",
            f"Run your script and confirm `{name}` behaves as expected:",
            "",
            _fence(
                f"# Example assertion\n"
                f"assert {name} is not None  # replace with real verification",
                lang,
            ),
            "",
            "## Summary",
            "",
            f"You have learned how to use `{name}` ({kind}).  "
            f"Refer to the API reference for full parameter documentation.",
            "",
            "## Next Steps",
            "",
            f"- Explore the troubleshooting guide for `{name}`.",
            f"- Review the code-example snippets for common usage patterns.",
            "",
        ]

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # generate_code_example
    # ------------------------------------------------------------------

    def generate_code_example(
        self,
        feature: dict[str, Any],
        *,
        language: str = "python",
        context: str | None = None,
    ) -> str:
        """Render a fenced Markdown code-example snippet for *feature*.

        Args:
            feature:  Feature dict with at minimum ``name``, ``kind``, and
                      ``description`` keys.
            language: Language identifier placed after the opening fence.
                      Defaults to ``"python"``.
            context:  Optional free-text context hint (e.g. ``"FastAPI route"``).
                      Included as a comment in the example when provided.

        Returns:
            A Markdown string containing at least one fenced code block.
        """
        name        = feature["name"]
        kind        = feature.get("kind", "function")
        description = feature.get("description", f"The {name} {kind}.")
        lang        = language or "python"

        context_comment = f"# Context: {context}\n" if context else ""

        if kind == "class":
            code_lines = [
                context_comment,
                f"# Example: using {name}",
                f"# {description}",
                f"",
                f"from your_module import {name}",
                f"",
                f"# Instantiate",
                f"instance = {name}()",
                f"",
                f"# Use methods",
                f"# instance.some_method()",
            ]
        else:
            code_lines = [
                context_comment,
                f"# Example: {name}",
                f"# {description}",
                f"",
                f"from your_module import {name}",
                f"",
                f"# Basic usage",
                f"result = {name}()",
                f"print(result)",
            ]

        code_body = "\n".join(line for line in code_lines if line is not None)

        lines = [
            f"### Usage example: `{name}`",
            "",
            _fence(code_body, lang),
        ]

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # generate_troubleshooting
    # ------------------------------------------------------------------

    def generate_troubleshooting(
        self,
        feature: dict[str, Any],
        *,
        known_issues: list[str] | None = None,
    ) -> str:
        """Render a Markdown troubleshooting section for *feature*.

        Args:
            feature:       Feature dict with at minimum ``name``, ``kind``, and
                           ``description`` keys.
            known_issues:  Optional list of additional known-issue strings to
                           include verbatim in the output.

        Returns:
            A Markdown string with a heading, common problems, and suggested fixes.
        """
        name  = feature["name"]
        kind  = feature.get("kind", "function")
        extra = known_issues or []

        # Build a small set of generic issues tailored by kind
        generic_issues: list[tuple[str, str]] = [
            (
                f"`{name}` raises `ImportError`",
                f"Ensure the module that defines `{name}` is installed and on "
                f"`sys.path`. Run `pip install -r requirements.txt`.",
            ),
            (
                f"`{name}` returns unexpected `None`",
                f"Check that all required arguments are passed correctly. "
                f"Review the `{name}` docstring for parameter details.",
            ),
        ]

        if kind == "class":
            generic_issues.append((
                f"`{name}` raises `TypeError` on instantiation",
                f"Verify that the constructor arguments match the `{name}.__init__` "
                f"signature.",
            ))
        else:
            generic_issues.append((
                f"`{name}` raises `TypeError`",
                f"Confirm the argument types and count match the function signature. "
                f"See the function's docstring for guidance.",
            ))

        lines = [
            f"# Troubleshooting: `{name}`",
            "",
            f"This section covers common problems encountered when using "
            f"**`{name}`** ({kind}) and how to resolve them.",
            "",
            "## Common Issues",
            "",
        ]

        # Generic built-in issues
        for problem, solution in generic_issues:
            lines += [
                f"### {problem}",
                "",
                f"**Solution:** {solution}",
                "",
            ]

        # Caller-supplied known issues
        if extra:
            lines += [
                "## Additional Known Issues",
                "",
            ]
            for issue in extra:
                lines += [
                    f"- **{issue}**",
                    "",
                    f"  Check the relevant configuration and ensure all "
                    f"  dependencies for `{name}` are correctly set up.",
                    "",
                ]

        lines += [
            "## General Checklist",
            "",
            f"- [ ] Verify `{name}` is imported from the correct module.",
            f"- [ ] Ensure all required arguments are provided.",
            f"- [ ] Check logs for stack traces that point to the root cause.",
            f"- [ ] Confirm the installed package version is compatible.",
            "",
        ]

        return "\n".join(lines)


### 🤖 Assistant

> 🔧 called: execute_command

Now run the full test suite for the tutorial agent:

> 🔧 **execute_command** — python -m pytest tests/test_tutorial_agent.py -v 2>&1

### 🤖 Assistant

> 🔧 called: apply_diff

59/60 pass. One failure: `MINIMAL_DIFF` lines start with `+` (it's a simple diff fragment without `diff --git` / `@@` headers), but `_is_diff_text` returns `False` for it, so the raw `+def create_user(...)` line is passed directly to the regex matcher — the `+` prefix makes it fail to match as a function. I need to also recognise bare `+def` / `+class` patterns as diff additions even when the full diff header is absent.

> 🔧 **apply_diff** — app/agents/tutorial_agent.py

### 🤖 Assistant

> 🔧 called: execute_command

Now verify the fix doesn't break `DELETION_ONLY_DIFF` (which also triggers `_is_diff_text` now, but only has `-` lines — `_strip_diff_prefix` correctly returns nothing for those). Run all tests:

> 🔧 **execute_command** — python -m pytest tests/test_tutorial_agent.py tests/test_changelog_agent.py -v 2>&1

### 🤖 Assistant

> 🔧 called: update_todo_list

**113/113 tests pass** — 60 tutorial tests and 53 changelog tests, zero failures.

> 🔧 **update_todo_list** — 
[x] Design and write tests/test_changelog_agent.py with comprehensive test coverage
[x] Implement app/agents/changelog_agent.py to pass all tests
[x] Run the test suite to verify all tests pass
[x] Design and write tests/test_tutorial_agent.py with comprehensive test coverage
[x] Implement app/agents/tutorial_agent.py to pass all tests
[x] Run the test suite to verify all tutorial tests pass


### 🤖 Assistant

All 60 tutorial tests pass (113 total across both agents). Here's a complete summary:

---

### [`tests/test_tutorial_agent.py`](tests/test_tutorial_agent.py) — 60 tests across 5 classes

| Class | Tests | What it covers |
|---|---|---|
| `TestDetectFeatures` | 18 | Function/class detection from real diffs & plain source; `kind` correctness; docstring capture; empty/whitespace/deletion-only input; no duplicates |
| `TestGenerateTutorial` | 14 | Markdown structure (`#` heading, `##` sections); Overview, Prerequisites, Steps, Summary presence; feature name in output; custom `title` and `language` params; class vs function handling |
| `TestGenerateCodeExample` | 12 | Fenced block present & balanced; `language` injected into fence tag; custom language; import hint; class instantiation; `context` param; balanced fence count |
| `TestGenerateTroubleshooting` | 11 | Troubleshooting keyword; feature name in output; at least one issue listed; solution keyword; `known_issues` list injected verbatim; empty `known_issues` still produces output |
| `TestFullPipeline` | 5 | End-to-end: `detect_features → tutorial / example / troubleshooting`; assembled multi-feature doc; class diff full pipeline |

---

### [`app/agents/tutorial_agent.py`](app/agents/tutorial_agent.py) — `TutorialAgent`

Four public methods, all keyword-argument optional params:

- **[`detect_features(diff_or_code)`](app/agents/tutorial_agent.py:131)** — Pure-regex static analyser. Auto-detects unified diffs (including bare `+def`/`+class` fragments without headers) and strips addition prefixes before matching. Extracts `class` and `def` symbols, skips dunder methods, peeks at the immediately following line for a docstring, and returns `[]` for empty/whitespace/deletion-only input. Each feature dict carries `name`, `kind` (`"function"` | `"class"` | `"method"`), and `description`.

- **[`generate_tutorial(feature, *, title, language)`](app/agents/tutorial_agent.py:168)** — Renders a full Keep-a-Tutorial-style Markdown document: `# Heading`, `## Overview`, `## Prerequisites`, `## Step 1–3`, `## Summary`, `## Next Steps`. Class and function features get tailored usage code. Custom `title` and `language` are fully respected.

- **[`generate_code_example(feature, *, language, context)`](app/agents/tutorial_agent.py:233)** — Renders a minimal, import-prefixed fenced code snippet. Language tag is injected directly after the opening fence. An optional `context` hint appears as a leading comment. Classes get instantiation examples; functions get call examples.

- **[`generate_troubleshooting(feature, *, known_issues)`](app/agents/tutorial_agent.py:282)** — Renders a `# Troubleshooting: name` document with `## Common Issues` (3 generic entries tailored by `kind`) and an `## Additional Known Issues` section that verbatim includes every string in the `known_issues` list. Closes with a `## General Checklist`.