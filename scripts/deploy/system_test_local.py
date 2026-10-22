"""System-test the integrated application running locally, across the native AI services and the Docker Compose services.

    python scripts/deploy/system_test_local.py [http://localhost:5100]

Run it in its own terminal while the others hold Ollama, the MCP server, the RAG server and the Multi-Agent Server. It checks:

  1. each native, non-containerised service answers on its own loopback port
  2. the shared gateway serves every student's front end
  3. Student 3's attraction CRUD lifecycle through the gateway (the row it creates is always removed again)
  4. AI-Mode, MCP, RAG and the Multi-Agent workflow through Student 3's backend (scripts/deploy/smoke_cloud_ai.py)

The Multi-Agent workflow is approved by this script as an automated test decision. That is not the human review the
application is built for: use the browser for that. Standard library only.
"""

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

NATIVE = {"ollama": "http://127.0.0.1:11434/api/tags", "mcp": "http://127.0.0.1:5400/mcp",
          "rag": "http://127.0.0.1:5500/health", "multi-agent": "http://127.0.0.1:5600/health"}
NATIVE_STATUS = {"mcp": (400, 406)}  # a bare GET is rejected by the MCP transport, which proves it is listening
FRONT_ENDS = ("/health", "/accommodation/", "/itinerary/", "/attractions/", "/budget/", "/logistics/")
API = "/attractions-api"
LOOPBACK = ("localhost", "127.0.0.1")
MODEL = "llama3.2:3b"
TIMEOUT = 200


def stamp(message):
    print(f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ} {message}", flush=True)


def make_call(origin):
    parsed = urlparse(origin)
    if parsed.scheme != "http" or parsed.hostname not in LOOPBACK or parsed.path not in ("", "/") or parsed.query:
        raise ValueError("Provide a local gateway origin such as http://localhost:5100.")

    def call(path, method="GET", body=None, expected=200):
        request = Request(origin.rstrip("/") + path, method=method,  # noqa: S310 - loopback http origin validated above
                          data=None if body is None else json.dumps(body).encode(),
                          headers={"Content-Type": "application/json"})
        try:
            response = urlopen(request, timeout=TIMEOUT)  # noqa: S310 - loopback http origin validated above
        except HTTPError as exc:
            response = exc
        with response:
            data = response.read(2097152)
            if response.status != expected:
                raise RuntimeError(f"{method} {path}: expected {expected}, received {response.status}")
        return json.loads(data) if data and data.startswith((b"{", b"[")) else data

    return call


def status_of(url):
    try:
        with urlopen(url, timeout=10) as response:  # noqa: S310 - fixed loopback URLs from NATIVE
            return response.status, response.read(65536)
    except HTTPError as exc:
        return exc.code, b""
    except (URLError, OSError) as exc:
        raise RuntimeError(f"{url} is not reachable: {exc}") from exc


def check_native(fetch=status_of):
    for name, url in NATIVE.items():
        status, body = fetch(url)
        if status not in NATIVE_STATUS.get(name, (200,)):
            raise RuntimeError(f"The {name} service answered {status} at {url}.")
        if name == "ollama" and MODEL not in [m.get("name") for m in json.loads(body).get("models", [])]:
            raise RuntimeError(f"Ollama does not have {MODEL} installed.")
        if name == "multi-agent" and json.loads(body).get("status") != "ok":
            raise RuntimeError("The Multi-Agent Server is not healthy.")
        stamp(f"PASS native {name}: {url} -> {status}")


def check_front_ends(call):
    for path in FRONT_ENDS:
        call(path)
        stamp(f"PASS gateway {path}")


def check_student3_crud(call):
    name = "System test attraction " + datetime.now(timezone.utc).strftime("%H%M%S")
    created = call(f"{API}/attractions", "POST", {"name": name, "category": "activity", "description": "created by system test", "rating": 4.0}, 201)
    path = f"{API}/attractions/{created['id']}"
    try:
        if call(path)["name"] != name:
            raise RuntimeError("The created attraction was not read back.")
        updated = call(path, "PUT", {"name": name, "category": "activity", "description": "updated by system test", "rating": 4.5})
        if updated["rating"] != 4.5 or call(path)["description"] != "updated by system test":
            raise RuntimeError("The attraction update was not stored.")
        if created["id"] not in [item["id"] for item in call(f"{API}/attractions")]:
            raise RuntimeError("The attraction is missing from the list.")
        stamp(f"PASS Student 3 create, read, update and list (id {created['id']})")
    finally:
        call(path, "DELETE", expected=204)
    call(path, expected=404)
    stamp("PASS Student 3 delete: the row is gone and reads as 404")


def load_ai_smoke():
    path = Path(__file__).resolve().parent / "smoke_cloud_ai.py"
    spec = importlib.util.spec_from_file_location("smoke_cloud_ai", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def retry_slow_rag(call):
    """Retry the model-backed RAG question once: the application enforces a short model deadline, and a CPU-only model that
    has just answered another request can miss it. The retry is logged, and a second failure still fails the run."""
    def wrapped(path, method="GET", body=None, expected=200):
        try:
            return call(path, method, body, expected)
        except RuntimeError as error:
            if not path.endswith("/rag/ask") or not any(f"received {code}" in str(error) for code in (502, 504)):
                raise
            stamp(f"RETRY {path} once after a model deadline ({error})")
            return call(path, method, body, expected)
    return wrapped


def run(origin, call=None, fetch=status_of, smoke=None):
    call = retry_slow_rag(call or make_call(origin))
    stamp("== 1. native services (one terminal each)")
    check_native(fetch)
    stamp("== 2. gateway and every student's front end")
    check_front_ends(call)
    stamp("== 3. Student 3 attraction CRUD through the gateway")
    check_student3_crud(call)
    stamp("== 4. AI-Mode, MCP, RAG and Multi-Agent through Student 3's backend")
    stamp("NOTE the workflow is approved by this script as an automated test decision, not by a human reviewer")
    smoke = smoke or load_ai_smoke()
    smoke.run(origin, smoke.parse_components(",".join(smoke.COMPONENTS)), call=call)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("origin", nargs="?", default="http://localhost:5100")
    args = parser.parse_args(argv)
    try:
        run(args.origin)
    except (RuntimeError, ValueError, KeyError, OSError) as error:
        stamp(f"FAIL: {error}")
        return 1
    stamp("ALL SYSTEM CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
