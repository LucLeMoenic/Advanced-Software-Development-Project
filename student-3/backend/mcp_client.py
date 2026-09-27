"""Client for the shared Release 1 MCP server's Student 3 tools.

Follows database_client.py's shape (env URL, timeout, custom exceptions
mapped to JSON/status codes by the route), adapted for the MCP protocol:
there is no single `_request` helper because a tool call is a short-lived
session (initialize -> call_tool -> close), not a single HTTP request.

Over the real streamable-HTTP protocol, a tool's own validation/domain
errors come back as a *successful* JSON-RPC response with
`CallToolResult(is_error=True, content=[TextContent(text="...")])`, not a
raised exception or a non-200 status. Confirmed by running the real MCP
server and calling it with a real ClientSession before writing this
module (an invalid category and an unknown-field call both returned
`is_error=True` with the message in `content[0].text`). That case becomes
McpToolError (a caller mistake -> 400 at the route); only an unreachable/
timed-out server (McpUnavailableError) or a malformed result shape
(McpResponseError) reflect an actual infrastructure problem -> 502.
"""

import os

import anyio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:5400/mcp")
REQUEST_TIMEOUT = 5

TOOL_PREFIX = "attractions."


class McpDisabledError(Exception):
    """MCP is disabled (MCP_ENABLED is not "true"); no network call is made."""


class McpUnavailableError(Exception):
    """The MCP server could not be reached (connection/timeout)."""


class McpToolError(Exception):
    """The tool itself rejected the call (bad/unknown input, not found).
    Both of Student 3's tools only ever raise this for input validation or
    a missing attraction id, so the route treats it as a 400, not a 502."""


class McpResponseError(Exception):
    """The MCP server responded, but not in the shape we expected (a
    malformed result) — an infrastructure problem, not a caller mistake."""


def _enabled():
    # Read fresh each call (not cached at import time) so tests can toggle
    # MCP_ENABLED with monkeypatch.setenv without reloading this module.
    return os.environ.get("MCP_ENABLED", "true").lower() == "true"


def _extract_error_text(result):
    for item in result.content:
        text = getattr(item, "text", None)
        if text:
            return text
    return "MCP tool call failed."


_OUR_ERRORS = (McpUnavailableError, McpResponseError, McpToolError)


def _unwrap_exception_group(exception):
    """anyio's TaskGroup wraps a task's exception in an ExceptionGroup, so
    a McpToolError raised deep inside session.call_tool's internals doesn't
    match a plain `except McpToolError` — verified live: an invalid-category
    call surfaced as "unhandled errors in a TaskGroup (1 sub-exception)"
    instead of the actual McpToolError, before this unwrap was added. Same
    fix as student-2's ai_clients.py IntegrationError handling.
    """
    if not isinstance(exception, BaseExceptionGroup):
        return None
    matching = exception.subgroup(_OUR_ERRORS)
    if matching is None:
        return None
    while isinstance(matching, BaseExceptionGroup):
        matching = matching.exceptions[0]
    return matching


async def _with_session(coroutine_fn, *args):
    try:
        with anyio.fail_after(REQUEST_TIMEOUT):
            async with streamable_http_client(MCP_SERVER_URL) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    return await coroutine_fn(session, *args)
    except _OUR_ERRORS:
        raise
    except TimeoutError as exc:
        raise McpUnavailableError("MCP server timed out.") from exc
    except Exception as exc:
        unwrapped = _unwrap_exception_group(exc)
        if unwrapped is not None:
            raise unwrapped from None
        raise McpUnavailableError(str(exc)) from exc


async def _list_tools(session):
    result = await session.list_tools()
    return [tool.name for tool in result.tools if tool.name.startswith(TOOL_PREFIX)]


async def _call_tool(session, tool_name, arguments):
    result = await session.call_tool(tool_name, {"params": arguments})
    if result.is_error:
        raise McpToolError(_extract_error_text(result))
    if not isinstance(result.structured_content, dict):
        raise McpResponseError("MCP tool returned an unexpected result shape.")
    return result.structured_content


def list_tools():
    if not _enabled():
        raise McpDisabledError("MCP is disabled.")
    return anyio.run(_with_session, _list_tools)


def call_tool(tool_name, arguments):
    if not _enabled():
        raise McpDisabledError("MCP is disabled.")
    return anyio.run(_with_session, _call_tool, tool_name, arguments)
