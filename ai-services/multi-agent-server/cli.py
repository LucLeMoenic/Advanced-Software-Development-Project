"""Terminal client for the Multi-Agent Server (same HTTP API the UI uses).

    python cli.py run --feature student-3 --task "Plan a food-focused day" \\
        --student3-backend http://localhost:5203 --category restaurant
    python cli.py review <workflow-id>            # interactive human review
    python cli.py show <workflow-id>
    python cli.py decide <workflow-id> --decision approve --notes "Looks right"
    python cli.py audit [<workflow-id>]  |  verify  |  list

Server: $MULTI_AGENT_SERVER_URL (default http://127.0.0.1:5600).
"""

import argparse
import json
import os
import sys
import time

import httpx

BASE = os.getenv("MULTI_AGENT_SERVER_URL", "http://127.0.0.1:5600").rstrip("/")
TERMINAL = {"awaiting_human_review", "approved", "corrected", "partially_accepted", "rejected", "failed"}


def call(method, path, **kwargs):
    try:
        response = httpx.request(method, BASE + path, timeout=30, **kwargs)
    except httpx.HTTPError as exc:
        sys.exit(f"Cannot reach the Multi-Agent Server at {BASE}: {exc}")
    body = response.json() if response.content else None
    if response.status_code >= 400:
        err = (body or {}).get("error", {})
        sys.exit(f"HTTP {response.status_code}: {err.get('code')} - {err.get('message')}")
    return body


def student3_evidence(backend, category):
    """Build evidence from the Student 3 backend's attraction catalogue."""
    params = {"category": category} if category else None
    rows = httpx.get(backend.rstrip("/") + "/api/attractions", params=params, timeout=15).json()
    return [{"id": f"attraction-{r['id']}", "title": r["name"],
             "text": f"{r['name']} is a {r['category']}. {r.get('description') or 'No description.'} "
                     f"Rating: {r['rating'] if r.get('rating') is not None else 'not rated'}."[:800]}
            for r in rows[:30]]


def wait_for(workflow_id, quiet=False):
    seen = None
    while True:
        record = call("GET", f"/workflows/{workflow_id}")
        if record["status"] != seen and not quiet:
            print(f"[{time.strftime('%H:%M:%S')}] {workflow_id}: {record['status']}", flush=True)
        seen = record["status"]
        if seen in TERMINAL:
            return record
        time.sleep(2)


def render(record):
    print(f"\n=== Workflow {record['id']}  ({record['feature']})  status: {record['status']} ===")
    print(f"Task: {record['task']}")
    if record["plan"]:
        print(f"\nPLANNER  objective: {record['plan']['objective']}")
        for step in record["plan"]["steps"]:
            print(f"  {step['id']}. {step['description']}")
        print("  requires evidence:", ", ".join(record["plan"]["required_evidence_ids"]))
    if record["work"]:
        print(f"\nWORKER   {record['work']['summary']}")
        for item in record["work"]["items"]:
            print(f"  [{item['id']}] {item['subject']}: {item['detail']}  (evidence: {', '.join(item['evidence_ids'])})")
    if record["review"]:
        review = record["review"]
        print(f"\nREVIEWER verdict: {review['verdict'].upper()} (model said {review['model_verdict']})")
        for f in review["findings"]:
            print(f"  - {f['severity']:<8} {f['item_id'] or '-':<4} {f['message']}")
        for r in review["recommendations"]:
            print(f"  * {r}")
    if record["error"]:
        print(f"\nFAILED at {record['error'].get('stage')}: {record['error']['code']} - {record['error']['message']}")
    if record["human_decision"]:
        hd = record["human_decision"]
        print(f"\nHUMAN    {hd['decision']} by {hd['decided_by']}: {hd['notes'] or '(no notes)'}")
    print()


def submit_decision(workflow_id, decision, notes, decided_by, corrected_file=None, accept=None):
    body = {"decision": decision, "notes": notes, "decided_by": decided_by}
    if corrected_file:
        with open(corrected_file, encoding="utf-8") as handle:
            body["corrected_output"] = json.load(handle)
    if accept:
        body["accepted_item_ids"] = [i.strip() for i in accept.split(",") if i.strip()]
    result = call("POST", f"/workflows/{workflow_id}/decision", json=body)
    print(f"Decision recorded: {result['status']}")
    return result


