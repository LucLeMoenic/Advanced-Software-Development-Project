"""Offline tests for scripts/deploy/system_test_local.py (the multi-terminal local system test)."""

import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("system_test_local", Path(__file__).resolve().parents[1] / "deploy" / "system_test_local.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

API = module.API


def healthy_fetch(url):
    if url.endswith("/api/tags"):
        return 200, json.dumps({"models": [{"name": module.MODEL}]}).encode()
    if url.endswith(":5600/health"):
        return 200, b'{"status":"ok","busy":false}'
    if url.endswith("/mcp"):
        return 406, b""
    return 200, b'{"status":"ok"}'


class FakeApp:
    """Student 3's attraction API in memory, with one deliberate fault injectable at a time."""

    def __init__(self, **faults):
        self.rows, self.faults, self.calls, self.next_id = {}, faults, [], 1

    def __call__(self, path, method="GET", body=None, expected=200):
        self.calls.append((method, path))
        status, data = self.route(path, method, body)
        if status != expected:
            raise RuntimeError(f"{method} {path}: expected {expected}, received {status}")
        return data

    def route(self, path, method, body):
        if path == f"{API}/attractions" and method == "POST":
            row = {"id": self.next_id, **body}
            self.rows[self.next_id], self.next_id = row, self.next_id + 1
            return 201, row
        if path == f"{API}/attractions" and method == "GET":
            return 200, [] if self.faults.get("missing_from_list") else list(self.rows.values())
        item = int(path.rsplit("/", 1)[1]) if path.startswith(f"{API}/attractions/") else None
        if item is None:
            return 200, b"ok"
        if method == "GET":
            return (200, self.rows[item]) if item in self.rows else (404, None)
        if method == "PUT":
            if self.faults.get("update_fails"):
                return 500, None
            self.rows[item] = {"id": item, **body}
            return 200, self.rows[item]
        if method == "DELETE":
            if self.faults.get("delete_keeps_row"):
                return 204, None
            self.rows.pop(item, None)
            return 204, None
        raise AssertionError(path)


# -- input safety ------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("origin", ["http://localhost:5100", "http://127.0.0.1:5100", "http://localhost"])
def test_loopback_http_origins_are_accepted(origin):
    assert callable(module.make_call(origin))


@pytest.mark.parametrize("origin", ["https://localhost:5100", "http://example.org", "http://192.168.1.5:5100", "localhost:5100",
                                    "http://localhost:5100/path", "http://localhost:5100?x=1", "ftp://localhost"])
def test_only_a_loopback_http_gateway_is_accepted(origin):
    with pytest.raises(ValueError, match="local gateway origin"):
        module.make_call(origin)


# -- native services ---------------------------------------------------------------------------------------------------------------

def test_all_four_native_services_are_checked(capsys):
    module.check_native(healthy_fetch)

    output = capsys.readouterr().out
    assert all(f"native {name}" in output for name in ("ollama", "mcp", "rag", "multi-agent"))


def test_a_missing_model_fails():
    def fetch(url):
        return (200, b'{"models": [{"name": "other:1b"}]}') if url.endswith("/api/tags") else healthy_fetch(url)

    with pytest.raises(RuntimeError, match="does not have llama3.2:3b"):
        module.check_native(fetch)


@pytest.mark.parametrize(("suffix", "status", "match"), [(":5500/health", 503, "rag service answered 503"), ("/mcp", 200, "mcp service answered 200"),
                                                         (":5600/health", 500, "multi-agent service answered 500")])
def test_a_native_service_with_the_wrong_status_fails(suffix, status, match):
    def fetch(url):
        return (status, b"") if url.endswith(suffix) else healthy_fetch(url)

    with pytest.raises(RuntimeError, match=match):
        module.check_native(fetch)


def test_an_unhealthy_multi_agent_body_fails():
    def fetch(url):
        return (200, b'{"status":"degraded"}') if url.endswith(":5600/health") else healthy_fetch(url)

    with pytest.raises(RuntimeError, match="not healthy"):
        module.check_native(fetch)


def test_an_unreachable_service_is_reported_with_its_url():
    def fetch(url):
        raise RuntimeError(f"{url} is not reachable: refused")

    with pytest.raises(RuntimeError, match="not reachable"):
        module.check_native(fetch)


# -- gateway and CRUD --------------------------------------------------------------------------------------------------------------

def test_every_front_end_path_is_requested():
    app = FakeApp()

    module.check_front_ends(app)

    assert [path for _, path in app.calls] == list(module.FRONT_ENDS)


def test_the_crud_lifecycle_passes_and_leaves_no_row_behind():
    app = FakeApp()

    module.check_student3_crud(app)

    assert app.rows == {}
    assert [method for method, _ in app.calls if method in ("POST", "PUT", "DELETE")] == ["POST", "PUT", "DELETE"]


def test_the_row_is_deleted_even_when_a_middle_step_fails():
    app = FakeApp(update_fails=True)

    with pytest.raises(RuntimeError, match="PUT"):
        module.check_student3_crud(app)

    assert app.rows == {}  # cleaned up despite the failure


def test_a_row_missing_from_the_list_fails_and_is_still_cleaned_up():
    app = FakeApp(missing_from_list=True)

    with pytest.raises(RuntimeError, match="missing from the list"):
        module.check_student3_crud(app)

    assert app.rows == {}


def test_a_delete_that_keeps_the_row_is_detected():
    with pytest.raises(RuntimeError, match="expected 404"):
        module.check_student3_crud(FakeApp(delete_keeps_row=True))


# -- the RAG retry ------------------------------------------------------------------------------------------------------------------

class Flaky:
    def __init__(self, failures, code=504):
        self.failures, self.code, self.calls = failures, code, 0

    def __call__(self, path, method="GET", body=None, expected=200):
        self.calls += 1
        if self.failures >= self.calls:
            raise RuntimeError(f"{method} {path}: expected {expected}, received {self.code}")
        return {"ok": True}


@pytest.mark.parametrize("code", [502, 504])
def test_a_rag_deadline_is_retried_once_and_logged(code, capsys):
    flaky = Flaky(1, code)

    assert module.retry_slow_rag(flaky)(f"{API}/rag/ask", "POST", {}) == {"ok": True}
    assert flaky.calls == 2 and "RETRY" in capsys.readouterr().out


def test_a_second_rag_failure_still_fails():
    flaky = Flaky(2)

    with pytest.raises(RuntimeError, match="received 504"):
        module.retry_slow_rag(flaky)(f"{API}/rag/ask", "POST", {})
    assert flaky.calls == 2  # one retry, never a loop


@pytest.mark.parametrize(("path", "code"), [(f"{API}/recommend", 504), (f"{API}/mcp/invoke", 502), (f"{API}/rag/ask", 400), (f"{API}/rag/ask", 503)])
def test_nothing_else_is_retried(path, code):
    flaky = Flaky(1, code)

    with pytest.raises(RuntimeError):
        module.retry_slow_rag(flaky)(path, "POST", {})
    assert flaky.calls == 1


# -- orchestration -------------------------------------------------------------------------------------------------------------------

class SmokeStub:
    COMPONENTS = ("ai", "mcp", "rag", "multi-agent")

    def __init__(self):
        self.enabled = None

    @staticmethod
    def parse_components(text):
        return frozenset(text.split(","))

    def run(self, origin, enabled, call=None):
        self.enabled = enabled


def test_run_executes_every_section_and_enables_all_four_ai_components(capsys):
    smoke = SmokeStub()

    module.run("http://localhost:5100", call=FakeApp(), fetch=healthy_fetch, smoke=smoke)

    output = capsys.readouterr().out
    assert [f"== {n}." in output for n in (1, 2, 3, 4)] == [True] * 4
    assert smoke.enabled == frozenset(SmokeStub.COMPONENTS)
    assert "automated test decision" in output  # the report never passes this off as the human review


def test_main_returns_zero_on_success_and_one_with_the_failure_named(monkeypatch, capsys):
    monkeypatch.setattr(module, "run", lambda origin: None)
    assert module.main(["http://localhost:5100"]) == 0
    assert "ALL SYSTEM CHECKS PASSED" in capsys.readouterr().out

    def failing(origin):
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "run", failing)
    assert module.main(["http://localhost:5100"]) == 1
    assert "FAIL: boom" in capsys.readouterr().out


def test_main_reports_a_bad_origin_as_a_failure_not_a_crash(capsys):
    assert module.main(["https://example.org"]) == 1
    assert "FAIL:" in capsys.readouterr().out
