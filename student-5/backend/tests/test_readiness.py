"""Release 2 trip readiness review: evidence, client, JSON routes and fragments.

Every Multi-Agent Server and database call is intercepted with ``responses``;
no test reaches a real server or model. Records below follow the shape the
shared server's workflow.py writes, with the evidence this backend builds.
"""

import copy
import json
import re
import time

import pytest
import requests
import responses

from advisory import AdvisoryContext
from app import create_app
from readiness import MAX_ROWS, MAX_TEXT_LENGTH, build_evidence, distinct_titles, task_for

SERVER_URL = "http://test-multi-agent:5600"
WID = "wf-20261021T101500Z-0a1b2c3d"
# The server's own EvidenceItem constraints (server.py).
EVIDENCE_ID = re.compile(r"^[A-Za-z0-9_.:#-]{1,60}$")

EVIDENCE = [
    {"id": "destination-1", "title": "Japan — entry requirement",
     "text": "Records supplied: 2 of 2 weather notes, 1 of 1 transit options. Visa requirement on record: visa-free."},
    {"id": "weather-1", "title": "Japan — weather: Spring (Mar-May)", "text": "Season: Spring (Mar-May). Mild days."},
    {"id": "transit-1", "title": "Japan — transit: rail", "text": "Transit type: rail. A Japan Rail Pass."},
]
PLAN = {"objective": "Prepare a <b>readiness</b> checklist for Japan.",
        "steps": [{"id": "s1", "description": "Check the entry requirement."}],
        "required_evidence_ids": ["destination-1", "weather-1"],
        "success_criteria": ["Every record is covered."]}
WORK = {"summary": "Three checks before departure.",
        "items": [
            {"id": "i1", "subject": "Japan — entry requirement", "detail": "Visa-free; pre-register on Visit Japan Web.",
             "evidence_ids": ["destination-1"]},
            {"id": "i2", "subject": "Japan — weather: Spring (Mar-May)", "detail": "Pack layers for cold evenings.",
             "evidence_ids": ["weather-1"]},
        ]}
REVIEW = {"verdict": "concerns", "model_verdict": "pass", "degraded": False, "automatic_findings": [],
          "model_findings": [], "recommendations": ["Confirm entry rules with Smartraveller."],
          "findings": [{"severity": "warning", "item_id": None,
                        "message": "Plan-required evidence was not used: transit-1."}]}


def record(status="awaiting_human_review", **overrides):
    body = {
        "id": WID, "feature": "student-5", "task": "Trip readiness review for Japan.",
        "submitted_by": "student-5-frontend", "status": status,
        "created_at": "2026-10-21T10:15:00Z", "updated_at": "2026-10-21T10:17:00Z",
        "evidence": copy.deepcopy(EVIDENCE), "plan": None, "work": None, "review": None,
        "human_decision": None, "final_output": None,
        "history": [{"stage": "planner", "model": "llama3.2:3b", "ok": True}], "error": None,
    }
    if status not in ("queued", "planning"):
        body["plan"] = copy.deepcopy(PLAN)
    if status not in ("queued", "planning", "working"):
        body["work"] = copy.deepcopy(WORK)
    if status not in ("queued", "planning", "working", "reviewing"):
        body["review"] = copy.deepcopy(REVIEW)
    body.update(overrides)
    return body


def decided(decision="approve", status="approved", **extra):
    return record(status, final_output=copy.deepcopy(WORK), human_decision={
        "decision": decision, "notes": "", "decided_by": "Alex", "decided_at": "2026-10-21T10:20:00Z", **extra})


@pytest.fixture
def reviews(database_url):
    app = create_app({
        "DATABASE_API_URL": database_url,
        "MULTI_AGENT_SERVER_URL": SERVER_URL, "MULTI_AGENT_ENABLED": True,
    })
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def server(method, path, status=200, **kwargs):
    if "body" not in kwargs:
        kwargs.setdefault("json", {})
    responses.add(method, SERVER_URL + path, status=status, **kwargs)


def sent(index=-1):
    return json.loads(responses.calls[index].request.body)


