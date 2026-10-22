"""Private gateway credentials and authenticated HTTPS deployment probes."""

import argparse
import base64
import json
import os
import re
import shutil
import subprocess  # noqa: S404 - fixed Caddy argv, credentials supplied on stdin
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

CADDY_IMAGE = "caddy:2.10.2-alpine"


def credentials(required=False):
    user = os.environ.get("CLOUD_AUTH_USER", "")
    password = os.environ.get("CLOUD_AUTH_PASSWORD", "")
    if not user and not password and not required:
        return None
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", user):
        raise ValueError("Set CLOUD_AUTH_USER to 1-64 letters, digits, dots, underscores or hyphens.")
    if not 16 <= len(password.encode("utf-8")) <= 72 or any(c in password for c in "\r\n\0"):
        raise ValueError("Set CLOUD_AUTH_PASSWORD to 16-72 UTF-8 bytes, without line breaks or NUL.")
    return user, password


def write_auth(path):
    user, password = credentials(required=True)
    docker = shutil.which("docker")
    if not docker:
        raise RuntimeError("Docker is required to hash the gateway password with Caddy.")
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell or password in argv
        [docker, "run", "--rm", "-i", CADDY_IMAGE, "caddy", "hash-password"],
        input=password.encode() + b"\n", capture_output=True, check=False, timeout=60)
    if result.returncode:
        raise RuntimeError("Caddy password hashing failed; no credential file was written.")
    hashed = result.stdout.decode().strip()
    if not re.fullmatch(r"\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}", hashed):
        raise RuntimeError("Caddy did not return a bcrypt password hash.")
    path = Path(path)
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as stream:
        stream.write(f"basic_auth {{\n    {user} {hashed}\n}}\n")
    path.chmod(0o600)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def make_call(base, timeout=200, authenticated=True):
    parsed = urlparse(base)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
        raise ValueError("Provide the public HTTPS origin.")
    auth = credentials() if authenticated else None
    opener = build_opener(NoRedirect())

    def call(path, method="GET", body=None, expected=200):
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("Use an origin-relative request path.")
        headers = {"Content-Type": "application/json"}
        if auth:
            token = base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
            headers["Authorization"] = f"Basic {token}"
        request = Request(base.rstrip("/") + path, method=method,  # noqa: S310 - HTTPS origin validated above
                          data=None if body is None else json.dumps(body).encode(), headers=headers)
        try:
            response = opener.open(request, timeout=timeout)
        except HTTPError as exc:
            response = exc
        with response:
            data = response.read(1048577)
            if response.status != expected:
                raise RuntimeError(f"{method} {path}: expected {expected}, received {response.status}")
            if len(data) > 1048576:
                raise RuntimeError(f"{method} {path}: response exceeds 1 MiB.")
        return json.loads(data) if data.startswith((b"{", b"[")) else data

    return call


def verify(origin, required=False):
    credentials(required)
    call = make_call(origin, timeout=15)
    deadline = time.monotonic() + 180
    while True:
        try:
            call("/")
            break
        except (URLError, RuntimeError) as exc:
            if time.monotonic() >= deadline:
                raise RuntimeError("Public HTTPS readiness failed after 180 seconds.") from exc
            print(f"Waiting for verified HTTPS ({type(exc).__name__}); retrying a read-only request.", flush=True)
            time.sleep(5)
    if required:
        anonymous = make_call(origin, timeout=15, authenticated=False)
        for path in ("/", "/accommodation/api/capabilities", "/itinerary-api/capabilities",
                     "/attractions-api/capabilities", "/budget-api/capabilities", "/logistics/api/destinations"):
            anonymous(path, expected=401)
        print("PASS: anonymous access rejected at the gateway for every feature.")
    print("PASS: verified HTTPS gateway is ready.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check")
    commands.add_parser("prepare").add_argument("output", type=Path)
    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("origin")
    verify_parser.add_argument("--required", action="store_true")
    args = parser.parse_args()
    if args.command == "check":
        credentials(required=True)
    elif args.command == "prepare":
        write_auth(args.output)
    else:
        verify(args.origin, args.required)


if __name__ == "__main__":
    main()
