"""Tests the backend's /api/mcp/* and /api/rag/* routes, mocking mcp_client
and rag_client so no real MCP/RAG server is required (same convention
test_backend_attractions.py uses for database_client).
"""

import mcp_client
import rag_client


def test_list_mcp_tools_returns_tool_names(backend_client, monkeypatch):
    monkeypatch.setattr(mcp_client, "list_tools", lambda: ["attractions.search", "attractions.get_reviews"])

    response = backend_client.get("/api/mcp/tools")

    assert response.status_code == 200
    assert response.get_json() == {"tools": ["attractions.search", "attractions.get_reviews"]}


def test_list_mcp_tools_returns_503_when_disabled(backend_client, monkeypatch):
    def raise_disabled():
        raise mcp_client.McpDisabledError("MCP is disabled.")

    monkeypatch.setattr(mcp_client, "list_tools", raise_disabled)

    response = backend_client.get("/api/mcp/tools")

    assert response.status_code == 503
    assert response.get_json()["error"] == "mcp_disabled"


def test_list_mcp_tools_returns_502_when_unavailable(backend_client, monkeypatch):
    def raise_unavailable():
        raise mcp_client.McpUnavailableError("connection refused")

    monkeypatch.setattr(mcp_client, "list_tools", raise_unavailable)

    response = backend_client.get("/api/mcp/tools")

    assert response.status_code == 502
    assert response.get_json()["error"] == "mcp_unavailable"


def test_invoke_mcp_tool_happy_path(backend_client, monkeypatch):
    monkeypatch.setattr(
        mcp_client, "call_tool", lambda tool, arguments: {"attractions": [], "total_matches": 0}
    )

    response = backend_client.post(
        "/api/mcp/invoke", json={"tool": "attractions.search", "arguments": {"category": "sight"}}
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["tool"] == "attractions.search"
    assert body["result"] == {"attractions": [], "total_matches": 0}


def test_invoke_mcp_tool_rejects_disallowed_tool(backend_client):
    response = backend_client.post("/api/mcp/invoke", json={"tool": "itinerary.get_summary", "arguments": {}})

    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"


def test_invoke_mcp_tool_rejects_non_object_arguments(backend_client):
    response = backend_client.post("/api/mcp/invoke", json={"tool": "attractions.search", "arguments": "sight"})

    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"


def test_invoke_mcp_tool_returns_400_for_tool_reported_error(backend_client, monkeypatch):
    def raise_tool_error(tool, arguments):
        raise mcp_client.McpToolError("category must be one of ['activity', 'restaurant', 'sight'].")

    monkeypatch.setattr(mcp_client, "call_tool", raise_tool_error)

    response = backend_client.post(
        "/api/mcp/invoke", json={"tool": "attractions.search", "arguments": {"category": "museum"}}
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"


def test_invoke_mcp_tool_returns_503_when_disabled(backend_client, monkeypatch):
    def raise_disabled(tool, arguments):
        raise mcp_client.McpDisabledError("MCP is disabled.")

    monkeypatch.setattr(mcp_client, "call_tool", raise_disabled)

    response = backend_client.post(
        "/api/mcp/invoke", json={"tool": "attractions.search", "arguments": {}}
    )

    assert response.status_code == 503
    assert response.get_json()["error"] == "mcp_disabled"


def test_invoke_mcp_tool_returns_502_when_unavailable(backend_client, monkeypatch):
    def raise_unavailable(tool, arguments):
        raise mcp_client.McpUnavailableError("connection refused")

    monkeypatch.setattr(mcp_client, "call_tool", raise_unavailable)

    response = backend_client.post(
        "/api/mcp/invoke", json={"tool": "attractions.search", "arguments": {}}
    )

    assert response.status_code == 502
    assert response.get_json()["error"] == "mcp_unavailable"


def test_invoke_mcp_tool_accepts_form_encoded_input(backend_client, monkeypatch):
    monkeypatch.setattr(mcp_client, "call_tool", lambda tool, arguments: {"ok": True})

    response = backend_client.post(
        "/api/mcp/invoke", data={"tool": "attractions.search"}
    )

    # form-encoded values are strings, so "arguments" (absent) falls back to
    # {} via payload.get("arguments", {}) and the call still succeeds.
    assert response.status_code == 200


def test_rag_ask_happy_path(backend_client, monkeypatch):
    body = {"answer": "The Opera House is rated 4.7.", "citations": [], "confidence": "high"}
    monkeypatch.setattr(rag_client, "ask", lambda question: body)

    response = backend_client.post("/api/rag/ask", json={"question": "How is the Opera House rated?"})

    assert response.status_code == 200
    assert response.get_json() == body


def test_rag_ask_returns_insufficient_context(backend_client, monkeypatch):
    body = {"answer": "Not enough information in the knowledge base to answer this.", "citations": [], "confidence": "insufficient"}
    monkeypatch.setattr(rag_client, "ask", lambda question: body)

    response = backend_client.post("/api/rag/ask", json={"question": "What is the capital of France?"})

    assert response.status_code == 200
    assert response.get_json()["confidence"] == "insufficient"


def test_rag_ask_rejects_missing_question(backend_client):
    response = backend_client.post("/api/rag/ask", json={})

    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"


def test_rag_ask_returns_503_when_disabled(backend_client, monkeypatch):
    def raise_disabled(question):
        raise rag_client.RagDisabledError("RAG is disabled.")

    monkeypatch.setattr(rag_client, "ask", raise_disabled)

    response = backend_client.post("/api/rag/ask", json={"question": "anything"})

    assert response.status_code == 503
    assert response.get_json()["error"] == "rag_disabled"


def test_rag_ask_returns_502_when_unavailable(backend_client, monkeypatch):
    def raise_unavailable(question):
        raise rag_client.RagUnavailableError("connection refused")

    monkeypatch.setattr(rag_client, "ask", raise_unavailable)

    response = backend_client.post("/api/rag/ask", json={"question": "anything"})

    assert response.status_code == 502
    assert response.get_json()["error"] == "rag_unavailable"


def test_rag_ask_accepts_form_encoded_input(backend_client, monkeypatch):
    body = {"answer": "a", "citations": [], "confidence": "low"}
    monkeypatch.setattr(rag_client, "ask", lambda question: body)

    response = backend_client.post("/api/rag/ask", data={"question": "Is Chin Chin busy?"})

    assert response.status_code == 200
