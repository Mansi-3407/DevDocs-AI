"""
Tests for app.agents.example_validator — Person 2 implementation.

Covers:
  - extract_code_blocks()  (fenced block extraction)
  - validate_examples()    (per-language validation)
  - auto_fix_examples()    (safe deterministic fixes)
  - run()                  (team-standard result envelope)
"""

import pytest

from app.agents.example_validator import ExampleValidator


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def ev() -> ExampleValidator:
    return ExampleValidator()


# ---------------------------------------------------------------------------
# Inline Markdown helpers (no files on disk)
# ---------------------------------------------------------------------------

VALID_PYTHON_MD = '```python\nname = "Arin"\nprint(name)\n```'
INVALID_PYTHON_MD = '```python\ndef hello(\n    print("x")\n```'
VALID_JSON_MD = '```json\n{"name": "Arin", "age": 19}\n```'
INVALID_JSON_MD = '```json\n{"name": "Arin",}\n```'
BASH_MD = '```bash\necho "hello"\n```'
EMPTY_BASH_MD = '```bash\n   \n```'

MULTI_MD = (
    "Some docs.\n\n"
    "```python\nx = 1 + 2\n```\n\n"
    '```json\n{"ok": true}\n```\n\n'
    "```bash\nls -la\n```\n\n"
    '```js\nconsole.log("hi")\n```'
)

ALIASES_MD = (
    "```py\nx = 1\n```\n\n"
    "```sh\necho test\n```\n\n"
    "```shell\necho test2\n```"
)

NO_LANG_MD = "```\nsome plain text\n```"

CRLF_MD = "line one\r\n```python\r\nprint(\"hi\")   \r\n```\r\nline two  \r\n"
TRAILING_WS_MD = "# Title\n\n```python\nx = 1  \ny = 2   \n```\n"
UNCLOSED_FENCE_MD = "# Title\n```python\nprint(\"hi\")\n"
CLEAN_MD = "# Title\n\n```python\nx = 1\n```\n"

MIXED_VALID_INVALID_MD = (
    "```python\nx = 1\n```\n\n"
    "```json\n{bad json}\n```"
)


# ===========================================================================
# 1.  extract_code_blocks
# ===========================================================================

class TestExtractCodeBlocks:

    def test_single_python_block_extracted(self, ev):
        blocks = ev.extract_code_blocks(VALID_PYTHON_MD)
        assert len(blocks) == 1
        assert blocks[0]["language"] == "python"

    def test_block_code_content(self, ev):
        blocks = ev.extract_code_blocks(VALID_PYTHON_MD)
        assert 'name = "Arin"' in blocks[0]["code"]
        assert "print(name)" in blocks[0]["code"]

    def test_block_has_start_line(self, ev):
        blocks = ev.extract_code_blocks(VALID_PYTHON_MD)
        assert isinstance(blocks[0]["start_line"], int)
        assert blocks[0]["start_line"] >= 1

    def test_block_has_end_line(self, ev):
        blocks = ev.extract_code_blocks(VALID_PYTHON_MD)
        assert isinstance(blocks[0]["end_line"], int)
        assert blocks[0]["end_line"] > blocks[0]["start_line"]

    def test_multi_block_extraction(self, ev):
        blocks = ev.extract_code_blocks(MULTI_MD)
        assert len(blocks) == 4

    def test_multi_block_languages(self, ev):
        langs = [b["language"] for b in ev.extract_code_blocks(MULTI_MD)]
        assert "python" in langs
        assert "json" in langs
        assert "bash" in langs

    def test_no_lang_tag_becomes_text(self, ev):
        blocks = ev.extract_code_blocks(NO_LANG_MD)
        assert blocks[0]["language"] == "text"

    # --- language aliases ---

    def test_alias_py_becomes_python(self, ev):
        langs = [b["language"] for b in ev.extract_code_blocks(ALIASES_MD)]
        assert langs[0] == "python"

    def test_alias_sh_becomes_bash(self, ev):
        langs = [b["language"] for b in ev.extract_code_blocks(ALIASES_MD)]
        assert langs[1] == "bash"

    def test_alias_shell_becomes_bash(self, ev):
        langs = [b["language"] for b in ev.extract_code_blocks(ALIASES_MD)]
        assert langs[2] == "bash"

    def test_alias_js_becomes_javascript(self, ev):
        langs = [b["language"] for b in ev.extract_code_blocks(MULTI_MD)]
        assert "javascript" in langs

    def test_empty_markdown_returns_empty_list(self, ev):
        assert ev.extract_code_blocks("") == []

    def test_no_code_blocks_returns_empty_list(self, ev):
        assert ev.extract_code_blocks("# Heading\n\nJust prose.") == []


