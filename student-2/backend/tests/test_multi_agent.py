import copy
import json

import httpx
import pytest

from app import DependencyError, create_app
from multi_agent import EditReview, MultiAgentClient, evidence_for, validate_record
from ai_clients import IntegrationError

ID = "wf-20261020T080000Z-0123abcd"
BASE = "/api/trips/12/multi-agent-workflows"
PREVIEW = "/api/trips/12/edit-preview"
CONFIRM = "/api/trips/12/edit-confirm"


def trip():
    return {"id": 12, "user": "Excluded identity", "destination": "Osaka", "startDate": "2026-11-01",
            "endDate": "2026-11-02", "budget": 900, "interests": "Quiet walks",
            "stops": [{"id": 4, "tripId": 12, "day": 1, "activity": "Park walk", "notes": "Saved plan", "sortOrder": 0}]}


def ready():
    work = {"summary": "A flexible plan.", "items": [
        {"id": "i1", "subject": "Trip overview", "detail": "Day 2 has no saved stops.", "evidence_ids": ["trip-12"]},
        {"id": "i2", "subject": "Day 1: Park walk", "detail": "Keep the walk flexible.", "evidence_ids": ["stop-4"]}]}
    return {"id": ID, "feature": "student-2", "task": "Review my saved plan", "submitted_by": "student-2-frontend",
            "status": "awaiting_human_review", "created_at": "2026-10-20T08:00:00Z", "updated_at": "2026-10-20T08:01:00Z",
            "evidence": evidence_for(trip(), 12), "plan": {
                "objective": "Review saved days", "steps": [{"id": "s1", "description": "Inspect saved days"}],
                "required_evidence_ids": ["trip-12"], "success_criteria": ["Cite saved evidence"]},
            "work": work, "review": {"verdict": "pass", "model_verdict": "pass", "degraded": False,
                "automatic_findings": [], "model_findings": [], "findings": [], "recommendations": []},
            "human_decision": None, "final_output": None, "history": [], "error": None}


