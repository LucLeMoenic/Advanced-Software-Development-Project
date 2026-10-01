import asyncio
from unittest.mock import Mock

import pytest
import requests
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from tools import logistics

BASE = "http://127.0.0.1:5305"
JAPAN = {"id": 1, "country": "Japan", "visa_requirement": "visa-free",
         "notes": "Visit Japan Web pre-registration speeds up immigration."}
WEATHER = [
    {"id": 2, "destination_id": 1, "season": "Summer (Jun-Aug)", "notes": "Hot and humid."},
    {"id": 1, "destination_id": 1, "season": "Spring (Mar-May)", "notes": "Pack layers."},
]
TRANSIT = [
    {"id": 1, "destination_id": 1, "type": "rail", "details": "Japan Rail Pass."},
    {"id": 2, "destination_id": 1, "type": "metro", "details": "Suica or Pasmo."},
]


def response(body, status=200):
    result = Mock(status_code=status)
    result.json.return_value = body
    result.raise_for_status.side_effect = None if status < 400 else requests.HTTPError("failed")
    return result


def call(tool, params):
    server = MCPServer("logistics-test")
    logistics.register(server)
    return asyncio.run(server.call_tool(tool, {"params": params})).structured_content


def route(monitor, bodies):
    """Answer each GET by its path; ``bodies`` maps path -> body or (body, status)."""
    calls = []

    def get(url, params=None, timeout=None):
        calls.append((url, params, timeout))
        body = bodies[url.removeprefix(BASE)]
        return response(*body) if isinstance(body, tuple) else response(body)

    monitor.setattr(logistics.requests, "get", get)
    return calls


def test_visa_returns_destination_and_official_source_reminder_with_get_only(monkeypatch):
    calls = route(monkeypatch, {"/api/destinations/1": JAPAN})
    result = call("logistics.check_visa_requirement", {"destination_id": 1})
    assert result == {"ok": True, "destination": JAPAN, "official_source_reminder": logistics.OFFICIAL_SOURCE_REMINDER}
    assert "Smartraveller" in result["official_source_reminder"]
    assert calls == [(f"{BASE}/api/destinations/1", None, 3)]


def test_visa_accepts_missing_notes(monkeypatch):
    route(monkeypatch, {"/api/destinations/16": {"id": 16, "country": "Testland", "visa_requirement": "Visa free 30 days", "notes": None}})
    assert call("logistics.check_visa_requirement", {"destination_id": 16})["destination"]["notes"] is None


def test_weather_returns_sorted_notes_for_destination(monkeypatch):
    calls = route(monkeypatch, {"/api/destinations/1": JAPAN, "/api/weather-notes": WEATHER})
    result = call("logistics.get_weather", {"destination_id": 1})
    assert result["ok"] is True
    assert result["destination"] == {"id": 1, "country": "Japan"}
    assert result["count"] == 2
    assert [note["season"] for note in result["weather_notes"]] == ["Spring (Mar-May)", "Summer (Jun-Aug)"]
    assert set(result["weather_notes"][0]) == {"id", "season", "notes"}
    assert calls == [(f"{BASE}/api/destinations/1", None, 3), (f"{BASE}/api/weather-notes", {"destination_id": 1}, 3)]


def test_transit_filters_by_type_and_handles_no_options(monkeypatch):
    route(monkeypatch, {"/api/destinations/1": JAPAN, "/api/transit-options": TRANSIT})
    result = call("logistics.get_transit", {"destination_id": 1, "type": "metro"})
    assert result["count"] == 1
    assert result["transit_options"] == [{"id": 2, "type": "metro", "details": "Suica or Pasmo."}]
    assert call("logistics.get_transit", {"destination_id": 1})["count"] == 2

    fiji = {"id": 12, "country": "Fiji", "visa_requirement": "visa-free", "notes": "Return ticket."}
    route(monkeypatch, {"/api/destinations/12": fiji, "/api/transit-options": []})
    assert call("logistics.get_transit", {"destination_id": 12}) == {
        "ok": True, "destination": {"id": 12, "country": "Fiji"}, "count": 0, "transit_options": []}


def test_results_are_capped(monkeypatch):
    many = [{"id": i, "destination_id": 1, "season": f"S{i}", "notes": "n"} for i in range(1, 26)]
    route(monkeypatch, {"/api/destinations/1": JAPAN, "/api/weather-notes": many})
    result = call("logistics.get_weather", {"destination_id": 1})
    assert result["count"] == logistics.MAX_ITEMS
    assert result["weather_notes"][-1]["id"] == 20


def test_transit_filter_runs_before_cap(monkeypatch):
    buses = [{"id": i, "destination_id": 1, "type": "bus", "details": "b"} for i in range(1, 21)]
    ferry = {"id": 21, "destination_id": 1, "type": "ferry", "details": "Harbour ferry."}
    route(monkeypatch, {"/api/destinations/1": JAPAN, "/api/transit-options": [*buses, ferry]})
    result = call("logistics.get_transit", {"destination_id": 1, "type": "ferry"})
    assert result["transit_options"] == [{"id": 21, "type": "ferry", "details": "Harbour ferry."}]
    assert call("logistics.get_transit", {"destination_id": 1})["count"] == logistics.MAX_ITEMS