def cmd_run(args):
    if args.evidence_file:
        with open(args.evidence_file, encoding="utf-8") as handle:
            evidence = json.load(handle)
    elif args.student3_backend:
        evidence = student3_evidence(args.student3_backend, args.category)
    else:
        sys.exit("Provide --evidence-file or --student3-backend.")
    created = call("POST", "/workflows", json={
        "feature": args.feature, "task": args.task, "evidence": evidence, "submitted_by": args.submitted_by})
    print(f"Created {created['id']} with {len(evidence)} evidence entries")
    if args.no_wait:
        return
    record = wait_for(created["id"])
    render(record)
    if record["status"] == "awaiting_human_review":
        print(f"Next: python cli.py review {record['id']}")


def cmd_review(args):
    record = call("GET", f"/workflows/{args.id}")
    if record["status"] not in TERMINAL:
        record = wait_for(args.id)
    render(record)
    if record["status"] != "awaiting_human_review":
        return
    choice = input("Decision [a]pprove / [c]orrect / [p]artial / [r]eject: ").strip().lower()[:1]
    decision = {"a": "approve", "c": "correct", "p": "partial", "r": "reject"}.get(choice)
    if decision is None:
        sys.exit("No decision recorded.")
    notes = input("Notes: ").strip()
    corrected = input("Path to corrected JSON file: ").strip() if decision == "correct" else None
    accept = input("Accepted item ids (comma separated): ").strip() if decision == "partial" else None
    submit_decision(args.id, decision, notes, args.decided_by, corrected, accept)
    render(call("GET", f"/workflows/{args.id}"))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="start a workflow and wait for the agents")
    run.add_argument("--feature", required=True)
    run.add_argument("--task", required=True)
    run.add_argument("--evidence-file")
    run.add_argument("--student3-backend", help="build evidence from this Student 3 backend, e.g. http://localhost:5203")
    run.add_argument("--category")
    run.add_argument("--submitted-by", default="terminal")
    run.add_argument("--no-wait", action="store_true")
    run.set_defaults(func=cmd_run)

    review = sub.add_parser("review", help="show a workflow and record the human decision interactively")
    review.add_argument("id")
    review.add_argument("--decided-by", default="terminal-reviewer")
    review.set_defaults(func=cmd_review)

    show = sub.add_parser("show", help="print a workflow")
    show.add_argument("id")
    show.add_argument("--json", action="store_true")
    show.set_defaults(func=lambda a: print(json.dumps(call("GET", f"/workflows/{a.id}"), indent=2)) if a.json
                      else render(call("GET", f"/workflows/{a.id}")))

    decide = sub.add_parser("decide", help="record the human decision non-interactively")
    decide.add_argument("id")
    decide.add_argument("--decision", required=True, choices=["approve", "correct", "partial", "reject"])
    decide.add_argument("--notes", default="")
    decide.add_argument("--decided-by", default="terminal-reviewer")
    decide.add_argument("--corrected-file")
    decide.add_argument("--accept", help="comma separated item ids for a partial acceptance")
    decide.set_defaults(func=lambda a: submit_decision(a.id, a.decision, a.notes, a.decided_by, a.corrected_file, a.accept))

    sub.add_parser("list", help="list workflows").set_defaults(
        func=lambda a: [print(f"{w['id']}  {w['status']:<22} {w['feature']}  {w['task'][:60]}") for w in call("GET", "/workflows")])

    audit = sub.add_parser("audit", help="print audit entries")
    audit.add_argument("id", nargs="?")
    audit.set_defaults(func=lambda a: [
        print(f"#{e['seq']:<3} {e['ts']}  {e['workflow_id']}  {e['actor']:<9} {e['event']}  {e['hash'][:12]}")
        for e in call("GET", "/audit", params={"workflow_id": a.id} if a.id else None)])

    sub.add_parser("verify", help="verify the audit hash chain").set_defaults(
        func=lambda a: print(json.dumps(call("GET", "/audit/verify"))))

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
