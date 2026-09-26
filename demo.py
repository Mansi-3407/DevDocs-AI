"""
DevDocs AI -- Hackathon Demo Script

Demonstrates the full pipeline against the sample_fastapi_app_v2 fixture,
which contains intentional documentation gaps:

  * __version__ = "2.0.0" but README/CHANGELOG still say v1.0.0
    -> version mismatch detected by audit_agent
  * DELETE /items/{id} endpoint added but not documented in README
    -> missing documentation detected by audit_agent

Usage
-----
    python demo.py

No API key required -- defaults to LLM_PROVIDER=stub.
Set LLM_PROVIDER=openai or LLM_PROVIDER=watsonx (once implemented)
to see real LLM-generated summaries.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure project root is on the path when run directly
_PROJECT_ROOT = Path(__file__).parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Default to stub LLM so demo runs without any API key
os.environ.setdefault("LLM_PROVIDER", "stub")

import orchestrator  # noqa: E402

# ---------------------------------------------------------------------------
# Demo configuration
# ---------------------------------------------------------------------------

_FIXTURE_V2 = _PROJECT_ROOT / "tests" / "fixtures" / "sample_fastapi_app_v2"

_BANNER = """\
====================================================================
   DevDocs AI -- Intelligent Documentation Ecosystem
                  IBM Bob 2.0 Hackathon Demo
====================================================================

Scenario
--------
  A FastAPI project was upgraded from v1.0.0 -> v2.0.0.
  A new DELETE /items/{{id}} endpoint was added.
  The README and CHANGELOG were NOT updated.

  DevDocs AI will detect these documentation gaps automatically.

Target repository : {repo_path}
LLM provider      : {llm_provider}
"""

_SEPARATOR = "=" * 68


def main() -> None:
    print(_BANNER.format(
        repo_path=_FIXTURE_V2,
        llm_provider=os.environ.get("LLM_PROVIDER", "stub"),
    ))

    if not _FIXTURE_V2.exists():
        print(
            f"ERROR: Demo fixture not found at:\n  {_FIXTURE_V2}\n"
            "Run the test suite first to confirm the fixture is in place.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("Running DevDocs AI pipeline...\n")
    print(_SEPARATOR)

    result = orchestrator.run(
        repo_path=str(_FIXTURE_V2),
        base_ref="HEAD~1",  # git_helper returns [] until Person 1 implements it
    )

    print(result["report"])
    print(_SEPARATOR)

    # Summary line
    n_content = len(result["results"])
    n_skipped = sum(1 for r in result["results"] if r.status == "skipped")
    n_issues = len(result["audit"].issues)

    print(f"Overall status : {result['status'].upper()}")
    print(f"Content agents : {n_content} ran, {n_skipped} skipped (awaiting teammates)")
    print(f"Audit issues   : {n_issues} detected")

    if n_issues:
        print("\nIssues found:")
        for issue in result["audit"].issues:
            print(f"  [!] {issue}")
    else:
        print("\nNo documentation issues detected.")

    print("\nDemo complete.")


if __name__ == "__main__":
    main()
