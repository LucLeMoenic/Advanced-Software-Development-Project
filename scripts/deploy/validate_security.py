"""Validate the endpoint-security controls of the public gateway (Release 2 cloud security bonus, B5).

    python scripts/deploy/validate_security.py https://<domain>
    python scripts/deploy/validate_security.py https://localhost:8443 --http-origin http://localhost:8081 --insecure --skip-ports

Checks, each reported PASS or FAIL (exit code 1 if any fails):
  redirect    plain HTTP is redirected to HTTPS
  tls         TLS 1.2 or newer, certificate valid for at least 7 more days
              (--insecure skips verification and is refused for any host except localhost)
  headers     HSTS, nosniff, frame protection, referrer policy, permissions policy, no server version
  methods     a verb the applications never use (TRACE) is refused with 405
  body        a 2 MB request body is refused with 413
  ports       the backend, database and AI-service ports are NOT reachable from outside
  ratelimit   a burst of requests from one client is answered 429 at some point

Only run it against a deployment you own: the rate-limit check sends a few hundred requests in a few seconds.
Standard library only.
"""

import argparse
import http.client
from functools import lru_cache
import socket
import ssl
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

INTERNAL_PORTS = (
    5101, 5102, 5103, 5104, 5105,      # feature frontends
    5201, 5202, 5203, 5204, 5205,      # backends
    5301, 5302, 5303, 5304, 5305,      # databases
    5100, 5400, 5500, 5600, 8080, 11434,  # gateway, MCP, RAG, Multi-Agent, service default, Ollama
)
LOOPBACK_HOSTS = ("localhost", "127.0.0.1", "::1")
BODY_BYTES = 2 * 1024 * 1024
BURST_REQUESTS = 240
BURST_THREADS = 20


class Result:
    def __init__(self, name, ok, detail):
        self.name, self.ok, self.detail = name, ok, detail

    def line(self):
        return f"{'PASS' if self.ok else 'FAIL'}  {self.name:<10} {self.detail}"


# -- pure evaluations (unit-tested without a network) ---------------------------------------------------------

def evaluate_headers(headers):
    """headers: a dict with lower-case names. Returns a list of Result."""
    results = []

    def check(name, ok, detail):
        results.append(Result(f"header:{name}", ok, detail))

    hsts = headers.get("strict-transport-security", "")
    max_age = next((int(p.split("=")[1]) for p in (s.strip() for s in hsts.split(";"))
                    if p.lower().startswith("max-age=") and p.split("=")[1].isdigit()), 0)
    check("hsts", max_age >= 15552000, f"Strict-Transport-Security max-age={max_age} (need at least 15552000)")
    check("nosniff", headers.get("x-content-type-options", "").lower() == "nosniff",
          f"X-Content-Type-Options={headers.get('x-content-type-options')!r}")
    framing = headers.get("x-frame-options", "").upper()
    csp = headers.get("content-security-policy", "")
    check("framing", framing in ("DENY", "SAMEORIGIN") or "frame-ancestors" in csp,
          f"X-Frame-Options={framing or None!r}, CSP frame-ancestors={'frame-ancestors' in csp}")
    check("referrer", bool(headers.get("referrer-policy")), f"Referrer-Policy={headers.get('referrer-policy')!r}")
    check("permissions", bool(headers.get("permissions-policy")), f"Permissions-Policy={headers.get('permissions-policy')!r}")
    server = headers.get("server", "")
    check("server", not any(ch.isdigit() for ch in server) and "/" not in server,
          f"Server={server or None!r} (must not reveal a product version)")
    return results


def evaluate_tls(version, days_left, verified):
    ok_version = version in ("TLSv1.2", "TLSv1.3")
    results = [Result("tls:version", ok_version, f"negotiated {version} (need TLSv1.2 or newer)")]
    if verified:
        results.append(Result("tls:cert", days_left is not None and days_left >= 7,
                              f"certificate verified, {days_left} days left (need at least 7)"))
    else:
        results.append(Result("tls:cert", True, "certificate verification skipped (--insecure); local testing only"))
    return results


def evaluate_ports(host, ports, connect):
    """connect(host, port) -> True if something accepted the connection. Every port must be closed."""
    open_ports = [p for p in ports if connect(host, p)]
    return Result("ports", not open_ports,
                  f"none of {len(ports)} internal ports is reachable" if not open_ports
                  else f"REACHABLE from outside: {open_ports}")


# -- network helpers ------------------------------------------------------------------------------------------

def tcp_connect(host, port, timeout=2):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@lru_cache(maxsize=2)
def tls_context(insecure):
    """Built once per mode: creating a context loads the system CA bundle (about 30 ms), which would otherwise throttle
    the rate-limit burst below the limit it is trying to exceed."""
    context = ssl.create_default_context()
    if insecure:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context


def connect(origin, insecure=False, timeout=15):
    parsed = urlparse(origin)
    if parsed.scheme == "https":
        return http.client.HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=timeout, context=tls_context(insecure))
    return http.client.HTTPConnection(parsed.hostname, parsed.port or 80, timeout=timeout)


