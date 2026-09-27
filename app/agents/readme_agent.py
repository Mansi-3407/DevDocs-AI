"""
README Auto-Updater Agent.

Scans the repository for:
  * A Python source file containing a FastAPI/Flask app with route decorators
    and an optional ``__version__`` assignment.
  * An existing ``README.md`` (or ``readme.md``) at the repository root.

Then:
  1. Detects API endpoints via AST (same technique as api_agent, no import/exec).
  2. Detects the project version from ``__version__`` in Python source files or
     from the FastAPI constructor keyword.
  3. Re-generates the ``## API Reference`` section as a markdown table.
  4. Updates any version badge / inline version string near the top of the README
     that differs from the detected version.
  5. Writes the updated README back to disk.

Public interface (matches the required agent contract):

    def run(context: AgentContext) -> AgentResult
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from app.models import AgentContext, AgentResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AGENT_NAME = "readme_agent"

# Regex for __version__ = "x.y.z"
_PY_VERSION_RE = re.compile(r'__version__\s*=\s*["\']([^"\']+)["\']')

# FastAPI single-method decorator names -> HTTP method (mirrors api_agent)
_FASTAPI_METHODS: dict[str, str] = {
    "get": "GET",
    "post": "POST",
    "put": "PUT",
    "patch": "PATCH",
    "delete": "DELETE",
    "options": "OPTIONS",
    "head": "HEAD",
}

# Heading that this agent owns
_API_REF_HEADING = "## API Reference"

# Regex to match the ## API Reference section heading line only (no trailing
# blank lines) and its body, through the next ## section or EOF.
# Group 1: heading line including its terminating newline (horizontal space only).
# Group 2: everything after the heading line until next ## or EOF.
_API_REF_RE = re.compile(
    r"(^## API Reference[ \t]*\n)(.*?)(?=\n## |\Z)",
    re.DOTALL | re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(context: AgentContext) -> AgentResult:
    """Auto-update README.md with detected version and API endpoint table.

    Args:
        context: Shared agent context (repo_path, config, etc.)

    Returns:
        AgentResult with status, summary, and output_files.
    """
    repo = Path(context.repo_path)

    # --- 1. Locate README --------------------------------------------------
    readme_path = _find_readme(repo)
    if readme_path is None:
        return AgentResult(
            agent_name=AGENT_NAME,
            status="warning",
            summary="No README.md found in repository root; nothing to update.",
            output_files=[],
            issues=["missing file: README.md"],
            raw_output={"version": None, "endpoints": []},
        )

    # --- 2. Locate Python source files with route decorators --------------
    py_files = list(repo.rglob("*.py"))
    if not py_files:
        return AgentResult(
            agent_name=AGENT_NAME,
            status="warning",
            summary="No Python source files found; README not updated.",
            output_files=[],
            issues=["no Python files found"],
            raw_output={"version": None, "endpoints": []},
        )

    # --- 3. Detect version and endpoints ----------------------------------
    version = _detect_version(py_files)
    endpoints = _detect_endpoints(py_files)

    # --- 4. Read current README -------------------------------------------
    try:
        original_content = readme_path.read_text(encoding="utf-8")
    except OSError as exc:
        return AgentResult(
            agent_name=AGENT_NAME,
            status="error",
            summary=f"Could not read README: {exc}",
            output_files=[],
            issues=[f"read error: {exc}"],
            raw_output={"version": version, "endpoints": endpoints},
        )

    # --- 5. Build updated content -----------------------------------------
    updated_content = _update_readme(original_content, version, endpoints)

    # --- 6. Write if changed ----------------------------------------------
    if updated_content == original_content:
        return AgentResult(
            agent_name=AGENT_NAME,
            status="success",
            summary="README.md is already up-to-date; no changes needed.",
            output_files=[],
            issues=[],
            raw_output={"version": version, "endpoints": endpoints},
        )

    try:
        readme_path.write_text(updated_content, encoding="utf-8")
    except OSError as exc:
        return AgentResult(
            agent_name=AGENT_NAME,
            status="error",
            summary=f"Could not write README: {exc}",
            output_files=[],
            issues=[f"write error: {exc}"],
            raw_output={"version": version, "endpoints": endpoints},
        )

    n_endpoints = len(endpoints)
    version_str = version or "unknown"
    return AgentResult(
        agent_name=AGENT_NAME,
        status="success",
        summary=(
            f"README.md updated: version={version_str}, "
            f"{n_endpoints} endpoint(s) documented in ## API Reference."
        ),
        output_files=[str(readme_path)],
        issues=[],
        raw_output={"version": version, "endpoints": endpoints},
    )


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------

def _find_readme(repo: Path) -> Path | None:
    """Return the README.md path at the repo root, or None if not found."""
    for name in ("README.md", "readme.md", "Readme.md"):
        candidate = repo / name
        if candidate.is_file():
            return candidate
    return None


def _detect_version(py_files: list[Path]) -> str | None:
    """
    Return the first ``__version__`` string found in any Python file.

    Preference: files named ``main.py`` or ``__init__.py`` are checked first
    so that the canonical application version takes precedence over helper
    modules that might also define a version constant.
    """
    # Prioritise main.py and __init__.py
    priority = [f for f in py_files if f.name in ("main.py", "__init__.py")]
    rest = [f for f in py_files if f not in priority]

    for py_file in priority + rest:
        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = _PY_VERSION_RE.search(text)
        if m:
            return m.group(1)

    # Fallback: check FastAPI constructor version= keyword
    for py_file in priority + rest:
        try:
            source = py_file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(py_file))
        except (OSError, SyntaxError):
            continue
        meta = _extract_app_metadata(tree)
        if meta.get("version"):
            return meta["version"]

    return None


def _detect_endpoints(py_files: list[Path]) -> list[dict[str, Any]]:
    """
    Return a list of endpoint dicts (method, path, description) from all
    Python source files in the repository.

    Each dict has keys: ``method``, ``path``, ``description``.
    """
    endpoints: list[dict[str, Any]] = []
    # Prioritise main.py so its endpoints appear first
    priority = [f for f in py_files if f.name == "main.py"]
    rest = [f for f in py_files if f not in priority]

    for py_file in priority + rest:
        try:
            source = py_file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(py_file))
        except (OSError, SyntaxError):
            continue
        file_endpoints = _scan_endpoints_from_tree(tree)
        for ep in file_endpoints:
            # Avoid duplicates (same method+path from multiple files)
            key = (ep["method"], ep["path"])
            if not any((e["method"], e["path"]) == key for e in endpoints):
                endpoints.append(ep)

    return endpoints


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def _extract_app_metadata(tree: ast.Module) -> dict[str, str]:
    """Extract title/version/description from a FastAPI(...) or Flask(...)
    constructor call in the given AST."""
    metadata: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        value = node.value
        if not isinstance(value, ast.Call):
            continue
        func_node = value.func
        if isinstance(func_node, ast.Name):
            ctor_name = func_node.id
        elif isinstance(func_node, ast.Attribute):
            ctor_name = func_node.attr
        else:
            continue
        if ctor_name not in ("FastAPI", "Flask"):
            continue
        for kw in value.keywords:
            if kw.arg in ("title", "description", "version"):
                val = _extract_static_str(kw.value)
                if val is not None:
                    metadata[kw.arg] = val
        if metadata:
            break
    return metadata


def _extract_static_str(node: ast.expr) -> str | None:
    """Return the string value of a constant string AST node, or None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _scan_endpoints_from_tree(
    tree: ast.Module,
) -> list[dict[str, Any]]:
    """
    Scan an AST module for FastAPI route decorators.

    Returns list of dicts with keys: method, path, description, _lineno.
    """
    endpoints: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            ep = _try_fastapi_decorator(node, dec)
            if ep:
                endpoints.append(ep)
                break  # one route per function

    endpoints.sort(key=lambda e: e.get("_lineno", 0))
    for ep in endpoints:
        ep.pop("_lineno", None)
    return endpoints


