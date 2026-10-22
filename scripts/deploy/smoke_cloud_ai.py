"""Verify the cloud AI components (bonus B1 to B4) through Student 3's application over the public HTTPS origin.

    python scripts/deploy/smoke_cloud_ai.py https://<domain> --components ai,mcp,rag,multi-agent

--components must match what the release was prepared with (prepare_cloud.py --ai-services). For each enabled component this
drives a real interaction through the application and checks the answer is genuine, and for each component that is NOT enabled
it checks the application still reports it cleanly disabled:

  ai           B1  AI-Mode: /api/recommend answered by the model (not the deterministic fallback)
  mcp          B2  MCP: a tool call through the backend returns real catalogue data
  rag          B3  RAG: a grounded answer with citations from retrieved context
  multi-agent  B4  Multi-Agent: a Planner, Worker, Reviewer workflow reaches human review and is approved

Use the baseline smoke test (smoke_cloud.py) for a release prepared without AI. Standard library only.
"""

import argparse
import json
import sys
import time
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

COMPONENTS = ("ai", "mcp", "rag", "multi-agent")
API = "/attractions-api"
CALL_TIMEOUT = 200  # seconds: a CPU-only 3B model can need over a minute per answer
WORKFLOW_TIMEOUT = 900  # seconds for Planner, Worker and Reviewer together
POLL_SECONDS = 5


def parse_components(value):
    items = [part.strip() for part in (value or "").split(",") if part.strip()]
    unknown = [item for item in items if item not in COMPONENTS]
    if not items or unknown:
        raise ValueError(f"Choose from: {', '.join(COMPONENTS)}" + (f" (unknown: {', '.join(unknown)})" if unknown else ""))
    return frozenset(items)


def make_call(base):
    parsed = urlparse(base)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise ValueError("Provide the public HTTPS origin.")

    def call(path, method="GET", body=None, expected=200):
        request = Request(base.rstrip("/") + path, method=method,  # noqa: S310 - HTTPS origin validated above
                          data=None if body is None else json.dumps(body).encode(),
                          headers={"Content-Type": "application/json"})
        try:
            response = urlopen(request, timeout=CALL_TIMEOUT)  # noqa: S310 - HTTPS origin checked above
        except HTTPError as exc:
            response = exc
        with response:
            data = response.read(1048576)
            if response.status != expected:
                raise RuntimeError(f"{method} {path}: expected {expected}, received {response.status}")
        return json.loads(data) if data and data.startswith((b"{", b"[")) else data

    return call


def check_capabilities(call, enabled):
    expected = {"aiEnabled": "ai" in enabled, "mcpEnabled": "mcp" in enabled,
                "ragEnabled": "rag" in enabled, "multiAgentEnabled": "multi-agent" in enabled}
    if call(f"{API}/capabilities") != expected:
        raise RuntimeError(f"Student 3 capabilities do not match the components this release was prepared with: expected {expected}.")


def check_ai_mode(call):
    answer = call(f"{API}/recommend", "POST", {"interest": "street art and good food"})
    if answer.get("source") not in ("ai", "ai_retry") or not str(answer.get("recommendation", "")).strip():
        raise RuntimeError(
            f"AI-Mode answered from '{answer.get('source')}', not the model. The deterministic fallback means the model "
            "did not respond: check the ollama container and that the model was pulled (pull-models-vm.sh).")


def check_mcp(call):
    tools = call(f"{API}/mcp/tools")
    if "attractions.search" not in tools.get("tools", []):
        raise RuntimeError("The MCP server did not list Student 3's attractions.search tool.")
    result = call(f"{API}/mcp/invoke", "POST", {"tool": "attractions.search", "arguments": {"category": "restaurant"}})["result"]
    attractions = result.get("attractions", [])
    if not attractions or any(item.get("category") != "restaurant" for item in attractions):
        raise RuntimeError("The MCP tool did not return restaurant data from the catalogue.")
    if result.get("total_matches", 0) < len(attractions):
        raise RuntimeError("The MCP tool's total_matches is smaller than the number of rows it returned.")


