"""Release 2: Student 3's integration with the shared Multi-Agent Server.

Covers the evidence builder, multi_agent_client and the /api/agents/* routes.
The Multi-Agent Server and the database service are mocked, so no model or
network is needed (same convention as test_backend_mcp_rag.py).
"""

import pytest
import requests

import agent_evidence
import database_client
import multi_agent_client as client

WORKFLOW_ID = "wf-20261019T011611Z-0ccf5c1c"

ATTRACTIONS = [
    {"id": 1, "name": "Opera House", "category": "sight", "description": "Harbour icon.", "rating": 4.8},
    {"id": 2, "name": "Corner Cafe", "category": "restaurant", "description": None, "rating": 4.1},
    {"id": 3, "name": "Harbour Kayak", "category": "activity", "description": "Paddle tour.", "rating": None},
]
REVIEWS = [
    {"id": 1, "attraction_id": 1, "rating": 5, "comment": "Stunning at sunset."},
    {"id": 2, "attraction_id": 1, "rating": 4, "comment": "Crowded."},
    {"id": 3, "attraction_id": 1, "rating": 4, "comment": "Third comment is left out."},
    {"id": 4, "attraction_id": 2, "rating": 3, "comment": "   "},
]


class FakeResponse:
    def __init__(self, status=200, body=None, text_body=False):
        self.status_code = status
        self._body = body
        self._text_body = text_body

    def json(self):
        if self._text_body:
            raise ValueError("not json")
        return self._body


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setenv("MULTI_AGENT_ENABLED", "true")


# -- evidence builder -----------------------------------------------------------------------

def test_evidence_uses_exact_names_as_titles_and_stable_ids():
    evidence = agent_evidence.build_evidence(ATTRACTIONS, REVIEWS)

    assert [(e["id"], e["title"]) for e in evidence] == [
        ("attraction-1", "Opera House"), ("attraction-2", "Corner Cafe"), ("attraction-3", "Harbour Kayak")]


def test_evidence_is_ordered_best_rated_first_with_unrated_last_and_ties_by_id():
    # Ids deliberately do NOT follow rating order, so sorting by id alone would fail this.
    rows = [
        {"id": 1, "name": "Low", "category": "sight", "description": None, "rating": 3.0},
        {"id": 2, "name": "Top", "category": "sight", "description": None, "rating": 5.0},
        {"id": 3, "name": "Unrated", "category": "sight", "description": None, "rating": None},
        {"id": 4, "name": "Tied", "category": "sight", "description": None, "rating": 3.0},
    ]

    assert [e["id"] for e in agent_evidence.build_evidence(rows, [])] == [
        "attraction-2", "attraction-1", "attraction-4", "attraction-3"]


def test_evidence_text_has_category_description_rating_and_two_review_comments():
    text = agent_evidence.build_evidence(ATTRACTIONS, REVIEWS)[0]["text"]

    assert "Opera House is a sight." in text and "Harbour icon." in text and "Rating: 4.8." in text
    assert "Stunning at sunset." in text and "Crowded." in text
    assert "Third comment" not in text


def test_evidence_text_handles_missing_description_rating_and_blank_comments():
    cafe, kayak = agent_evidence.build_evidence(ATTRACTIONS, REVIEWS)[1:]

    assert cafe["text"] == "Corner Cafe is a restaurant. Rating: 4.1."  # blank comment ignored
    assert "Rating: not rated." in kayak["text"]


def test_evidence_respects_server_limits():
    many = [{"id": i, "name": "N" * 300, "category": "sight", "description": "d" * 2000, "rating": 3}
            for i in range(1, 45)]
    evidence = agent_evidence.build_evidence(many, [])

    assert len(evidence) == agent_evidence.MAX_EVIDENCE == 30
    assert all(len(e["title"]) <= 120 and len(e["text"]) <= 800 for e in evidence)


def test_evidence_skips_attractions_without_a_usable_name():
    rows = [{"id": 1, "name": "  ", "category": "sight", "description": None, "rating": 5}, ATTRACTIONS[0]]

    assert [e["id"] for e in agent_evidence.build_evidence(rows, [])] == ["attraction-1"]


# -- client -----------------------------------------------------------------------------------