def server_calls():
    return [call for call in responses.calls if call.request.url.startswith(SERVER_URL)]


def context(destination=None, weather=(), transit=()):
    return AdvisoryContext(destination or {"id": 1, "country": "Japan", "visa_requirement": "visa-free",
                                           "notes": "Visit Japan Web."}, list(weather), list(transit))


def no_title_overlaps(evidence):
    """The server's checks.py substring rule, applied across every pair."""
    titles = [" ".join(item["title"].lower().split()) for item in evidence]
    return not any(i != j and (a in b) for i, a in enumerate(titles) for j, b in enumerate(titles))


# ---------------------------------------------------------------------------
# Configuration and the switched-off state (TL-NFR-10)
# ---------------------------------------------------------------------------


def test_multi_agent_fails_closed_unless_the_environment_opts_in(monkeypatch):
    monkeypatch.delenv("MULTI_AGENT_ENABLED", raising=False)
    monkeypatch.delenv("MULTI_AGENT_SERVER_URL", raising=False)
    app = create_app()
    assert app.config["MULTI_AGENT_CLIENT"].enabled is False
    assert app.config["MULTI_AGENT_CLIENT"].url == "http://host.docker.internal:5600"

    monkeypatch.setenv("MULTI_AGENT_ENABLED", "yes")
    assert create_app().config["MULTI_AGENT_CLIENT"].enabled is False

    monkeypatch.setenv("MULTI_AGENT_ENABLED", " TRUE ")
    monkeypatch.setenv("MULTI_AGENT_SERVER_URL", "http://elsewhere:1/")
    client = create_app().config["MULTI_AGENT_CLIENT"]
    assert client.enabled is True and client.url == "http://elsewhere:1"


def test_disabled_routes_return_503_quickly_without_any_network_call(client):
    disabled = {"error": "multi_agent_disabled", "message": "Multi-Agent is disabled."}
    started = time.monotonic()
    with responses.RequestsMock():  # any HTTP call at all would raise
        replies = [
            client.post("/api/destinations/1/readiness-reviews"),
            client.get("/api/readiness-reviews/{}?destination_id=1".format(WID)),
            client.get("/api/readiness-reviews/not-a-workflow?destination_id=1"),
            client.post("/api/readiness-reviews/{}/decision".format(WID),
                        json={"destination_id": 1, "decision": "approve"}),
        ]
    assert time.monotonic() - started < 1
    for reply in replies:
        assert reply.status_code == 503
        assert reply.get_json() == disabled


def test_disabled_fragments_say_so_without_any_network_call(client):
    with responses.RequestsMock():
        for reply in (
            client.post("/ui/readiness-reviews", data={"destination_id": "1"}),
            client.get("/ui/readiness-reviews/{}?destination_id=1".format(WID)),
            client.post("/ui/readiness-reviews/{}/decision".format(WID), data={"destination_id": "1"}),
        ):
            assert reply.status_code == 200
            assert "Multi-Agent is disabled" in reply.get_data(as_text=True)


# ---------------------------------------------------------------------------
# Evidence builder
# ---------------------------------------------------------------------------


def test_evidence_has_one_distinct_item_per_seeded_record(destination, weather_notes, transit_options):
    evidence = build_evidence(1, context(destination, weather_notes, transit_options))
    assert [item["id"] for item in evidence] == ["destination-1", "weather-1", "weather-2", "transit-1"]
    assert [item["title"] for item in evidence] == [
        "Japan — entry requirement",
        "Japan — weather: Spring (Mar-May)",
        "Japan — weather: Summer (Jun-Aug)",
        "Japan — transit: rail",
    ]
    assert evidence[0]["text"].startswith("Records supplied: 2 of 2 weather notes, 1 of 1 transit options.")
    assert "visa-free" in evidence[0]["text"] and "cherry blossom" in evidence[1]["text"]
    assert no_title_overlaps(evidence)


