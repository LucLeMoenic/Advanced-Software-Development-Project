"""Release 1 MCP and RAG integration: clients, JSON routes and HTMX fragments.

The MCP transport is replaced at ``mcp_client.open_session`` with a fake
session, so everything above it -- the deadline, error mapping, allow-list and
routes -- is the real code. RAG HTTP calls are intercepted with ``responses``.
No test reaches a real MCP server, RAG server or model.
"""

from contextlib import asynccontextmanager
from types import SimpleNamespace

import anyio
import pytest
import requests
import responses

import mcp_client
from app import create_app

MCP_URL = "http://test-mcp:5400/mcp"
RAG_URL = "http://test-rag:5500"
INSUFFICIENT = "Not enough information in the knowledge base to answer this."

VISA_RESULT = {
    "ok": True,
    "destination": {"id": 1, "country": "Japan", "visa_requirement": "visa-free",
                    "notes": "Visit Japan Web pre-registration."},
    "official_source_reminder": "General guidance only. Confirm with Smartraveller.",
}
WEATHER_RESULT = {
    "ok": True, "destination": {"id": 1, "country": "Japan"}, "count": 1,
    "weather_notes": [{"id": 1, "season": "Spring (Mar-May)", "notes": "Pack layers."}],
}
TRANSIT_RESULT = {
    "ok": True, "destination": {"id": 1, "country": "Japan"}, "count": 1,
    "transit_options": [{"id": 2, "type": "metro", "details": "Suica or Pasmo."}],
}
GROUNDED = {
    "answer": "An eVisa is applied for online before departure. [visa-categories#3]",
    "citations": [{"source": "Visa Requirement Categories", "chunk_id": "visa-categories#3",
                   "snippet": "An eVisa is an electronic visa applied for online.", "score": 0.38}],
    "confidence": "medium",
}
INSUFFICIENT_ANSWER = {"answer": INSUFFICIENT, "citations": [], "confidence": "insufficient"}


def tool_result(content=None, is_error=False, text=""):
    return SimpleNamespace(is_error=is_error, structured_content=content,
                           content=[SimpleNamespace(text=text)] if text else [])


class FakeSession:
    def __init__(self, result=None, tools=None, delay=0.0):
        self.result = result
        self.tools = tools or []
        self.delay = delay
        self.calls = []

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        if self.delay:
            await anyio.sleep(self.delay)
        return self.result

    async def list_tools(self):
        return SimpleNamespace(tools=self.tools)


@pytest.fixture
def fake_mcp(monkeypatch):
    """Install a fake MCP session; returns a setter and the recorded state."""
    state = SimpleNamespace(session=FakeSession(), urls=[], failure=None)

    @asynccontextmanager
    async def open_session(url):
        state.urls.append(url)
        if state.failure is not None:
            raise state.failure
        yield state.session

    monkeypatch.setattr(mcp_client, "open_session", open_session)
    return state


@pytest.fixture
def integrated(database_url):
    app = create_app({
        "DATABASE_API_URL": database_url,
        "MCP_SERVER_URL": MCP_URL, "MCP_ENABLED": True,
        "RAG_SERVER_URL": RAG_URL, "RAG_ENABLED": True,
    })
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def invoke(client, tool="logistics.check_visa_requirement", arguments=None):
    return client.post("/api/mcp/invoke", json={"tool": tool, "arguments": arguments or {"destination_id": 1}})


def rag_reply(**kwargs):
    if "body" not in kwargs:
        kwargs.setdefault("json", GROUNDED)
    responses.add(responses.POST, RAG_URL + "/query", **kwargs)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def test_integrations_fail_closed_unless_the_environment_opts_in(monkeypatch):
    monkeypatch.delenv("MCP_ENABLED", raising=False)
    monkeypatch.setenv("RAG_ENABLED", "yes")
    app = create_app()
    assert app.config["MCP_ENABLED"] is False and app.config["RAG_ENABLED"] is False

    monkeypatch.setenv("MCP_ENABLED", "TRUE")
    monkeypatch.setenv("RAG_ENABLED", " true ")
    monkeypatch.setenv("MCP_SERVER_URL", "http://elsewhere:1/mcp")
    app = create_app()
    assert app.config["MCP_CLIENT"].enabled is True and app.config["RAG_CLIENT"].enabled is True
    assert app.config["MCP_CLIENT"].url == "http://elsewhere:1/mcp"