# ===========================================================================
# 2.  validate_examples — Python
# ===========================================================================

class TestValidatePython:

    def test_valid_python_is_valid(self, ev):
        results = ev.validate_examples(VALID_PYTHON_MD)
        assert results[0]["valid"] is True

    def test_valid_python_is_supported(self, ev):
        results = ev.validate_examples(VALID_PYTHON_MD)
        assert results[0]["supported"] is True

    def test_valid_python_no_line_number(self, ev):
        results = ev.validate_examples(VALID_PYTHON_MD)
        assert results[0]["line"] is None

    def test_invalid_python_is_invalid(self, ev):
        results = ev.validate_examples(INVALID_PYTHON_MD)
        assert results[0]["valid"] is False

    def test_invalid_python_is_supported(self, ev):
        results = ev.validate_examples(INVALID_PYTHON_MD)
        assert results[0]["supported"] is True

    def test_invalid_python_has_message(self, ev):
        results = ev.validate_examples(INVALID_PYTHON_MD)
        assert results[0]["message"]

    def test_invalid_python_has_line_number(self, ev):
        results = ev.validate_examples(INVALID_PYTHON_MD)
        assert results[0]["line"] is not None
        assert isinstance(results[0]["line"], int)

    def test_invalid_python_message_mentions_error(self, ev):
        results = ev.validate_examples(INVALID_PYTHON_MD)
        assert "SyntaxError" in results[0]["message"] or "syntax" in results[0]["message"].lower()


# ===========================================================================
# 3.  validate_examples — JSON
# ===========================================================================

class TestValidateJSON:

    def test_valid_json_is_valid(self, ev):
        results = ev.validate_examples(VALID_JSON_MD)
        assert results[0]["valid"] is True

    def test_valid_json_is_supported(self, ev):
        results = ev.validate_examples(VALID_JSON_MD)
        assert results[0]["supported"] is True

    def test_valid_json_language(self, ev):
        results = ev.validate_examples(VALID_JSON_MD)
        assert results[0]["language"] == "json"

    def test_invalid_json_is_invalid(self, ev):
        results = ev.validate_examples(INVALID_JSON_MD)
        assert results[0]["valid"] is False

    def test_invalid_json_is_supported(self, ev):
        results = ev.validate_examples(INVALID_JSON_MD)
        assert results[0]["supported"] is True

    def test_invalid_json_has_message(self, ev):
        results = ev.validate_examples(INVALID_JSON_MD)
        assert results[0]["message"]

    def test_invalid_json_message_mentions_error(self, ev):
        results = ev.validate_examples(INVALID_JSON_MD)
        assert "JSON" in results[0]["message"] or "json" in results[0]["message"].lower()


# ===========================================================================
# 4.  validate_examples — Bash
# ===========================================================================

class TestValidateBash:

    def test_bash_block_is_valid(self, ev):
        results = ev.validate_examples(BASH_MD)
        assert results[0]["valid"] is True

    def test_bash_block_is_supported(self, ev):
        results = ev.validate_examples(BASH_MD)
        assert results[0]["supported"] is True

    def test_bash_language_tag(self, ev):
        results = ev.validate_examples(BASH_MD)
        assert results[0]["language"] == "bash"

    def test_bash_message_does_not_claim_executed(self, ev):
        """Bash validator must not claim the code was executed."""
        results = ev.validate_examples(BASH_MD)
        msg = results[0]["message"].lower()
        assert "execut" not in msg or "not" in msg

    def test_empty_bash_is_invalid(self, ev):
        results = ev.validate_examples(EMPTY_BASH_MD)
        assert results[0]["valid"] is False


# ===========================================================================
# 5.  validate_examples — unsupported / text
# ===========================================================================

class TestValidateUnsupported:

    def test_text_block_supported_false(self, ev):
        results = ev.validate_examples(NO_LANG_MD)
        assert results[0]["supported"] is False

    def test_text_block_valid_true(self, ev):
        """Unsupported language should not be marked invalid."""
        results = ev.validate_examples(NO_LANG_MD)
        assert results[0]["valid"] is True

    def test_javascript_supported_false(self, ev):
        js_md = '```js\nconsole.log("hi")\n```'
        results = ev.validate_examples(js_md)
        assert results[0]["supported"] is False

    def test_javascript_valid_true(self, ev):
        js_md = '```js\nconsole.log("hi")\n```'
        results = ev.validate_examples(js_md)
        assert results[0]["valid"] is True


