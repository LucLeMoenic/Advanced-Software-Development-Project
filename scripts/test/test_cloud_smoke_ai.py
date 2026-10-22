"""Offline tests for scripts/deploy/smoke_cloud_ai.py (the B1 to B4 cloud AI verification)."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("smoke_cloud_ai", Path(__file__).resolve().parents[1] / "deploy" / "smoke_cloud_ai.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

API = "/attractions-api"
ALL = frozenset(module.COMPONENTS)
WORKFLOW = "wf-20261021T000000Z-0123abcd"


class FakeGateway:
    """Behaves like a deployment with `enabled` components, with one deliberate fault injectable at a time."""

    def __init__(self, enabled=ALL, **faults):
        self.enabled, self.faults = frozenset(enabled), faults
        self.calls = []
        self.polls = 0

    def __call__(self, path, method="GET", body=None, expected=200):
        self.calls.append((method, path))
        status, response = self.route(path, method, body)
        if status != expected:
            raise RuntimeError(f"{method} {path}: expected {expected}, received {status}")
        return response

    def on(self, component):
        return component in self.enabled

    def route(self, path, method, body):
        f = self.faults
        if path == f"{API}/capabilities":
            flags = {"aiEnabled": self.on("ai"), "mcpEnabled": self.on("mcp"), "ragEnabled": self.on("rag"),
                     "multiAgentEnabled": self.on("multi-agent")}
            return 200, {**flags, **f.get("capabilities", {})}
        if path == f"{API}/recommend":
            source = f.get("source", "ai" if self.on("ai") else "fallback")
            return 200, {"source": source, "recommendation": f.get("recommendation", "Try Chin Chin.")}
        if path == f"{API}/mcp/tools":
            return (200, {"tools": f.get("tools", ["attractions.search", "attractions.get_reviews"])}) if self.on("mcp") else (503, None)
        if path == f"{API}/mcp/invoke":
            rows = f.get("rows", [{"category": "restaurant"}, {"category": "restaurant"}])
            return (200, {"tool": "attractions.search", "result": {"attractions": rows, "total_matches": f.get("total", len(rows))}}) \
                if self.on("mcp") else (503, {"error": "mcp_disabled"})
        if path == f"{API}/rag/ask":
            answer = {"answer": f.get("answer", "It is popular; book ahead. [c1]"), "confidence": f.get("confidence", "high"),
                      "citations": f.get("citations", [{"source": "x"}])}
            return (200, answer) if self.on("rag") else (503, {"error": "rag_disabled"})
        if (method, path) == ("POST", f"{API}/agents/workflows"):
            return (202, {"id": WORKFLOW}) if self.on("multi-agent") else (503, {"error": "multi_agent_disabled"})
        if path == f"{API}/agents/workflows/{WORKFLOW}" and method == "GET":
            self.polls += 1
            if f.get("stuck"):
                return 200, {"status": "working"}
            if self.polls < f.get("polls_until_ready", 3):
                return 200, {"status": "working"}
            if f.get("failed"):
                return 200, {"status": "failed", "error": {"stage": "working", "code": "dependency_timeout", "message": "timed out"}}
            return 200, {"status": "awaiting_human_review", "plan": f.get("plan", {"objective": "o"}), "work": {"items": []},
                         "review": {"verdict": "pass"},
                         "human_decision": f.get("human_decision"),
                         "history": f.get("history", [{"stage": "planner"}, {"stage": "worker"}, {"stage": "reviewer"}])}
        if path == f"{API}/agents/workflows/{WORKFLOW}/decision":
            return 200, {"status": f.get("decided", "approved"), "final_output": f.get("final", {"items": []})}
        raise AssertionError(f"unexpected call {method} {path}")


def run(gateway, enabled=None):
    module.run("https://cloud.example", gateway.enabled if enabled is None else enabled, call=gateway)


def no_sleep(monkeypatch):
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)


@pytest.fixture(autouse=True)
def fast_polling(monkeypatch):
    monkeypatch.setattr(module, "POLL_SECONDS", 0)


# -- parsing and input safety ------------------------------------------------------------------------------------------

@pytest.mark.parametrize(("text", "expected"), [("ai", {"ai"}), (" ai , rag ", {"ai", "rag"}), ("ai,mcp,rag,multi-agent", set(ALL))])
def test_components_are_parsed(text, expected):
    assert module.parse_components(text) == expected


@pytest.mark.parametrize("text", ["", " , ", "all", "AI", "multi_agent", "ai,bogus"])
def test_empty_or_unknown_components_are_rejected(text):
    with pytest.raises(ValueError, match="Choose from"):
        module.parse_components(text)


@pytest.mark.parametrize("origin", ["http://example.org", "example.org", "https://example.org/path", "https://example.org?x=1", "ftp://x"])
def test_only_a_plain_https_origin_is_accepted(origin):
    with pytest.raises(ValueError, match="HTTPS origin"):
        module.make_call(origin)


# -- every enabled component, and each on its own ---------------------------------------------------------------------------

def test_a_full_cloud_ai_deployment_passes_and_prints_each_bonus(capsys):
    run(FakeGateway(ALL))

    output = capsys.readouterr().out
    for line in ("B1 AI-Mode", "B2 MCP", "B3 RAG", "B4 Multi-Agent"):
        assert line in output
    assert "still report disabled" not in output  # nothing is disabled


@pytest.mark.parametrize("component", sorted(ALL))
def test_each_component_can_be_enabled_and_verified_on_its_own(component, capsys):
    run(FakeGateway({component}))

    output = capsys.readouterr().out
    assert "still report disabled" in output
    assert all(c in output for c in ALL - {component})


def test_a_component_that_is_off_is_never_exercised_beyond_its_disabled_response():
    gateway = FakeGateway({"mcp"})

    run(gateway)

    assert ("POST", f"{API}/agents/workflows") in gateway.calls and ("GET", f"{API}/agents/workflows/{WORKFLOW}") not in gateway.calls
    assert not any(path.endswith("/decision") for _, path in gateway.calls)


# -- capabilities -----------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("flag", ["aiEnabled", "mcpEnabled", "ragEnabled", "multiAgentEnabled"])
def test_capabilities_that_disagree_with_the_prepared_components_fail(flag):
    gateway = FakeGateway({"ai"}, capabilities={flag: True, "aiEnabled": True} if flag != "aiEnabled" else {"aiEnabled": False})

    with pytest.raises(RuntimeError, match="capabilities do not match"):
        run(gateway)


# -- B1 AI-Mode ------------------------------------------------------------------------------------------------------------------

def test_the_deterministic_fallback_is_not_accepted_as_ai_and_the_error_says_what_to_check():
    with pytest.raises(RuntimeError, match="not the model.*pull-models-vm.sh"):
        run(FakeGateway(ALL, source="fallback"))


def test_a_retried_model_answer_counts_as_ai():
    run(FakeGateway(ALL, source="ai_retry"))


def test_an_empty_ai_recommendation_fails():
    with pytest.raises(RuntimeError, match="not the model"):
        run(FakeGateway(ALL, recommendation="   "))


# -- B2 MCP ----------------------------------------------------------------------------------------------------------------------

def test_mcp_must_list_the_attractions_tool():
    with pytest.raises(RuntimeError, match="did not list"):
        run(FakeGateway(ALL, tools=["something.else"]))


@pytest.mark.parametrize("rows", [[], [{"category": "sight"}], [{"category": "restaurant"}, {"category": "activity"}]])
def test_mcp_must_return_only_restaurant_rows_and_at_least_one(rows):
    with pytest.raises(RuntimeError, match="restaurant data"):
        run(FakeGateway(ALL, rows=rows))


def test_mcp_total_matches_must_cover_the_returned_rows():
    with pytest.raises(RuntimeError, match="total_matches"):
        run(FakeGateway(ALL, rows=[{"category": "restaurant"}] * 3, total=1))


# -- B3 RAG ----------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("fault", [{"confidence": "insufficient"}, {"citations": []}, {"answer": ""}])
def test_rag_must_give_a_grounded_answer_with_citations(fault):
    with pytest.raises(RuntimeError, match="grounded answer"):
        run(FakeGateway(ALL, **fault))


# -- B4 Multi-Agent ---------------------------------------------------------------------------------------------------------------

def test_the_workflow_is_polled_until_human_review_without_submitting_a_decision(capsys):
    gateway = FakeGateway(ALL, polls_until_ready=5)

    run(gateway)

    assert gateway.polls == 5
    assert not any(p.endswith("/decision") for _, p in gateway.calls)
    assert f"MANUAL: review workflow {API}/agents/workflows/{WORKFLOW}" in capsys.readouterr().out


def test_a_failed_workflow_reports_its_stage_and_code():
    with pytest.raises(RuntimeError, match="failed at working: dependency_timeout"):
        run(FakeGateway(ALL, failed=True))


def test_a_workflow_that_never_finishes_times_out_without_any_real_waiting():
    clock = iter(range(0, 100000, 400))  # a fake clock that jumps 400 seconds per reading
    slept = []

    with pytest.raises(RuntimeError, match="still 'working' after 900 seconds"):
        module.check_multi_agent(FakeGateway(ALL, stuck=True), sleep=slept.append, now=lambda: next(clock))

    assert slept and set(slept) == {module.POLL_SECONDS}  # it did wait between polls, but only on the fake sleep


def test_the_clock_is_resolved_at_call_time_so_patching_it_takes_effect(monkeypatch):
    clock = iter(range(0, 100000, 400))
    monkeypatch.setattr(module.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)

    with pytest.raises(RuntimeError, match="still 'working'"):
        module.check_multi_agent(FakeGateway(ALL, stuck=True))


def test_review_without_a_plan_is_rejected():
    with pytest.raises(RuntimeError, match="without a plan"):
        run(FakeGateway(ALL, plan=None))


def test_history_must_show_all_three_agents_in_order():
    with pytest.raises(RuntimeError, match="Planner, Worker and Reviewer in order"):
        run(FakeGateway(ALL, history=[{"stage": "worker"}, {"stage": "planner"}, {"stage": "reviewer"}]))


def test_a_workflow_with_an_existing_human_decision_is_not_reported_as_pending():
    with pytest.raises(RuntimeError, match="already has a human decision"):
        run(FakeGateway(ALL, human_decision={"decision": "approve"}))


# -- disabled components -------------------------------------------------------------------------------------------------------------

class LeakyGateway(FakeGateway):
    """A component that is not enabled but answers anyway."""

    def route(self, path, method, body):
        if path == f"{API}/mcp/invoke" and "mcp" not in self.enabled:
            return 200, {"result": {}}
        return super().route(path, method, body)


def test_a_component_that_should_be_off_but_answers_is_a_failure():
    with pytest.raises(RuntimeError, match="expected 503, received 200"):
        run(LeakyGateway({"ai"}))


def test_ai_mode_that_should_be_off_must_use_the_fallback():
    with pytest.raises(RuntimeError, match="did not answer with the deterministic fallback"):
        run(FakeGateway({"mcp"}, source="ai"))


# -- the command line --------------------------------------------------------------------------------------------------------------------

def test_main_returns_one_and_names_the_failure_when_a_check_fails(monkeypatch, capsys):
    monkeypatch.setattr(module, "make_call", lambda origin: FakeGateway(ALL, source="fallback"))

    assert module.main(["https://cloud.example", "--components", "ai,mcp,rag,multi-agent"]) == 1
    assert "FAIL:" in capsys.readouterr().out


def test_main_returns_zero_when_everything_passes(monkeypatch):
    monkeypatch.setattr(module, "make_call", lambda origin: FakeGateway({"mcp", "rag"}))

    assert module.main(["https://cloud.example", "--components", "mcp,rag"]) == 0


def test_main_reports_bad_components_as_a_failure_not_a_crash(capsys):
    assert module.main(["https://cloud.example", "--components", "telepathy"]) == 1
    assert "Choose from" in capsys.readouterr().out


class OtherFeaturesGateway:
    def __init__(self, fail_path=None):
        self.calls = []
        self.fail_path = fail_path

    def __call__(self, path, method="GET", body=None, expected=200):
        self.calls.append((path, method, body))
        assert not path.endswith("/decision"), "Smoke tests must not manufacture human decisions."
        if path == self.fail_path:
            raise RuntimeError("injected dependency failure")
        if path in ("/accommodation/api/searches", "/itinerary-api/trips", "/logistics/api/destinations"):
            return [{"id": 1}]
        if path == "/itinerary-api/trips/1":
            return {"id": 1}
        if path == "/budget-api/journeys":
            return [{"journeyLabel": "Demo"}]
        if path == "/logistics/api/advisory":
            return {"advisory": "Recorded advice", "model": "llama3.2:3b"}
        if path == "/accommodation/api/assistant" and body["mode"] == "lookup":
            return {"tool": "accommodation.get_search", "result": {"id": 1}}
        if path.endswith("/mcp-summary"):
            return {"tool": "itinerary.get_summary", "summary": {"tripId": 1}}
        if path == "/budget-api/budget-check":
            return {"tool": "budget.get_summary", "result": {"ok": True}}
        if path == "/logistics/api/mcp/invoke":
            return {"result": {"ok": True}}
        if path in ("/accommodation/api/assistant", "/itinerary-api/itinerary-advice",
                    "/budget-api/budget-guidance", "/logistics/api/rag/ask"):
            return {"answer": "Grounded advice", "citations": [{"source": "test"}], "confidence": "high"}
        if path.endswith("/edit-preview"):
            return {"preview": {"workflowId": WORKFLOW}}
        if method == "POST" and path.endswith(("/reviews", "/readiness-reviews")):
            assert expected == 202
            return {"id": WORKFLOW}
        if WORKFLOW in path:
            return {"status": "awaiting_human_review", "plan": {"objective": "demo"}, "work": {"items": []},
                    "review": {"verdict": "pass"}, "human_decision": None,
                    "history": [{"stage": stage} for stage in ("planner", "worker", "reviewer")]}
        raise AssertionError(f"Unexpected path: {path}")


def test_all_supported_feature_integrations_are_exercised_without_human_decisions(capsys):
    gateway = OtherFeaturesGateway()
    module.check_other_features(gateway, ALL)
    output = capsys.readouterr().out
    assert output.count("MANUAL:") == 3
    assert "Student 4 has no Multi-Agent integration" in output
    assert any(path == "/logistics/api/advisory" for path, _, _ in gateway.calls)
    assert sum(path.endswith("/rag/ask") or path.endswith("/itinerary-advice")
               or path.endswith("/budget-guidance") for path, _, _ in gateway.calls) == 3


@pytest.mark.parametrize("path", ["/logistics/api/advisory", "/accommodation/api/assistant",
                                 "/itinerary-api/trips/1/mcp-summary", "/budget-api/budget-check",
                                 "/logistics/api/mcp/invoke", "/itinerary-api/itinerary-advice",
                                 "/budget-api/budget-guidance", "/logistics/api/rag/ask",
                                 "/accommodation/api/searches/1/reviews", "/itinerary-api/trips/1/edit-preview",
                                 "/logistics/api/destinations/1/readiness-reviews"])
def test_any_feature_dependency_failure_blocks_group_ai_acceptance(path):
    with pytest.raises(RuntimeError, match="injected dependency failure"):
        module.check_other_features(OtherFeaturesGateway(fail_path=path), ALL)


@pytest.mark.parametrize("answer", [
    {"confidence": "insufficient", "citations": [], "answer": "No answer"},
    {"confidence": "high", "citations": [], "answer": "Uncited"},
    {"confidence": "high", "citations": [{"source": "x"}], "answer": ""},
])
def test_grounded_answer_checks_reject_abstention_or_missing_evidence(answer):
    with pytest.raises(RuntimeError, match="grounded answer"):
        module.grounded(answer, "Test feature")


def test_full_group_cli_requires_credentials_before_any_requests(monkeypatch):
    monkeypatch.delenv("CLOUD_AUTH_USER", raising=False)
    monkeypatch.delenv("CLOUD_AUTH_PASSWORD", raising=False)
    monkeypatch.setattr(module, "make_call", lambda *args: pytest.fail("Must reject before network access."))
    assert module.main(["https://cloud.example", "--components", "ai,mcp,rag,multi-agent", "--all-features"]) == 1