def test_evidence_names_missing_records_instead_of_omitting_them():
    evidence = build_evidence(12, context({"id": 12, "country": "Fiji", "visa_requirement": "visa-free", "notes": None}))
    assert [(item["id"], item["title"]) for item in evidence] == [
        ("destination-12", "Fiji — entry requirement"),
        ("weather-none", "Fiji — weather: none recorded"),
        ("transit-none", "Fiji — transit: none recorded"),
    ]
    assert "Entry notes: none recorded." in evidence[0]["text"]


def test_evidence_is_bounded_and_fits_the_server_contract():
    long = "x" * 2000
    weather = [{"id": i, "season": "Season {} {}".format(i, long), "notes": long} for i in range(1, 11)]
    transit = [{"id": i, "type": "bus", "details": long} for i in range(1, 9)]
    evidence = build_evidence(3, context({"id": 3, "country": "C" * 300, "visa_requirement": "eVisa", "notes": long},
                                         weather, transit))
    assert len(evidence) == 1 + 2 * MAX_ROWS <= 30
    assert evidence[0]["text"].startswith("Records supplied: 6 of 10 weather notes, 6 of 8 transit options.")
    for item in evidence:
        assert EVIDENCE_ID.match(item["id"])
        assert 1 <= len(item["title"]) <= 120
        assert 1 <= len(item["text"]) <= MAX_TEXT_LENGTH <= 800
    assert len({item["id"] for item in evidence}) == len(evidence)
    assert no_title_overlaps(evidence)
    assert len(task_for({"country": "C" * 300})) <= 500


def test_repeated_or_overlapping_labels_get_a_closed_suffix():
    weather = [{"id": 4, "season": "Spring", "notes": "a"}, {"id": 5, "season": "Spring (Mar-May)", "notes": "b"}]
    transit = [{"id": 7, "type": "metro", "details": "a"}, {"id": 9, "type": "metro", "details": "b"}]
    titles = [item["title"] for item in build_evidence(1, context(weather=weather, transit=transit))]
    assert titles == [
        "Japan — entry requirement",
        "Japan — weather: Spring [weather-4]",
        "Japan — weather: Spring (Mar-May) [weather-5]",
        "Japan — transit: metro [transit-7]",
        "Japan — transit: metro [transit-9]",
    ]
    assert no_title_overlaps([{"title": t} for t in titles])
    # Already-distinct titles are left exactly as they were.
    assert distinct_titles(EVIDENCE) == EVIDENCE


def test_rows_are_sorted_and_a_non_list_child_reply_is_a_database_failure(database_url, reviews):
    evidence = build_evidence(1, context(weather=[{"id": 9, "season": "B", "notes": "b"},
                                                  {"id": 2, "season": "A", "notes": "a"}]))
    assert [item["id"] for item in evidence[1:3]] == ["weather-2", "weather-9"]

    with responses.RequestsMock() as mock:
        mock.add(responses.GET, database_url + "/api/destinations/1", json={"id": 1, "country": "Japan"})
        mock.add(responses.GET, database_url + "/api/weather-notes", json={"error": "boom"}, status=500)
        mock.add(responses.GET, database_url + "/api/transit-options", json=[])
        reply = reviews.post("/api/destinations/1/readiness-reviews")
    assert reply.status_code == 503
    assert reply.get_json() == {"error": "database service unavailable"}


# ---------------------------------------------------------------------------
# JSON routes: create
# ---------------------------------------------------------------------------


@responses.activate
def test_create_sends_student5_evidence_and_returns_202(reviews, mock_destination):
    mock_destination()
    server(responses.POST, "/workflows", 202, json={"id": WID, "status": "queued"})
    reply = reviews.post("/api/destinations/1/readiness-reviews")
    assert reply.status_code == 202
    assert reply.get_json() == {"id": WID, "status": "queued", "destination_id": 1}
    body = sent()
    assert set(body) == {"feature", "task", "evidence", "submitted_by"}
    assert body["feature"] == "student-5" and body["submitted_by"] == "student-5-api"
    assert body["task"].startswith("Trip readiness review for Japan.")
    assert body["evidence"][0]["id"] == "destination-1"
    assert {item["id"] for item in body["evidence"]} == {"destination-1", "weather-1", "weather-2", "transit-1"}


