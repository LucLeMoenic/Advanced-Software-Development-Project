import asyncio
from datetime import datetime, timedelta, timezone

import pytest
import requests
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from tools import itinerary
from tools import itinerary_weather as weather


def trip():
    return {
        "id": 12, "user": "Private name", "destination": "Tokyo",
        "startDate": "2026-10-10", "endDate": "2026-10-12", "budget": 100,
        "stops": [{"tripId": 12, "day": 1}, {"tripId": 12, "day": 1}, {"tripId": 12, "day": 2}],
    }


@pytest.mark.parametrize("operation", [
    {"action": "swap_days", "sourceDay": 1, "targetDay": 2, "stopId": 0},
    {"action": "reorder_before", "sourceDay": 1, "targetDay": 1, "stopId": 2, "targetStopId": 1},
    {"action": "reorder_after", "sourceDay": 1, "targetDay": 1, "stopId": 1, "targetStopId": 2},
    {"action": "undo", "sourceDay": 1, "targetDay": 1, "stopId": 0},
    {"action": "add_stop", "sourceDay": 2, "targetDay": 2, "stopId": 0, "activity": "Lunch", "notes": ""},
    {"action": "remove_stop", "sourceDay": 1, "targetDay": 1, "stopId": 2},
    {"action": "update_stop", "sourceDay": 1, "targetDay": 1, "stopId": 2, "notes": "Bring tickets"},
    {"action": "shift_dates", "sourceDay": 1, "targetDay": 1, "stopId": 0, "startDate": "2027-06-01"},
])
def test_edit_tools_enforce_boundaries_and_forward_preview_token(monkeypatch, operation):
    from unittest.mock import Mock

    server = MCPServer("edit-test")
    itinerary.register(server)
    calls = []
    def post(url, **kwargs):
        calls.append((url, kwargs))
        body = {"tripId": 12, "changes": []}
        body.update({"token": "signed", "expiresIn": 600} if url.endswith("edit-preview") else {"applied": True})
        return Mock(status_code=200, json=lambda: body)
    monkeypatch.setattr(itinerary.requests, "post", post)
    result = asyncio.run(server.call_tool("itinerary.preview_edit", {"params": {"trip_id": 12, "operation": operation}})).structured_content
    assert result["token"] == "signed"
    assert calls[0][1]["json"] == operation
    result = asyncio.run(server.call_tool("itinerary.apply_edit", {"params": {"trip_id": 12, "token": "signed"}})).structured_content
    assert result["applied"] is True
    assert calls[1][1]["json"] == {"token": "signed"}
    for params in [{"trip_id": 12, "operation": {**operation, "action": "delete"}},
                   {"trip_id": True, "operation": operation}, {"trip_id": 12, "operation": {**operation, "targetDay": "2"}}]:
        with pytest.raises(ToolError):
            asyncio.run(server.call_tool("itinerary.preview_edit", {"params": params}))
    with pytest.raises(ToolError):
        asyncio.run(server.call_tool("itinerary.apply_edit", {"params": {"trip_id": 12, "token": "signed"}, "operation": operation}))
    assert len(calls) == 2


@pytest.mark.parametrize("status,code", [(400, "invalid_edit"), (404, "trip_not_found"), (409, "stale_preview")])
def test_edit_tools_map_database_rejections(monkeypatch, status, code):
    from unittest.mock import Mock

    monkeypatch.setattr(itinerary.requests, "post", lambda *args, **kwargs: Mock(status_code=status))
    server = MCPServer("edit-test")
    itinerary.register(server)
    result = asyncio.run(server.call_tool("itinerary.apply_edit", {"params": {"trip_id": 12, "token": "signed"}})).structured_content
    assert result["error"]["code"] == code


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


