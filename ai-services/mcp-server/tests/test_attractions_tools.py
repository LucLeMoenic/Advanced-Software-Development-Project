"""Input-validation tests for Student 3's MCP tools.

Never calls the live student-3 database service: `attractions.requests.get`
is always mocked, so these tests run offline and deterministically, the
same convention student-3's own test_recommend.py uses for Ollama.
"""

import asyncio

import pytest
import requests

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from tools import attractions

SAMPLE_ATTRACTIONS = [
    {"id": 1, "name": "Sydney Opera House", "category": "sight", "description": "d", "rating": 4.7},
    {"id": 2, "name": "Chat Thai", "category": "restaurant", "description": "d", "rating": 4.3},
]


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError("bad status")

    def json(self):
        return self._payload


@pytest.fixture
def server():
    server = MCPServer("test-attractions-server")
    attractions.register(server)
    return server


def call(server, tool_name, params):
    return asyncio.run(server.call_tool(tool_name, {"params": params}))


def test_search_returns_attractions(server, monkeypatch):
    monkeypatch.setattr(attractions.requests, "get", lambda *a, **k: FakeResponse(SAMPLE_ATTRACTIONS))

    result = call(server, "attractions.search", {"category": "sight"})

    assert result.is_error is False
    assert result.structured_content["attractions"] == SAMPLE_ATTRACTIONS


def test_search_rejects_unknown_category(server):
    with pytest.raises(ToolError):
        call(server, "attractions.search", {"category": "museum"})


@pytest.mark.parametrize("limit", [0, 11, -1])
def test_search_rejects_limit_out_of_range(server, limit):
    with pytest.raises(ToolError):
        call(server, "attractions.search", {"limit": limit})


def test_search_rejects_unknown_field(server):
    with pytest.raises(ToolError):
        call(server, "attractions.search", {"category": "sight", "sort": "asc"})


def test_search_caps_results_to_limit(server, monkeypatch):
    many = [dict(a, id=i) for i, a in enumerate(SAMPLE_ATTRACTIONS * 5)]
    monkeypatch.setattr(attractions.requests, "get", lambda *a, **k: FakeResponse(many))

    result = call(server, "attractions.search", {"limit": 3})

    assert len(result.structured_content["attractions"]) == 3


def test_search_reports_total_matches_before_limit_is_applied(server, monkeypatch):
    many = [dict(a, id=i) for i, a in enumerate(SAMPLE_ATTRACTIONS * 5)]
    monkeypatch.setattr(attractions.requests, "get", lambda *a, **k: FakeResponse(many))

    result = call(server, "attractions.search", {"limit": 3})

    assert result.structured_content["total_matches"] == len(many)
    assert len(result.structured_content["attractions"]) == 3


def test_search_reports_total_matches_after_min_rating_filter(server, monkeypatch):
    monkeypatch.setattr(attractions.requests, "get", lambda *a, **k: FakeResponse(SAMPLE_ATTRACTIONS))

    result = call(server, "attractions.search", {"min_rating": 4.5, "limit": 5})

    assert result.structured_content["total_matches"] == 1


def test_search_filters_by_min_rating(server, monkeypatch):
    monkeypatch.setattr(attractions.requests, "get", lambda *a, **k: FakeResponse(SAMPLE_ATTRACTIONS))

    result = call(server, "attractions.search", {"min_rating": 4.5})

    names = [a["name"] for a in result.structured_content["attractions"]]
    assert names == ["Sydney Opera House"]


def test_search_reports_database_unavailable(server, monkeypatch):
    def raise_connection_error(*args, **kwargs):
        raise requests.exceptions.ConnectionError("refused")

    monkeypatch.setattr(attractions.requests, "get", raise_connection_error)

    with pytest.raises(ToolError):
        call(server, "attractions.search", {})


def test_get_reviews_returns_reviews(server, monkeypatch):
    attraction = {
        "id": 3,
        "name": "Mr. Wong",
        "reviews": [{"id": 1, "attraction_id": 3, "rating": 5.0, "comment": "great"}],
    }
    monkeypatch.setattr(attractions.requests, "get", lambda *a, **k: FakeResponse(attraction))

    result = call(server, "attractions.get_reviews", {"attraction_id": 3})

    assert result.structured_content["reviews"] == attraction["reviews"]


def test_get_reviews_rejects_missing_attraction(server, monkeypatch):
    monkeypatch.setattr(attractions.requests, "get", lambda *a, **k: FakeResponse({}, status_code=404))

    with pytest.raises(ToolError):
        call(server, "attractions.get_reviews", {"attraction_id": 999})


def test_get_reviews_rejects_unknown_field(server):
    with pytest.raises(ToolError):
        call(server, "attractions.get_reviews", {"attraction_id": 1, "verbose": True})


def test_get_reviews_rejects_wrong_type(server):
    with pytest.raises(ToolError):
        call(server, "attractions.get_reviews", {"attraction_id": "not-an-int"})
