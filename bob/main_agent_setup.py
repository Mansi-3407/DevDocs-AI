"""
DevDocs AI — IBM Bob 2.0 Integration

This module exposes one MCP tool to Bob:

    run_devdocs_pipeline(repo_path, base_ref="HEAD~1") -> str

Bob integration is intentionally thin:
  * No audit logic
  * No LLM calls
  * No git operations
  * No file analysis

All processing is delegated to orchestrator.run().
The report string returned by the orchestrator is passed back to Bob as-is.

Registering with Bob
---------------------
Add the following to your Bob mcp.json (workspace or global):

    {
      "mcpServers": {
        "devdocs-ai": {
          "command": "python",
          "args": ["bob/main_agent_setup.py"],
          "env": {
            "LLM_PROVIDER": "stub"
          }
        }
      }
    }

Replace "stub" with "openai" or "watsonx" once a real provider is configured.
"""

from __future__ import annotations

import sys
import os

# Ensure the project root is on sys.path so orchestrator and app/ are importable
# when this file is invoked directly by the MCP runtime.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types as mcp_types
    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False

import orchestrator  # noqa: E402 — project root module

# ---------------------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------------------

def run_devdocs_pipeline(repo_path: str, base_ref: str = "HEAD~1") -> str:
    """Run the full DevDocs AI documentation pipeline against a repository.

    Analyses the repository at *repo_path*, detects changed files relative to
    *base_ref*, runs all documentation agents, audits the results, and returns
    a formatted markdown report.

    Args:
        repo_path: Absolute or relative path to the root of the git repository.
        base_ref:  Git ref to diff against.  Default is one commit back (HEAD~1).

    Returns:
        A markdown-formatted pipeline report string.
    """
    result = orchestrator.run(repo_path=repo_path, base_ref=base_ref)
    return result["report"]


# ---------------------------------------------------------------------------
# MCP server entry point
# ---------------------------------------------------------------------------

def _build_server() -> "Server":
    """Construct and return the MCP Server with the DevDocs tool registered."""
    server = Server("devdocs-ai")

    @server.list_tools()
    async def list_tools() -> list[mcp_types.Tool]:
        return [
            mcp_types.Tool(
                name="run_devdocs_pipeline",
                description=(
                    "Run the DevDocs AI documentation pipeline against a local "
                    "git repository. Detects documentation issues, version "
                    "inconsistencies, and broken links, then returns a markdown "
                    "report of all findings."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo_path": {
                            "type": "string",
                            "description": "Absolute path to the repository root.",
                        },
                        "base_ref": {
                            "type": "string",
                            "description": (
                                "Git ref to diff against (default: HEAD~1)."
                            ),
                            "default": "HEAD~1",
                        },
                    },
                    "required": ["repo_path"],
                },
            )
        ]

    @server.call_tool()
    async def call_tool(
        name: str, arguments: dict
    ) -> list[mcp_types.TextContent]:
        if name != "run_devdocs_pipeline":
            return [mcp_types.TextContent(type="text", text=f"Unknown tool: {name}")]
        repo_path = arguments.get("repo_path", ".")
        base_ref = arguments.get("base_ref", "HEAD~1")
        report = run_devdocs_pipeline(repo_path=repo_path, base_ref=base_ref)
        return [mcp_types.TextContent(type="text", text=report)]

    return server


async def _main() -> None:
    """Run the MCP server over stdio."""
    server = _build_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    if not _MCP_AVAILABLE:
        print(
            "ERROR: The 'mcp' package is not installed.\n"
            "Install it with:  pip install mcp\n"
            "Then restart the MCP server.",
            file=sys.stderr,
        )
        sys.exit(1)

    import asyncio
    asyncio.run(_main())
