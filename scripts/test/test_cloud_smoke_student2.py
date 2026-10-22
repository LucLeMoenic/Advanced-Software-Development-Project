import pytest

import smoke_cloud


class Gateway:
    def __init__(self, enabled=frozenset(), generation=None):
        self.enabled = enabled
        self.generation = generation or ("ai" if "ai" in enabled else "fallback")
        self.calls = []
        self.deleted = False
        self.trip = None

    def __call__(self, path, method="GET", body=None, expected=200):
        self.calls.append((path, method, expected))
        status, result = self.route(path, method, body)
        assert status == expected, (path, status, expected)
        return result

    def route(self, path, method, body):
        if path in ("/", "/accommodation/", "/itinerary/", "/attractions/", "/budget/", "/logistics/"):
            return 200, b"page"
        if path == "/itinerary-api/capabilities":
            return 200, smoke_cloud.capabilities(self.enabled)
        if path == "/itinerary-api/trips" and method == "GET":
            return 200, [{"id": 1}] * 10
        if path == "/itinerary-api/trips" and method == "POST":
            self.trip = {**body, "id": 99, "generationMode": self.generation, "stops": [{"id": i} for i in range(4)]}
            return 201, dict(self.trip)
        if path == "/itinerary-api/trips/99":
            if method == "DELETE":
                self.deleted = True
                return 204, None
            if method == "PUT":
                self.trip.update(body)
            return (404, None) if self.deleted else (200, dict(self.trip))
        if path == "/itinerary-api/trips/99/stops":
            return 201, {"id": 100}
        if path == "/itinerary-api/stops/100":
            return (204, None) if method == "DELETE" else (200, {})
        if path.endswith(("/edit-preview", "/edit-operation-preview", "/edit-confirm", "/itinerary-advice")) or "/multi-agent-workflows/" in path:
            return 503, {}
        raise AssertionError(f"Unexpected route {path}")


@pytest.fixture
def itinerary_only(monkeypatch):
    for number in (1, 3, 4, 5):
        monkeypatch.setattr(smoke_cloud, f"check_student{number}", lambda call, enabled: None)


@pytest.mark.parametrize("enabled", [frozenset(), frozenset({"ai", "mcp", "rag", "multi-agent"})])
def test_selected_profile_checks_generation_and_crud_and_removes_fixture(itinerary_only, enabled):
    gateway = Gateway(enabled)
    smoke_cloud.run("https://example.org", enabled=enabled, call=gateway)
    assert gateway.deleted
    assert any(method == "PUT" for _, method, _ in gateway.calls)
    assert any(status == 503 for _, _, status in gateway.calls) == (not enabled)


def test_fallback_cannot_pass_ai_deployment_and_fixture_is_removed(itinerary_only):
    enabled = frozenset({"ai", "mcp", "rag", "multi-agent"})
    gateway = Gateway(enabled, generation="fallback")
    with pytest.raises(RuntimeError, match="generation did not match"):
        smoke_cloud.run("https://example.org", enabled=enabled, call=gateway)
    assert gateway.deleted
