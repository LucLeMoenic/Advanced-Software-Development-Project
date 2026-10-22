"""Opt-in real Caddy TLS/auth checks; uses isolated containers and a disposable local CA."""

import base64
import json
import os
import shutil
import ssl
import subprocess  # noqa: S404 - fixed container commands with task-owned names
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest

from cloud_auth import CADDY_IMAGE, write_auth
from prepare_cloud import caddyfile, cloud_proxy_config

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_CLOUD_GATEWAY_TESTS") != "1", reason="set RUN_CLOUD_GATEWAY_TESTS=1 for isolated container/TLS checks")


def test_real_compose_materializes_cloud_nginx_configs_and_preserves_variables(tmp_path):
    docker = shutil.which("docker")
    assert docker, "Docker Compose is required for the nginx integration check."
    names = ["shared-frontend", *(f"student{i}-frontend" for i in range(1, 6))]
    services = {
        name: {"image": "nginx:stable-alpine",
               "environment": {"NGINX_ENTRYPOINT_LOCAL_RESOLVERS": "1"},
               "extra_hosts": {f"student{i}-backend": "127.0.0.1" for i in (1, 2)},
               "configs": [{"source": name, "target": "/etc/nginx/" + (
                   "templates/default.conf.template" if name == "shared-frontend" else "conf.d/default.conf")}]}
        for name in names
    }
    compose = tmp_path / "compose.json"
    compose.write_text(json.dumps({"services": services, "configs": {
        name: {"content": cloud_proxy_config(name)} for name in names}}), encoding="utf-8")
    command = [docker, "compose", "-p", "asd-deadline-test-" + uuid.uuid4().hex[:12], "-f", str(compose)]
    try:
        subprocess.run([*command, "config", "--quiet"], check=True, capture_output=True, text=True, timeout=30)  # noqa: S603
        for name in names:
            result = subprocess.run(  # noqa: S603 - isolated project, no published ports or application volumes
                [*command, "run", "--rm", "--no-deps", name, "nginx", "-T"],
                capture_output=True, text=True, timeout=90)
            assert result.returncode == 0, result.stdout + result.stderr
            assert "proxy_read_timeout 400s;" in result.stdout
            assert "proxy_send_timeout 400s;" in result.stdout
            assert "$$" not in result.stdout
            if name == "shared-frontend":
                assert "proxy_pass $student2_backend;" in result.stdout
                assert "${NGINX_LOCAL_RESOLVERS}" not in result.stdout
                assert "limit_req zone=asd_clients burst=60 nodelay;" in result.stdout
    finally:
        subprocess.run([*command, "down", "--remove-orphans"], check=True, capture_output=True, timeout=90)  # noqa: S603


@pytest.mark.parametrize("password", ["a" * 20, "  " + "a" * 20 + "  ", "\u00e9" * 10])
def test_real_gateway_requires_auth_on_every_route_and_does_not_forward_credentials(tmp_path, monkeypatch, password):
    docker = shutil.which("docker")
    assert docker, "Docker is required for the gateway integration check."

    def command(*args):
        return subprocess.run([docker, *args], check=True, capture_output=True, text=True, timeout=90).stdout.strip()  # noqa: S603

    monkeypatch.setenv("CLOUD_AUTH_USER", "demo")
    monkeypatch.setenv("CLOUD_AUTH_PASSWORD", password)
    write_auth(tmp_path / "gateway-auth.caddy")
    config = caddyfile("localhost", protected=True).replace("localhost {", "localhost {\n    tls internal")
    (tmp_path / "Caddyfile").write_text(config)
    (tmp_path / "upstream.py").write_text(
        "import json\nfrom http.server import BaseHTTPRequestHandler,HTTPServer\n"
        "class Handler(BaseHTTPRequestHandler):\n"
        " def do_GET(self):\n"
        "  self.send_response(200); self.end_headers()\n"
        "  self.wfile.write(json.dumps({'authorization':self.headers.get('Authorization')}).encode())\n"
        " do_POST=do_GET\n"
        "HTTPServer(('0.0.0.0',80),Handler).serve_forever()\n")
    network = "asd-auth-test-" + uuid.uuid4().hex[:12]
    containers = []
    command("network", "create", network)
    try:
        upstream = command("run", "-d", "--network", network, "--network-alias", "shared-frontend",
                           "--mount", f"type=bind,source={tmp_path},target=/test,readonly",
                           "python:3.11-slim", "python", "/test/upstream.py")
        containers.append(upstream)
        gateway = command("run", "-d", "--network", network, "-p", "127.0.0.1::443",
                          "--mount", f"type=bind,source={tmp_path},target=/etc/caddy,readonly", CADDY_IMAGE)
        containers.append(gateway)
        address = command("port", gateway, "443/tcp")
        port = address.splitlines()[0].rsplit(":", 1)[1]
        ca = tmp_path / "root.crt"
        for attempt in range(30):
            result = subprocess.run(  # noqa: S603 - copy the disposable public test CA, not a credential
                [docker, "cp", f"{gateway}:/data/caddy/pki/authorities/local/root.crt", str(ca)],
                capture_output=True, timeout=10)
            if result.returncode == 0:
                break
            time.sleep(1)
        assert ca.is_file(), command("logs", gateway)
        context = ssl.create_default_context(cafile=str(ca))
        origin = f"https://localhost:{port}"
        token = base64.b64encode(("demo:" + password).encode()).decode()

        def request(path, auth=None, method="GET"):
            headers = {"Authorization": "Basic " + auth} if auth else {}
            req = Request(origin + path, headers=headers, method=method)  # noqa: S310 - fixed local HTTPS origin
            try:
                with urlopen(req, context=context, timeout=10) as response:  # noqa: S310 - local HTTPS with verified test CA
                    return response.status, response.read()
            except HTTPError as error:
                return error.code, error.read()

        for attempt in range(30):
            try:
                assert request("/")[0] == 401
                break
            except URLError:
                if attempt == 29:
                    raise
                time.sleep(1)
        for path in ("/", "/accommodation/api/capabilities", "/itinerary-api/capabilities",
                     "/attractions-api/capabilities", "/budget-api/capabilities", "/logistics/api/destinations"):
            assert request(path)[0] == 401
            status, body = request(path, token)
            assert status == 200 and json.loads(body)["authorization"] is None
        assert request("/itinerary-api/trips", method="POST")[0] == 401
        assert request("/", base64.b64encode(b"demo:incorrect").decode())[0] == 401
    finally:
        for container in reversed(containers):
            command("rm", "-f", container)
        command("network", "rm", network)