def _try_fastapi_decorator(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    dec: ast.expr,
) -> dict[str, Any] | None:
    """
    Return an endpoint dict if *dec* is a FastAPI-style route decorator.
    Returns None otherwise.
    """
    if not (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)):
        return None

    call: ast.Call = dec
    attr: ast.Attribute = call.func  # type: ignore[assignment]
    method_name: str = attr.attr

    http_method = _FASTAPI_METHODS.get(method_name)
    if http_method is None:
        return None

    # First positional argument must be the path string
    if not call.args:
        return None
    path = _extract_static_str(call.args[0])
    if path is None:
        return None

    # Description: prefer decorator summary= kwarg, then function docstring
    description: str = ""
    for kw in call.keywords:
        if kw.arg == "summary":
            val = _extract_static_str(kw.value)
            if val:
                description = val
                break
    if not description:
        docstring = ast.get_docstring(func)
        if docstring:
            # Use only the first line of the docstring
            description = docstring.splitlines()[0].strip()

    return {
        "_lineno": func.lineno,
        "method": http_method,
        "path": path,
        "description": description,
    }


# ---------------------------------------------------------------------------
# README transformation
# ---------------------------------------------------------------------------

def _build_api_table(endpoints: list[dict[str, Any]]) -> str:
    """
    Build a markdown table for the ## API Reference section.

    Returns the table as a string (no trailing newline).
    """
    if not endpoints:
        return "_No API endpoints detected._"

    # Column widths (minimum width = header length)
    method_width = max(len("Method"), *(len(ep["method"]) for ep in endpoints))
    path_width = max(len("Path"), *(len(ep["path"]) for ep in endpoints))
    desc_width = max(
        len("Description"),
        *(len(ep.get("description", "")) for ep in endpoints),
    )

    def _row(method: str, path: str, desc: str) -> str:
        return (
            f"| {method:<{method_width}} "
            f"| {path:<{path_width}} "
            f"| {desc:<{desc_width}} |"
        )

    sep = (
        f"| {'-' * method_width} "
        f"| {'-' * path_width} "
        f"| {'-' * desc_width} |"
    )

    lines = [
        _row("Method", "Path", "Description"),
        sep,
        *(_row(ep["method"], ep["path"], ep.get("description", "")) for ep in endpoints),
    ]
    return "\n".join(lines)