def test_review_tool_returns_bounded_stops_without_identity(monkeypatch):
    from unittest.mock import Mock

    data = trip()
    for index, stop in enumerate(data["stops"]):
        stop.update(id=index + 1, activity="Park walk", notes="Outdoor path", private="omitted")
    monkeypatch.setattr(itinerary.requests, "get", lambda *args, **kwargs: Mock(status_code=200, json=lambda: data))
    server = MCPServer("review-test")
    itinerary.register(server)
    result = asyncio.run(server.call_tool("itinerary.get_itinerary", {"params": {"trip_id": 12}})).structured_content
    assert result["ok"] is True
    assert result["stops"][0] == {"id": 1, "day": 1, "activity": "Park walk", "notes": "Outdoor path", "sortOrder": 0}
    assert "Private name" not in str(result)
    data["stops"][1]["id"] = 1
    result = asyncio.run(server.call_tool("itinerary.get_itinerary", {"params": {"trip_id": 12}})).structured_content
    assert result["error"]["code"] == "invalid_dependency_response"


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


def test_overview_preserves_summary_when_weather_fails(monkeypatch):
    from unittest.mock import Mock

    monkeypatch.setattr(itinerary.requests, "get", lambda *args, **kwargs: Mock(status_code=200, json=trip))
    monkeypatch.setattr("tools.itinerary_weather.read_provider", lambda *args: (_ for _ in ()).throw(requests.Timeout()))
    server = MCPServer("overview-test")
    itinerary.register(server)
    result = asyncio.run(server.call_tool("itinerary.get_overview", {"params": {"trip_id": 12}})).structured_content
    assert result["ok"] is True
    assert result["summary"]["unplannedDays"] == [3]
    assert result["weather"]["status"] == "unavailable"
    assert result["weather"]["days"] == []


@pytest.fixture
def weather_provider(monkeypatch):
    today = datetime.now(timezone.utc).date()
    location = {"id": 1850147, "name": "Tokyo", "country": "Japan", "admin1": "Tokyo",
                "latitude": 35.68, "longitude": 139.69}
    dates = [(today + timedelta(days=offset)).isoformat() for offset in range(16)]
    forecast = {"daily": {"time": dates, "weather_code": [3] * 16, "temperature_2m_min": [10.0] * 16,
                          "temperature_2m_max": [20.0] * 16, "precipitation_probability_max": [30.0] * 16},
                "daily_units": {"weather_code": "wmo code", "temperature_2m_min": "\u00b0C",
                                "temperature_2m_max": "\u00b0C", "precipitation_probability_max": "%"}}
    geocoding = {"results": [location]}
    calls = []

    def provider(url, params, deadline):
        calls.append((url, params))
        return geocoding if "geocoding-api" in url else forecast

    monkeypatch.setattr(weather, "read_provider", provider)
    summary = {"destination": "Tokyo", "startDate": dates[0], "dayCount": 3}
    return summary, geocoding, forecast, calls


def test_weather_uses_fixed_provider_urls_and_only_destination_coordinates(weather_provider):
    summary, geocoding, forecast, calls = weather_provider
    result = weather.trip_weather(summary)
    assert result["status"] == "available"
    assert len(result["days"]) == 3
    assert result["unavailableDates"] == []
    assert result["days"][0]["precipitationProbability"] == 30.0
    assert calls[0] == ("https://geocoding-api.open-meteo.com/v1/search", {
        "name": "Tokyo", "count": 5, "language": "en", "format": "json"})
    assert calls[1][0] == "https://api.open-meteo.com/v1/forecast"
    assert calls[1][1]["timezone"] == "auto"
    assert calls[1][1]["forecast_days"] == 16
    assert "trip_id" not in calls[1][1]


def test_ambiguous_destination_defaults_to_first_result(weather_provider):
    summary, geocoding, forecast, calls = weather_provider
    geocoding["results"].append({**geocoding["results"][0], "id": 123, "country": "Other country"})
    result = weather.trip_weather(summary)
    assert result["status"] == "available"
    assert result["location"] == geocoding["results"][0]
    assert len(calls) == 2
    result = weather.trip_weather(summary, 999)
    assert result["status"] == "choose_location"
    assert result["location"] is None
    result = weather.trip_weather(summary, 123)
    assert result["location"]["country"] == "Other country"
    assert result["status"] == "available"


def test_missing_destination_does_not_call_forecast(weather_provider):
    summary, geocoding, forecast, calls = weather_provider
    geocoding.clear()
    assert weather.trip_weather(summary)["status"] == "not_found"
    assert len(calls) == 1


