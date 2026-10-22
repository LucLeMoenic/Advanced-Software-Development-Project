"""Offline tests for the Student 1 section of scripts/deploy/smoke_cloud.py."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("smoke_cloud", Path(__file__).resolve().parents[1] / "deploy" / "smoke_cloud.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

API = "/accommodation/api"
OFF = {"aiRanking": False, "lookup": False, "guide": False, "multiAgent": False}


class FakeGateway:
    """Answers the Student 1 routes like a baseline cloud deployment and records each call."""

    def __init__(self, capabilities=OFF, ranking_mode="programmatic", keep_title=False, ai_enabled=False):
        self.capabilities = capabilities
        self.ranking_mode = ranking_mode
        self.keep_title = keep_title
        self.calls = []
        self.title = "Tokyo"
        self.deleted = False
        self.ai_enabled = ai_enabled

    def __call__(self, path, method="GET", body=None, expected=200):
        self.calls.append((method, path))
        results = [{"accommodationId": 51, "rank": 1}]
        routes = {
            ("GET", f"{API}/capabilities"): (200, self.capabilities),
            ("GET", f"{API}/searches"): (200, [{}] * 12),
            ("POST", f"{API}/searches"): (503, None) if body and body.get("useAi") and not self.ai_enabled
            else (201, {"id": 7, "rankingMode": self.ranking_mode, "results": results}),
            ("PATCH", f"{API}/searches/7"): (200, None),
            ("GET", f"{API}/searches/7"): (404, None) if self.deleted else (200, {"title": self.title, "results": results}),
            ("POST", f"{API}/searches/7/reviews"): (503, None),
            ("DELETE", f"{API}/searches/7"): (204, None),
        }
        status, response = routes[(method, path)]
        if method == "PATCH" and not self.keep_title:
            self.title = body["title"]
        if method == "DELETE":
            self.deleted = True
        if status != expected:
            raise RuntimeError(f"{method} {path}: expected {expected}, received {status}")
        return response


def test_student1_check_passes_for_baseline_and_deletes_its_search():
    gateway = FakeGateway()

    module.check_student1(gateway)

    assert ("DELETE", f"{API}/searches/7") in gateway.calls
    assert gateway.calls[-1] == ("GET", f"{API}/searches/7")
    assert ("POST", f"{API}/searches/7/reviews") in gateway.calls


def test_student1_check_fails_when_any_ai_mode_is_enabled():
    gateway = FakeGateway(capabilities={**OFF, "multiAgent": True})

    with pytest.raises(RuntimeError, match="disable every Student 1 AI capability"):
        module.check_student1(gateway)

    assert not any(method == "POST" for method, _ in gateway.calls)


def test_student1_check_deletes_the_search_when_a_later_check_fails():
    gateway = FakeGateway(keep_title=True)

    with pytest.raises(RuntimeError, match="Rename/readback"):
        module.check_student1(gateway)

    assert gateway.deleted


def test_student1_check_fails_when_disabled_ai_does_not_rank_programmatically():
    gateway = FakeGateway(ranking_mode="fallback")

    with pytest.raises(RuntimeError, match="rank the cached Tokyo catalogue"):
        module.check_student1(gateway)

    assert gateway.deleted


@pytest.mark.parametrize("mode", ["ai", "fallback"])
def test_ai_profile_requires_real_ai_ranking_and_still_cleans_up(mode):
    gateway = FakeGateway(capabilities={key: True for key in OFF}, ranking_mode=mode, ai_enabled=True)
    if mode == "ai":
        module.check_student1(gateway, {"ai", "mcp", "rag", "multi-agent"})
    else:
        with pytest.raises(RuntimeError, match="AI ranking failed"):
            module.check_student1(gateway, {"ai", "mcp", "rag", "multi-agent"})
    assert gateway.deleted