def test_disabled_integrations_return_503_without_any_network_call(client, fake_mcp):
    for response in (invoke(client), client.get("/api/mcp/tools")):
        assert response.status_code == 503
        assert response.get_json() == {"error": "mcp_disabled", "message": "MCP is disabled."}
    with responses.RequestsMock():  # any un-registered HTTP call would raise
        response = client.post("/api/rag/ask", json={"question": "Is an eVisa a visa?"})
    assert response.status_code == 503
    assert response.get_json() == {"error": "rag_disabled", "message": "RAG is disabled."}
    assert fake_mcp.urls == []


# ---------------------------------------------------------------------------
# MCP JSON routes
# ---------------------------------------------------------------------------


def test_invoke_calls_the_allow_listed_tool_with_wrapped_params(integrated, fake_mcp):
    fake_mcp.session.result = tool_result(VISA_RESULT)
    response = invoke(integrated)
    assert response.status_code == 200
    assert response.get_json() == {"tool": "logistics.check_visa_requirement", "result": VISA_RESULT}
    assert fake_mcp.urls == [MCP_URL]
    assert fake_mcp.session.calls == [("logistics.check_visa_requirement", {"params": {"destination_id": 1}})]


@pytest.mark.parametrize("body,code", [
    ({"tool": "accommodation.find", "arguments": {"destination": "Tokyo"}}, "unknown_tool"),
    ({"tool": "logistics.delete_everything", "arguments": {}}, "unknown_tool"),
    ({"arguments": {"destination_id": 1}}, "unknown_tool"),
    ({"tool": "logistics.get_weather", "arguments": [1]}, "invalid_request"),
    (["logistics.get_weather"], "invalid_request"),
])
def test_invoke_rejects_unknown_tools_and_malformed_bodies_before_mcp(integrated, fake_mcp, body, code):
    response = integrated.post("/api/mcp/invoke", json=body)
    assert response.status_code == 400
    assert response.get_json()["error"] == code
    assert fake_mcp.urls == []


def test_invoke_rejects_a_non_json_body(integrated, fake_mcp):
    response = integrated.post("/api/mcp/invoke", data="tool=x", content_type="text/plain")
    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_request"


def test_server_side_argument_rejection_is_a_400(integrated, fake_mcp):
    fake_mcp.session.result = tool_result(is_error=True, text="destination_id: Input should be greater than 0")
    response = invoke(integrated, arguments={"destination_id": 0})
    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid_arguments",
                                    "message": "destination_id: Input should be greater than 0"}


@pytest.mark.parametrize("code,status", [
    ("destination_not_found", 404), ("dependency_timeout", 504),
    ("dependency_unavailable", 502), ("invalid_dependency_response", 502),
])
def test_tool_domain_failures_keep_the_result_with_an_honest_status(integrated, fake_mcp, code, status):
    failure = {"ok": False, "error": {"code": code, "message": "m"}}
    fake_mcp.session.result = tool_result(failure)
    response = invoke(integrated, "logistics.get_weather")
    assert response.status_code == status
    assert response.get_json() == {"tool": "logistics.get_weather", "result": failure}


@pytest.mark.parametrize("content", [None, ["not", "a", "dict"], {"weather_notes": []}])
def test_unexpected_tool_result_shape_is_a_502(integrated, fake_mcp, content):
    fake_mcp.session.result = tool_result(content)
    response = invoke(integrated)
    assert response.status_code == 502
    assert response.get_json()["error"] == "mcp_unavailable"


@pytest.mark.parametrize("failure", [
    ConnectionError("refused at 10.0.0.1"),
    ExceptionGroup("unhandled errors in a TaskGroup", [OSError("All connection attempts failed")]),
])
def test_unreachable_server_is_a_502_without_internal_details(integrated, fake_mcp, failure):
    fake_mcp.failure = failure
    response = invoke(integrated)
    assert response.status_code == 502
    assert response.get_json() == {"error": "mcp_unavailable", "message": "The MCP server is unavailable."}


def test_slow_server_hits_the_client_deadline(integrated, fake_mcp):
    integrated.application.config["MCP_CLIENT"].timeout = 0.05
    fake_mcp.session = FakeSession(tool_result(VISA_RESULT), delay=1)
    response = invoke(integrated)
    assert response.status_code == 502
    assert response.get_json()["message"] == "The MCP server timed out."


