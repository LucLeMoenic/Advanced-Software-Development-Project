import asyncio
import json
from contextlib import suppress
from decimal import Decimal

import pytest
from mcp.client.session import ClientSession
from mcp.server.mcpserver import MCPServer
from mcp.shared.memory import create_client_server_memory_streams

from tools import budget


def dashboard(planned=10000, actual=8000, **overrides):
    remaining = planned - actual
    percentage = float((Decimal(actual) * 100 / Decimal(planned)).quantize(Decimal("0.01")))
    result = {
        "journeyLabel": "Sydney Weekender",
        "baseCurrency": "AUD",
        "plannedAmountMinor": planned,
        "actualAmountMinor": actual,
        "remainingAmountMinor": remaining,
        "percentageUsed": percentage,
        "categories": [{
            "category": "food",
            "plannedAmountMinor": planned,
            "actualAmountMinor": actual,
            "remainingAmountMinor": remaining,
            "percentageUsed": percentage,
            "status": "overspent" if actual > planned else "warning" if actual * 100 >= planned * 80 else "within_budget",
        }],
    }
    result.update(overrides)
    return result


class FakeResponse:
    def __init__(self, body=b"", status=200, delay=0):
        self.body = body
        self.status_code = status
        self.delay = delay

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def aiter_bytes(self, chunk_size=4096):
        if self.delay:
            await asyncio.sleep(self.delay)
        for offset in range(0, len(self.body), chunk_size):
            yield self.body[offset:offset + chunk_size]


class FakeClient:
    def __init__(self, response, timeout=None):
        self.response = response
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    def stream(self, method, url, **kwargs):
        HTTP.calls.append((method, url, kwargs))
        return self.response


class HTTP:
    response = FakeResponse()
    calls = []

    @classmethod
    def client(cls, **kwargs):
        return FakeClient(cls.response, **kwargs)


async def sdk_call(tool_name, arguments):
    server = MCPServer("budget-test")
    budget.register(server)
    async with create_client_server_memory_streams() as (client_streams, server_streams):
        server_task = asyncio.create_task(server._lowlevel_server.run(
            *server_streams, server._lowlevel_server.create_initialization_options()))
        try:
            async with ClientSession(*client_streams) as client:
                await client.initialize()
                tools = await client.list_tools()
                result = await client.call_tool(tool_name, arguments)
                return tools, result
        finally:
            server_task.cancel()
            with suppress(asyncio.CancelledError):
                await server_task


def call(tool_name, params):
    return asyncio.run(sdk_call(tool_name, {"params": params}))


def structured(result):
    return getattr(result, "structuredContent", None) or getattr(result, "structured_content", None)


@pytest.fixture(autouse=True)
def mock_http(monkeypatch):
    HTTP.calls = []
    HTTP.response = FakeResponse(json.dumps(dashboard()).encode())
    monkeypatch.setattr(budget.httpx2, "AsyncClient", HTTP.client)
    monkeypatch.delenv(budget.BACKEND_ENV, raising=False)


def test_sdk_discovers_read_only_tool_and_calls_fixed_dashboard(monkeypatch):
    monkeypatch.setenv(budget.BACKEND_ENV, "http://127.0.0.1:5204/")
    tools, result = call("budget.get_summary", {"journey_label": "  Sydney Weekender  "})

    tool = next(tool for tool in tools.tools if tool.name == "budget.get_summary")
    assert tool.annotations.read_only_hint is True
    assert tool.annotations.destructive_hint is False
    assert tool.input_schema["additionalProperties"] is False
    params_schema = tool.input_schema["properties"]["params"]
    if "$ref" in params_schema:
        params_schema = tool.input_schema["$defs"][params_schema["$ref"].rsplit("/", 1)[-1]]
    assert params_schema["additionalProperties"] is False
    assert result.is_error is not True
    assert structured(result) == {"ok": True, "summary": dashboard()}
    assert HTTP.calls == [("GET", "http://127.0.0.1:5204/api/dashboard", {
        "params": {"journeyLabel": "Sydney Weekender"}, "headers": {"Accept": "application/json"},
    })]


@pytest.mark.parametrize("arguments", [
    {"params": {}},
    {"params": {"journey_label": "   "}},
    {"params": {"journey_label": "x" * 81}},
    {"params": {"journey_label": 42}},
    {"params": {"journey_label": "Sydney", "url": "http://other"}},
    {"params": {"journey_label": "Sydney"}, "url": "http://other"},
])
def test_invalid_or_extra_arguments_are_rejected_before_http(arguments):
    _, result = asyncio.run(sdk_call("budget.get_summary", arguments))
    assert result.is_error is True
    assert HTTP.calls == []


