"""Offline tests for scripts/deploy/validate_security.py (the public-gateway security validator)."""

import importlib.util
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("validate_security", Path(__file__).resolve().parents[1] / "deploy" / "validate_security.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

GOOD = {
    "strict-transport-security": "max-age=31536000; includeSubDomains",
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
    "permissions-policy": "camera=(), microphone=()",
    "content-security-policy": "frame-ancestors 'none'",
    "server": "nginx",
}


def failed(results):
    return sorted(r.name for r in results if not r.ok)


# -- headers --------------------------------------------------------------------------------------------------

def test_a_fully_hardened_response_passes_every_header_check():
    assert failed(module.evaluate_headers(GOOD)) == []


@pytest.mark.parametrize(("removed", "expected"), [
    ("strict-transport-security", "header:hsts"),
    ("x-content-type-options", "header:nosniff"),
    ("referrer-policy", "header:referrer"),
    ("permissions-policy", "header:permissions"),
])
def test_each_missing_header_fails_only_its_own_check(removed, expected):
    headers = {k: v for k, v in GOOD.items() if k != removed}

    assert failed(module.evaluate_headers(headers)) == [expected]


def test_framing_is_protected_by_either_x_frame_options_or_csp_frame_ancestors():
    only_xfo = {k: v for k, v in GOOD.items() if k != "content-security-policy"}
    only_csp = {k: v for k, v in GOOD.items() if k != "x-frame-options"}
    neither = {k: v for k, v in GOOD.items() if k not in ("x-frame-options", "content-security-policy")}

    assert failed(module.evaluate_headers(only_xfo)) == []
    assert failed(module.evaluate_headers(only_csp)) == []
    assert failed(module.evaluate_headers(neither)) == ["header:framing"]


@pytest.mark.parametrize("value", ["max-age=0", "max-age=3600", "max-age=abc", "includeSubDomains", ""])
def test_hsts_must_have_a_long_max_age(value):
    headers = {**GOOD, "strict-transport-security": value}

    assert failed(module.evaluate_headers(headers)) == ["header:hsts"]


@pytest.mark.parametrize(("server", "leaks"), [("nginx/1.27.2", True), ("Apache/2.4.58", True), ("nginx", False), ("", False), ("Caddy", False)])
def test_the_server_header_must_not_reveal_a_version(server, leaks):
    headers = {**GOOD, "server": server}

    assert (failed(module.evaluate_headers(headers)) == ["header:server"]) is leaks


# -- TLS ---------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize(("version", "ok"), [("TLSv1.3", True), ("TLSv1.2", True), ("TLSv1.1", False), ("TLSv1", False), ("SSLv3", False)])
def test_only_tls_1_2_or_newer_is_acceptable(version, ok):
    results = module.evaluate_tls(version, 90, verified=True)

    assert (results[0].ok) is ok


@pytest.mark.parametrize(("days", "ok"), [(90, True), (7, True), (6, False), (0, False), (None, False)])
def test_a_verified_certificate_needs_at_least_a_week_left(days, ok):
    assert module.evaluate_tls("TLSv1.3", days, verified=True)[1].ok is ok


def test_skipping_verification_is_reported_as_skipped_not_as_proof():
    result = module.evaluate_tls("TLSv1.3", None, verified=False)[1]

    assert result.ok and "skipped" in result.detail


# -- ports (real sockets) ----------------------------------------------------------------------------------------

def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def test_tcp_connect_sees_a_listening_port_and_a_closed_one():
    closed = free_port()
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        open_port = listener.getsockname()[1]

        assert module.tcp_connect("127.0.0.1", open_port) is True
        assert module.tcp_connect("127.0.0.1", closed, timeout=1) is False


def test_the_ports_check_fails_and_names_every_reachable_port():
    result = module.evaluate_ports("host", (5201, 5301, 5600), lambda host, port: port in (5201, 5600))

    assert not result.ok and "5201" in result.detail and "5600" in result.detail and "5301" not in result.detail


def test_the_ports_check_passes_when_nothing_internal_is_reachable():
    assert module.evaluate_ports("host", module.INTERNAL_PORTS, lambda host, port: False).ok


def test_the_internal_port_list_covers_backends_databases_and_ai_services():
    for port in (5201, 5205, 5301, 5305, 5400, 5500, 5600, 11434):
        assert port in module.INTERNAL_PORTS


# -- request() against a real local server -------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.send_response(308)
        self.send_header("Location", "https://example.test/")
        self.end_headers()

    def do_TRACE(self):
        self.send_response(405)
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)  # drain the body first, as a real server does, so the client is not aborted mid-upload
        self.send_response(413 if length > 1024 * 1024 else 200)
        self.end_headers()