def test_client_is_disabled_by_default_and_makes_no_request(monkeypatch):
    monkeypatch.delenv("MULTI_AGENT_ENABLED", raising=False)
    monkeypatch.setattr(requests, "request", lambda *a, **k: pytest.fail("network call while disabled"))

    for call in (client.health, lambda: client.start_workflow("task", []),
                 lambda: client.get_workflow(WORKFLOW_ID), lambda: client.decide(WORKFLOW_ID, {})):
        with pytest.raises(client.MultiAgentDisabledError):
            call()


@pytest.mark.parametrize("value", ["false", "", "1", "yes"])
def test_only_the_literal_true_enables_the_client(monkeypatch, value):
    monkeypatch.setenv("MULTI_AGENT_ENABLED", value)
    assert client.enabled() is False


def test_start_workflow_posts_feature_task_and_evidence(enabled, monkeypatch):
    sent = {}

    def fake_request(method, url, timeout=None, **kwargs):
        sent.update(method=method, url=url, timeout=timeout, json=kwargs["json"])
        return FakeResponse(202, {"id": WORKFLOW_ID, "status": "queued"})

    monkeypatch.setattr(requests, "request", fake_request)
    result = client.start_workflow("Plan a day", [{"id": "a", "title": "A", "text": "t"}])

    assert result == {"id": WORKFLOW_ID, "status": "queued"}
    assert sent["method"] == "POST" and sent["url"].endswith("/workflows")
    assert sent["json"] == {"feature": "student-3", "task": "Plan a day", "submitted_by": "student-3-ui",
                            "evidence": [{"id": "a", "title": "A", "text": "t"}]}
    assert sent["timeout"] == client.REQUEST_TIMEOUT


def test_server_error_keeps_its_code_and_status(enabled, monkeypatch):
    body = {"error": {"code": "not_awaiting_review", "message": "Already decided.", "fields": {}}}
    monkeypatch.setattr(requests, "request", lambda *a, **k: FakeResponse(409, body))

    with pytest.raises(client.MultiAgentResponseError) as caught:
        client.decide(WORKFLOW_ID, {"decision": "approve"})
    assert (caught.value.code, caught.value.status, str(caught.value)) == (
        "not_awaiting_review", 409, "Already decided.")


def test_error_without_json_body_is_a_generic_response_error(enabled, monkeypatch):
    monkeypatch.setattr(requests, "request", lambda *a, **k: FakeResponse(500, text_body=True))

    with pytest.raises(client.MultiAgentResponseError) as caught:
        client.get_workflow(WORKFLOW_ID)
    assert caught.value.status == 500 and caught.value.code == "unknown"


def test_connection_failure_is_unavailable(enabled, monkeypatch):
    def refuse(*args, **kwargs):
        raise requests.exceptions.ConnectionError("refused")

    monkeypatch.setattr(requests, "request", refuse)

    with pytest.raises(client.MultiAgentUnavailableError):
        client.health()


@pytest.mark.parametrize("body", [["not", "a", "dict"], None])
def test_unexpected_success_shape_is_rejected(enabled, monkeypatch, body):
    monkeypatch.setattr(requests, "request", lambda *a, **k: FakeResponse(200, body))

    with pytest.raises(client.MultiAgentResponseError):
        client.get_workflow(WORKFLOW_ID)


def test_start_workflow_rejects_a_reply_without_id_and_status(enabled, monkeypatch):
    monkeypatch.setattr(requests, "request", lambda *a, **k: FakeResponse(202, {"ok": True}))

    with pytest.raises(client.MultiAgentResponseError):
        client.start_workflow("task", [])


# -- routes: disabled by default ----------------------------------------------------------------

def _no_database(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("database touched while Multi-Agent is disabled")

    monkeypatch.setattr(database_client, "list_attractions", forbidden)
    monkeypatch.setattr(database_client, "list_reviews", forbidden)


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("get", "/api/agents/status", None),
        ("post", "/api/agents/workflows", {"task": "Plan a day"}),
        ("get", f"/api/agents/workflows/{WORKFLOW_ID}", None),
        ("post", f"/api/agents/workflows/{WORKFLOW_ID}/decision", {"decision": "approve"}),
    ],
)
def test_every_agent_route_returns_503_disabled_by_default(backend_client, monkeypatch, method, path, body):
    monkeypatch.delenv("MULTI_AGENT_ENABLED", raising=False)
    _no_database(monkeypatch)
    monkeypatch.setattr(requests, "request", lambda *a, **k: pytest.fail("network call while disabled"))

    response = getattr(backend_client, method)(path, json=body) if body else getattr(backend_client, method)(path)

    assert response.status_code == 503
    assert response.get_json() == {"error": "multi_agent_disabled", "message": "Multi-Agent is disabled."}


