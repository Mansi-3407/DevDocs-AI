"""
Pytest configuration for DevDocs AI tests.

Session-scoped autouse fixture forces LLM_PROVIDER=stub for every test,
ensuring no test ever makes a real LLM network call.
"""

import os
import pytest


@pytest.fixture(autouse=True, scope="session")
def force_stub_llm():
    """Set LLM_PROVIDER=stub for the entire test session."""
    original = os.environ.get("LLM_PROVIDER")
    os.environ["LLM_PROVIDER"] = "stub"
    yield
    # Restore original value after the session
    if original is None:
        os.environ.pop("LLM_PROVIDER", None)
    else:
        os.environ["LLM_PROVIDER"] = original
