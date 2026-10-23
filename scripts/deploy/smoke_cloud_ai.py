"""Verify cloud AI components through the public HTTPS gateway.

    python scripts/deploy/smoke_cloud_ai.py https://<domain> --components ai,mcp,rag,multi-agent

--components must match what the release was prepared with (prepare_cloud.py --ai-services). For each enabled component this
drives a real interaction through the application and checks the answer is genuine, and for each component that is NOT enabled
it checks the application still reports it cleanly disabled:

  ai           B1  AI-Mode: /api/recommend answered by the model (not the deterministic fallback)
  mcp          B2  MCP: a tool call through the backend returns real catalogue data
  rag          B3  RAG: a grounded answer with citations from retrieved context
  multi-agent  B4  Multi-Agent: a Planner, Worker, Reviewer workflow reaches human review (no automatic decision)

--all-features also requires gateway credentials and checks group CRUD and all supported integrations.
Student 4 has no Multi-Agent integration. Use smoke_cloud.py for the AI-off baseline. Standard library only.
"""

import argparse
import sys
import time
from urllib.error import URLError

from cloud_auth import credentials, make_call
from smoke_cloud import run as check_crud

COMPONENTS = ("ai", "mcp", "rag", "multi-agent")
API = "/attractions-api"
WORKFLOW_TIMEOUT = 2220  # three stages, each with up to two 360-second calls, plus polling overhead
POLL_SECONDS = 5


def parse_components(value):
    items = [part.strip() for part in (value or "").split(",") if part.strip()]
    unknown = [item for item in items if item not in COMPONENTS]
    if not items or unknown:
        raise ValueError(f"Choose from: {', '.join(COMPONENTS)}" + (f" (unknown: {', '.join(unknown)})" if unknown else ""))
    return frozenset(items)


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
    started = call(f"{API}/agents/workflows", "POST", {"task": "Suggest a relaxed afternoon of food", "category": "restaurant"}, 202)
    wait_for_review(call, f"{API}/agents/workflows/{started['id']}", sleep, now)


def wait_for_review(call, path, sleep=None, now=None):
    # Resolved at call time, not bound as defaults, so a test (or a caller) can supply its own clock.
    sleep = sleep or time.sleep
    now = now or time.monotonic
    deadline = now() + WORKFLOW_TIMEOUT
    print(f"CHECK: waiting for workflow {path} (up to {WORKFLOW_TIMEOUT} seconds).", flush=True)
    while True:
        record = call(path)
        if record["status"] in ("awaiting_human_review", "failed"):
            break
        if now() > deadline:
            raise RuntimeError(f"The workflow {path} was still '{record['status']}' after {WORKFLOW_TIMEOUT} seconds.")
        sleep(POLL_SECONDS)
    if record["status"] == "failed":
        error = record.get("error") or {}
        raise RuntimeError(f"The workflow failed at {error.get('stage')}: {error.get('code')} ({error.get('message')}); path: {path}.")
    if not (record.get("plan") and record.get("work") and record.get("review")):
        raise RuntimeError("The workflow reached human review without a plan, a Worker output and a Reviewer verdict.")
    if [step.get("stage") for step in record.get("history", [])] != ["planner", "worker", "reviewer"]:
        raise RuntimeError("The workflow history does not show Planner, Worker and Reviewer in order.")
    if record.get("human_decision") is not None or record.get("humanDecision") is not None:
        raise RuntimeError("The smoke workflow already has a human decision; inspect the audit before continuing.")
    print(f"MANUAL: review workflow {path} in the application; no human approval has been submitted.")


def grounded(answer, feature):
    if (answer.get("confidence") not in ("low", "medium", "high")
            or not answer.get("citations") or not str(answer.get("answer", "")).strip()):
        raise RuntimeError(f"{feature}: RAG did not return a grounded answer with citations.")