def test_database_url_is_configurable(monkeypatch):
    monkeypatch.setenv("STUDENT5_DATABASE_API_URL", "http://127.0.0.1:9999/")
    calls = []

    def get(url, params=None, timeout=None):
        calls.append(url)
        return response(JAPAN)

    monkeypatch.setattr(logistics.requests, "get", get)
    assert call("logistics.check_visa_requirement", {"destination_id": 1})["ok"] is True
    assert calls == ["http://127.0.0.1:9999/api/destinations/1"]


@pytest.mark.parametrize("tool", ["logistics.check_visa_requirement", "logistics.get_weather", "logistics.get_transit"])
def test_missing_destination_is_a_domain_error_and_children_are_not_read(tool, monkeypatch):
    calls = route(monkeypatch, {"/api/destinations/99": ({"error": "not found"}, 404)})
    assert call(tool, {"destination_id": 99}) == {
        "ok": False, "error": {"code": "destination_not_found", "message": "The destination was not found."}}
    assert len(calls) == 1


@pytest.mark.parametrize("tool,params", [
    ("logistics.check_visa_requirement", {}),
    ("logistics.check_visa_requirement", {"destination_id": 0}),
    ("logistics.check_visa_requirement", {"destination_id": "1"}),
    ("logistics.check_visa_requirement", {"destination_id": True}),
    ("logistics.check_visa_requirement", {"destination_id": 1.0}),
    ("logistics.get_weather", {"destination_id": 1, "season": "Summer"}),
    ("logistics.get_transit", {"destination_id": 1, "type": "teleport"}),
    ("logistics.get_transit", {"destination_id": 1, "url": "http://other"}),
])
def test_invalid_arguments_never_reach_database(tool, params, monkeypatch):
    monkeypatch.setattr(logistics.requests, "get", lambda *args, **kwargs: pytest.fail("Unexpected database call"))
    with pytest.raises(ToolError):
        call(tool, params)


def test_top_level_arguments_are_strict_and_tools_are_read_only(monkeypatch):
    monkeypatch.setattr(logistics.requests, "get", lambda *args, **kwargs: pytest.fail("Unexpected database call"))
    server = MCPServer("logistics-test")
    logistics.register(server)
    tools = {tool.name: tool for tool in asyncio.run(server.list_tools())}
    assert set(tools) == {"logistics.check_visa_requirement", "logistics.get_weather", "logistics.get_transit"}
    for tool in tools.values():
        assert tool.input_schema["additionalProperties"] is False
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.destructive_hint is False
    with pytest.raises(ToolError):
        asyncio.run(server.call_tool("logistics.get_weather", {"params": {"destination_id": 1}, "url": "http://other"}))


@pytest.mark.parametrize("record", [
    {**JAPAN, "id": 2}, {**JAPAN, "country": ""}, {**JAPAN, "visa_requirement": None},
    {**JAPAN, "notes": 5}, {**JAPAN, "id": "1"}, {"id": 1}, [JAPAN],
])
def test_invalid_destination_records_are_rejected(record, monkeypatch):
    route(monkeypatch, {"/api/destinations/1": record})
    assert call("logistics.check_visa_requirement", {"destination_id": 1})["error"]["code"] == "invalid_dependency_response"


@pytest.mark.parametrize("records", [
    {"id": 1}, [{**WEATHER[0], "destination_id": 2}], [{**WEATHER[0], "notes": ""}], [{"id": 1, "destination_id": 1}],
])
def test_invalid_child_records_are_rejected(records, monkeypatch):
    route(monkeypatch, {"/api/destinations/1": JAPAN, "/api/weather-notes": records})
    assert call("logistics.get_weather", {"destination_id": 1})["error"]["code"] == "invalid_dependency_response"


@pytest.mark.parametrize("failure,code", [
    (requests.Timeout, "dependency_timeout"), (requests.ConnectionError, "dependency_unavailable"),
])
def test_database_failures_are_structured_without_internal_details(failure, code, monkeypatch):
    def get(*args, **kwargs):
        raise failure("Internal details must not escape")

    monkeypatch.setattr(logistics.requests, "get", get)
    for tool in ("logistics.check_visa_requirement", "logistics.get_weather", "logistics.get_transit"):
        result = call(tool, {"destination_id": 1})
        assert result["error"]["code"] == code
        assert "Internal" not in result["error"]["message"]


def test_server_error_and_invalid_json_are_distinct(monkeypatch):
    route(monkeypatch, {"/api/destinations/1": (None, 500)})
    assert call("logistics.get_weather", {"destination_id": 1})["error"]["code"] == "dependency_unavailable"
    invalid = Mock(status_code=200)
    invalid.json.side_effect = requests.exceptions.JSONDecodeError("Invalid JSON", "<html>", 0)
    monkeypatch.setattr(logistics.requests, "get", lambda *args, **kwargs: invalid)
    assert call("logistics.get_weather", {"destination_id": 1})["error"]["code"] == "invalid_dependency_response"


def test_child_read_failure_is_structured(monkeypatch):
    route(monkeypatch, {"/api/destinations/1": JAPAN, "/api/transit-options": (None, 503)})
    assert call("logistics.get_transit", {"destination_id": 1})["error"]["code"] == "dependency_unavailable"
