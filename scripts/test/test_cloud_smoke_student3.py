"""Offline tests for the Student 3 section of scripts/deploy/smoke_cloud.py."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("smoke_cloud", Path(__file__).resolve().parents[1] / "deploy" / "smoke_cloud.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

API = "/attractions-api"
OFF = {"aiEnabled": False, "mcpEnabled": False, "ragEnabled": False, "multiAgentEnabled": False}


class FakeGateway:
    """Answers the Student 3 routes like a baseline cloud deployment and records each call."""

    def __init__(self, capabilities=OFF, source="fallback", attractions=12, keep_name=False,
                 review_ids=(5,), disabled_status=503):
        self.capabilities, self.source, self.attractions = capabilities, source, attractions
        self.keep_name, self.review_ids, self.disabled_status = keep_name, list(review_ids), disabled_status
        self.calls = []
        self.name = None
        self.rating = None
        self.deleted = False

    def __call__(self, path, method="GET", body=None, expected=200):
        self.calls.append((method, path))
        if method == "POST" and path == f"{API}/attractions":
            self.name, self.rating = body["name"], body["rating"]
            status, response = 201, {"id": 7, "name": body["name"], "rating": body["rating"]}
        elif method == "PUT" and path == f"{API}/attractions/7":
            if not self.keep_name:
                self.name, self.rating = body["name"], body["rating"]
            status, response = 200, {"id": 7}
        elif method == "GET" and path == f"{API}/attractions/7":
            status, response = (404, None) if self.deleted else (200, {"id": 7, "name": self.name, "rating": self.rating})
        elif method == "DELETE" and path == f"{API}/attractions/7":
            self.deleted = True
            status, response = 204, None
        else:
            status, response = {
                ("GET", f"{API}/capabilities"): (200, self.capabilities),
                ("GET", f"{API}/attractions"): (200, [{}] * self.attractions),
                ("POST", f"{API}/recommend"): (200, {"source": self.source, "recommendation": "Try the Opera House."}),
                ("POST", f"{API}/mcp/invoke"): (self.disabled_status, None),
                ("POST", f"{API}/rag/ask"): (self.disabled_status, None),
                ("POST", f"{API}/agents/workflows"): (self.disabled_status, None),
                ("POST", f"{API}/reviews"): (201, {"id": 5, "attraction_id": 7}),
                ("GET", f"{API}/reviews?attraction_id=7"): (200, [{"id": i} for i in self.review_ids]),
            }[(method, path)]
        if status != expected:
            raise RuntimeError(f"{method} {path}: expected {expected}, received {status}")
        return response


def test_student3_check_passes_for_baseline_and_deletes_its_attraction():
    gateway = FakeGateway()

    module.check_student3(gateway)

    assert ("DELETE", f"{API}/attractions/7") in gateway.calls
    assert gateway.calls[-1] == ("GET", f"{API}/attractions/7")  # the 404 readback after deletion


@pytest.mark.parametrize("flag", list(OFF))
def test_student3_check_fails_when_any_ai_capability_is_enabled(flag):
    gateway = FakeGateway(capabilities={**OFF, flag: True})

    with pytest.raises(RuntimeError, match="disable every Student 3 AI capability"):
        module.check_student3(gateway)

    assert not any(method == "POST" for method, _ in gateway.calls)  # nothing was created


def test_student3_check_requires_the_seeded_demonstration_catalogue():
    with pytest.raises(RuntimeError, match="At least ten demonstration attractions"):
        module.check_student3(FakeGateway(attractions=9))


def test_student3_check_fails_when_disabled_ai_does_not_fall_back():
    with pytest.raises(RuntimeError, match="deterministic recommendation"):
        module.check_student3(FakeGateway(source="ai"))


@pytest.mark.parametrize("route", ["/mcp/invoke", "/rag/ask", "/agents/workflows"])
def test_student3_check_fails_when_an_ai_route_answers_instead_of_503(route):
    class Leaky(FakeGateway):
        def __call__(self, path, method="GET", body=None, expected=200):
            if path == f"{API}{route}":
                self.calls.append((method, path))
                if expected == 503:
                    raise RuntimeError(f"{method} {path}: expected 503, received 200")
            return super().__call__(path, method, body, expected)

    with pytest.raises(RuntimeError, match="expected 503"):
        module.check_student3(Leaky())


def test_student3_check_deletes_the_attraction_when_a_later_check_fails():
    gateway = FakeGateway(keep_name=True)

    with pytest.raises(RuntimeError, match="Update/readback"):
        module.check_student3(gateway)

    assert gateway.deleted


def test_student3_check_fails_and_cleans_up_when_the_review_is_not_listed():
    gateway = FakeGateway(review_ids=())

    with pytest.raises(RuntimeError, match="Review create/readback"):
        module.check_student3(gateway)

    assert gateway.deleted
