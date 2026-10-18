"""Live post-commit check of the two Student 3 endpoints against running containers.

    GET  /api/attractions   (list + ?category= filter)
    POST /api/attractions   (create + validation)

Run by .github/workflows/student-3.yml after `docker compose up`:
    python student-3/tests/live_endpoint_check.py http://localhost:5203
Standard library only. Exits non-zero on any failed check and appends a
Markdown table to $GITHUB_STEP_SUMMARY when set.
"""

import http.client
import json
import os
import sys
import urllib.parse

results = []


def call(base, method, path, body=None):
    parsed = urllib.parse.urlparse(base)
    conn = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=10)
    try:
        headers = {"Content-Type": "application/json"} if body is not None else {}
        conn.request(method, path, json.dumps(body) if body is not None else None, headers)
        response = conn.getresponse()
        raw = response.read()
        return response.status, (json.loads(raw) if raw else None)
    finally:
        conn.close()


def check(name, condition, detail=""):
    results.append((name, bool(condition), detail))
    print(f"{'PASS' if condition else 'FAIL'}  {name}  {detail}")


def main(base):
    marker = "CI Live Check Cafe"
    status, created = call(base, "POST", "/api/attractions", {"name": marker, "category": "restaurant", "rating": 4.2})
    check("POST /api/attractions valid -> 201", status == 201, f"status={status}")
    new_id = (created or {}).get("id")
    check("POST returns id and echoes fields", isinstance(new_id, int) and created.get("name") == marker)

    status, listing = call(base, "GET", "/api/attractions")
    check("GET /api/attractions -> 200 list", status == 200 and isinstance(listing, list), f"status={status}")
    check("GET list contains the created row", any(a.get("id") == new_id for a in listing or []))
    check("GET list includes seeded data (>=10 rows)", len(listing or []) >= 10, f"rows={len(listing or [])}")

    status, filtered = call(base, "GET", "/api/attractions?category=restaurant")
    check(
        "GET ?category=restaurant returns only restaurants",
        status == 200 and filtered and all(a["category"] == "restaurant" for a in filtered)
        and any(a["id"] == new_id for a in filtered),
    )
    status, none_found = call(base, "GET", "/api/attractions?category=nightclub")
    check("GET ?category=<unknown> -> 200 []", status == 200 and none_found == [], f"status={status}")

    status, err = call(base, "POST", "/api/attractions", {"category": "sight"})
    check("POST missing name -> 400 validation_error", status == 400 and (err or {}).get("error") == "validation_error", f"status={status}")
    status, err = call(base, "POST", "/api/attractions", {})
    check("POST empty body -> 400 validation_error", status == 400 and (err or {}).get("error") == "validation_error", f"status={status}")
    _, after = call(base, "GET", "/api/attractions")
    check("Rejected POSTs stored nothing", len(after) == len(listing), f"before={len(listing)} after={len(after)}")

    if new_id is not None:  # cleanup so reruns against a long-lived stack stay tidy
        status, _ = call(base, "DELETE", f"/api/attractions/{new_id}")
        check("Cleanup DELETE -> 204", status == 204, f"status={status}")


if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5203"
    try:
        main(base_url)
    except OSError as exc:
        check("Backend reachable", False, str(exc))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("### Student 3 live endpoint check (GET + POST /api/attractions)\n\n| Check | Result |\n|---|---|\n")
            for name, ok, detail in results:
                handle.write(f"| {name} {detail} | {'pass' if ok else 'FAIL'} |\n")
    failed = [name for name, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    sys.exit(1 if failed else 0)
