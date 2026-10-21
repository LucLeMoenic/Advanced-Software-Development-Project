"""Offline tests for the Student 5 section of scripts/deploy/smoke_cloud.py."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("smoke_cloud", Path(__file__).resolve().parents[1] / "deploy" / "smoke_cloud.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

API = "/logistics/api"


class FakeGateway:
    """Answers the Student 5 routes like a baseline cloud deployment and records each call."""

    def __init__(self, destinations=12, readback_id=1, weather=True, transit=True, leaks=()):
        self.destinations, self.readback_id = destinations, readback_id
        self.weather, self.transit = weather, transit
        self.leaks = set(leaks)  # AI routes that wrongly answer 200 instead of 503
        self.calls = []

    def __call__(self, path, method="GET", body=None, expected=200):
        self.calls.append((method, path))
        status, response = {
            ("GET", f"{API}/destinations"): (200, [{"id": i + 1} for i in range(self.destinations)]),
            ("GET", f"{API}/destinations/1"): (200, {"id": self.readback_id}),
            ("GET", f"{API}/weather-notes"): (200, [{"id": 1}] if self.weather else []),
            ("GET", f"{API}/transit-options"): (200, [{"id": 1}] if self.transit else []),
            ("GET", f"{API}/mcp/tools"): (200 if "mcp" in self.leaks else 503, None),
            ("POST", f"{API}/rag/ask"): (200 if "rag" in self.leaks else 503, None),
            ("POST", f"{API}/advisory"): (200 if "advisory" in self.leaks else 503, None),
        }[(method, path)]
        if status != expected:
            raise RuntimeError(f"{method} {path}: expected {expected}, received {status}")
        return response


def test_student5_check_passes_for_baseline_and_changes_no_data():
    gateway = FakeGateway()

    module.check_student5(gateway)

    # Student 5 has no delete, so the only POSTs allowed are the two AI routes expected to be refused.
    posts = [path for method, path in gateway.calls if method == "POST"]
    assert posts == [f"{API}/rag/ask", f"{API}/advisory"]


def test_student5_check_requires_the_seeded_demonstration_destinations():
    with pytest.raises(RuntimeError, match="At least ten demonstration destinations"):
        module.check_student5(FakeGateway(destinations=9))


def test_student5_check_fails_when_a_destination_cannot_be_read_back():
    with pytest.raises(RuntimeError, match="Destination readback failed"):
        module.check_student5(FakeGateway(readback_id=2))


@pytest.mark.parametrize(("option", "table"), [({"weather": False}, "weather-notes"), ({"transit": False}, "transit-options")])
def test_student5_check_fails_when_reference_data_is_empty(option, table):
    with pytest.raises(RuntimeError, match=f"{table} reference data is empty"):
        module.check_student5(FakeGateway(**option))


@pytest.mark.parametrize("route", ["mcp", "rag", "advisory"])
def test_student5_check_fails_when_any_single_ai_route_answers_instead_of_503(route):
    # Leak each route on its own so every one of the three assertions is shown to matter.
    with pytest.raises(RuntimeError, match="expected 503, received 200"):
        module.check_student5(FakeGateway(leaks=[route]))
