"""Tests mcp_client.py's session handling and error mapping.

Never opens a real MCP connection: streamable_http_client and ClientSession
are always faked, the same convention test_recommend.py uses for Ollama.
The fakes match the real shapes verified by running the actual MCP server
with a real ClientSession while writing mcp_client.py (see its docstring).
"""

from types import SimpleNamespace

import pytest

import mcp_client


class FakeStreams:
    """Fakes streamable_http_client's async context manager."""

    def __init__(self, connect_error=None):
        self.connect_error = connect_error

    def __call__(self, url):
        return self

    async def __aenter__(self):
        if self.connect_error:
            raise self.connect_error
        return (None, None)

    async def __aexit__(self, *args):
        return False


class FakeSession:
    """Fakes ClientSession; tools_result/call_result are set per test."""

    tools_result = None
    call_result = None

    def __init__(self, *streams):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def initialize(self):
        pass

    async def list_tools(self):
        return self.tools_result

    async def call_tool(self, name, arguments):
        return self.call_result


def tool(name):
    return SimpleNamespace(name=name)


def result(is_error=False, content=None, structured_content=None):
    return SimpleNamespace(is_error=is_error, content=content or [], structured_content=structured_content)


def text_content(text):
    return SimpleNamespace(text=text)


@pytest.fixture(autouse=True)
def fake_transport(monkeypatch):
    monkeypatch.setattr(mcp_client, "streamable_http_client", FakeStreams())
    monkeypatch.setattr(mcp_client, "ClientSession", FakeSession)


def test_list_tools_filters_to_attractions_prefix():
    FakeSession.tools_result = SimpleNamespace(
        tools=[tool("attractions.search"), tool("attractions.get_reviews"), tool("itinerary.get_summary")]
    )

    tools = mcp_client.list_tools()

    assert tools == ["attractions.search", "attractions.get_reviews"]


def test_list_tools_raises_disabled_without_any_network_call(monkeypatch):
    monkeypatch.setenv("MCP_ENABLED", "false")

    def fail_if_called(url):
        raise AssertionError("streamable_http_client should not be called when disabled")

    monkeypatch.setattr(mcp_client, "streamable_http_client", fail_if_called)

    with pytest.raises(mcp_client.McpDisabledError):
        mcp_client.list_tools()


def test_call_tool_returns_structured_content_on_success():
    FakeSession.call_result = result(structured_content={"attractions": [], "total_matches": 0})

    body = mcp_client.call_tool("attractions.search", {"category": "sight"})

    assert body == {"attractions": [], "total_matches": 0}


def test_call_tool_raises_tool_error_when_result_is_error():
    FakeSession.call_result = result(is_error=True, content=[text_content("category must be one of [...]")])

    with pytest.raises(mcp_client.McpToolError, match="category must be one of"):
        mcp_client.call_tool("attractions.search", {"category": "museum"})


def test_call_tool_raises_response_error_for_non_dict_structured_content():
    FakeSession.call_result = result(structured_content=None)

    with pytest.raises(mcp_client.McpResponseError):
        mcp_client.call_tool("attractions.search", {})


def test_call_tool_raises_disabled_without_any_network_call(monkeypatch):
    monkeypatch.setenv("MCP_ENABLED", "false")

    def fail_if_called(url):
        raise AssertionError("streamable_http_client should not be called when disabled")

    monkeypatch.setattr(mcp_client, "streamable_http_client", fail_if_called)

    with pytest.raises(mcp_client.McpDisabledError):
        mcp_client.call_tool("attractions.search", {})


def test_call_tool_raises_unavailable_when_server_unreachable(monkeypatch):
    monkeypatch.setattr(mcp_client, "streamable_http_client", FakeStreams(connect_error=ConnectionError("refused")))

    with pytest.raises(mcp_client.McpUnavailableError):
        mcp_client.call_tool("attractions.search", {})


def test_call_tool_raises_unavailable_on_timeout(monkeypatch):
    def raise_timeout(url):
        raise TimeoutError("too slow")

    monkeypatch.setattr(mcp_client, "streamable_http_client", raise_timeout)

    with pytest.raises(mcp_client.McpUnavailableError):
        mcp_client.call_tool("attractions.search", {})
