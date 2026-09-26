"""
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

# Detects a unified-diff file header OR bare +def / +class addition lines
_IS_DIFF = re.compile(
    r"^(?:diff --git|---|\+\+\+|@@|[+-]def\s|[+-]class\s)",
    re.MULTILINE,
)

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