class Database:
    def __init__(self):
        self.body = trip()
        self.calls = []
        self.status = 200

    def request(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        return copy.deepcopy(self.body), self.status


class Server:
    def __init__(self):
        self.record = ready()
        self.calls = []

    def request(self, method, path, payload=None, expected=200):
        self.calls.append((method, path, payload))
        if path == "/workflows":
            self.record["evidence"] = payload["evidence"]
            self.record["plan"]["required_evidence_ids"] = [payload["evidence"][0]["id"]]
            for item, evidence in zip(self.record["work"]["items"], payload["evidence"]):
                item.update(subject=evidence["title"], evidence_ids=[evidence["id"]])
            return {"id": ID, "status": "queued"}
        if method == "POST":
            decision = payload["decision"]
            self.record["status"] = {"approve": "approved", "correct": "corrected",
                                     "partial": "partially_accepted", "reject": "rejected"}[decision]
            self.record["human_decision"] = payload
            self.record["final_output"] = copy.deepcopy(self.record["work"])
            if decision == "reject":
                self.record["final_output"] = None
            elif decision == "correct":
                self.record["final_output"] = payload["corrected_output"]
            elif decision == "partial":
                self.record["final_output"]["items"] = [
                    i for i in self.record["work"]["items"] if i["id"] in payload["accepted_item_ids"]]
        return copy.deepcopy(self.record)


class Mcp:
    def __init__(self):
        self.applied = []

    def itinerary(self, trip_id):
        value = trip()
        return {"summary": {
            "tripId": trip_id, "destination": value["destination"], "startDate": value["startDate"],
            "endDate": value["endDate"], "dayCount": 2, "stopCount": 1, "plannedDayCount": 1,
            "unplannedDays": [2], "totalBudget": 900.0, "dailyBudgetAllocation": 450.0,
        }, "stops": [{key: stop[key] for key in ("id", "day", "activity", "notes", "sortOrder")} for stop in value["stops"]]}

    def preview_edit(self, trip_id, operation):
        return {"tripId": trip_id, "token": "signed-preview", "expiresIn": 600, "changes": [
            {"id": 4, "activity": "Park walk", "notes": "Saved plan",
             "fromDay": 1, "toDay": 2, "fromOrder": 0, "toOrder": 0}]}

    def apply_edit(self, trip_id, token):
        self.applied.append(token)
        return {"tripId": trip_id, "applied": True, "changes": self.preview_edit(trip_id, {})["changes"]}


class Model:
    def generate(self, *args):
        return {"operation": {"action": "move_stop", "sourceDay": 1, "targetDay": 2, "stopId": 4}, "clarification": ""}


@pytest.fixture
def setup():
    database, server = Database(), Server()
    client = create_app(database_client=database, multi_agent_client=server, mcp_client=Mcp(), review_model=Model(), settings={
        "MULTI_AGENT_ENABLED": True, "AI_ENABLED": True, "MCP_ENABLED": True, "RAG_ENABLED": False,
    }).test_client()
    return client, database, server


def test_disabled_is_default_and_makes_no_dependency_calls(monkeypatch):
    monkeypatch.delenv("MULTI_AGENT_ENABLED", raising=False)
    db, server = Database(), Server()
    client = create_app(database_client=db, multi_agent_client=server).test_client()
    assert client.get("/api/capabilities").json["multiAgentEnabled"] is False
    for method, path in [("get", f"{BASE}/{ID}"), ("post", f"{BASE}/{ID}/decision")]:
        assert getattr(client, method)(path).json["error"]["code"] == "mode_disabled"
    assert not db.calls and not server.calls


def test_create_builds_bounded_identity_free_evidence(setup):
    client, db, server = setup
    response = client.post(PREVIEW, json={"question": " Move the walk to day 2 "})
    assert response.status_code == 200 and response.json["preview"]["workflowId"] == ID
    payload = server.calls[0][2]
    assert payload["feature"] == "student-2" and "Assess the exact proposed edit" in payload["task"]
    assert "Excluded identity" not in json.dumps(payload)
    assert "Move the walk to day 2" in json.dumps(payload)
    assert json.loads(payload["evidence"][0]["text"])["previewHash"]
    assert "signed-preview" not in json.dumps(payload)
    assert json.loads(payload["evidence"][-1]["text"]) == response.json["preview"]["changes"][0]
    assert client.get(f"{BASE}/{ID}").json["stale"] is False
    assert all(call[0] == "GET" for call in db.calls)


@pytest.mark.parametrize("payload", [None, [], {}, {"question": "  "}, {"question": "x" * 1001},
                                          {"question": "Review", "feature": "student-3"}, {"question": 123}])
def test_invalid_start_never_calls_dependencies(setup, payload):
    client, db, server = setup
    assert client.post(PREVIEW, json=payload).status_code == 400
    assert not db.calls and not server.calls


def test_evidence_limits_and_fingerprint_cover_omitted_stops():
    value = trip()
    value["stops"] = [{**value["stops"][0], "id": i + 1, "notes": "x" * 1000, "activity": "a" * 160} for i in range(40)]
    evidence = evidence_for(value, 12)
    assert len(evidence) == 30
    assert json.loads(evidence[0]["text"])["omittedStops"] == 12
    assert all(len(e["text"]) <= 800 and len(e["title"]) <= 120 for e in evidence)
    assert "truncated" in evidence[2]["text"]
    value["stops"][-1]["notes"] = "Changed omitted stop"
    assert evidence_for(value, 12)[0] != evidence[0]


@pytest.mark.parametrize("change", [{"budget": float("nan")}, {"endDate": "2025-01-01"}, {"id": True},
                                  {"stops": [{"id": 1}]}])
def test_invalid_database_snapshot_is_explicit_502(setup, change):
    client, db, server = setup
    db.body.update(change)
    assert client.post(PREVIEW, json={"question": "Move walk"}).status_code == 502
    assert not server.calls


def test_poll_reopens_without_backend_memory_and_reports_staleness(setup):
    client, db, _ = setup
    assert client.get(f"{BASE}/{ID}").json["stale"] is False
    db.body["stops"][0]["notes"] = "Changed"
    assert client.get(f"{BASE}/{ID}").json["stale"] is True
    db.status = 404
    assert client.get(f"{BASE}/{ID}").json["stale"] is True


@pytest.mark.parametrize("feature,trip_id", [("student-3", 12), ("student-2", 99)])
def test_foreign_workflow_is_not_exposed(setup, feature, trip_id):
    client, _, server = setup
    server.record["feature"] = feature
    assert client.get(f"/api/trips/{trip_id}/multi-agent-workflows/{ID}").status_code == 404


@pytest.mark.parametrize("decision,extra,status", [
    ("approve", {}, "approved"), ("partial", {"accepted_item_ids": ["i1"]}, "partially_accepted"),
    ("reject", {"notes": "Unsupported claim"}, "rejected"),
    ("correct", {"corrected_output": ready()["work"]}, "corrected"),
])
def test_all_human_decisions_do_not_write_saved_trips(setup, decision, extra, status):
    client, db, _ = setup
    before = copy.deepcopy(db.body)
    response = client.post(f"{BASE}/{ID}/decision", json={"decision": decision, **extra})
    assert response.status_code == 200 and response.json["status"] == status
    assert db.body == before and all(call[0] == "GET" for call in db.calls)
    assert client.post(f"{BASE}/{ID}/decision", json={"decision": decision, **extra}).status_code == 409


@pytest.mark.parametrize("payload", [
    {"decision": "reject"}, {"decision": "partial", "accepted_item_ids": []},
    {"decision": "partial", "accepted_item_ids": ["i9"]},
    {"decision": "partial", "accepted_item_ids": ["i1", "i1"]},
    {"decision": "correct"}, {"decision": "approve", "accepted_item_ids": ["i1"]},
    {"decision": "approve", "decided_by": "forged"},
    {"decision": "correct", "corrected_output": {"summary": "x", "items": [
        {"id": "i1", "subject": "x", "detail": "x", "evidence_ids": ["unknown"]}]}},
])
def test_invalid_decisions_never_forward_a_write(setup, payload):
    client, _, server = setup
    assert client.post(f"{BASE}/{ID}/decision", json=payload).status_code == 400
    assert all(call[0] == "GET" for call in server.calls)


def test_changed_trip_blocks_decision(setup):
    client, db, server = setup
    db.body["budget"] = 800
    assert client.post(f"{BASE}/{ID}/decision", json={"decision": "approve"}).status_code == 409
    assert all(call[0] == "GET" for call in server.calls)


def test_database_outage_is_not_a_success(setup):
    client, db, server = setup
    def fail(*args):
        raise DependencyError("Unavailable")
    db.request = fail
    assert client.post(PREVIEW, json={"question": "Move walk"}).status_code == 503
    assert not server.calls


@pytest.mark.parametrize("decision,extra", [
    ("approve", {}), ("partial", {"accepted_item_ids": ["i1"]}),
    ("correct", {"corrected_output": ready()["work"]}),
])
def test_confirmation_requires_accepted_exact_preview(setup, decision, extra):
    client, _, server = setup
    assert client.post(PREVIEW, json={"question": "Move walk"}).status_code == 200
    body = {"token": "signed-preview", "workflowId": ID}
    assert client.post(CONFIRM, json={"token": "signed-preview"}).status_code == 400
    assert client.post(CONFIRM, json=body).json["error"]["code"] == "edit_review_required"
    assert client.post(f"{BASE}/{ID}/decision", json={"decision": decision, **extra}).status_code == 200
    assert client.post(CONFIRM, json={**body, "token": "different-preview"}).status_code == 409
    assert client.post(CONFIRM, json=body).json["applied"] is True
    assert server.record["status"] != "applied"


def test_rejected_historical_and_changed_reviews_cannot_authorise_edits(setup):
    client, db, server = setup
    body = {"token": "signed-preview", "workflowId": ID}
    assert client.post(f"{BASE}/{ID}/decision", json={"decision": "approve"}).status_code == 200
    assert client.post(CONFIRM, json=body).status_code == 409  # historical review has no preview binding
    server.record = ready()
    client.post(PREVIEW, json={"question": "Move walk"})
    client.post(f"{BASE}/{ID}/decision", json={"decision": "reject", "notes": "Do not move it"})
    assert client.post(CONFIRM, json=body).status_code == 409
    server.record = ready()
    client.post(PREVIEW, json={"question": "Move walk"})
    client.post(f"{BASE}/{ID}/decision", json={"decision": "approve"})
    db.body["interests"] = "Changed"
    assert client.post(CONFIRM, json=body).json["error"]["code"] == "stale_workflow"


def test_full_candidate_is_preserved_and_oversize_edits_fail_explicitly():
    db, server = Database(), Server()
    db.body["stops"] = [{**db.body["stops"][0], "id": i + 1} for i in range(40)]
    service = EditReview(db, server)
    preview = Mcp().preview_edit(12, {})
    preview["changes"][0]["notes"] = "x" * 1000
    question = "q" * 1000
    service.start(12, preview, question, evidence_for(db.body, 12))
    entries = server.record["evidence"]
    assert len(entries) <= 30 and all(len(entry["text"]) <= 800 for entry in entries)
    assert json.loads(entries[0]["text"])["omittedStops"] == 40 - sum(e["id"].startswith("stop-") for e in entries)
    candidate = "".join(e["text"] for e in entries if e["title"].startswith("Proposed change"))
    assert json.loads(candidate) == preview["changes"][0]
    assert "".join(e["text"] for e in entries if e["title"].startswith("Requested edit")) == question
    preview["changes"] *= 30
    server.calls.clear()
    with pytest.raises(IntegrationError, match="exceeds"):
        service.start(12, preview, question, evidence_for(db.body, 12))
    assert not server.calls


def test_changes_during_preview_cannot_start_review(setup, monkeypatch):
    client, db, server = setup
    original = Mcp.preview_edit
    def changed(self, trip_id, operation):
        db.body["budget"] = 10
        return original(self, trip_id, operation)
    monkeypatch.setattr(Mcp, "preview_edit", changed)
    assert client.post(PREVIEW, json={"question": "Move walk"}).json["error"]["code"] == "stale_preview"
    assert not server.calls


def test_clarification_does_not_start_agents(setup, monkeypatch):
    client, _, server = setup
    monkeypatch.setattr(Model, "generate", lambda *args: {"operation": None, "clarification": "Which stop?"})
    assert client.post(PREVIEW, json={"question": "Move"}).json["preview"] is None
    assert not server.calls


def test_busy_service_is_not_bypassed(setup, monkeypatch):
    client, _, server = setup
    def busy(*args, **kwargs):
        raise IntegrationError("workflow_busy")
    monkeypatch.setattr(server, "request", busy)
    assert client.post(PREVIEW, json={"question": "Move walk"}).json["error"]["code"] == "workflow_busy"


def test_uncertain_application_does_not_retry_or_claim_workflow_was_applied(setup, monkeypatch):
    client, _, server = setup
    client.post(PREVIEW, json={"question": "Move walk"})
    client.post(f"{BASE}/{ID}/decision", json={"decision": "approve"})
    calls = []
    def fail(self, trip_id, token):
        calls.append(token)
        raise IntegrationError("dependency_timeout")
    monkeypatch.setattr(Mcp, "apply_edit", fail)
    result = client.post(CONFIRM, json={"token": "signed-preview", "workflowId": ID})
    assert result.status_code == 504 and calls == ["signed-preview"]
    assert server.record["status"] == "approved"


@pytest.mark.parametrize("mutation", [
    {"id": "wf-20261020T080000Z-deadbeef"}, {"work": None}, {"status": "invented"},
    {"final_output": ready()["work"]}, {"review": {**ready()["review"], "degraded": True}},
])
def test_invalid_upstream_record_is_502(mutation):
    with pytest.raises(IntegrationError) as exc:
        validate_record({**ready(), **mutation}, ID, 12)
    assert exc.value.status == 502


@pytest.mark.parametrize("status,code,expected", [
    (503, "busy", "workflow_busy"), (503, "offline", "dependency_unavailable"),
    (404, "not_found", "workflow_not_found"), (409, "not_awaiting_review", "workflow_conflict"),
    (400, "invalid_selection", "invalid_workflow"), (302, "", "invalid_dependency_response"),
])
def test_client_maps_http_errors_without_retry(monkeypatch, status, code, expected):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={"error": {"code": code}})
    original = httpx.stream
    def stream(method, url, **kwargs):
        client = httpx.Client(transport=httpx.MockTransport(handler))
        return client.stream(method, url, **kwargs)
    monkeypatch.setattr(httpx, "stream", stream)
    with pytest.raises(IntegrationError) as exc:
        MultiAgentClient("http://native.invalid").request("POST", "/workflows", {})
    assert exc.value.code == expected and len(calls) == 1
    monkeypatch.setattr(httpx, "stream", original)


@pytest.mark.parametrize("exception,code", [
    (httpx.ReadTimeout("timeout"), "dependency_timeout"),
    (httpx.ConnectError("offline"), "dependency_unavailable"),
])
def test_client_network_failures_are_explicit(monkeypatch, exception, code):
    def fail(*args, **kwargs):
        raise exception
    monkeypatch.setattr(httpx, "stream", fail)
    with pytest.raises(IntegrationError) as exc:
        MultiAgentClient("http://native.invalid").request("GET", f"/workflows/{ID}")
    assert exc.value.code == code


@pytest.mark.parametrize("body", [{"error": "invalid"}, {"error": None}, {"error": {"code": 3}}, []])
def test_client_rejects_malformed_error_envelopes(monkeypatch, body):
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(503, json=body)))
    monkeypatch.setattr(httpx, "stream", client.stream)
    try:
        with pytest.raises(IntegrationError) as exc:
            MultiAgentClient("http://native.invalid").request("GET", f"/workflows/{ID}")
        assert exc.value.status == 502
    finally:
        client.close()
