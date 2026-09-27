"""
Example Validator Agent — Markdown code-block extractor and validator.

Extracts fenced code blocks from Markdown text and validates supported
languages using only the Python standard library.  No code is ever executed;
all validation is purely syntactic/structural.

Public interface
----------------
::

    validator = ExampleValidator()

    # Extract all fenced code blocks from a Markdown string.
    blocks = validator.extract_code_blocks(markdown)

    # Validate every extractable block and return results.
    results = validator.validate_examples(markdown)

    # Return a Markdown string with safe deterministic fixes applied.
    fixed = validator.auto_fix_examples(markdown)

    # Run the full pipeline and return the team-standard result envelope.
    result = validator.run(markdown)

Result envelope shape
---------------------
::

    {
        "agent":    "example_validator",
        "status":   "success" | "error",
        "output":   [<validation result dict>, ...],
        "warnings": [<str>, ...],
        "errors":   [<str>, ...]
    }

``status`` is ``"success"`` as long as the pipeline ran — individual
validation failures appear inside ``output``, not as top-level errors.
``status`` is ``"error"`` only for actual processing failures (e.g. wrong
input type).
"""

from __future__ import annotations

import ast
import json
import re
from typing import Any

# ---------------------------------------------------------------------------
# Optional YAML support — import at module load; never fail if absent
# ---------------------------------------------------------------------------
try:
    import yaml as _yaml  # type: ignore[import]
    _YAML_AVAILABLE = True
except ImportError:
    _yaml = None  # type: ignore[assignment]
    _YAML_AVAILABLE = False


# ---------------------------------------------------------------------------
# Language alias normalisation
# ---------------------------------------------------------------------------

_LANG_ALIASES: dict[str, str] = {
    "py":     "python",
    "js":     "javascript",
    "sh":     "bash",
    "shell":  "bash",
}

def _normalise_lang(raw: str) -> str:
    """Lower-case and resolve known language aliases."""
    key = raw.strip().lower()
    return _LANG_ALIASES.get(key, key) if key else "text"


# ---------------------------------------------------------------------------
# Fenced code-block extraction
# ---------------------------------------------------------------------------

# Matches fenced blocks opened with ``` or ~~~, with an optional language tag.
# Group 1 — fence character repeated 3+ times
# Group 2 — language tag (may be empty)
# Group 3 — block body (may contain internal newlines)
_FENCE_RE = re.compile(
    r"^(?P<fence>`{3,}|~{3,})[ \t]*(?P<lang>[^\n`~]*)[ \t]*\n"
    r"(?P<body>.*?)"
    r"^(?P=fence)[ \t]*$",
    re.MULTILINE | re.DOTALL,
)


def _extract_blocks(markdown: str) -> list[dict[str, Any]]:
    """
    Low-level fenced-block extractor.

    Returns a list of dicts with keys: language, code, start_line, end_line.
    Line numbers are 1-based.
    """
    blocks: list[dict[str, Any]] = []

    for match in _FENCE_RE.finditer(markdown):
        lang_raw = match.group("lang") or ""
        language = _normalise_lang(lang_raw)
        body     = match.group("body")
        # Strip exactly one trailing newline that the regex consumed as part
        # of the block body so that ``code`` reflects the user-authored text.
        code = body.rstrip("\n")

        start_char = match.start()
        end_char   = match.end()

        # Convert character offsets to 1-based line numbers
        start_line = markdown[:start_char].count("\n") + 1
        end_line   = markdown[:end_char].count("\n") + 1

        blocks.append({
            "language":   language,
            "code":       code,
            "start_line": start_line,
            "end_line":   end_line,
        })

    return blocks


# ---------------------------------------------------------------------------
# Per-language validators
# ---------------------------------------------------------------------------

def _validate_python(code: str) -> dict[str, Any]:
    """Validate Python syntax using ast.parse().  Code is never executed."""
    try:
        ast.parse(code)
        return {
            "valid":     True,
            "supported": True,
            "message":   "Valid Python syntax",
            "line":      None,
        }
    except SyntaxError as exc:
        return {
            "valid":     False,
            "supported": True,
            "message":   f"SyntaxError: {exc.msg}",
            "line":      exc.lineno,
        }


def _validate_json(code: str) -> dict[str, Any]:
    """Validate JSON using json.loads()."""
    try:
        json.loads(code)
        return {
            "valid":     True,
            "supported": True,
            "message":   "Valid JSON",
            "line":      None,
        }
    except json.JSONDecodeError as exc:
        return {
            "valid":     False,
            "supported": True,
            "message":   f"JSONDecodeError: {exc.msg} (line {exc.lineno}, col {exc.colno})",
            "line":      exc.lineno,
        }


def _validate_yaml(code: str) -> dict[str, Any]:
    """Validate YAML if PyYAML is available; otherwise report unsupported."""
    if not _YAML_AVAILABLE:
        return {
            "valid":     True,
            "supported": False,
            "message":   "YAML validation not supported (PyYAML not installed)",
            "line":      None,
        }
    try:
        _yaml.safe_load(code)
        return {
            "valid":     True,
            "supported": True,
            "message":   "Valid YAML",
            "line":      None,
        }
    except _yaml.YAMLError as exc:
        line: int | None = None
        if hasattr(exc, "problem_mark") and exc.problem_mark is not None:
            line = exc.problem_mark.line + 1  # 1-based
        return {
            "valid":     False,
            "supported": True,
            "message":   f"YAMLError: {exc}",
            "line":      line,
        }


def _validate_bash(code: str) -> dict[str, Any]:
    """
    Perform safe, non-executing Bash validation.

    Only checks that the block is non-empty.  Commands are never run.
    """
    stripped = code.strip()
    if not stripped:
        return {
            "valid":     False,
            "supported": True,
            "message":   "Bash block is empty",
            "line":      None,
        }
    return {
        "valid":     True,
        "supported": True,
        "message":   "Bash block is non-empty (not executed)",
        "line":      None,
    }


