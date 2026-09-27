"""
Tests for app/agents/readme_agent.py.

All tests use only the standard library (no network, no LLM calls).
LLM_PROVIDER=stub is enforced by tests/conftest.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.agents.readme_agent import (
    _build_api_table,
    _detect_endpoints,
    _detect_version,
    _find_readme,
    _scan_endpoints_from_tree,
    _try_fastapi_decorator,
    _update_readme,
    _update_version_in_readme,
    run,
)
from app.models import AgentContext, AgentResult

import ast


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_FASTAPI_SOURCE_V1 = """\
from fastapi import FastAPI
from pydantic import BaseModel

__version__ = "1.0.0"

app = FastAPI(title="Test API", version=__version__)

@app.get("/items")
def list_items():
    \"\"\"Return all items.\"\"\"
    return []

@app.post("/items")
def create_item():
    \"\"\"Create a new item.\"\"\"
    pass
"""

_FASTAPI_SOURCE_V2 = """\
from fastapi import FastAPI, HTTPException

__version__ = "2.0.0"

app = FastAPI(title="Sample API", version=__version__)

@app.get("/items")
def list_items():
    \"\"\"Return all items.\"\"\"
    return []

@app.post("/items")
def create_item():
    \"\"\"Create a new item.\"\"\"
    pass

@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    \"\"\"Delete an item by id.\"\"\"
    pass
"""

_README_TEMPLATE = """\
# Test App

## Installation

```bash
pip install test-app
```

## API Reference

| Method | Path   | Description    |
|--------|--------|----------------|
| GET    | /items | List all items |
| POST   | /items | Create an item |
"""

_README_NO_API_REF = """\
# Test App

## Installation

```bash
pip install test-app
```

## Usage

Start the server.
"""


# ---------------------------------------------------------------------------
# Unit tests: _find_readme
# ---------------------------------------------------------------------------

class TestFindReadme:
    def test_finds_readme_md(self, tmp_path: Path):
        (tmp_path / "README.md").write_text("# Hi")
        assert _find_readme(tmp_path) == tmp_path / "README.md"

    def test_finds_lowercase_readme(self, tmp_path: Path):
        (tmp_path / "readme.md").write_text("# Hi")
        assert _find_readme(tmp_path) == tmp_path / "readme.md"

    def test_returns_none_when_missing(self, tmp_path: Path):
        assert _find_readme(tmp_path) is None

    def test_prefers_readme_md_over_readme_lowercase(self, tmp_path: Path):
        """README.md (capitalised) takes precedence over readme.md."""
        (tmp_path / "README.md").write_text("# Upper")
        (tmp_path / "readme.md").write_text("# Lower")
        assert _find_readme(tmp_path) == tmp_path / "README.md"


# ---------------------------------------------------------------------------
# Unit tests: _detect_version
# ---------------------------------------------------------------------------

class TestDetectVersion:
    def test_detects_dunder_version(self, tmp_path: Path):
        (tmp_path / "main.py").write_text('__version__ = "1.2.3"')
        result = _detect_version([tmp_path / "main.py"])
        assert result == "1.2.3"

    def test_prioritises_main_py(self, tmp_path: Path):
        (tmp_path / "helper.py").write_text('__version__ = "0.0.1"')
        (tmp_path / "main.py").write_text('__version__ = "2.0.0"')
        result = _detect_version([tmp_path / "helper.py", tmp_path / "main.py"])
        assert result == "2.0.0"

    def test_returns_none_when_no_version(self, tmp_path: Path):
        (tmp_path / "main.py").write_text("# no version here")
        result = _detect_version([tmp_path / "main.py"])
        assert result is None

    def test_single_quotes_version(self, tmp_path: Path):
        (tmp_path / "main.py").write_text("__version__ = '3.1.4'")
        result = _detect_version([tmp_path / "main.py"])
        assert result == "3.1.4"

    def test_detects_from_fastapi_constructor_when_no_dunder(self, tmp_path: Path):
        source = 'from fastapi import FastAPI\napp = FastAPI(title="X", version="4.5.6")\n'
        (tmp_path / "main.py").write_text(source)
        result = _detect_version([tmp_path / "main.py"])
        assert result == "4.5.6"


# ---------------------------------------------------------------------------
# Unit tests: _detect_endpoints
# ---------------------------------------------------------------------------

class TestDetectEndpoints:
    def test_detects_get_and_post(self, tmp_path: Path):
        (tmp_path / "main.py").write_text(_FASTAPI_SOURCE_V1)
        result = _detect_endpoints([tmp_path / "main.py"])
        methods = {ep["method"] for ep in result}
        paths = {ep["path"] for ep in result}
        assert methods == {"GET", "POST"}
        assert "/items" in paths

    def test_detects_delete_in_v2(self, tmp_path: Path):
        (tmp_path / "main.py").write_text(_FASTAPI_SOURCE_V2)
        result = _detect_endpoints([tmp_path / "main.py"])
        methods = {ep["method"] for ep in result}
        assert "DELETE" in methods

    def test_no_duplicates_across_files(self, tmp_path: Path):
        (tmp_path / "main.py").write_text(_FASTAPI_SOURCE_V1)
        (tmp_path / "other.py").write_text(_FASTAPI_SOURCE_V1)
        result = _detect_endpoints([tmp_path / "main.py", tmp_path / "other.py"])
        keys = [(ep["method"], ep["path"]) for ep in result]
        assert len(keys) == len(set(keys))

    def test_empty_list_on_no_python_files(self):
        result = _detect_endpoints([])
        assert result == []

    def test_endpoint_has_description(self, tmp_path: Path):
        (tmp_path / "main.py").write_text(_FASTAPI_SOURCE_V1)
        result = _detect_endpoints([tmp_path / "main.py"])
        descriptions = [ep["description"] for ep in result]
        assert any(d for d in descriptions)

    def test_endpoint_description_from_summary_kwarg(self, tmp_path: Path):
        source = """\