def check_other_features(call, enabled):
    searches = call("/accommodation/api/searches")
    search_id = searches[0]["id"]
    trip = call(f"/itinerary-api/trips/{call('/itinerary-api/trips')[0]['id']}")
    journey = call("/budget-api/journeys")[0]["journeyLabel"]
    destination = call("/logistics/api/destinations")[0]["id"]
    if "ai" in enabled:
        advisory = call("/logistics/api/advisory", "POST", {"destination_id": destination})
        if not str(advisory.get("advisory", "")).strip() or advisory.get("model") != "llama3.2:3b":
            raise RuntimeError("Student 5 did not return an advisory from the provisioned model.")
    if "mcp" in enabled:
        lookup = call("/accommodation/api/assistant", "POST", {"mode": "lookup", "question": f"Show saved search {search_id}"})
        if lookup.get("tool") != "accommodation.get_search" or not lookup.get("result"):
            raise RuntimeError("Student 1 catalogue lookup did not call the expected MCP tool.")
        summary = call(f"/itinerary-api/trips/{trip['id']}/mcp-summary", "POST", {})
        if summary.get("tool") != "itinerary.get_summary" or summary.get("summary", {}).get("tripId") != trip["id"]:
            raise RuntimeError("Student 2 MCP summary did not match the selected trip.")
        budget = call("/budget-api/budget-check", "POST", {"journeyLabel": journey})
        if budget.get("tool") != "budget.get_summary" or budget.get("result", {}).get("ok") is not True:
            raise RuntimeError("Student 4 MCP budget check failed.")
        visa = call("/logistics/api/mcp/invoke", "POST",
                    {"tool": "logistics.check_visa_requirement", "arguments": {"destination_id": destination}})
        if visa.get("result", {}).get("ok") is not True:
            raise RuntimeError("Student 5 MCP visa lookup failed.")
    if "rag" in enabled:
        for feature, path, body in (
            ("Student 1", "/accommodation/api/assistant", {"mode": "guide", "question": "Is Tokyo safe for families?"}),
            ("Student 2", "/itinerary-api/itinerary-advice", {"tripId": trip["id"], "question": "How should I pace activities and leave buffer time?"}),
            ("Student 4", "/budget-api/budget-guidance", {"question": "What does warning mean for a category budget?"}),
            ("Student 5", "/logistics/api/rag/ask", {"question": "What is the difference between visa on arrival and an eVisa?"}),
        ):
            grounded(call(path, "POST", body), feature)
    if "multi-agent" in enabled:
        started = call(f"/accommodation/api/searches/{search_id}/reviews", "POST", {}, 202)
        wait_for_review(call, f"/accommodation/api/reviews/{started['id']}")
        if not {"ai", "mcp"} <= set(enabled):
            raise RuntimeError("Student 2 edit assessment requires AI and MCP as well as Multi-Agent.")
        preview = call(f"/itinerary-api/trips/{trip['id']}/edit-preview", "POST",
                       {"question": "Add a Coffee break to day 1"})
        workflow_id = (preview.get("preview") or {}).get("workflowId")
        if not workflow_id:
            raise RuntimeError("Student 2 did not create a review for the natural-language edit preview.")
        wait_for_review(call, f"/itinerary-api/trips/{trip['id']}/multi-agent-workflows/{workflow_id}")
        started = call(f"/logistics/api/destinations/{destination}/readiness-reviews", "POST", {}, 202)
        wait_for_review(call, f"/logistics/api/readiness-reviews/{started['id']}?destination_id={destination}")
        print("INFO: Student 4 has no Multi-Agent integration; no unsupported capability is claimed.")
    print("PASS: enabled AI integrations exercised through Students 1, 2, 4 and 5.")


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
          ("multi-agent", check_multi_agent, "B4 Multi-Agent: Planner, Worker and Reviewer reached human review; decision pending"))


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
    parser.add_argument("--all-features", action="store_true", help="Verify protected group CRUD and every supported AI integration.")
    args = parser.parse_args(argv)
    try:
        enabled = parse_components(args.components)
        if args.all_features:
            credentials(required=True)
            call = make_call(args.origin)
            check_crud(args.origin, enabled=enabled, call=call)
            run(args.origin, enabled, call=call)
            check_other_features(call, enabled)
        else:
            run(args.origin, enabled)
    except (RuntimeError, ValueError, URLError) as error:
        print(f"FAIL: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