@pytest.mark.parametrize("offset,status,available", [(14, "partial", 2), (16, "outside_window", 0), (-3, "outside_window", 0)])
def test_forecast_window_never_invents_missing_days(weather_provider, offset, status, available):
    summary, geocoding, forecast, calls = weather_provider
    summary["startDate"] = (datetime.now(timezone.utc).date() + timedelta(days=offset)).isoformat()
    result = weather.trip_weather(summary)
    assert result["status"] == status
    assert len(result["days"]) == available
    assert len(result["unavailableDates"]) == 3 - available


def test_null_forecast_values_are_not_zeroes(weather_provider):
    summary, geocoding, forecast, calls = weather_provider
    forecast["daily"]["precipitation_probability_max"][0] = None
    result = weather.trip_weather(summary)
    assert result["days"][0]["precipitationProbability"] is None
    for field in forecast["daily"]:
        if field != "time":
            forecast["daily"][field] = [None] * 16
    result = weather.trip_weather(summary)
    assert result["status"] == "unavailable"
    assert result["retrievedAt"] is None


@pytest.mark.parametrize("field,value", [("temperature_2m_min", 25.0), ("temperature_2m_max", float("nan")),
                                        ("weather_code", True), ("precipitation_probability_max", 101)])
def test_invalid_forecast_values_are_unavailable(weather_provider, field, value):
    summary, geocoding, forecast, calls = weather_provider
    forecast["daily"][field][0] = value
    assert weather.trip_weather(summary)["status"] == "unavailable"


def test_mismatched_arrays_and_wrong_units_are_unavailable(weather_provider):
    summary, geocoding, forecast, calls = weather_provider
    forecast["daily"]["weather_code"].pop()
    assert weather.trip_weather(summary)["status"] == "unavailable"
    forecast["daily"]["weather_code"].append(3)
    forecast["daily_units"]["temperature_2m_min"] = "F"
    assert weather.trip_weather(summary)["status"] == "unavailable"


@pytest.mark.parametrize("invalid_date", ["9999-12-31", "0001-01-01", "not-a-date"])
def test_invalid_provider_dates_preserve_overview_summary(weather_provider, monkeypatch, invalid_date):
    from unittest.mock import Mock

    summary, geocoding, forecast, calls = weather_provider
    forecast["daily"]["time"] = [invalid_date] * 16
    monkeypatch.setattr(itinerary.requests, "get", lambda *args, **kwargs: Mock(status_code=200, json=trip))
    server = MCPServer("invalid-weather-date-test")
    itinerary.register(server)
    result = asyncio.run(server.call_tool("itinerary.get_overview", {"params": {"trip_id": 12}})).structured_content
    assert result["ok"] is True
    assert result["summary"]["unplannedDays"] == [3]
    assert result["weather"]["status"] == "unavailable"
    assert result["weather"]["days"] == []
    assert result["weather"]["retrievedAt"] is None


@pytest.mark.parametrize("params", [{"trip_id": 12, "location_id": True}, {"trip_id": 12, "latitude": 0},
                                     {"trip_id": 12, "location_id": -1}])
def test_overview_rejects_unknown_arguments_before_any_io(monkeypatch, params):
    monkeypatch.setattr(itinerary.requests, "get", lambda *args, **kwargs: pytest.fail("Unexpected network call"))
    server = MCPServer("overview-boundary-test")
    itinerary.register(server)
    with pytest.raises(ToolError):
        asyncio.run(server.call_tool("itinerary.get_overview", {"params": params}))


def test_provider_rejects_redirects_and_stops_oversized_stream(monkeypatch):
    from unittest.mock import Mock
    from time import monotonic

    response = Mock(status_code=302)
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    get = Mock(return_value=response)
    monkeypatch.setattr(weather.requests, "get", get)
    original = weather.read_provider
    with pytest.raises(ValueError):
        original("https://api.open-meteo.com/v1/forecast", {}, monotonic() + 8)
    assert get.call_args.kwargs["allow_redirects"] is False
    response.status_code = 200
    consumed = []

    def chunks(chunk_size):
        for index in range(100):
            consumed.append(index)
            yield b"x" * chunk_size

    response.iter_content = chunks
    with pytest.raises(ValueError):
        original("https://api.open-meteo.com/v1/forecast", {}, monotonic() + 8)
    assert len(consumed) == 17
    assert response.__exit__.call_count == 2