from fastapi import FastAPI
app = FastAPI()

@app.get("/ping", summary="Health ping")
def ping():
    pass
"""
        (tmp_path / "main.py").write_text(source)
        result = _detect_endpoints([tmp_path / "main.py"])
        assert result[0]["description"] == "Health ping"


# ---------------------------------------------------------------------------
# Unit tests: _build_api_table
# ---------------------------------------------------------------------------

class TestBuildApiTable:
    def test_returns_markdown_table_header(self):
        endpoints = [{"method": "GET", "path": "/items", "description": "List"}]
        table = _build_api_table(endpoints)
        assert "Method" in table
        assert "Path" in table
        assert "Description" in table

    def test_includes_all_endpoints(self):
        endpoints = [
            {"method": "GET", "path": "/items", "description": "List"},
            {"method": "POST", "path": "/items", "description": "Create"},
            {"method": "DELETE", "path": "/items/{id}", "description": "Delete"},
        ]
        table = _build_api_table(endpoints)
        assert "DELETE" in table
        assert "/items/{id}" in table

    def test_returns_placeholder_for_empty_endpoints(self):
        table = _build_api_table([])
        assert "No API endpoints" in table

    def test_separator_row_present(self):
        endpoints = [{"method": "GET", "path": "/x", "description": ""}]
        table = _build_api_table(endpoints)
        lines = table.splitlines()
        # Second line should be the separator row (dashes)
        assert any("---" in line for line in lines)


# ---------------------------------------------------------------------------
# Unit tests: _update_readme
# ---------------------------------------------------------------------------

class TestUpdateReadme:
    def test_replaces_existing_api_ref_section(self):
        endpoints = [
            {"method": "GET", "path": "/items", "description": "List"},
            {"method": "DELETE", "path": "/items/{id}", "description": "Delete"},
        ]
        result = _update_readme(_README_TEMPLATE, "1.0.0", endpoints)
        assert "DELETE" in result
        assert "/items/{id}" in result

    def test_appends_api_ref_section_when_missing(self):
        endpoints = [{"method": "GET", "path": "/ping", "description": "Ping"}]
        result = _update_readme(_README_NO_API_REF, None, endpoints)
        assert "## API Reference" in result
        assert "/ping" in result

    def test_does_not_duplicate_heading(self):
        endpoints = [{"method": "GET", "path": "/x", "description": ""}]
        result = _update_readme(_README_TEMPLATE, None, endpoints)
        assert result.count("## API Reference") == 1

    def test_updates_version_badge(self):
        readme = "# App\n\n![version](https://img.shields.io/badge/version-1.0.0-blue)\n"
        endpoints: list = []
        result = _update_readme(readme, "2.5.0", endpoints)
        assert "version-2.5.0-blue" in result

    def test_no_version_update_when_version_none(self):
        readme = "# App\n\nVersion: 1.0.0\n\n## API Reference\n\n_nothing_\n"
        endpoints: list = []
        result = _update_readme(readme, None, endpoints)
        assert "Version: 1.0.0" in result


# ---------------------------------------------------------------------------
# Unit tests: _update_version_in_readme
# ---------------------------------------------------------------------------

class TestUpdateVersionInReadme:
    def test_updates_badge_style(self):
        content = "version-1.0.0-blue"
        assert "version-2.0.0-blue" in _update_version_in_readme(content, "2.0.0")

    def test_updates_version_colon_line(self):
        content = "Version: 1.0.0"
        assert "Version: 2.0.0" in _update_version_in_readme(content, "2.0.0")

    def test_updates_bold_version(self):
        content = "**Version** 1.0.0"
        assert "**Version** 2.0.0" in _update_version_in_readme(content, "2.0.0")

    def test_no_change_when_already_current(self):
        content = "Version: 3.0.0"
        assert _update_version_in_readme(content, "3.0.0") == content


# ---------------------------------------------------------------------------
# Integration tests: run() with AgentContext
# ---------------------------------------------------------------------------

class TestRunIntegration:
    def _make_context(self, repo_path: str) -> AgentContext:
        return AgentContext(repo_path=repo_path, changed_files=[], git_diff="", config={})

    def test_success_with_fastapi_v2_fixture(self, tmp_path: Path):
        """Agent processes the v2 fixture and returns success."""
        fixture_src = Path(__file__).parent / "fixtures" / "sample_fastapi_app_v2"
        import shutil
        repo = tmp_path / "sample_fastapi_app_v2"
        shutil.copytree(fixture_src, repo)

        ctx = self._make_context(str(repo))
        result = run(ctx)

        assert isinstance(result, AgentResult)
        assert result.agent_name == "readme_agent"
        assert result.status == "success"

    def test_v2_fixture_readme_contains_delete_endpoint(self, tmp_path: Path):
        """After agent runs, README.md should include the DELETE endpoint."""
        fixture_src = Path(__file__).parent / "fixtures" / "sample_fastapi_app_v2"
        import shutil
        repo = tmp_path / "sample_fastapi_app_v2"
        shutil.copytree(fixture_src, repo)

        ctx = self._make_context(str(repo))
        run(ctx)

        readme = (repo / "README.md").read_text(encoding="utf-8")
        assert "DELETE" in readme

    def test_v2_fixture_readme_contains_updated_version(self, tmp_path: Path):
        """After agent runs, README.md should reflect the 2.0.0 version."""
        fixture_src = Path(__file__).parent / "fixtures" / "sample_fastapi_app_v2"
        import shutil
        repo = tmp_path / "sample_fastapi_app_v2"
        shutil.copytree(fixture_src, repo)

        ctx = self._make_context(str(repo))
        result = run(ctx)

        assert result.raw_output.get("version") == "2.0.0"

    def test_output_files_listed_when_changed(self, tmp_path: Path):
        """When README is updated, its path appears in output_files."""
        (tmp_path / "main.py").write_text(
            '__version__ = "9.9.9"\nfrom fastapi import FastAPI\n'
            'app = FastAPI()\n\n@app.get("/ping")\ndef ping():\n    """Ping."""\n    pass\n'
        )
        (tmp_path / "README.md").write_text("# App\n\n## API Reference\n\nold content\n")

        ctx = self._make_context(str(tmp_path))
        result = run(ctx)

        assert result.status == "success"
        assert any("README" in f for f in result.output_files)

    def test_no_readme_returns_warning(self, tmp_path: Path):
        (tmp_path / "main.py").write_text('__version__ = "1.0.0"')
        ctx = self._make_context(str(tmp_path))
        result = run(ctx)
        assert result.status == "warning"
        assert result.agent_name == "readme_agent"

    def test_no_python_files_returns_warning(self, tmp_path: Path):
        (tmp_path / "README.md").write_text("# App")
        ctx = self._make_context(str(tmp_path))
        result = run(ctx)
        assert result.status == "warning"

    def test_no_change_when_readme_already_current(self, tmp_path: Path):
        """When README already has the correct content, output_files is empty."""
        # Build the exact same content the agent would produce
        source = (
            'from fastapi import FastAPI\n'
            '__version__ = "1.0.0"\n'
            'app = FastAPI()\n\n'
            '@app.get("/ping")\n'
            'def ping():\n'
            '    """Ping."""\n'
            '    pass\n'
        )
        (tmp_path / "main.py").write_text(source)

        ctx_build = self._make_context(str(tmp_path))
        # First run: generates and writes updated README
        (tmp_path / "README.md").write_text("# App\n\n## API Reference\n\nold\n")
        first_result = run(ctx_build)
        assert first_result.status == "success"

        # Second run: README is already up-to-date
        second_result = run(ctx_build)
        assert second_result.status == "success"
        assert second_result.output_files == []

    def test_result_raw_output_contains_endpoints(self, tmp_path: Path):
        (tmp_path / "main.py").write_text(
            'from fastapi import FastAPI\napp = FastAPI()\n\n'
            '@app.get("/items")\ndef get(): pass\n'
        )
        (tmp_path / "README.md").write_text("# App\n")

        ctx = self._make_context(str(tmp_path))
        result = run(ctx)
        assert "endpoints" in result.raw_output
        endpoints = result.raw_output["endpoints"]
        assert isinstance(endpoints, list)
        assert any(ep["path"] == "/items" for ep in endpoints)
