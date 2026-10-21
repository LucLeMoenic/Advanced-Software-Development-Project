"""Verify the public gateway and Student 1 and Student 2 CRUD without native AI dependencies."""

import argparse
import json
import uuid
from datetime import date, timedelta
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def run(base):
    parsed = urlparse(base)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise ValueError("Provide the public HTTPS origin.")

    def call(path, method="GET", body=None, expected=200):
        request = Request(base.rstrip("/") + path, method=method,  # noqa: S310 - HTTPS origin validated above
                          data=None if body is None else json.dumps(body).encode(),
                          headers={"Content-Type": "application/json"})
        try:
            response = urlopen(request, timeout=30)  # noqa: S310 - HTTPS origin checked above
        except HTTPError as exc:
            response = exc
        with response:
            data = response.read(1048576)
            if response.status != expected:
                raise RuntimeError(f"{method} {path}: expected {expected}, received {response.status}")
        return json.loads(data) if data and data.startswith((b"{", b"[")) else data

    for route in ("/", "/accommodation/", "/itinerary/", "/attractions/", "/budget/", "/logistics/"):
        call(route)
    modes = call("/itinerary-api/capabilities")
    if modes != {"aiEnabled": False, "mcpEnabled": False, "ragEnabled": False, "multiAgentEnabled": False}:
        raise RuntimeError("The cloud baseline must disable every Student 2 AI capability.")
    baseline = call("/itinerary-api/trips")
    if len(baseline) < 10:
        raise RuntimeError("At least ten demonstration trips are required.")
    criteria = {"user": f"R2 smoke {uuid.uuid4().hex[:8]}", "destination": "Osaka",
                "startDate": "2026-11-01", "endDate": "2026-11-02", "budget": 900, "interests": "Parks"}
    trip = call("/itinerary-api/trips", "POST", criteria, 201)
    path = f"/itinerary-api/trips/{trip['id']}"
    try:
        if trip.get("generationMode") != "fallback" or len(trip.get("stops", [])) != 4:
            raise RuntimeError("Disabled AI must still create a complete deterministic itinerary.")
        call(path, "PUT", {**criteria, "budget": 1200})
        saved = call(path)
        if saved["budget"] != 1200 or saved["stops"] != trip["stops"]:
            raise RuntimeError("Update/readback did not preserve the itinerary.")
        stop = call(path + "/stops", "POST", {"day": 1, "activity": "Cloud smoke stop", "notes": "Synthetic fixture"}, 201)
        stop_path = f"/itinerary-api/stops/{stop['id']}"
        call(stop_path, "PUT", {"day": 2, "activity": "Updated cloud smoke stop", "notes": "Synthetic fixture"})
        call(stop_path, "DELETE", expected=204)
        for endpoint in ("/edit-preview", "/multi-agent-workflows"):
            call(path + endpoint, "POST", {}, 503)
        call("/itinerary-api/itinerary-advice", "POST", {"question": "Budget?"}, 503)
    finally:
        call(path, "DELETE", expected=204)
    call(path, expected=404)
    print("PASS: six gateway pages; four AI modes disabled; deterministic create; trip/stop CRUD.")
    check_student1(call)
    print("PASS: Student 1 AI modes disabled; cached-catalogue search create, rename and delete.")
    print("Persistence across redeploy, other features' CRUD and rollback require separate evidence.")


def check_student1(call):
    """Student 1 through the gateway: every AI mode off, and saved-search CRUD on the cached catalogue."""
    api = "/accommodation/api"
    modes = call(f"{api}/capabilities")
    if modes != {"aiRanking": False, "lookup": False, "guide": False, "multiAgent": False}:
        raise RuntimeError("The cloud baseline must disable every Student 1 AI capability.")
    if len(call(f"{api}/searches")) < 10:
        raise RuntimeError("At least ten demonstration accommodation searches are required.")
    check_in = date.today() + timedelta(days=30)
    criteria = {"destination": "Tokyo", "checkIn": check_in.isoformat(),
                "checkOut": (check_in + timedelta(days=2)).isoformat(), "guests": 1,
                "minimumPrice": 0, "maximumPrice": 100000, "preferences": "", "useAi": False}
    search = call(f"{api}/searches", "POST", criteria, 201)
    path = f"{api}/searches/{search['id']}"
    try:
        if search.get("rankingMode") != "programmatic" or not search.get("results"):
            raise RuntimeError("Disabled AI must still rank the cached Tokyo catalogue.")
        title = f"R2 smoke {uuid.uuid4().hex[:8]}"
        call(path, "PATCH", {"title": title})
        saved = call(path)
        if saved["title"] != title or saved["results"] != search["results"]:
            raise RuntimeError("Rename/readback did not preserve the saved search.")
        call(f"{api}/searches", "POST", {**criteria, "useAi": True}, 503)
        call(f"{path}/reviews", "POST", {}, 503)
    finally:
        call(path, "DELETE", expected=204)
    call(path, expected=404)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("origin")
    run(parser.parse_args().origin)
