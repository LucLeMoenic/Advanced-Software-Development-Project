"""Exercise real native agents through the Student 2 backend using a saved synthetic trip.

This is not a substitute for container-to-host or human-acceptance evidence.
It never submits a human decision or changes saved trips.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "student-2" / "backend"))
from app import DatabaseClient, create_app
from multi_agent import MultiAgentClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default="http://127.0.0.1:5302")
    parser.add_argument("--multi-agent-url", default="http://127.0.0.1:5600")
    parser.add_argument("--trip-id", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for value in (args.database_url, args.multi_agent_url):
        url = urlparse(value)
        if url.scheme != "http" or url.hostname not in ("127.0.0.1", "localhost") or url.path not in ("", "/"):
            raise ValueError("Live checks require loopback HTTP services and synthetic demonstration data.")
    database = DatabaseClient(args.database_url)
    before, status = database.request("GET", f"/api/data/trips/{args.trip_id}")
    if status != 200:
        raise RuntimeError("The synthetic saved trip is unavailable.")
    client = create_app(database_client=database, multi_agent_client=MultiAgentClient(args.multi_agent_url),
                        settings={"MULTI_AGENT_ENABLED": True, "AI_ENABLED": False, "MCP_ENABLED": False, "RAG_ENABLED": False}).test_client()
    path = f"/api/trips/{args.trip_id}/multi-agent-workflows"
    created = client.post(path, json={"task": "Review the balance of saved days without inventing activities, costs or availability. Cite supplied evidence titles."})
    if created.status_code != 202:
        raise RuntimeError(f"Workflow creation failed: {created.json}")
    workflow_id = created.json["id"]
    print(f"Created {workflow_id}", flush=True)
    deadline = time.monotonic() + 1200
    previous = None
    while True:
        response = client.get(f"{path}/{workflow_id}")
        if response.status_code != 200:
            raise RuntimeError(f"Workflow read failed: {response.json}")
        record = response.json
        if record["status"] != previous:
            print(record["status"], flush=True)
            previous = record["status"]
        if record["status"] in ("awaiting_human_review", "failed") or time.monotonic() >= deadline:
            break
        time.sleep(2)
    after, status = database.request("GET", f"/api/data/trips/{args.trip_id}")
    audit = httpx.get(args.multi_agent_url + "/audit", params={"workflow_id": workflow_id}, timeout=10)
    audit.raise_for_status()
    verification = httpx.get(args.multi_agent_url + "/audit/verify", timeout=10)
    verification.raise_for_status()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        "execution": "Native backend test client -> container database API + native Multi-Agent HTTP server",
        "humanDecision": "Pending; no human decision was automated.",
        "savedTripUnchanged": status == 200 and before == after,
        "record": record, "audit": audit.json(), "auditVerification": verification.json(),
    }, indent=2), encoding="utf-8")
    if (record["status"] != "awaiting_human_review" or record["review"]["degraded"]
            or record["review"]["verdict"] != "pass" or before != after or not verification.json()["valid"]):
        raise RuntimeError(f"Live acceptance failed; inspect {args.output}.")
    print(f"PASS: real three-agent workflow, unchanged trip and valid audit. Human review remains pending. Evidence: {args.output}")


if __name__ == "__main__":
    main()