def _update_readme(
    content: str,
    version: str | None,
    endpoints: list[dict[str, Any]],
) -> str:
    """
    Return a new README string with:
      * ## API Reference section replaced by a freshly generated table.
      * Version badge / inline version updated if *version* is detected.

    If no ## API Reference section exists, one is appended at the end.
    """
    updated = content

    # --- Update ## API Reference section ----------------------------------
    new_table = _build_api_table(endpoints)
    new_section_body = f"\n{new_table}\n"

    match = _API_REF_RE.search(updated)
    if match:
        # Replace the body of the existing section, preserving the heading
        heading_part = match.group(1)  # "## API Reference\n"
        start = match.start()
        end = match.end()
        replacement = heading_part + new_section_body
        updated = updated[:start] + replacement + updated[end:]
    else:
        # Append a new section at the end
        if not updated.endswith("\n"):
            updated += "\n"
        updated += f"\n{_API_REF_HEADING}\n{new_section_body}"

    # --- Update version string -------------------------------------------
    if version:
        updated = _update_version_in_readme(updated, version)

    return updated


def _update_version_in_readme(content: str, version: str) -> str:
    """
    Replace version strings in common README patterns with *version*.

    Patterns handled:
      * Inline badge URLs like ``version-1.0.0-...``
      * Version badge text: ``![version](... /v1.0.0 ...)``
      * Explicit ``Version: 1.0.0`` or ``version: 1.0.0`` lines
      * ``__version__ = "x.y.z"`` blocks embedded in README code fences
    """
    # Semver pattern: digits.digits.digits
    _SV = r"\d+\.\d+\.\d+"

    # 1. Badge-style: version-X.Y.Z-color  (shields.io etc.)
    content = re.sub(
        rf"(version-)({_SV})(-[a-zA-Z])",
        lambda m: m.group(1) + version + m.group(3),
        content,
    )

    # 2. Explicit "Version: X.Y.Z" line (case-insensitive)
    content = re.sub(
        rf"(?i)(Version\s*[:=]\s*)({_SV})",
        lambda m: m.group(1) + version,
        content,
    )

    # 3. Markdown heading or bold label: **Version** X.Y.Z
    content = re.sub(
        rf"(\*\*[Vv]ersion\*\*\s+)({_SV})",
        lambda m: m.group(1) + version,
        content,
    )

    return content
