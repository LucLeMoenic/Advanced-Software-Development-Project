"""Verify gateway pages and group CRUD against the selected cloud capability profile."""

import argparse
import uuid
from datetime import date, timedelta
from cloud_auth import make_call


def run(base, enabled=frozenset(), call=None):
    call = call or make_call(base, timeout=420 if enabled else 30)
    for route in ("/", "/accommodation/", "/itinerary/", "/attractions/", "/budget/", "/logistics/"):
        call(route)
    modes = call("/itinerary-api/capabilities")
    if modes != capabilities(enabled):
        raise RuntimeError("Student 2 capabilities do not match the selected cloud profile.")
    baseline = call("/itinerary-api/trips")
    if len(baseline) < 10:
        raise RuntimeError("At least ten demonstration trips are required.")
    criteria = {"user": f"R2 smoke {uuid.uuid4().hex[:8]}", "destination": "Osaka",
                "startDate": "2026-11-01", "endDate": "2026-11-02", "budget": 900, "interests": "Parks"}
    trip = call("/itinerary-api/trips", "POST", criteria, 201)
    path = f"/itinerary-api/trips/{trip['id']}"
    try:
        expected_mode = "ai" if "ai" in enabled else "fallback"
        if trip.get("generationMode") != expected_mode or len(trip.get("stops", [])) != 4:
            raise RuntimeError(
                f"Trip generation did not match the selected AI mode or required stop count: "
                f"expected mode={expected_mode}, stops=4; received mode={trip.get('generationMode')}, "
                f"stops={len(trip.get('stops', []))}. Check student2-backend and Ollama logs for the cause.")
        call(path, "PUT", {**criteria, "budget": 1200})
        saved = call(path)
        if saved["budget"] != 1200 or saved["stops"] != trip["stops"]:
            raise RuntimeError("Update/readback did not preserve the itinerary.")
        stop = call(path + "/stops", "POST", {"day": 1, "activity": "Cloud smoke stop", "notes": "Synthetic fixture"}, 201)
        stop_path = f"/itinerary-api/stops/{stop['id']}"
        call(stop_path, "PUT", {"day": 2, "activity": "Updated cloud smoke stop", "notes": "Synthetic fixture"})
        call(stop_path, "DELETE", expected=204)
        if not {"ai", "mcp"} <= set(enabled):
            for endpoint in ("/edit-preview", "/edit-operation-preview", "/edit-confirm"):
                call(path + endpoint, "POST", {}, 503)
        if "multi-agent" not in enabled:
            call(path + "/multi-agent-workflows/wf-20261020T080000Z-0123abcd", expected=503)
        if "rag" not in enabled:
            call("/itinerary-api/itinerary-advice", "POST", {"question": "Budget?"}, 503)
    finally:
        call(path, "DELETE", expected=204)
    call(path, expected=404)
    print("PASS: six gateway pages; Student 2 capability/generation mode and trip/stop CRUD.")
    for number, check in ((1, check_student1), (3, check_student3), (4, check_student4), (5, check_student5)):
        check(call, enabled)
        print(f"PASS: Student {number} cloud profile and CRUD checks.")
    print("Persistence across redeploy and rollback require separate evidence.")


def capabilities(enabled):
    return {flag: component in enabled for flag, component in
            (("aiEnabled", "ai"), ("mcpEnabled", "mcp"), ("ragEnabled", "rag"), ("multiAgentEnabled", "multi-agent"))}