@responses.activate
def test_unknown_destination_forwards_the_database_404_without_calling_the_server(reviews, mock_destination):
    mock_destination(row_id=99, status=404, payload={"error": "No destinations row with id 99"})
    reply = reviews.post("/api/destinations/99/readiness-reviews")
    assert reply.status_code == 404
    assert reply.get_json() == {"error": "No destinations row with id 99"}
    assert server_calls() == []


@pytest.mark.parametrize("kwargs,status,code", [
    ({"status": 503, "json": {"error": {"code": "busy", "message": "A workflow is already running."}}},
     503, "multi_agent_busy"),
    ({"status": 500, "body": "<html>"}, 502, "multi_agent_unavailable"),
    # Our own evidence was refused, so it is a dependency fault, not the caller's 400.
    ({"status": 400, "json": {"error": {"code": "validation_error", "message": "Invalid request: evidence.1"}}},
     502, "multi_agent_unavailable"),
    ({"status": 202, "json": {"id": "../etc", "status": "queued"}}, 502, "multi_agent_unavailable"),
    ({"status": 202, "body": "not json"}, 502, "multi_agent_unavailable"),
    ({"body": requests.ConnectionError("refused at 10.0.0.1")}, 502, "multi_agent_unavailable"),
    ({"body": requests.Timeout("slow")}, 502, "multi_agent_unavailable"),
])
@responses.activate
def test_create_failures_map_to_honest_statuses(reviews, mock_destination, kwargs, status, code):
    mock_destination()
    reply_status = kwargs.pop("status", 202)
    server(responses.POST, "/workflows", reply_status, **kwargs)
    reply = reviews.post("/api/destinations/1/readiness-reviews")
    assert reply.status_code == status
    assert reply.get_json()["error"] == code
    assert "10.0.0.1" not in reply.get_data(as_text=True)


# ---------------------------------------------------------------------------
# JSON routes: poll
# ---------------------------------------------------------------------------


@responses.activate
def test_poll_returns_the_validated_record(reviews):
    server(responses.GET, "/workflows/" + WID, json=record())
    reply = reviews.get("/api/readiness-reviews/{}?destination_id=1".format(WID))
    assert reply.status_code == 200
    assert reply.get_json() == record()


@pytest.mark.parametrize("body", [
    record(feature="student-3"),
    record(evidence=[{**EVIDENCE[0], "id": "destination-2"}] + EVIDENCE[1:]),
    record(evidence=EVIDENCE[1:] + EVIDENCE[:1]),  # the binding item must come first
])
@responses.activate
def test_another_features_or_destinations_review_is_not_found(reviews, body):
    server(responses.GET, "/workflows/" + WID, json=body)
    reply = reviews.get("/api/readiness-reviews/{}?destination_id=1".format(WID))
    assert reply.status_code == 404
    assert reply.get_json()["error"] == "review_not_found"


@pytest.mark.parametrize("body", [
    record(id="wf-20261021T101500Z-ffffffff"),
    record(status="finished"),
    record(evidence=[]),
    record(work={"summary": "s", "items": "not a list"}),
    record(review=None),
    record("approved", final_output=copy.deepcopy(WORK)),  # decided, but no human_decision
    ["not", "a", "record"],
])
@responses.activate
def test_records_that_break_the_contract_are_rejected(reviews, body):
    server(responses.GET, "/workflows/" + WID, json=body)
    reply = reviews.get("/api/readiness-reviews/{}?destination_id=1".format(WID))
    assert reply.status_code == 502
    assert reply.get_json()["error"] == "multi_agent_unavailable"


@responses.activate
def test_poll_validates_its_inputs_before_calling_the_server(reviews):
    assert reviews.get("/api/readiness-reviews/{}".format(WID)).status_code == 400
    assert reviews.get("/api/readiness-reviews/{}?destination_id=x".format(WID)).status_code == 400
    for bad_id in ("wf-not-a-real-id", "WF-20261021T101500Z-0A1B2C3D", WID + "x"):
        reply = reviews.get("/api/readiness-reviews/{}?destination_id=1".format(bad_id))
        assert reply.status_code == 404 and reply.get_json()["error"] == "review_not_found"
    # An encoded slash is decoded before routing, so no route matches at all.
    assert reviews.get("/api/readiness-reviews/wf-..%2F..%2Faudit?destination_id=1").status_code == 404
    assert len(responses.calls) == 0


