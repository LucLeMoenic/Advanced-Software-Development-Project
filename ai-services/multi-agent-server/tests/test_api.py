import time

import pytest
from fastapi.testclient import TestClient

import server


@pytest.fixture
def client(data_dir, fake_llm):
    server._active["id"] = None
    with TestClient(server.app) as test_client:
        yield test_client
    server._active["id"] = None


def _body(evidence, **overrides):
    return {"feature": "student-3", "task": "Plan a food day", "evidence": evidence, **overrides}


def _wait(client, workflow_id, wanted=("awaiting_human_review", "failed"), timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        record = client.get(f"/workflows/{workflow_id}").json()
        if record["status"] in wanted:
            return record
        time.sleep(0.02)
    raise AssertionError(f"timed out; last status {record['status']}")


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "busy": False}


def test_full_http_lifecycle_create_poll_decide_audit(client, evidence):
    created = client.post("/workflows", json=_body(evidence))
    assert created.status_code == 202
    workflow_id = created.json()["id"]

    record = _wait(client, workflow_id)
    assert record["status"] == "awaiting_human_review"
    assert [h["stage"] for h in record["history"]] == ["planner", "worker", "reviewer"]

    decided = client.post(f"/workflows/{workflow_id}/decision",
                          json={"decision": "approve", "notes": "ok", "decided_by": "khushi"})
    assert decided.status_code == 200 and decided.json()["status"] == "approved"

    assert client.get("/workflows").json()[0]["id"] == workflow_id
    events = [e["event"] for e in client.get("/audit", params={"workflow_id": workflow_id}).json()]
    assert events[0] == "workflow_created" and events[-1] == "decision_approve"
    assert client.get("/audit/verify").json()["valid"] is True


def test_second_workflow_while_one_is_running_gets_503(client, fake_llm, evidence):
    fake_llm.delay = 0.3
    first = client.post("/workflows", json=_body(evidence))
    second = client.post("/workflows", json=_body(evidence))

    assert first.status_code == 202
    assert second.status_code == 503 and second.json()["error"]["code"] == "busy"
    _wait(client, first.json()["id"], timeout=20)
    assert client.post("/workflows", json=_body(evidence)).status_code == 202  # slot released


@pytest.mark.parametrize(
    "mutation",
    [
        {"feature": "student-9"},
        {"task": "  "},
        {"task": "x" * 501},
        {"evidence": []},
        {"extra": "field"},
    ],
)
def test_invalid_create_requests_return_400(client, evidence, mutation):
    response = client.post("/workflows", json={**_body(evidence), **mutation})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


def test_duplicate_evidence_ids_are_rejected(client, evidence):
    response = client.post("/workflows", json=_body(evidence + [dict(evidence[0])]))
    assert response.status_code == 400


def test_evidence_with_unsafe_id_is_rejected(client, evidence):
    evidence[0]["id"] = "../../x"
    assert client.post("/workflows", json=_body(evidence)).status_code == 400


def test_unknown_and_malformed_workflow_ids_return_404(client):
    assert client.get("/workflows/wf-20260101T000000Z-deadbeef").status_code == 404
    assert client.get("/workflows/not-an-id").status_code == 404
    assert client.post("/workflows/not-an-id/decision", json={"decision": "approve"}).status_code == 404


def test_decision_before_review_is_409_and_bad_decision_is_400(client, fake_llm, evidence):
    fake_llm.delay = 0.3
    workflow_id = client.post("/workflows", json=_body(evidence)).json()["id"]
    early = client.post(f"/workflows/{workflow_id}/decision", json={"decision": "approve"})
    assert early.status_code == 409 and early.json()["error"]["code"] == "not_awaiting_review"

    assert client.post(f"/workflows/{workflow_id}/decision", json={"decision": "maybe"}).status_code == 400
    _wait(client, workflow_id, timeout=20)


def test_reject_without_notes_is_400_over_http(client, evidence):
    workflow_id = client.post("/workflows", json=_body(evidence)).json()["id"]
    _wait(client, workflow_id)

    response = client.post(f"/workflows/{workflow_id}/decision", json={"decision": "reject"})
    assert response.status_code == 400 and response.json()["error"]["code"] == "notes_required"


def test_audit_filter_rejects_malformed_workflow_id(client):
    assert client.get("/audit", params={"workflow_id": "../x"}).status_code == 400