def check_student1(call, enabled=frozenset()):
    """Check Student 1's selected capability/ranking mode and saved-search CRUD."""
    api = "/accommodation/api"
    modes = call(f"{api}/capabilities")
    if modes != dict(zip(("aiRanking", "lookup", "guide", "multiAgent"), capabilities(enabled).values())):
        raise RuntimeError("The cloud baseline must disable every Student 1 AI capability.")
    if len(call(f"{api}/searches")) < 10:
        raise RuntimeError("At least ten demonstration accommodation searches are required.")
    check_in = date.today() + timedelta(days=30)
    criteria = {"destination": "Tokyo", "checkIn": check_in.isoformat(),
                "checkOut": (check_in + timedelta(days=2)).isoformat(), "guests": 1,
                "minimumPrice": 0, "maximumPrice": 100000, "preferences": "", "useAi": "ai" in enabled}
    search = call(f"{api}/searches", "POST", criteria, 201)
    path = f"{api}/searches/{search['id']}"
    try:
        if search.get("rankingMode") != ("ai" if "ai" in enabled else "programmatic") or not search.get("results"):
            raise RuntimeError("AI ranking failed." if "ai" in enabled else "Disabled AI must still rank the cached Tokyo catalogue.")
        title = f"R2 smoke {uuid.uuid4().hex[:8]}"
        call(path, "PATCH", {"title": title})
        saved = call(path)
        if saved["title"] != title or saved["results"] != search["results"]:
            raise RuntimeError("Rename/readback did not preserve the saved search.")
        if "ai" not in enabled:
            call(f"{api}/searches", "POST", {**criteria, "useAi": True}, 503)
        if "multi-agent" not in enabled:
            call(f"{path}/reviews", "POST", {}, 503)
    finally:
        call(path, "DELETE", expected=204)
    call(path, expected=404)


def check_student3(call, enabled=frozenset()):
    """Check Student 3's selected capability/recommendation mode and attraction/review CRUD."""
    api = "/attractions-api"
    modes = call(f"{api}/capabilities")
    if modes != capabilities(enabled):
        raise RuntimeError("The cloud baseline must disable every Student 3 AI capability.")
    if len(call(f"{api}/attractions")) < 10:
        raise RuntimeError("At least ten demonstration attractions are required.")
    recommendation = call(f"{api}/recommend", "POST", {"interest": "street art"})
    if recommendation.get("source") not in (("ai", "ai_retry") if "ai" in enabled else ("fallback",)) or not recommendation.get("recommendation"):
        raise RuntimeError("AI recommendation failed." if "ai" in enabled else "Disabled AI must still return a deterministic recommendation.")
    for component, endpoint, body in (("mcp", f"{api}/mcp/invoke", {"tool": "attractions.search", "arguments": {}}),
                                     ("rag", f"{api}/rag/ask", {"question": "Is Chin Chin busy?"}),
                                     ("multi-agent", f"{api}/agents/workflows", {"task": "Plan a relaxed day"})):
        if component not in enabled:
            call(endpoint, "POST", body, 503)
    name = f"R2 smoke {uuid.uuid4().hex[:8]}"
    fields = {"name": name, "category": "activity", "description": "Synthetic fixture", "rating": 4}
    attraction = call(f"{api}/attractions", "POST", fields, 201)
    path = f"{api}/attractions/{attraction['id']}"
    try:
        call(path, "PUT", {**fields, "name": f"{name} updated", "rating": 3.5})
        saved = call(path)
        if saved["name"] != f"{name} updated" or saved["rating"] != 3.5:
            raise RuntimeError("Update/readback did not preserve the attraction.")
        review = call(f"{api}/reviews", "POST", {"attraction_id": attraction["id"], "rating": 5, "comment": "Cloud smoke review"}, 201)
        listed = call(f"{api}/reviews?attraction_id={attraction['id']}")
        if [item["id"] for item in listed] != [review["id"]]:
            raise RuntimeError("Review create/readback failed.")
    finally:
        call(path, "DELETE", expected=204)  # also removes the attraction's reviews
    call(path, expected=404)