@responses.activate
def test_a_review_the_server_does_not_know_is_not_found(reviews):
    server(responses.GET, "/workflows/" + WID, 404, json={"error": {"code": "not_found", "message": "m"}})
    reply = reviews.get("/api/readiness-reviews/{}?destination_id=1".format(WID))
    assert reply.status_code == 404 and reply.get_json()["error"] == "review_not_found"


# ---------------------------------------------------------------------------
# JSON routes: decision (TL-FR-17)
# ---------------------------------------------------------------------------


def post_decision(client, **body):
    return client.post("/api/readiness-reviews/{}/decision".format(WID), json={"destination_id": 1, **body})


@responses.activate
def test_decision_forwards_only_decision_fields_and_returns_the_record(reviews):
    server(responses.GET, "/workflows/" + WID, json=record())
    server(responses.POST, "/workflows/{}/decision".format(WID), json=decided())
    reply = post_decision(reviews, decision="approve", notes="Looks right", decided_by="Alex", extra="dropped")
    assert reply.status_code == 200
    assert reply.get_json()["status"] == "approved"
    assert sent() == {"decision": "approve", "notes": "Looks right", "decided_by": "Alex"}


@responses.activate
def test_second_decision_is_409(reviews):
    server(responses.GET, "/workflows/" + WID, json=decided())
    server(responses.POST, "/workflows/{}/decision".format(WID), 409,
           json={"error": {"code": "not_awaiting_review", "message": "Workflow is approved, not awaiting human review."}})
    reply = post_decision(reviews, decision="approve")
    assert reply.status_code == 409
    assert reply.get_json() == {"error": "review_not_awaiting_decision",
                                "message": "Workflow is approved, not awaiting human review."}


@pytest.mark.parametrize("code,message", [
    ("notes_required", "A rejection must include notes explaining why."),
    ("invalid_selection", "Partial acceptance needs a non-empty list of existing item ids."),
    ("invalid_correction", "corrected_output cites evidence that was not supplied."),
])
@responses.activate
def test_server_decision_rules_are_relayed(reviews, code, message):
    server(responses.GET, "/workflows/" + WID, json=record())
    server(responses.POST, "/workflows/{}/decision".format(WID), 400, json={"error": {"code": code, "message": message}})
    reply = post_decision(reviews, decision="reject")
    assert reply.status_code == 400
    assert reply.get_json() == {"error": code, "message": message}


@pytest.mark.parametrize("body", [
    {"decision": "approve", "destination_id": None},
    {"decision": "maybe"},
    {"destination_id": 1},
])
@responses.activate
def test_malformed_decisions_are_rejected_before_the_server(reviews, body):
    reply = reviews.post("/api/readiness-reviews/{}/decision".format(WID), json={"destination_id": 1, **body})
    assert reply.status_code == 400 and reply.get_json()["error"] == "invalid_request"
    assert reviews.post("/api/readiness-reviews/{}/decision".format(WID), data="x").status_code == 400
    assert len(responses.calls) == 0


@responses.activate
def test_decision_on_another_destinations_review_is_never_posted(reviews):
    server(responses.GET, "/workflows/" + WID, json=record())
    reply = reviews.post("/api/readiness-reviews/{}/decision".format(WID),
                         json={"destination_id": 2, "decision": "approve"})
    assert reply.status_code == 404
    assert [call.request.method for call in responses.calls] == ["GET"]


# ---------------------------------------------------------------------------
# HTMX fragments (TL-FR-16/17 in the UI)
# ---------------------------------------------------------------------------


def poll_fragment(client, seen=None):
    url = "/ui/readiness-reviews/{}?destination_id=1".format(WID)
    return client.get(url + ("&seen=" + seen if seen else ""))