# ===========================================================================
# 6.  validate_examples — multiple blocks
# ===========================================================================

class TestMultipleBlocks:

    def test_multi_returns_four_results(self, ev):
        assert len(ev.validate_examples(MULTI_MD)) == 4

    def test_all_multi_results_valid(self, ev):
        for r in ev.validate_examples(MULTI_MD):
            assert r["valid"] is True

    def test_result_has_language_key(self, ev):
        for r in ev.validate_examples(MULTI_MD):
            assert "language" in r

    def test_result_has_code_key(self, ev):
        for r in ev.validate_examples(MULTI_MD):
            assert "code" in r

    def test_result_has_start_line_key(self, ev):
        for r in ev.validate_examples(MULTI_MD):
            assert "start_line" in r

    def test_result_has_end_line_key(self, ev):
        for r in ev.validate_examples(MULTI_MD):
            assert "end_line" in r


# ===========================================================================
# 7.  auto_fix_examples
# ===========================================================================

class TestAutoFix:

    def test_crlf_normalised_to_lf(self, ev):
        fixed = ev.auto_fix_examples(CRLF_MD)
        assert "\r\n" not in fixed

    def test_bare_cr_normalised(self, ev):
        fixed = ev.auto_fix_examples("line\rend\r")
        assert "\r" not in fixed

    def test_trailing_whitespace_stripped(self, ev):
        fixed = ev.auto_fix_examples(TRAILING_WS_MD)
        for line in fixed.split("\n"):
            assert line == line.rstrip(), f"Trailing whitespace on: {line!r}"

    def test_code_content_preserved_after_fix(self, ev):
        fixed = ev.auto_fix_examples(CRLF_MD)
        assert "print" in fixed

    def test_unclosed_fence_gets_closing_fence(self, ev):
        fixed = ev.auto_fix_examples(UNCLOSED_FENCE_MD)
        stripped_lines = [l.strip() for l in fixed.split("\n") if l.strip()]
        assert "```" in stripped_lines[-1]

    def test_clean_document_unchanged(self, ev):
        fixed = ev.auto_fix_examples(CLEAN_MD)
        assert fixed == CLEAN_MD

    def test_autofix_returns_string(self, ev):
        assert isinstance(ev.auto_fix_examples(CLEAN_MD), str)


# ===========================================================================
# 8.  run() — team-standard result envelope
# ===========================================================================

class TestRun:

    def test_agent_name(self, ev):
        result = ev.run(VALID_PYTHON_MD)
        assert result["agent"] == "example_validator"

    def test_status_success_for_valid(self, ev):
        result = ev.run(VALID_PYTHON_MD)
        assert result["status"] == "success"

    def test_status_success_for_invalid_code(self, ev):
        """Validation failures should not set status=error on the envelope."""
        result = ev.run(INVALID_PYTHON_MD)
        assert result["status"] == "success"

    def test_output_is_list(self, ev):
        result = ev.run(VALID_PYTHON_MD)
        assert isinstance(result["output"], list)

    def test_output_length_matches_blocks(self, ev):
        result = ev.run(MULTI_MD)
        assert len(result["output"]) == 4

    def test_no_errors_on_success(self, ev):
        result = ev.run(VALID_PYTHON_MD)
        assert result["errors"] == []

    def test_non_string_input_returns_error_status(self, ev):
        result = ev.run(12345)  # type: ignore[arg-type]
        assert result["status"] == "error"

    def test_non_string_input_error_message(self, ev):
        result = ev.run(None)  # type: ignore[arg-type]
        assert result["errors"]
        assert "string" in result["errors"][0].lower()

    def test_none_input_returns_error_status(self, ev):
        result = ev.run(None)  # type: ignore[arg-type]
        assert result["status"] == "error"

    def test_warnings_present_for_invalid_blocks(self, ev):
        result = ev.run(MIXED_VALID_INVALID_MD)
        assert result["warnings"]

    def test_warnings_reference_invalid_language(self, ev):
        result = ev.run(MIXED_VALID_INVALID_MD)
        warning_text = " ".join(result["warnings"]).lower()
        assert "json" in warning_text

    def test_warnings_not_generated_for_valid_blocks(self, ev):
        result = ev.run(VALID_PYTHON_MD)
        assert result["warnings"] == []

    def test_run_on_empty_string(self, ev):
        result = ev.run("")
        assert result["status"] == "success"
        assert result["output"] == []

    def test_run_on_prose_only(self, ev):
        result = ev.run("# Title\n\nNo code blocks here.")
        assert result["status"] == "success"
        assert result["output"] == []