def test_tool_discovery_lists_only_allow_listed_student5_tools(integrated, fake_mcp):
    fake_mcp.session.tools = [
        SimpleNamespace(name="logistics.get_weather", description="Weather notes."),
        SimpleNamespace(name="logistics.get_transit", description=None),
        SimpleNamespace(name="accommodation.find", description="Other student."),
    ]
    response = integrated.get("/api/mcp/tools")
    assert response.status_code == 200
    assert response.get_json() == {"tools": [
        {"name": "logistics.get_weather", "description": "Weather notes."},
        {"name": "logistics.get_transit", "description": ""},
    ]}


# ---------------------------------------------------------------------------
# RAG JSON route
# ---------------------------------------------------------------------------


@responses.activate
def test_rag_ask_posts_the_trimmed_question_for_student5_and_returns_the_contract(integrated):
    rag_reply(json={**GROUNDED, "debug": "dropped"})
    response = integrated.post("/api/rag/ask", json={"question": "  What is an eVisa?  "})
    assert response.status_code == 200
    assert response.get_json() == GROUNDED
    sent = responses.calls[0].request
    assert sent.url == RAG_URL + "/query"
    assert sent.body == b'{"feature": "student-5", "question": "What is an eVisa?"}'


@responses.activate
def test_insufficient_answer_is_a_valid_200(integrated):
    rag_reply(json=INSUFFICIENT_ANSWER)
    response = integrated.post("/api/rag/ask", json={"question": "What is the capital of France?"})
    assert response.status_code == 200
    assert response.get_json() == INSUFFICIENT_ANSWER


@pytest.mark.parametrize("body", [{}, {"question": ""}, {"question": "   "}, {"question": 5},
                                  {"question": "x" * 501}, "question"])
@responses.activate
def test_invalid_questions_are_rejected_before_the_rag_server(integrated, body):
    response = integrated.post("/api/rag/ask", json=body)
    assert response.status_code == 400
    assert response.get_json()["error"] in {"invalid_question", "invalid_request"}
    assert len(responses.calls) == 0


@pytest.mark.parametrize("kwargs,status,code", [
    ({"status": 504, "json": {"error": {"code": "dependency_timeout", "message": "m"}}}, 504, "rag_timeout"),
    ({"body": requests.Timeout("slow")}, 504, "rag_timeout"),
    ({"status": 503, "json": {"error": {"code": "dependency_unavailable", "message": "m"}}}, 502, "rag_unavailable"),
    ({"status": 500, "body": "<html>"}, 502, "rag_unavailable"),
    ({"body": requests.ConnectionError("refused")}, 502, "rag_unavailable"),
])
@responses.activate
def test_rag_failures_map_to_distinct_statuses(integrated, kwargs, status, code):
    rag_reply(**kwargs)
    response = integrated.post("/api/rag/ask", json={"question": "What is an eVisa?"})
    assert response.status_code == status
    assert response.get_json()["error"] == code


@pytest.mark.parametrize("body", [
    {**INSUFFICIENT_ANSWER, "citations": GROUNDED["citations"]},
    {**GROUNDED, "citations": []},
    {**GROUNDED, "confidence": "certain"},
    {**GROUNDED, "answer": ""},
    {**GROUNDED, "citations": [{**GROUNDED["citations"][0], "score": "high"}]},
    {**GROUNDED, "citations": [{**GROUNDED["citations"][0], "chunk_id": ""}]},
    ["not", "an", "object"],
])
@responses.activate
def test_answers_that_break_the_rag_contract_are_rejected(integrated, body):
    rag_reply(json=body)
    response = integrated.post("/api/rag/ask", json={"question": "What is an eVisa?"})
    assert response.status_code == 502
    assert response.get_json()["error"] == "rag_unavailable"


# ---------------------------------------------------------------------------
# HTMX fragments
# ---------------------------------------------------------------------------


def post_tool(client, tool, destination_id="1", **extra):
    return client.post("/ui/mcp", data={"tool": tool, "destination_id": destination_id, **extra})


def test_mcp_fragment_renders_visa_result_with_tool_provenance(integrated, fake_mcp):
    fake_mcp.session.result = tool_result(VISA_RESULT)
    response = post_tool(integrated, "logistics.check_visa_requirement")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "logistics.check_visa_requirement" in html and "shared MCP server" in html
    assert "visa-free" in html and "Confirm with Smartraveller." in html
    assert 'style="' not in html