def request(origin, method, path="/", body=None, insecure=False, headers=None, timeout=15, connection=None):
    """One request. Pass `connection` to reuse a keep-alive connection (the caller then closes it)."""
    owned = connection is None
    connection = connection or connect(origin, insecure, timeout)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        response.read()  # drain fully so a reused connection stays usable
        return response.status, {k.lower(): v for k, v in response.getheaders()}
    finally:
        if owned:
            connection.close()


def tls_details(origin, insecure):
    parsed = urlparse(origin)
    context = ssl.create_default_context()
    if insecure:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    with socket.create_connection((parsed.hostname, parsed.port or 443), timeout=15) as raw:
        with context.wrap_socket(raw, server_hostname=parsed.hostname) as tls:
            days_left = None
            if not insecure:
                expires = ssl.cert_time_to_seconds(tls.getpeercert()["notAfter"])
                days_left = int((expires - time.time()) // 86400)
            return tls.version(), days_left


def burst(origin, insecure):
    """BURST_REQUESTS GETs from BURST_THREADS workers, each on its own persistent connection (so the client is fast
    enough to exceed a limit of tens of requests per second). Returns the status codes; 0 marks a failed request."""
    per_worker = BURST_REQUESTS // BURST_THREADS

    def worker(_):
        statuses = []
        connection = connect(origin, insecure)
        try:
            for _ in range(per_worker):
                try:
                    statuses.append(request(origin, "GET", "/", insecure=insecure, connection=connection)[0])
                except (OSError, http.client.HTTPException):
                    connection.close()
                    connection = connect(origin, insecure)
                    statuses.append(0)
        finally:
            connection.close()
        return statuses

    with ThreadPoolExecutor(max_workers=BURST_THREADS) as pool:
        return [status for chunk in pool.map(worker, range(BURST_THREADS)) for status in chunk]


# -- the run -----------------------------------------------------------------------------------------------------

def run(origin, http_origin=None, insecure=False, skip_ports=False, skip_rate_limit=False, ports=INTERNAL_PORTS):
    parsed = urlparse(origin)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Provide the public HTTPS origin, for example https://example.org")
    if insecure and parsed.hostname not in LOOPBACK_HOSTS:
        # Skipping certificate verification is only for a self-signed local test gateway, never a real deployment.
        raise ValueError("--insecure is only allowed for localhost, 127.0.0.1 or ::1")
    http_origin = http_origin or f"http://{parsed.hostname}"
    results = []

    try:
        status, headers = request(http_origin, "GET", "/")
        location = headers.get("location", "")
        results.append(Result("redirect", status in (301, 302, 307, 308) and location.startswith("https://"),
                              f"GET {http_origin}/ -> {status} Location={location!r}"))
    except OSError as error:
        results.append(Result("redirect", False, f"could not reach {http_origin}: {error}"))

    try:
        results += evaluate_tls(*tls_details(origin, insecure)[:2], verified=not insecure)
    except (OSError, ssl.SSLError) as error:
        results.append(Result("tls", False, f"TLS handshake failed: {error}"))

    try:
        _, headers = request(origin, "GET", "/", insecure=insecure)
        results += evaluate_headers(headers)
    except OSError as error:
        results.append(Result("headers", False, f"could not fetch {origin}/: {error}"))

    try:
        status, _ = request(origin, "TRACE", "/", insecure=insecure)
        results.append(Result("methods", status == 405, f"TRACE / -> {status} (expected 405)"))
    except OSError as error:
        results.append(Result("methods", False, f"TRACE request failed: {error}"))

    try:
        status, _ = request(origin, "POST", "/", body=b"x" * BODY_BYTES, insecure=insecure,
                            headers={"Content-Type": "application/octet-stream"})
        results.append(Result("body", status == 413, f"POST / with {BODY_BYTES // 1024 // 1024} MB -> {status} (expected 413)"))
    except OSError as error:
        # A server that slams the connection on an oversized body is also refusing it; report it honestly.
        results.append(Result("body", False, f"oversized POST failed at the socket ({error}); expected a clean 413"))

    if skip_ports:
        results.append(Result("ports", True, "skipped (--skip-ports)"))
    else:
        results.append(evaluate_ports(parsed.hostname, ports, tcp_connect))

    if skip_rate_limit:
        results.append(Result("ratelimit", True, "skipped (--skip-rate-limit)"))
    else:
        statuses = burst(origin, insecure)
        limited = statuses.count(429)
        results.append(Result("ratelimit", limited > 0,
                              f"{len(statuses)} rapid requests from one client: {limited} answered 429, {statuses.count(200)} answered 200"))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("origin", help="public HTTPS origin, e.g. https://example.org")
    parser.add_argument("--http-origin", help="plain-HTTP origin to test the redirect (default http://<host>)")
    parser.add_argument("--insecure", action="store_true", help="do not verify the certificate (local self-signed testing only)")
    parser.add_argument("--skip-ports", action="store_true", help="skip the closed-ports check (local runs publish them)")
    parser.add_argument("--skip-rate-limit", action="store_true", help="skip the burst of requests")
    args = parser.parse_args(argv)
    results = run(args.origin, args.http_origin, args.insecure, args.skip_ports, args.skip_rate_limit)
    for result in results:
        print(result.line())
    failed = [r for r in results if not r.ok]
    print(f"\n{len(results) - len(failed)} of {len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