# -- routes: start --------------------------------------------------------------------------------

@pytest.fixture
def stubbed_db(monkeypatch):
    seen = {}

    def list_attractions(category=None):
        seen["category"] = category
        return [a for a in ATTRACTIONS if category in (None, a["category"])]

    monkeypatch.setattr(database_client, "list_attractions", list_attractions)
    monkeypatch.setattr(database_client, "list_reviews", lambda attraction_id=None: REVIEWS)
    return seen


def test_start_builds_evidence_from_the_catalogue_and_returns_202(backend_client, enabled, stubbed_db, monkeypatch):
    sent = {}

    def start(task, evidence):
        sent.update(task=task, evidence=evidence)
        return {"id": WORKFLOW_ID, "status": "queued"}

    monkeypatch.setattr(client, "start_workflow", start)
    response = backend_client.post("/api/agents/workflows", json={"task": "  Plan a food day  "})

    assert response.status_code == 202
    assert response.get_json() == {"id": WORKFLOW_ID, "status": "queued", "evidence_count": 3}
    assert sent["task"] == "Plan a food day"
    assert [e["title"] for e in sent["evidence"]] == ["Opera House", "Corner Cafe", "Harbour Kayak"]


def test_start_passes_the_category_filter_to_the_database(backend_client, enabled, stubbed_db, monkeypatch):
    sent = {}
    monkeypatch.setattr(client, "start_workflow",
                        lambda task, evidence: sent.update(evidence=evidence) or {"id": WORKFLOW_ID, "status": "queued"})

    response = backend_client.post("/api/agents/workflows", json={"task": "Plan a food day", "category": "restaurant"})

    assert response.status_code == 202 and stubbed_db["category"] == "restaurant"
    assert [e["title"] for e in sent["evidence"]] == ["Corner Cafe"]


@pytest.mark.parametrize(
    "payload",
    [{}, {"task": "  "}, {"task": "ab"}, {"task": "x" * 501}, {"task": "Plan a day", "category": "nightclub"}],
    ids=["no-task", "blank-task", "too-short", "too-long", "bad-category"],
)
def test_start_rejects_invalid_requests_with_400(backend_client, enabled, stubbed_db, payload):
    response = backend_client.post("/api/agents/workflows", json=payload)

    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"


def test_start_with_an_empty_catalogue_is_400_no_evidence(backend_client, enabled, monkeypatch):
    monkeypatch.setattr(database_client, "list_attractions", lambda category=None: [])
    monkeypatch.setattr(database_client, "list_reviews", lambda attraction_id=None: [])
    monkeypatch.setattr(client, "start_workflow", lambda *a: pytest.fail("started with no evidence"))

    response = backend_client.post("/api/agents/workflows", json={"task": "Plan a day"})

    assert response.status_code == 400 and response.get_json()["error"] == "no_evidence"


def test_start_returns_502_when_the_database_is_down(backend_client, enabled, monkeypatch):
    def down(category=None):
        raise database_client.DatabaseUnavailableError("refused")

    monkeypatch.setattr(database_client, "list_attractions", down)

    response = backend_client.post("/api/agents/workflows", json={"task": "Plan a day"})

    assert response.status_code == 502 and response.get_json()["error"] == "database_unavailable"


def test_start_when_the_server_is_busy_passes_503_busy_through(backend_client, enabled, stubbed_db, monkeypatch):
    def busy(task, evidence):
        raise client.MultiAgentResponseError("A workflow is already running.", code="busy", status=503)

    monkeypatch.setattr(client, "start_workflow", busy)
    response = backend_client.post("/api/agents/workflows", json={"task": "Plan a day"})

    assert response.status_code == 503
    assert response.get_json() == {"error": "busy", "message": "A workflow is already running."}