def test_mcp_fragment_renders_weather_and_passes_transit_type_only_for_transit(integrated, fake_mcp):
    fake_mcp.session.result = tool_result(WEATHER_RESULT)
    html = post_tool(integrated, "logistics.get_weather", transit_type="metro").get_data(as_text=True)
    assert "Spring (Mar-May)" in html and "Pack layers." in html

    fake_mcp.session.result = tool_result(TRANSIT_RESULT)
    html = post_tool(integrated, "logistics.get_transit", transit_type="metro").get_data(as_text=True)
    assert "Suica or Pasmo." in html
    post_tool(integrated, "logistics.get_transit", transit_type="")
    assert [call[1]["params"] for call in fake_mcp.session.calls] == [
        {"destination_id": 1}, {"destination_id": 1, "type": "metro"}, {"destination_id": 1}]


@pytest.mark.parametrize("setup,form,message", [
    (None, {"destination_id": ""}, "Choose a destination"),
    (None, {"tool": "accommodation.find"}, "tool must be one of"),
    ("not_found", {}, "That destination could not be found."),
    ("db_down", {}, "could not read the travel database"),
    ("rejected", {}, "The tool rejected that request."),
    ("unreachable", {}, "shared tool server is unavailable"),
])
def test_mcp_fragment_renders_every_failure_as_readable_content(integrated, fake_mcp, setup, form, message):
    if setup == "not_found":
        fake_mcp.session.result = tool_result({"ok": False, "error": {"code": "destination_not_found", "message": "m"}})
    elif setup == "db_down":
        fake_mcp.session.result = tool_result({"ok": False, "error": {"code": "dependency_unavailable", "message": "m"}})
    elif setup == "rejected":
        fake_mcp.session.result = tool_result(is_error=True, text="bad type")
    elif setup == "unreachable":
        fake_mcp.failure = ConnectionError("refused")
    data = {"tool": "logistics.get_weather", "destination_id": "1", **form}
    response = integrated.post("/ui/mcp", data=data)
    assert response.status_code == 200
    assert 'class="fragment-message"' in response.get_data(as_text=True)
    assert message in response.get_data(as_text=True)


def test_mcp_fragment_when_disabled_says_so(client, fake_mcp):
    response = post_tool(client, "logistics.get_weather")
    assert response.status_code == 200
    assert "MCP is disabled" in response.get_data(as_text=True)


@responses.activate
def test_rag_fragment_renders_answer_confidence_and_citations(integrated):
    rag_reply()
    response = integrated.post("/ui/rag", data={"question": "What is an <b>eVisa</b>?"})
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Medium confidence" in html and "confidence-medium" in html
    assert "Visa Requirement Categories" in html and "visa-categories#3" in html and "score 0.38" in html
    assert "&lt;b&gt;eVisa&lt;/b&gt;" in html and "<b>" not in html
    assert "rag-caution" not in html


@responses.activate
def test_rag_fragment_shows_insufficient_as_not_covered_without_sources(integrated):
    rag_reply(json=INSUFFICIENT_ANSWER)
    html = integrated.post("/ui/rag", data={"question": "Capital of France?"}).get_data(as_text=True)
    assert INSUFFICIENT in html and "Insufficient confidence" in html
    assert "Sources" not in html


@responses.activate
def test_rag_fragment_flags_low_confidence(integrated):
    rag_reply(json={**GROUNDED, "confidence": "low"})
    html = integrated.post("/ui/rag", data={"question": "Is an ESTA a visa?"}).get_data(as_text=True)
    assert "rag-caution" in html


@pytest.mark.parametrize("kwargs,form,message", [
    ({"status": 504, "json": {}}, {"question": "What is an eVisa?"}, "took too long"),
    ({"status": 503, "json": {}}, {"question": "What is an eVisa?"}, "knowledge base is unavailable"),
    (None, {"question": "  "}, "Ask a question"),
])
@responses.activate
def test_rag_fragment_renders_failures_as_content(integrated, kwargs, form, message):
    if kwargs:
        rag_reply(**kwargs)
    response = integrated.post("/ui/rag", data=form)
    assert response.status_code == 200
    assert message in response.get_data(as_text=True)


def test_rag_fragment_when_disabled_says_so(client):
    response = client.post("/ui/rag", data={"question": "What is an eVisa?"})
    assert response.status_code == 200
    assert "RAG is disabled" in response.get_data(as_text=True)