@pytest.fixture
def local_server():
    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def test_request_returns_status_and_lowercase_headers(local_server):
    status, headers = module.request(local_server, "GET", "/")

    assert status == 308 and headers["location"] == "https://example.test/"


def test_request_can_send_a_verb_and_a_large_body(local_server):
    assert module.request(local_server, "TRACE", "/")[0] == 405
    assert module.request(local_server, "POST", "/", body=b"x" * module.BODY_BYTES)[0] == 413


# -- burst(): the real function against a real local server --------------------------------------------------------

class LimitingHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # keep-alive, so the burst's persistent connections work
    served = 0
    lock = threading.Lock()

    def log_message(self, *args):
        pass

    def do_GET(self):
        with LimitingHandler.lock:
            LimitingHandler.served += 1
            limited = LimitingHandler.served > 100
        self.send_response(429 if limited else 200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")


@pytest.fixture
def limiting_server():
    LimitingHandler.served = 0
    server = type("S", (HTTPServer,), {"request_queue_size": 64})(("127.0.0.1", 0), LimitingHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def test_burst_sends_every_request_and_reports_the_limited_ones(limiting_server):
    statuses = module.burst(limiting_server, insecure=False)

    assert len(statuses) == module.BURST_REQUESTS
    assert statuses.count(429) == module.BURST_REQUESTS - 100 and statuses.count(200) == 100
    assert 0 not in statuses  # no request failed at the socket


def test_burst_counts_a_dead_server_as_failed_requests_not_as_a_crash(monkeypatch):
    # A small burst: refusing a connection to a closed port is slow on some systems, and the logic needs only a few.
    monkeypatch.setattr(module, "BURST_REQUESTS", 4)
    monkeypatch.setattr(module, "BURST_THREADS", 2)
    dead = f"http://127.0.0.1:{free_port()}"

    statuses = module.burst(dead, insecure=False)

    assert len(statuses) == 4 and set(statuses) == {0}


def test_the_tls_context_is_built_once_per_mode_so_the_client_is_fast_enough():
    assert module.tls_context(False) is module.tls_context(False)
    assert module.tls_context(True) is module.tls_context(True)
    assert module.tls_context(False) is not module.tls_context(True)
    assert module.tls_context(True).verify_mode.name == "CERT_NONE" and module.tls_context(False).verify_mode.name == "CERT_REQUIRED"


def test_a_reused_connection_serves_many_requests(limiting_server):
    connection = module.connect(limiting_server)
    try:
        statuses = [module.request(limiting_server, "GET", "/", connection=connection)[0] for _ in range(5)]
    finally:
        connection.close()

    assert statuses == [200] * 5


# -- the run: orchestration decisions -------------------------------------------------------------------------------

@pytest.fixture
def healthy(monkeypatch):
    """A gateway that satisfies every control; individual tests then break one thing."""
    state = {"redirect": (308, {"location": "https://example.org/"}), "headers": dict(GOOD), "trace": 405,
             "body": 413, "open_ports": set(), "burst": [200] * 100 + [429] * 140, "tls": ("TLSv1.3", 80)}

    def fake_request(origin, method, path="/", body=None, insecure=False, headers=None, timeout=15):
        if origin.startswith("http://"):
            return state["redirect"]
        if method == "TRACE":
            return state["trace"], {}
        if method == "POST":
            return state["body"], {}
        return 200, state["headers"]

    monkeypatch.setattr(module, "request", fake_request)
    monkeypatch.setattr(module, "tls_details", lambda origin, insecure: state["tls"])
    monkeypatch.setattr(module, "tcp_connect", lambda host, port, timeout=2: port in state["open_ports"])
    monkeypatch.setattr(module, "burst", lambda origin, insecure: state["burst"])
    return state


def run_all():
    return {r.name: r for r in module.run("https://example.org")}


def test_a_gateway_with_every_control_passes_everything(healthy):
    results = module.run("https://example.org")

    assert failed(results) == []
    assert {"redirect", "tls:version", "tls:cert", "methods", "body", "ports", "ratelimit"} <= {r.name for r in results}


def test_no_redirect_to_https_fails(healthy):
    healthy["redirect"] = (200, {})

    assert failed(module.run("https://example.org")) == ["redirect"]


def test_a_redirect_to_another_plain_http_url_fails(healthy):
    healthy["redirect"] = (301, {"location": "http://example.org/other"})

    assert failed(module.run("https://example.org")) == ["redirect"]


def test_an_allowed_trace_verb_fails(healthy):
    healthy["trace"] = 200

    assert failed(module.run("https://example.org")) == ["methods"]


def test_an_oversized_body_that_is_accepted_fails(healthy):
    healthy["body"] = 200

    assert failed(module.run("https://example.org")) == ["body"]


def test_a_reachable_backend_port_fails(healthy):
    healthy["open_ports"] = {5203}

    results = module.run("https://example.org")

    assert failed(results) == ["ports"] and "5203" in next(r for r in results if r.name == "ports").detail


def test_no_rate_limiting_fails(healthy):
    healthy["burst"] = [200] * 240

    assert failed(module.run("https://example.org")) == ["ratelimit"]


def test_old_tls_fails(healthy):
    healthy["tls"] = ("TLSv1.1", 80)

    assert failed(module.run("https://example.org")) == ["tls:version"]


def test_an_unreachable_host_fails_cleanly_instead_of_crashing(monkeypatch):
    def refuse(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(module, "request", refuse)
    monkeypatch.setattr(module, "tls_details", refuse)
    monkeypatch.setattr(module, "tcp_connect", lambda *a, **k: False)
    monkeypatch.setattr(module, "burst", lambda *a: [0] * 240)

    names = failed(module.run("https://example.org"))

    assert {"redirect", "tls", "headers", "methods", "body", "ratelimit"} <= set(names)


def test_skip_flags_are_reported_as_skipped(healthy):
    healthy["open_ports"] = {5203}
    healthy["burst"] = [200] * 240

    results = module.run("https://example.org", skip_ports=True, skip_rate_limit=True)

    assert failed(results) == [] and sum("skipped" in r.detail for r in results) == 2


# -- input safety --------------------------------------------------------------------------------------------------------

@pytest.fixture
def no_network(monkeypatch):
    """Fail loudly if the validator tries to touch the network. These tests exercise the input guards; if a guard were
    ever broken, `run()` would otherwise go on to send real requests (including a burst and a 2 MB POST) to the host."""
    def forbidden(*args, **kwargs):
        raise AssertionError("the validator tried to use the network past a guard that should have stopped it")

    for name in ("request", "tls_details", "tcp_connect", "burst"):
        monkeypatch.setattr(module, name, forbidden)


@pytest.mark.parametrize("origin", ["http://example.org", "example.org", "ftp://example.org", "https://"])
def test_only_an_https_origin_is_accepted(no_network, origin):
    with pytest.raises(ValueError, match="HTTPS origin"):
        module.run(origin)


@pytest.mark.parametrize("host", ["example.org", "10.0.0.5", "192.168.1.10", "evil.localhost.example.org"])
def test_insecure_is_refused_for_every_non_loopback_host(no_network, host):
    with pytest.raises(ValueError, match="only allowed for localhost"):
        module.run(f"https://{host}", insecure=True)


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1"])
def test_insecure_is_allowed_for_loopback(healthy, host):
    assert failed(module.run(f"https://{host}:8443", insecure=True)) == []


def test_main_exits_non_zero_when_any_check_fails_and_zero_otherwise(healthy, capsys):
    assert module.main(["https://example.org"]) == 0
    healthy["trace"] = 200

    assert module.main(["https://example.org"]) == 1
    assert "FAIL  methods" in capsys.readouterr().out
