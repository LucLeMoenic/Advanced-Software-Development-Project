"""Live post-commit check of the two Student 5 endpoints against running containers.

    POST /api/destinations        (create)
    PUT  /api/destinations/<id>   (update)

Run by .github/workflows/student-5.yml after `docker compose up`, so the
request travels backend -> database API -> SQLite with nothing mocked:
    python student-5/backend/tests/live_endpoint_check.py http://localhost:5205
Standard library only, and not collected by pytest (no test_ prefix). The
destination it creates has a unique country name and is always deleted, so
reruns against a long-lived local stack leave no trace. Exits non-zero on any
failed check and appends a Markdown table to $GITHUB_STEP_SUMMARY when set.
"""

import http.client
import json
import os
import sys
import urllib.parse
import uuid

# Far above any id SQLite will hand out to this table.
MISSING_ID = 2147483647

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


def create(base, country):
    """POST one destination; returns its id, or None if it was not created."""
    created_row = {"country": country, "visa_requirement": "visa-free", "notes": "Created by CI"}
    status, created = call(base, "POST", "/api/destinations", created_row)
    check("POST /api/destinations valid -> 201", status == 201, f"status={status}")
    new_id = (created or {}).get("id")
    check(
        "POST returns an id and the stored fields",
        isinstance(new_id, int) and all(created.get(k) == v for k, v in created_row.items()),
    )
    return new_id if isinstance(new_id, int) else None


def exercise(base, country, new_id):
    """Invalid create, then update and read back the destination created first."""
    _, before = call(base, "GET", "/api/destinations")
    status, err = call(base, "POST", "/api/destinations", {"country": country})
    check(
        "POST missing visa_requirement -> 400 from the database",
        status == 400 and "visa_requirement" in (err or {}).get("error", ""),
        f"status={status}",
    )
    _, after = call(base, "GET", "/api/destinations")
    check(
        "Rejected POST stored nothing",
        len(after or []) == len(before or []),
        f"before={len(before or [])} after={len(after or [])}",
    )

    change = {"visa_requirement": "eVisa", "notes": "Updated by CI"}
    status, updated = call(base, "PUT", f"/api/destinations/{new_id}", change)
    check("PUT /api/destinations/<id> valid -> 200", status == 200, f"status={status}")
    check(
        "PUT merges the change and keeps the country",
        updated == {"id": new_id, "country": country, **change},
    )

    status, reread = call(base, "GET", f"/api/destinations/{new_id}")
    check("GET after PUT returns the updated row", status == 200 and reread == updated, f"status={status}")

    status, err = call(base, "PUT", f"/api/destinations/{new_id}", {"visa_requirement": ""})
    check(
        "PUT blank visa_requirement -> 400 from the database",
        status == 400 and "error" in (err or {}),
        f"status={status}",
    )
    _, reread = call(base, "GET", f"/api/destinations/{new_id}")
    check("Rejected PUT changed nothing", reread == updated)

    status, err = call(base, "PUT", f"/api/destinations/{MISSING_ID}", {"notes": "Missing"})
    check("PUT unknown id -> 404 from the database", status == 404 and "error" in (err or {}), f"status={status}")


def cleanup(base, country, new_id):
    """Delete the destination this run created, found by its unique country
    when the create reply did not yield a usable id."""
    if new_id is None:
        _, rows = call(base, "GET", "/api/destinations")
        ids = [row.get("id") for row in rows or [] if row.get("country") == country]
        if not ids:
            return  # nothing was created
    else:
        ids = [new_id]
    for row_id in ids:
        status, _ = call(base, "DELETE", f"/api/destinations/{row_id}")
        check("Cleanup DELETE -> 204", status == 204, f"status={status}")
        status, _ = call(base, "GET", f"/api/destinations/{row_id}")
        check("Deleted destination is gone (404)", status == 404, f"status={status}")


def main(base):
    country = f"CI Endpoint Check {uuid.uuid4().hex[:8]}"
    new_id = None
    # Cleanup runs even if a check raises (e.g. the backend drops mid-run).
    try:
        new_id = create(base, country)
        if new_id is not None:
            exercise(base, country, new_id)
    finally:
        cleanup(base, country, new_id)


def cell(text):
    """Keep exception text from breaking a Markdown table row."""
    return str(text).replace("|", "/").replace("\r", " ").replace("\n", " ")


if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5205"
    try:
        main(base_url)
    except Exception as exc:  # any failure must still reach the step summary
        check("Backend reachable and answering as expected", False, f"{type(exc).__name__}: {exc}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(
                "### Student 5 live endpoint check (POST and PUT /api/destinations)\n\n"
                "| Check | Result |\n|---|---|\n"
            )
            for name, ok, detail in results:
                handle.write(f"| {cell(name)} {cell(detail)} | {'pass' if ok else 'FAIL'} |\n")
    failed = [name for name, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    sys.exit(1 if failed or not results else 0)