def check_student4(call, enabled=frozenset()):
    """Check Student 4's supported capability/advice mode and budget/expense CRUD."""
    api = "/budget-api"
    modes = call(f"{api}/capabilities")
    if modes != {key: value for key, value in capabilities(enabled).items() if key != "multiAgentEnabled"}:
        raise RuntimeError("The cloud baseline must disable every Student 4 AI capability.")
    if len(call(f"{api}/budgets")) < 10:
        raise RuntimeError("At least ten demonstration budgets are required.")
    journeys = call(f"{api}/journeys")
    advice = call(f"{api}/insights", "POST", {"journeyLabel": journeys[0]["journeyLabel"]})
    if advice.get("source") not in (("ai", "ai_retry") if "ai" in enabled else ("fallback",)) or not advice.get("suggestions"):
        raise RuntimeError("AI budget advice failed." if "ai" in enabled else "Disabled AI must still return deterministic budget advice.")
    for component, endpoint, body in (("rag", f"{api}/budget-guidance", {"question": "How should I split my budget?"}),
                                     ("mcp", f"{api}/budget-check", {})):
        if component not in enabled:
            call(endpoint, "POST", body, 503)
    label = f"R2 smoke {uuid.uuid4().hex[:8]}"
    fields = {"journeyLabel": label, "category": "food", "limitAmountMinor": 20000, "baseCurrency": "AUD",
              "startDate": "2026-09-01", "endDate": "2026-09-07"}
    budget = call(f"{api}/budgets", "POST", fields, 201)
    budget_path = f"{api}/budgets/{budget['id']}"
    expense_path = None
    try:
        call(budget_path, "PUT", {**fields, "limitAmountMinor": 25000})
        saved = call(budget_path)
        if saved["limitAmountMinor"] != 25000 or saved["journeyLabel"] != label:
            raise RuntimeError("Budget update/readback did not preserve the changes.")
        expense = {"budgetId": budget["id"], "description": "Cloud smoke lunch", "originalAmountMinor": 1500,
                   "originalCurrency": "AUD", "spentOn": "2026-09-02"}
        created = call(f"{api}/expenses", "POST", expense, 201)
        expense_path = f"{api}/expenses/{created['id']}"
        if created["convertedAmountMinor"] != 1500:
            raise RuntimeError("A same-currency expense must keep its amount.")
        call(expense_path, "PUT", {**expense, "description": "Cloud smoke lunch updated", "originalAmountMinor": 1800})
        updated = call(expense_path)
        if updated["originalAmountMinor"] != 1800 or updated["convertedAmountMinor"] != 1800:
            raise RuntimeError("Expense update/readback did not recompute the conversion.")
    finally:
        if expense_path:
            call(expense_path, "DELETE", expected=204)
        call(budget_path, "DELETE", expected=204)
    if expense_path:
        call(expense_path, expected=404)
    call(budget_path, expected=404)


def check_student5(call, enabled=frozenset()):
    """Check Student 5's disabled routes, reference data and destination CRUD.

    The 503 bodies are checked as well as the status, because a backend that is down also answers 503
    through the gateway; only the named error proves the switch is off. The AI routes are checked before
    anything is created. Enabled routes are exercised by the separate AI smoke checks.
    """
    api = "/logistics/api"
    destinations = call(f"{api}/destinations")
    if len(destinations) < 10:
        raise RuntimeError("At least ten demonstration destinations are required.")
    for table in ("weather-notes", "transit-options"):
        if not call(f"{api}/{table}"):
            raise RuntimeError(f"The Student 5 {table} reference data is empty.")
    seeded = destinations[0]["id"]
    for path, method, body, code in ((f"{api}/advisory", "POST", {"destination_id": seeded}, "ai_disabled"),
                                     (f"{api}/mcp/tools", "GET", None, "mcp_disabled"),
                                     (f"{api}/rag/ask", "POST", {"question": "What is a visa on arrival?"}, "rag_disabled"),
                                     (f"{api}/destinations/{seeded}/readiness-reviews", "POST", {}, "multi_agent_disabled")):
        if code.removesuffix("_disabled").replace("_", "-") in enabled:
            continue
        refusal = call(path, method, body, 503)
        if not isinstance(refusal, dict) or refusal.get("error") != code:
            raise RuntimeError(f"{method} {path}: expected the {code} body.")
    country = f"R2 smoke {uuid.uuid4().hex[:8]}"
    destination = call(f"{api}/destinations", "POST", {"country": country, "visa_requirement": "Synthetic fixture"}, 201)
    path = f"{api}/destinations/{destination['id']}"
    try:
        if call(path).get("country") != country:
            raise RuntimeError("Destination create/readback failed.")
        call(path, "PUT", {"visa_requirement": "Synthetic fixture updated", "notes": "Cloud smoke"})
        saved = call(path)
        if saved.get("country") != country or saved.get("visa_requirement") != "Synthetic fixture updated":
            raise RuntimeError("Update/readback did not preserve the destination.")
    finally:
        call(path, "DELETE", expected=204)
    call(path, expected=404)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("origin")
    run(parser.parse_args().origin)