def test_start_when_the_server_is_unreachable_is_502(backend_client, enabled, stubbed_db, monkeypatch):
    def down(task, evidence):
        raise client.MultiAgentUnavailableError("refused")

    monkeypatch.setattr(client, "start_workflow", down)
    response = backend_client.post("/api/agents/workflows", json={"task": "Plan a day"})

    assert response.status_code == 502 and response.get_json()["error"] == "multi_agent_unavailable"


# -- routes: status / poll / decide -----------------------------------------------------------------

def test_status_reports_ok_and_busy(backend_client, enabled, monkeypatch):
    monkeypatch.setattr(client, "health", lambda: {"status": "ok", "busy": True})

    response = backend_client.get("/api/agents/status")

    assert response.status_code == 200 and response.get_json() == {"status": "ok", "busy": True}


def test_poll_returns_the_servers_workflow_record(backend_client, enabled, monkeypatch):
    record = {"id": WORKFLOW_ID, "status": "awaiting_human_review", "plan": {"objective": "o"}}
    monkeypatch.setattr(client, "get_workflow", lambda workflow_id: record if workflow_id == WORKFLOW_ID else None)

    response = backend_client.get(f"/api/agents/workflows/{WORKFLOW_ID}")

    assert response.status_code == 200 and response.get_json() == record


@pytest.mark.parametrize("bad_id", ["not-an-id", "wf-1", "..%2F..%2Fadmin", "wf-20261019T011611Z-ZZZZZZZZ"])
def test_malformed_workflow_ids_are_404_and_never_reach_the_server(backend_client, enabled, monkeypatch, bad_id):
    monkeypatch.setattr(requests, "request", lambda *a, **k: pytest.fail("malformed id was forwarded"))

    assert backend_client.get(f"/api/agents/workflows/{bad_id}").status_code == 404
    assert backend_client.post(f"/api/agents/workflows/{bad_id}/decision", json={"decision": "approve"}).status_code == 404


def test_unknown_workflow_on_the_server_is_404(backend_client, enabled, monkeypatch):
    def missing(workflow_id):
        raise client.MultiAgentResponseError("Workflow not found.", code="not_found", status=404)

    monkeypatch.setattr(client, "get_workflow", missing)

    assert backend_client.get(f"/api/agents/workflows/{WORKFLOW_ID}").status_code == 404


def test_decision_relays_only_known_fields_and_fixes_the_reviewer_identity(backend_client, enabled, monkeypatch):
    sent = {}
    monkeypatch.setattr(client, "decide", lambda wid, body: sent.update(id=wid, body=body) or {"status": "partially_accepted"})

    response = backend_client.post(f"/api/agents/workflows/{WORKFLOW_ID}/decision", json={
        "decision": "partial", "notes": "Keep one", "accepted_item_ids": ["i1"],
        "decided_by": "someone-else", "status": "approved", "final_output": {"hacked": True}})

    assert response.status_code == 200
    assert sent["id"] == WORKFLOW_ID
    assert sent["body"] == {"decision": "partial", "notes": "Keep one", "accepted_item_ids": ["i1"],
                            "decided_by": "student-3-ui"}


@pytest.mark.parametrize("payload", [{}, {"decision": "maybe"}, {"decision": None}, {"notes": "no decision"}])
def test_decision_without_a_valid_decision_is_400(backend_client, enabled, monkeypatch, payload):
    monkeypatch.setattr(client, "decide", lambda *a: pytest.fail("invalid decision was forwarded"))

    response = backend_client.post(f"/api/agents/workflows/{WORKFLOW_ID}/decision", json=payload)

    assert response.status_code == 400 and response.get_json()["error"] == "validation_error"


@pytest.mark.parametrize(
    ("server_status", "server_code", "expected_status"),
    [(409, "not_awaiting_review", 409), (400, "notes_required", 400), (500, "unknown", 502), (418, "unknown", 502)],
)
def test_server_decision_errors_keep_actionable_statuses_and_hide_the_rest(
        backend_client, enabled, monkeypatch, server_status, server_code, expected_status):
    def refuse(wid, body):
        raise client.MultiAgentResponseError("nope", code=server_code, status=server_status)

    monkeypatch.setattr(client, "decide", refuse)
    response = backend_client.post(f"/api/agents/workflows/{WORKFLOW_ID}/decision", json={"decision": "approve"})

    assert response.status_code == expected_status and response.get_json()["error"] == server_code
