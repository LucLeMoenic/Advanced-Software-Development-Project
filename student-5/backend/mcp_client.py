"""Client for the Student 5 tools on the shared Release 1 MCP server.

Marked requirement: Frontend -> Backend/API -> MCP server -> tool. The browser
never speaks MCP; this module is the only part of the backend that does.

Each call is one short streamable-HTTP session (initialize -> call -> close)
under a single deadline. The raw ``CallToolResult`` is returned *out of* the
session before it is inspected, so a tool-level error is raised after the
anyio task group has closed and never arrives wrapped in an ExceptionGroup.

Failure modes, kept separate because the route maps them differently:

* ``McpDisabled``   -- ``MCP_ENABLED`` is not true; no network call is made.
* ``McpToolError``  -- the server rejected the arguments (``is_error`` result).
* ``McpUnavailable`` -- unreachable, timed out, or an unexpected result shape.
"""

from contextlib import asynccontextmanager
from typing import Any, Dict, List

import anyio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

DEFAULT_MCP_SERVER_URL = "http://host.docker.internal:5400/mcp"
DEFAULT_TIMEOUT_SECONDS = 5.0
TOOL_PREFIX = "logistics."


class McpDisabled(Exception):
    """MCP is switched off for this deployment."""


class McpUnavailable(Exception):
    """The MCP server could not complete the call."""


class McpToolError(Exception):
    """The MCP server rejected the tool call's arguments."""


@asynccontextmanager
async def open_session(url: str):
    """An initialised MCP client session. Tests replace this with a fake."""
    async with streamable_http_client(url) as (read_stream, write_stream, *_):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


def _error_text(result: Any) -> str:
    for item in getattr(result, "content", None) or []:
        text = getattr(item, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()
    return "The MCP tool rejected the request."


class McpClient:
    """Calls the ``logistics.*`` tools through the shared MCP server."""

    def __init__(self, url: str, enabled: bool, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.url = url
        self.enabled = enabled
        self.timeout = timeout

    def _run(self, operation):
        if not self.enabled:
            raise McpDisabled("MCP is disabled.")

        async def session_call():
            with anyio.fail_after(self.timeout):
                async with open_session(self.url) as session:
                    return await operation(session)

        try:
            return anyio.run(session_call)
        except TimeoutError as exc:
            raise McpUnavailable("The MCP server timed out.") from exc
        except Exception as exc:  # transport errors arrive as varied (grouped) types
            raise McpUnavailable("The MCP server is unavailable.") from exc

    def list_tools(self) -> List[Dict[str, str]]:
        """Name and description of every Student 5 tool the server advertises."""
        result = self._run(lambda session: session.list_tools())
        tools = getattr(result, "tools", None)
        if not isinstance(tools, list):
            raise McpUnavailable("The MCP server returned an unexpected tool list.")
        return [
            {"name": tool.name, "description": tool.description or ""}
            for tool in tools
            if isinstance(getattr(tool, "name", None), str) and tool.name.startswith(TOOL_PREFIX)
        ]

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke one tool and return its structured result.

        The shared server wraps every tool's arguments in ``{"params": ...}``
        so that unknown fields are rejected at the boundary.
        """
        result = self._run(lambda session: session.call_tool(name, {"params": arguments}))
        if getattr(result, "is_error", False):
            raise McpToolError(_error_text(result))
        content = getattr(result, "structured_content", None)
        if not isinstance(content, dict) or not isinstance(content.get("ok"), bool):
            raise McpUnavailable("The MCP tool returned an unexpected result.")
        return content