def check_rag(call):
    answer = call(f"{API}/rag/ask", "POST", {"question": "Is Chin Chin busy? Do I need to book?"})
    if answer.get("confidence") == "insufficient" or not answer.get("citations") or not str(answer.get("answer", "")).strip():
        raise RuntimeError("RAG did not give a grounded answer with citations from retrieved context "
                           f"(confidence={answer.get('confidence')!r}, citations={len(answer.get('citations') or [])}).")


def check_multi_agent(call, sleep=None, now=None):
    # Resolved at call time, not bound as defaults, so a test (or a caller) can supply its own clock.
    sleep = sleep or time.sleep
    now = now or time.monotonic
    started = call(f"{API}/agents/workflows", "POST", {"task": "Suggest a relaxed afternoon of food", "category": "restaurant"}, 202)
    path = f"{API}/agents/workflows/{started['id']}"
    deadline = now() + WORKFLOW_TIMEOUT
    while True:
        record = call(path)
        if record["status"] in ("awaiting_human_review", "failed"):
            break
        if now() > deadline:
            raise RuntimeError(f"The workflow was still '{record['status']}' after {WORKFLOW_TIMEOUT} seconds.")
        sleep(POLL_SECONDS)
    if record["status"] == "failed":
        error = record.get("error") or {}
        raise RuntimeError(f"The workflow failed at {error.get('stage')}: {error.get('code')} ({error.get('message')}).")
    if not (record.get("plan") and record.get("work") and record.get("review")):
        raise RuntimeError("The workflow reached human review without a plan, a Worker output and a Reviewer verdict.")
    if [step.get("stage") for step in record.get("history", [])] != ["planner", "worker", "reviewer"]:
        raise RuntimeError("The workflow history does not show Planner, Worker and Reviewer in order.")
    decided = call(f"{path}/decision", "POST", {"decision": "approve", "notes": "Cloud AI smoke test approval"})
    if decided.get("status") != "approved" or not decided.get("final_output"):
        raise RuntimeError("The human approval was not recorded with a final output.")


def check_disabled(call, enabled):
    """Every component that was not enabled must still answer with its disabled response."""
    if "ai" not in enabled and call(f"{API}/recommend", "POST", {"interest": "street art"}).get("source") != "fallback":
        raise RuntimeError("AI-Mode is off but did not answer with the deterministic fallback.")
    if "mcp" not in enabled:
        call(f"{API}/mcp/invoke", "POST", {"tool": "attractions.search", "arguments": {}}, 503)
    if "rag" not in enabled:
        call(f"{API}/rag/ask", "POST", {"question": "Is Chin Chin busy?"}, 503)
    if "multi-agent" not in enabled:
        call(f"{API}/agents/workflows", "POST", {"task": "Plan a relaxed day"}, 503)


CHECKS = (("mcp", check_mcp, "B2 MCP: a tool call through the application returned real catalogue data"),
          ("ai", check_ai_mode, "B1 AI-Mode: the model answered through the application"),
          ("rag", check_rag, "B3 RAG: a grounded answer with citations from retrieved context"),
          ("multi-agent", check_multi_agent, "B4 Multi-Agent: Planner, Worker, Reviewer and human approval completed"))


def run(origin, enabled, call=None):
    call = call or make_call(origin)
    check_capabilities(call, enabled)
    print("PASS: capabilities match the enabled components: " + ", ".join(sorted(enabled)))
    for component, check, message in CHECKS:
        if component in enabled:
            check(call)
            print("PASS: " + message)
    check_disabled(call, enabled)
    disabled = [c for c in COMPONENTS if c not in enabled]
    if disabled:
        print("PASS: components not enabled still report disabled: " + ", ".join(disabled))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("origin", help="public HTTPS origin, e.g. https://example.org")
    parser.add_argument("--components", required=True, help="comma list matching the release: " + ", ".join(COMPONENTS))
    args = parser.parse_args(argv)
    try:
        run(args.origin, parse_components(args.components))
    except (RuntimeError, ValueError) as error:
        print(f"FAIL: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
