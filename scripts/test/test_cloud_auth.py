import base64
import subprocess
from urllib.error import HTTPError, URLError

import pytest

import cloud_auth


@pytest.fixture
def auth(monkeypatch):
    monkeypatch.setenv("CLOUD_AUTH_USER", "demo")
    monkeypatch.setenv("CLOUD_AUTH_PASSWORD", "a" * 20)


@pytest.mark.parametrize("user,password", [("", ""), ("a:b", "x" * 20), ("a\nb", "x" * 20),
                                           ("demo", ""), ("demo", "x" * 15), ("demo", "x" * 73),
                                           ("demo", "x" * 20 + "\n"), ("demo", "x" * 20 + "\0")])
def test_invalid_required_credentials_fail_without_echoing_values(monkeypatch, user, password):
    monkeypatch.setenv("CLOUD_AUTH_USER", user)
    if "\0" in password:
        monkeypatch.setattr(cloud_auth.os, "environ", {"CLOUD_AUTH_USER": user, "CLOUD_AUTH_PASSWORD": password})
    else:
        monkeypatch.setenv("CLOUD_AUTH_PASSWORD", password)
    with pytest.raises(ValueError):
        cloud_auth.credentials(required=True)


def test_baseline_does_not_require_credentials(monkeypatch):
    monkeypatch.delenv("CLOUD_AUTH_USER", raising=False)
    monkeypatch.delenv("CLOUD_AUTH_PASSWORD", raising=False)
    assert cloud_auth.credentials() is None


def test_hashing_uses_stdin_and_private_file_not_plaintext_or_command_arguments(auth, monkeypatch, tmp_path):
    calls = []
    hashed = "$2a$14$" + "A" * 53

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, hashed.encode(), b"")

    monkeypatch.setattr(cloud_auth.shutil, "which", lambda _: "docker")
    monkeypatch.setattr(cloud_auth.subprocess, "run", run)
    path = tmp_path / "gateway-auth.caddy"
    cloud_auth.write_auth(path)
    assert "a" * 20 not in path.read_text()
    assert hashed in path.read_text() and "basic_auth" in path.read_text()
    assert calls[0][1]["input"] == b"a" * 20 + b"\n"
    assert all("a" * 20 not in arg for arg in calls[0][0])


@pytest.mark.parametrize("result", [(1, b"error"), (0, b"not a hash")])
def test_hashing_failure_does_not_write_a_credential_file(auth, monkeypatch, tmp_path, result):
    monkeypatch.setattr(cloud_auth.shutil, "which", lambda _: "docker")
    monkeypatch.setattr(cloud_auth.subprocess, "run",
                        lambda *args, **kwargs: subprocess.CompletedProcess([], result[0], result[1], b""))
    path = tmp_path / "gateway-auth.caddy"
    with pytest.raises(RuntimeError):
        cloud_auth.write_auth(path)
    assert not path.exists()


class Response:
    def __init__(self, status=200, body=b'{"ok":true}'):
        self.status, self.body = status, body

    def read(self, size):
        return self.body[:size]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_https_calls_use_auth_but_anonymous_probes_do_not(auth, monkeypatch):
    requests = []

    class Opener:
        def open(self, request, timeout):
            assert timeout == 420
            requests.append(request)
            return Response()

    monkeypatch.setattr(cloud_auth, "build_opener", lambda *args: Opener())
    assert cloud_auth.make_call("https://example.org")("/api") == {"ok": True}
    cloud_auth.make_call("https://example.org", authenticated=False)("/api")
    assert requests[0].get_header("Authorization") == "Basic " + base64.b64encode(b"demo:" + b"a" * 20).decode()
    assert requests[1].get_header("Authorization") is None


# pragma: allowlist nextline secret - synthetic URL credentials test rejection of unsafe origins
@pytest.mark.parametrize("origin", ["http://example.org", "https://user:pass@example.org", "https://example.org/path",
                                  "https://example.org?x=1", "https://example.org/#x"])
def test_credentials_cannot_be_sent_to_an_unsafe_origin(origin):
    with pytest.raises(ValueError, match="HTTPS origin"):
        cloud_auth.make_call(origin)


def test_redirects_are_not_followed_with_credentials():
    assert cloud_auth.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.example") is None


def test_oversized_responses_and_unexpected_statuses_fail(monkeypatch):
    class Opener:
        response = Response(body=b"x" * 1048577)

        def open(self, request, timeout):
            return self.response

    opener = Opener()
    monkeypatch.setattr(cloud_auth, "build_opener", lambda *args: opener)
    call = cloud_auth.make_call("https://example.org", authenticated=False)
    with pytest.raises(RuntimeError, match="1 MiB"):
        call("/")
    opener.response = Response(status=302)
    with pytest.raises(RuntimeError, match="received 302"):
        call("/")


def test_readiness_checks_all_feature_auth_boundaries(auth, monkeypatch):
    calls = []
    monkeypatch.setattr(cloud_auth, "make_call", lambda origin, **kwargs:
                        lambda path, **request: calls.append((kwargs["authenticated"] if "authenticated" in kwargs else True, path, request)))
    cloud_auth.verify("https://example.org", required=True)
    assert len(calls) == 7 and calls[0][0] is True
    assert all(not authenticated and request["expected"] == 401 for authenticated, _, request in calls[1:])


def test_readiness_timeout_is_bounded_and_does_not_retry_mutations(monkeypatch):
    times = iter([0, 0, 181])
    paths = []

    def call(path):
        paths.append(path)
        raise URLError("not ready")

    monkeypatch.setattr(cloud_auth, "credentials", lambda required: None)
    monkeypatch.setattr(cloud_auth, "make_call", lambda *args, **kwargs: call)
    monkeypatch.setattr(cloud_auth.time, "monotonic", lambda: next(times))
    monkeypatch.setattr(cloud_auth.time, "sleep", lambda seconds: None)
    with pytest.raises(RuntimeError, match="180 seconds"):
        cloud_auth.verify("https://example.org")
    assert paths == ["/", "/"]


def test_http_auth_challenge_is_reported_as_expected_status(monkeypatch):
    class Opener:
        def open(self, request, timeout):
            raise HTTPError(request.full_url, 401, "unauthorised", {}, None)

    monkeypatch.setattr(cloud_auth, "build_opener", lambda *args: Opener())
    assert cloud_auth.make_call("https://example.org", authenticated=False)("/", expected=401) == b""
