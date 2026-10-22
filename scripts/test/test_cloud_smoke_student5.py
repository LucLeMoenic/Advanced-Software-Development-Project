"""Offline tests for the Student 5 section of scripts/deploy/smoke_cloud.py."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("smoke_cloud", Path(__file__).resolve().parents[1] / "deploy" / "smoke_cloud.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

API = "/logistics/api"
CREATED = f"{API}/destinations/99"
DISABLED = {"advisory": ("POST", f"{API}/advisory", "ai_disabled"),
            "mcp": ("GET", f"{API}/mcp/tools", "mcp_disabled"),
            "rag": ("POST", f"{API}/rag/ask", "rag_disabled"),
            "multi-agent": ("POST", f"{API}/destinations/1/readiness-reviews", "multi_agent_disabled")}


class FakeGateway:
    """Answers the Student 5 routes like a baseline cloud deployment and records each call."""

    def __init__(self, destinations=12, weather=True, transit=True, leaks=(), bare=(),
                 keep_update=False, keep_row=False, corrupt=None, error_on=None):
        self.destinations, self.weather, self.transit = destinations, weather, transit
        self.leaks = set(leaks)  # AI routes that wrongly answer 200 instead of 503
        self.bare = set(bare)  # AI routes that answer 503 without their disabled body, like a backend that is down
        self.keep_update, self.keep_row = keep_update, keep_row
        self.corrupt = corrupt  # "create" stores another country; "update" drops the country on PUT
        self.error_on = error_on  # a method on the created row that answers 500
        self.row = None
        self.deleted = False
        self.calls = []

    def __call__(self, path, method="GET", body=None, expected=200):
        self.calls.append((method, path))
        routes = {
            ("GET", f"{API}/destinations"): (200, [{"id": i + 1} for i in range(self.destinations)]),
            ("GET", f"{API}/weather-notes"): (200, [{"id": 1}] if self.weather else []),
            ("GET", f"{API}/transit-options"): (200, [{"id": 1}] if self.transit else []),
            ("POST", f"{API}/destinations"): (201, {"id": 99, **(body or {})}),
            ("GET", CREATED): (404, None) if self.deleted and not self.keep_row else (200, self.row),
            ("PUT", CREATED): (200, None),
            ("DELETE", CREATED): (204, None),
        }
        for name, (route_method, route, code) in DISABLED.items():
            refusal = b"<html>503</html>" if name in self.bare else {"error": code, "message": "Disabled."}
            routes[(route_method, route)] = (200, {}) if name in self.leaks else (503, refusal)
        status, response = routes[(method, path)]
        if path == CREATED and method == self.error_on and not self.deleted:
            status = 500
        if (method, path) == ("POST", f"{API}/destinations"):
            self.row = {**response, "country": "Elsewhere"} if self.corrupt == "create" else dict(response)
        if method == "PUT" and not self.keep_update:
            self.row = {**self.row, **body}
            if self.corrupt == "update":
                self.row.pop("country")
        if method == "DELETE":
            self.deleted = True
        if status != expected:
            raise RuntimeError(f"{method} {path}: expected {expected}, received {status}")
        return response


def test_student5_check_passes_for_baseline_and_deletes_its_destination():
    gateway = FakeGateway()

    module.check_student5(gateway)

    assert ("PUT", CREATED) in gateway.calls
    assert gateway.calls[-2:] == [("DELETE", CREATED), ("GET", CREATED)]
    # Every AI refusal is checked before the only write is made.
    create = gateway.calls.index(("POST", f"{API}/destinations"))
    assert {(method, path) for method, path, _ in DISABLED.values()} <= set(gateway.calls[:create])


def test_student5_check_requires_the_seeded_demonstration_destinations():
    with pytest.raises(RuntimeError, match="At least ten demonstration destinations"):
        module.check_student5(FakeGateway(destinations=9))


@pytest.mark.parametrize(("option", "table"), [({"weather": False}, "weather-notes"), ({"transit": False}, "transit-options")])
def test_student5_check_fails_when_reference_data_is_empty(option, table):
    with pytest.raises(RuntimeError, match=f"{table} reference data is empty"):
        module.check_student5(FakeGateway(**option))


@pytest.mark.parametrize("route", DISABLED)
def test_student5_check_fails_without_writing_when_any_ai_route_is_enabled(route):
    # Leak each route on its own so every one of the four assertions is shown to matter.
    gateway = FakeGateway(leaks=[route])

    with pytest.raises(RuntimeError, match="expected 503, received 200"):
        module.check_student5(gateway)

    assert ("POST", f"{API}/destinations") not in gateway.calls


@pytest.mark.parametrize("route", DISABLED)
def test_student5_check_fails_when_a_503_is_not_the_disabled_body(route):
    with pytest.raises(RuntimeError, match=f"expected the {DISABLED[route][2]} body"):
        module.check_student5(FakeGateway(bare=[route]))


@pytest.mark.parametrize(("option", "message"), [({"keep_update": True}, "Update/readback did not preserve"),
                                                 ({"corrupt": "update"}, "Update/readback did not preserve"),
                                                 ({"corrupt": "create"}, "Destination create/readback failed"),
                                                 ({"error_on": "GET"}, f"GET {CREATED}: expected 200, received 500"),
                                                 ({"error_on": "PUT"}, f"PUT {CREATED}: expected 200, received 500")])
def test_student5_check_deletes_the_destination_when_a_later_step_fails(option, message):
    gateway = FakeGateway(**option)

    with pytest.raises(RuntimeError, match=message):
        module.check_student5(gateway)

    assert gateway.deleted


def test_student5_check_fails_when_the_deleted_destination_is_still_readable():
    gateway = FakeGateway(keep_row=True)

    with pytest.raises(RuntimeError, match=f"GET {CREATED}: expected 404, received 200"):
        module.check_student5(gateway)
