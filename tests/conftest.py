"""
Pytest configuration for DevDocs AI tests.

Ensures the repository root is available for app.* imports and
forces the LLM provider to stub during tests.
"""

import os
import sys
from pathlib import Path

import pytest

# Repository root = tests/../
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


@pytest.fixture(scope="session", autouse=True)
def force_stub_llm_provider():
    """Force all tests to use the stub LLM provider."""
    previous = os.environ.get("LLM_PROVIDER")
    os.environ["LLM_PROVIDER"] = "stub"

    yield

    if previous is None:
        os.environ.pop("LLM_PROVIDER", None)
    else:
        os.environ["LLM_PROVIDER"] = previous