"""
Provider-agnostic LLM utility.

Public API
----------
    complete(prompt, system="") -> str

The active provider is chosen by the LLM_PROVIDER environment variable
(default: "stub").  Only the stub provider is implemented now.  Real
providers raise NotImplementedError until they are actually wired up.

Supported values for LLM_PROVIDER
----------------------------------
    stub     — returns deterministic canned text; no network, no API key.
               This is the default and the only value suitable for tests
               and local development before a real provider is configured.
    openai   — not yet implemented (raises NotImplementedError)
    watsonx  — not yet implemented (raises NotImplementedError)
"""

from __future__ import annotations

import os


def complete(prompt: str, system: str = "") -> str:
    """Send a prompt to the configured LLM and return the text response.

    Args:
        prompt: The user-facing prompt text.
        system: Optional system / instruction prompt (ignored by stub).

    Returns:
        A string response from the LLM (or a canned stub string).

    Raises:
        NotImplementedError: When LLM_PROVIDER is "openai" or "watsonx"
                             (these providers are not yet implemented).
        ValueError:          When LLM_PROVIDER is set to an unknown value.
    """
    provider = os.environ.get("LLM_PROVIDER", "stub").lower().strip()

    if provider == "stub":
        return _stub_complete(prompt, system)

    if provider == "openai":
        # TODO: implement when OpenAI provider is chosen
        # Required env vars: OPENAI_API_KEY, OPENAI_MODEL
        raise NotImplementedError(
            "OpenAI provider is not yet implemented. "
            "Set LLM_PROVIDER=stub for local development and tests."
        )

    if provider == "watsonx":
        # TODO: implement when WatsonX provider is chosen
        # Required env vars: WATSONX_API_KEY, WATSONX_PROJECT_ID,
        #                    WATSONX_MODEL_ID, WATSONX_URL
        raise NotImplementedError(
            "WatsonX provider is not yet implemented. "
            "Set LLM_PROVIDER=stub for local development and tests."
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER: '{provider}'. "
        "Supported values: stub, openai, watsonx."
    )


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------

def _stub_complete(prompt: str, system: str) -> str:  # noqa: ARG001
    """Return deterministic canned text without any network call."""
    preview = prompt[:80].replace("\n", " ")
    return f"[stub-llm] Response for: {preview}"
