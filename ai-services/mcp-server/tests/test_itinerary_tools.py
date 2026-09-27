import asyncio

import pytest
import requests
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from tools import itinerary


def trip():
    return {
        "id": 12, "user": "Private name", "destination": "Tokyo",
        "startDate": "2026-10-10", "endDate": "2026-10-12", "budget": 100,
        "stops": [{"tripId": 12, "day": 1}, {"tripId": 12, "day": 1}, {"tripId": 12, "day": 2}],
    }


def call(params):
    server = MCPServer("itinerary-test")
    itinerary.register(server)
    return asyncio.run(server.call_tool("itinerary.get_summary", {"params": params})).structured_content


def test_summary_calculates_coverage_and_budget_without_private_fields(monkeypatch):
    class Response:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return trip()

    calls = []

    def get(url, timeout):
        calls.append((url, timeout))
        return Response()

    monkeypatch.setattr(itinerary.requests, "get", get)
    result = call({"trip_id": 12})
    assert result["ok"] is True
    assert result["summary"]["unplannedDays"] == [3]
    assert result["summary"]["stopCount"] == 3
    assert result["summary"]["dailyBudgetAllocation"] == 33.33
    assert "user" not in result["summary"]
    assert calls == [("http://127.0.0.1:5302/api/data/trips/12", 3)]


@pytest.mark.parametrize("params", [{"trip_id": 0}, {"trip_id": True}, {"trip_id": "12"}, {"trip_id": 12, "url": "http://other"}])
def test_invalid_arguments_never_reach_database(params, monkeypatch):
    monkeypatch.setattr(itinerary.requests, "get", lambda *args, **kwargs: pytest.fail("Unexpected database call"))
    with pytest.raises(ToolError):
        call(params)


@pytest.mark.parametrize("failure,code", [(requests.Timeout, "dependency_timeout"), (requests.ConnectionError, "dependency_unavailable")])
def test_database_failures_are_structured(failure, code, monkeypatch):
    def get(*args, **kwargs):
        raise failure("Internal details must not escape")

    monkeypatch.setattr(itinerary.requests, "get", get)
    assert call({"trip_id": 12})["error"]["code"] == code


def test_empty_stops_and_corrupt_data():
    data = trip()
    data["stops"] = []
    assert itinerary.summarize(data, 12)["unplannedDays"] == [1, 2, 3]
    data["budget"] = float("nan")
    with pytest.raises(ValueError):
        itinerary.summarize(data, 12)
    data = trip()
    data["stops"][0]["tripId"] = 13
    with pytest.raises(ValueError):
        itinerary.summarize(data, 12)


def test_invalid_database_json_is_not_a_network_failure(monkeypatch):
    from unittest.mock import Mock

    response = Mock(status_code=200)
    response.json.side_effect = requests.exceptions.JSONDecodeError("Invalid JSON", "<html>", 0)
    monkeypatch.setattr(itinerary.requests, "get", lambda *args, **kwargs: response)
    assert call({"trip_id": 12})["error"]["code"] == "invalid_dependency_response"


def test_top_level_arguments_are_strict_and_advertised(monkeypatch):
    monkeypatch.setattr(itinerary.requests, "get", lambda *args, **kwargs: pytest.fail("Unexpected database call"))
    server = MCPServer("itinerary-test")
    itinerary.register(server)
    tools = asyncio.run(server.list_tools())
    assert tools[0].input_schema["additionalProperties"] is False
    with pytest.raises(ToolError):
        asyncio.run(server.call_tool("itinerary.get_summary", {"params": {"trip_id": 12}, "url": "http://other"}))