@responses.activate
def test_start_fragment_returns_a_self_polling_status_block(reviews, mock_destination):
    mock_destination()
    server(responses.POST, "/workflows", 202, json={"id": WID, "status": "queued"})
    reply = reviews.post("/ui/readiness-reviews", data={"destination_id": "1"})
    html = reply.get_data(as_text=True)
    assert reply.status_code == 200
    assert 'hx-trigger="every 2s"' in html and 'hx-swap="outerHTML"' in html and 'hx-target="this"' in html
    assert "/ui/readiness-reviews/{}?destination_id=1&amp;seen=queued".format(WID) in html
    assert sent()["submitted_by"] == "student-5-frontend"
    assert 'style="' not in html


@responses.activate
def test_unchanged_status_is_a_bodiless_204_and_a_new_stage_replaces_the_block(reviews):
    server(responses.GET, "/workflows/" + WID, json=record("working"))
    unchanged = poll_fragment(reviews, seen="working")
    assert unchanged.status_code == 204 and unchanged.get_data() == b""

    changed = poll_fragment(reviews, seen="planning")
    html = changed.get_data(as_text=True)
    assert changed.status_code == 200
    assert "Worker is writing the checklist" in html and "seen=working" in html


@responses.activate
def test_a_missed_poll_keeps_polling_and_the_next_good_poll_clears_the_warning(reviews):
    server(responses.GET, "/workflows/" + WID, body=requests.ConnectionError("refused"))
    html = poll_fragment(reviews, seen="working").get_data(as_text=True)
    assert 'hx-trigger="every 2s"' in html and "did not answer the last check" in html
    assert "Worker is writing the checklist" in html and "seen=retry" in html

    responses.replace(responses.GET, SERVER_URL + "/workflows/" + WID, json=record("working"))
    html = poll_fragment(reviews, seen="retry").get_data(as_text=True)
    assert "did not answer" not in html and "seen=working" in html


@responses.activate
def test_finished_review_shows_every_stage_and_the_decision_form_and_stops_polling(reviews):
    server(responses.GET, "/workflows/" + WID, json=record())
    html = poll_fragment(reviews, seen="reviewing").get_data(as_text=True)
    assert "hx-trigger" not in html
    # Pipeline order: plan, checklist, review, then the decision.
    order = [html.index(text + " &middot;") for text in ("Planner", "Worker", "Reviewer", "Human review")]
    assert order == sorted(order)
    assert "&lt;b&gt;readiness&lt;/b&gt;" in html and "<b>" not in html
    assert "Pack layers for cold evenings." in html
    assert "Based on: <span class=\"readiness-cite\">Japan — weather: Spring (Mar-May)</span>" in html
    assert "Plan-required evidence was not used: transit-1." in html and "verdict-concerns" in html
    assert 'hx-post="/ui/readiness-reviews/{}/decision"'.format(WID) in html
    for value in ("approve", "correct", "partial", "reject"):
        assert 'value="{}"'.format(value) in html
    assert 'name="decided_by"' in html and 'name="detail-i1"' in html
    assert html.count('name="accepted_item_ids"') == 2 and html.count(" checked") == 2
    assert "id=" not in html.replace("item_ids", "")


@pytest.mark.parametrize("body,expected,absent", [
    (decided("partial", "partially_accepted", accepted_item_ids=["i1"]), "Partially accepted by Alex", "<form"),
    (decided("reject", "rejected", notes="Wrong season"), "Wrong season", "<form"),
    (record("failed", error={"code": "invalid_agent_output", "stage": "working",
                             "message": "worker output failed validation after 2 attempts."}),
     "The review stopped at the working stage", "<form"),
])
@responses.activate
def test_decided_and_failed_reviews_render_without_a_form(reviews, body, expected, absent):
    server(responses.GET, "/workflows/" + WID, json=body)
    html = poll_fragment(reviews).get_data(as_text=True)
    assert expected in html and absent not in html and "hx-trigger" not in html


def decide_fragment(client, **form):
    return client.post("/ui/readiness-reviews/{}/decision".format(WID),
                       data={"destination_id": "1", "decided_by": "Alex", **form})


