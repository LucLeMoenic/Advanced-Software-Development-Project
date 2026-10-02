"""Release 1 integrations: the shared MCP tools and RAG knowledge base.

Marked requirement: Frontend -> Backend/API -> MCP/RAG. This blueprint owns
the JSON routes; ui.py renders the same calls as HTMX fragments, and both go
through the two helpers below so the allow-list and validation live in one
place.

JSON contract (honest status codes, like the ``api`` blueprint):

    GET  /api/mcp/tools   -> 200 {"tools": [{"name", "description"}]}
    POST /api/mcp/invoke  {"tool": "logistics.get_weather", "arguments": {"destination_id": 1}}
                          -> 200 {"tool", "result": {"ok": true, ...}}
                          -> 404/502/504 {"tool", "result": {"ok": false, "error": {...}}}
    POST /api/rag/ask     {"question": "..."}
                          -> 200 {"answer", "citations", "confidence"}

    400 {"error": "invalid_request" | "unknown_tool" | "invalid_arguments" | "invalid_question"}
    503 {"error": "mcp_disabled" | "rag_disabled"}
    502 {"error": "mcp_unavailable" | "rag_unavailable"}
    504 {"error": "rag_timeout"}
"""

from typing import Any, Dict, Tuple

from flask import Blueprint, current_app, jsonify, request

from mcp_client import McpClient, McpDisabled, McpToolError, McpUnavailable
from rag_client import (
    MAX_QUESTION_LENGTH,
    RagClient,
    RagDisabled,
    RagTimeout,
    RagUnavailable,
)

integrations_bp = Blueprint("integrations", __name__)

# Second boundary on top of the MCP server's own registration: the backend
# only ever forwards Student 5's read-only tools, whatever else the shared
# server advertises.
ALLOWED_TOOLS = (
    "logistics.check_visa_requirement",
    "logistics.get_weather",
    "logistics.get_transit",
)

# A tool's domain failure ({"ok": false}) keeps the result body but gets an
# honest status, so a caller can tell "no such destination" from "database down".
DOMAIN_ERROR_STATUS = {
    "destination_not_found": 404,
    "dependency_timeout": 504,
}


class InvalidRequest(Exception):
    """The caller's request was malformed; ``code`` names the problem."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def mcp() -> McpClient:
    return current_app.config["MCP_CLIENT"]


def rag() -> RagClient:
    return current_app.config["RAG_CLIENT"]


def invoke_tool(tool: Any, arguments: Any) -> Dict[str, Any]:
    """Validate the envelope and call one allow-listed Student 5 MCP tool.

    Argument *values* are validated by the MCP server's strict schema, so a
    bad destination id comes back as McpToolError rather than being checked
    twice here.
    """
    if tool not in ALLOWED_TOOLS:
        raise InvalidRequest("unknown_tool", "tool must be one of {}.".format(", ".join(ALLOWED_TOOLS)))
    if not isinstance(arguments, dict):
        raise InvalidRequest("invalid_request", "arguments must be a JSON object.")
    return mcp().call_tool(tool, arguments)


def clean_question(question: Any) -> str:
    if not isinstance(question, str) or not question.strip():
        raise InvalidRequest("invalid_question", "Ask a question about travel logistics.")
    question = question.strip()
    if len(question) > MAX_QUESTION_LENGTH:
        raise InvalidRequest(
            "invalid_question",
            "Questions are limited to {} characters.".format(MAX_QUESTION_LENGTH),
        )
    return question


def _error(code: str, message: str, status: int) -> Tuple[Any, int]:
    return jsonify({"error": code, "message": message}), status


def _json_object() -> Dict[str, Any]:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise InvalidRequest("invalid_request", "Send a JSON object body.")
    return body


@integrations_bp.errorhandler(InvalidRequest)
def handle_invalid_request(exc: InvalidRequest):
    return _error(exc.code, exc.message, 400)


@integrations_bp.errorhandler(McpDisabled)
def handle_mcp_disabled(_exc):
    return _error("mcp_disabled", "MCP is disabled.", 503)


@integrations_bp.errorhandler(McpUnavailable)
def handle_mcp_unavailable(exc):
    return _error("mcp_unavailable", str(exc), 502)


@integrations_bp.errorhandler(RagDisabled)
def handle_rag_disabled(_exc):
    return _error("rag_disabled", "RAG is disabled.", 503)


@integrations_bp.errorhandler(RagUnavailable)
def handle_rag_unavailable(exc: RagUnavailable):
    return _error(exc.code, str(exc), 504 if isinstance(exc, RagTimeout) else 502)


@integrations_bp.get("/api/mcp/tools")
def list_mcp_tools():
    tools = [tool for tool in mcp().list_tools() if tool["name"] in ALLOWED_TOOLS]
    return jsonify({"tools": tools})


@integrations_bp.post("/api/mcp/invoke")
def invoke_mcp_tool():
    body = _json_object()
    tool = body.get("tool")
    try:
        result = invoke_tool(tool, body.get("arguments", {}))
    except McpToolError as exc:
        return _error("invalid_arguments", str(exc)[:300], 400)

    status = 200
    if result.get("ok") is False:
        error = result.get("error")
        code = error.get("code") if isinstance(error, dict) else None
        status = DOMAIN_ERROR_STATUS.get(code, 502)
    return jsonify({"tool": tool, "result": result}), status


@integrations_bp.post("/api/rag/ask")
def rag_ask():
    question = clean_question(_json_object().get("question"))
    return jsonify(rag().ask(question))