@pytest.mark.parametrize("status,code", [
    (400, "invalid_input"),
    (404, "journey_not_found"),
    (503, "dependency_unavailable"),
    (504, "dependency_timeout"),
    (500, "invalid_dependency_response"),
])
def test_http_errors_have_stable_structured_codes(status, code):
    HTTP.response = FakeResponse(status=status)
    _, result = call("budget.get_summary", {"journey_label": "Sydney Weekender"})
    error = structured(result)["error"]
    assert error["code"] == code
    assert isinstance(error["message"], str)


def test_connection_errors_are_unavailable_and_timeout_is_bounded(monkeypatch):
    class UnavailableClient(FakeClient):
        async def __aenter__(self):
            raise budget.httpx2.ConnectError("private detail", request=None)

    monkeypatch.setattr(budget.httpx2, "AsyncClient", lambda **kwargs: UnavailableClient(HTTP.response, **kwargs))
    _, unavailable = call("budget.get_summary", {"journey_label": "Sydney Weekender"})
    assert structured(unavailable)["error"]["code"] == "dependency_unavailable"
    assert "private detail" not in structured(unavailable)["error"]["message"]

    monkeypatch.setattr(budget, "SUMMARY_TIMEOUT_SECONDS", 0.01)
    HTTP.response = FakeResponse(json.dumps(dashboard()).encode(), delay=0.1)
    monkeypatch.setattr(budget.httpx2, "AsyncClient", HTTP.client)
    _, timed_out = call("budget.get_summary", {"journey_label": "Sydney Weekender"})
    assert structured(timed_out)["error"]["code"] == "dependency_timeout"


@pytest.mark.parametrize("body", [b"{", b"NaN", b"Infinity", b"-Infinity"])
def test_malformed_or_non_finite_json_is_rejected(body):
    HTTP.response = FakeResponse(body)
    _, result = call("budget.get_summary", {"journey_label": "Sydney Weekender"})
    assert structured(result)["error"]["code"] == "invalid_dependency_response"


def test_response_limit_is_enforced_while_streaming():
    HTTP.response = FakeResponse(b" " * (budget.MAX_RESPONSE_BYTES + 1))
    _, result = call("budget.get_summary", {"journey_label": "Sydney Weekender"})
    assert structured(result)["error"]["code"] == "response_too_large"


@pytest.mark.parametrize("actual,status,percentage", [
    (7999, "within_budget", 79.99),
    (8000, "warning", 80.0),
    (10000, "warning", 100.0),
    (25001, "overspent", 100.0),
])
def test_status_uses_unrounded_ratio_and_preserves_negative_remaining(actual, status, percentage):
    planned = 25000 if actual == 25001 else 10000
    HTTP.response = FakeResponse(json.dumps(dashboard(planned, actual)).encode())
    _, result = call("budget.get_summary", {"journey_label": "sydney weekender"})
    summary = structured(result)["summary"]
    assert summary["categories"][0]["status"] == status
    assert summary["percentageUsed"] == percentage
    assert summary["remainingAmountMinor"] == planned - actual


@pytest.mark.parametrize("change", [
    {"baseCurrency": "JPY"},
    {"journeyLabel": "Other journey"},
    {"plannedAmountMinor": True},
    {"plannedAmountMinor": 2**63},
    {"remainingAmountMinor": 1},
    {"description": "must not be exposed"},
    {"percentageUsed": "Infinity"},
    {"categories": [{"category": "food", "plannedAmountMinor": 10000, "actualAmountMinor": 8000,
                     "remainingAmountMinor": 2000, "percentageUsed": 80, "status": "within_budget"}]},
])
def test_unusable_dashboard_summaries_fail_closed(change):
    body = dashboard()
    body.update(change)
    HTTP.response = FakeResponse(json.dumps(body).encode())
    _, result = call("budget.get_summary", {"journey_label": "Sydney Weekender"})
    assert structured(result)["error"]["code"] == "invalid_dependency_response"


def test_duplicate_categories_and_incoherent_category_totals_fail_closed():
    body = dashboard()
    body["categories"].append(dict(body["categories"][0]))
    HTTP.response = FakeResponse(json.dumps(body).encode())
    _, duplicate = call("budget.get_summary", {"journey_label": "Sydney Weekender"})
    assert structured(duplicate)["error"]["code"] == "invalid_dependency_response"

    body = dashboard()
    body["categories"][0]["actualAmountMinor"] = 7999
    HTTP.response = FakeResponse(json.dumps(body).encode())
    _, inconsistent = call("budget.get_summary", {"journey_label": "Sydney Weekender"})
    assert structured(inconsistent)["error"]["code"] == "invalid_dependency_response"