@responses.activate
def test_approve_fragment_records_the_decision(reviews):
    server(responses.GET, "/workflows/" + WID, json=record())
    server(responses.POST, "/workflows/{}/decision".format(WID), json=decided())
    html = decide_fragment(reviews, decision="approve", notes="  Fine  ").get_data(as_text=True)
    assert sent() == {"decision": "approve", "notes": "Fine", "decided_by": "Alex"}
    assert "Approved by Alex" in html and "No travel record was changed." in html and "<form" not in html


@responses.activate
def test_partial_and_correct_fragments_build_the_server_payload(reviews):
    server(responses.GET, "/workflows/" + WID, json=record())
    server(responses.POST, "/workflows/{}/decision".format(WID), json=decided("partial", "partially_accepted"))
    decide_fragment(reviews, decision="partial", accepted_item_ids=["i2"])
    assert sent()["accepted_item_ids"] == ["i2"]

    decide_fragment(reviews, decision="correct", summary="", **{"detail-i2": "Pack a warm jacket.\r\nAnd gloves."})
    corrected = sent()["corrected_output"]
    assert corrected["summary"] == WORK["summary"]
    assert [item["detail"] for item in corrected["items"]] == [WORK["items"][0]["detail"], "Pack a warm jacket.\nAnd gloves."]
    assert [item["evidence_ids"] for item in corrected["items"]] == [["destination-1"], ["weather-1"]]


@responses.activate
def test_refused_decision_is_shown_above_the_form_with_the_typed_values_kept(reviews):
    server(responses.GET, "/workflows/" + WID, json=record())
    server(responses.POST, "/workflows/{}/decision".format(WID), 400,
           json={"error": {"code": "notes_required", "message": "A rejection must include notes explaining why."}})
    html = decide_fragment(reviews, decision="reject", notes="", decided_by="Sam <i>").get_data(as_text=True)
    assert "A rejection must include notes explaining why." in html and "<form" in html
    assert 'value="Sam &lt;i&gt;"' in html
    assert 'value="reject" required checked' in html


@pytest.mark.parametrize("form,message", [
    ({"decision": "approve", "decided_by": " "}, "Enter your name in Decided by."),
    ({"decision": "sure"}, "Choose approve, correct, partial or reject."),
    ({"decision": "correct", "detail-i1": "  "}, "Every corrected item needs text."),
])
@responses.activate
def test_incomplete_decision_forms_are_answered_without_posting(reviews, form, message):
    server(responses.GET, "/workflows/" + WID, json=record())
    html = decide_fragment(reviews, **form).get_data(as_text=True)
    assert message in html and "<form" in html
    assert [call.request.method for call in responses.calls] == ["GET"]


@pytest.mark.parametrize("setup,message", [
    ("busy", "Another review is already running"),
    ("down", "Multi-Agent Server is unavailable"),
    ("missing", "Choose a destination before starting"),
])
@responses.activate
def test_start_fragment_renders_failures_as_content(reviews, mock_destination, setup, message):
    mock_destination()
    if setup == "busy":
        server(responses.POST, "/workflows", 503, json={"error": {"code": "busy", "message": "m"}})
    elif setup == "down":
        server(responses.POST, "/workflows", body=requests.ConnectionError("refused"))
    data = {"destination_id": "" if setup == "missing" else "1"}
    reply = reviews.post("/ui/readiness-reviews", data=data)
    assert reply.status_code == 200
    assert 'class="fragment-message"' in reply.get_data(as_text=True)
    assert message in reply.get_data(as_text=True)


@responses.activate
def test_already_decided_fragment_explains_instead_of_erroring(reviews):
    server(responses.GET, "/workflows/" + WID, json=record())
    server(responses.POST, "/workflows/{}/decision".format(WID), 409,
           json={"error": {"code": "not_awaiting_review", "message": "m"}})
    reply = decide_fragment(reviews, decision="approve")
    assert reply.status_code == 200
    assert "not awaiting a decision any more" in reply.get_data(as_text=True)