def _validate_unsupported(language: str) -> dict[str, Any]:
    """Return a neutral result for languages with no validator."""
    return {
        "valid":     True,
        "supported": False,
        "message":   f"Validation not supported for language: {language}",
        "line":      None,
    }


# Map language → validator callable
_VALIDATORS: dict[str, Any] = {
    "python":     _validate_python,
    "json":       _validate_json,
    "yaml":       _validate_yaml,
    "bash":       _validate_bash,
}


# ---------------------------------------------------------------------------
# Safe auto-fix helpers
# ---------------------------------------------------------------------------

def _fix_line_endings(text: str) -> str:
    """Normalise CRLF and bare CR to LF."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _fix_trailing_whitespace(text: str) -> str:
    """Strip trailing whitespace from every line while preserving structure."""
    return "\n".join(line.rstrip() for line in text.split("\n"))


def _fix_unclosed_fences(text: str) -> str:
    """
    Append a closing fence for any block that was opened but never closed.

    Only acts on blocks that use the triple-backtick style and are
    genuinely unclosed (i.e. the file ends without a closing fence).
    This is safe because we only append — we never mutate existing text.
    """
    lines       = text.split("\n")
    fence_open  = re.compile(r"^(`{3,}|~{3,})[ \t]*\S*")
    open_fence: str | None = None

    for line in lines:
        m = fence_open.match(line)
        if m:
            fence_char = m.group(1)
            if open_fence is None:
                open_fence = fence_char  # opening a block
            elif open_fence == fence_char:
                open_fence = None        # closing the block

    if open_fence is not None:
        # Unclosed block — append a matching closing fence
        text = text.rstrip("\n") + "\n" + open_fence + "\n"

    return text


# ---------------------------------------------------------------------------
# ExampleValidator
# ---------------------------------------------------------------------------

class ExampleValidator:
    """
    Extracts fenced code blocks from Markdown and validates supported languages.

    All operations are read-only and safe:
    * No code is executed.
    * No files are modified.
    * No network requests are made.
    * eval() is never used.
    """

    # ------------------------------------------------------------------
    # Public: extract_code_blocks
    # ------------------------------------------------------------------

    def extract_code_blocks(self, markdown: str) -> list[dict[str, Any]]:
        """
        Extract all fenced code blocks from *markdown*.

        Returns a list of dicts with keys:
        ``language``, ``code``, ``start_line``, ``end_line``.

        Supports both backtick (```) and tilde (~~~) fences, with optional
        language tags.  Common aliases are normalised (py→python, sh→bash …).
        """
        return _extract_blocks(markdown)

    # ------------------------------------------------------------------
    # Public: validate_examples
    # ------------------------------------------------------------------

    def validate_examples(self, markdown: str) -> list[dict[str, Any]]:
        """
        Extract and validate every fenced code block in *markdown*.

        Returns a list of dicts combining block metadata with validation
        result keys: ``valid``, ``supported``, ``message``, ``line``.
        """
        blocks  = _extract_blocks(markdown)
        results = []

        for block in blocks:
            lang      = block["language"]
            code      = block["code"]
            validator = _VALIDATORS.get(lang)

            if validator is not None:
                verdict = validator(code)
            else:
                verdict = _validate_unsupported(lang)

            result: dict[str, Any] = {
                "language":   lang,
                "code":       code,
                "start_line": block["start_line"],
                "end_line":   block["end_line"],
                **verdict,
            }
            results.append(result)

        return results

    # ------------------------------------------------------------------
    # Public: auto_fix_examples
    # ------------------------------------------------------------------

    def auto_fix_examples(self, markdown: str) -> str:
        """
        Apply safe, deterministic fixes to *markdown* and return the result.

        Fixes applied (in order):
        1. Normalise line endings (CRLF / bare CR → LF).
        2. Strip trailing whitespace from every line.
        3. Append a closing fence if a fenced block is left unclosed.

        No code logic is rewritten; only whitespace and structural issues
        are addressed.  If no changes are needed, the original string is
        returned unchanged.
        """
        text = _fix_line_endings(markdown)
        text = _fix_trailing_whitespace(text)
        text = _fix_unclosed_fences(text)
        return text

    # ------------------------------------------------------------------
    # Public: run — team-standard result envelope
    # ------------------------------------------------------------------

    def run(self, markdown: str) -> dict[str, Any]:
        """
        Run the full extraction + validation pipeline on *markdown*.

        Returns the team-standard envelope::

            {
                "agent":    "example_validator",
                "status":   "success" | "error",
                "output":   [<validation result>, ...],
                "warnings": [...],
                "errors":   [...]
            }

        ``status`` is ``"success"`` whenever the pipeline completes — even
        when individual blocks are invalid.  ``"error"`` is reserved for
        processing failures (wrong input type, etc.).
        """
        if not isinstance(markdown, str):
            return {
                "agent":    "example_validator",
                "status":   "error",
                "output":   [],
                "warnings": [],
                "errors":   ["markdown must be a string"],
            }

        try:
            results  = self.validate_examples(markdown)
            warnings = [
                f"Line {r['start_line']}: {r['language']} block is invalid — {r['message']}"
                for r in results
                if not r["valid"] and r["supported"]
            ]
            return {
                "agent":    "example_validator",
                "status":   "success",
                "output":   results,
                "warnings": warnings,
                "errors":   [],
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "agent":    "example_validator",
                "status":   "error",
                "output":   [],
                "warnings": [],
                "errors":   [f"Unexpected error during validation: {exc}"],
            }
