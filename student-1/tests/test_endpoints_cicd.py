"""Release 2 post-commit CI/CD endpoint tests for the Student 1 backend/API.

The two endpoint functions under test (run by .github/workflows/student-1.yml
after the student1-database and student1-backend containers are started):

    1. POST  /api/searches        (rank the cached catalogue and save the search)
    2. PATCH /api/searches/{id}   (rename a saved search)

The requests go to the running backend container, which calls the real
database container and its SQLite file; nothing is mocked. The workflow starts
the backend with AI_ENABLED=false and no LiteAPI key, as in the cloud baseline.
Every search a test creates is deleted again.

    STUDENT1_BACKEND_URL=http://localhost:5201 python -m pytest student-1/tests/test_endpoints_cicd.py
"""

import http.client
import json
import os
import urllib.parse
from datetime import date, timedelta

import pytest

BASE_URL = os.environ.get("STUDENT1_BACKEND_URL", "http://localhost:5201")
# Tokyo is one of the ten cached demonstration destinations (five or more active stays).
DESTINATION = "Tokyo"


def call(method, path, body=None):
    parsed = urllib.parse.urlparse(BASE_URL)
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=15)
    try:
        headers = {"Content-Type": "application/json"} if body is not None else {}
        connection.request(method, path, json.dumps(body) if body is not None else None, headers)
        response = connection.getresponse()
        raw = response.read()
        return response.status, dict(response.getheaders()), json.loads(raw) if raw else None
    finally:
        connection.close()


def search_criteria(**overrides):
    check_in = date.today() + timedelta(days=30)
    criteria = {
        "destination": DESTINATION,
        "checkIn": check_in.isoformat(),
        "checkOut": (check_in + timedelta(days=2)).isoformat(),
        "guests": 1,
        "minimumPrice": 0,
        "maximumPrice": 100000,
        "preferences": "",
        "useAi": False,
    }
    criteria.update(overrides)
    return criteria


@pytest.fixture
def saved_search():
    status, _, search = call("POST", "/api/searches", search_criteria())
    assert status == 201, search
    yield search
    call("DELETE", f"/api/searches/{search['id']}")


@pytest.fixture
def created_ids():
    ids = []
    yield ids
    for search_id in ids:
        call("DELETE", f"/api/searches/{search_id}")


# --- Endpoint 1: POST /api/searches ---------------------------------------


def test_create_search_ranks_cached_catalogue_and_saves_it(created_ids):
    status, headers, search = call("POST", "/api/searches", search_criteria())
    if status == 201:
        created_ids.append(search["id"])

    assert status == 201, search
    assert headers["Location"] == f"/api/searches/{search['id']}"
    assert search["title"] == DESTINATION
    assert search["rankingMode"] == "programmatic"
    assert search["notice"] is None
    assert len(search["results"]) >= 5
    assert [result["rank"] for result in search["results"]] == list(range(1, len(search["results"]) + 1))
    assert {result["destination"] for result in search["results"]} == {DESTINATION}

    status, _, reopened = call("GET", f"/api/searches/{search['id']}")
    assert status == 200
    assert reopened["results"] == search["results"]


def test_create_search_rejects_check_out_before_check_in():
    criteria = search_criteria()
    criteria["checkOut"] = criteria["checkIn"]

    status, _, body = call("POST", "/api/searches", criteria)

    assert status == 400
    assert body["error"]["code"] == "validation_error"
    assert "checkOut" in body["error"]["fields"]


def test_create_ai_search_is_refused_when_ai_ranking_is_disabled():
    status, _, body = call("POST", "/api/searches", search_criteria(useAi=True, preferences="Quiet"))

    assert status == 503
    assert body["error"]["code"] == "mode_disabled"
    assert body["error"]["message"] == "AI ranking is disabled."


# --- Endpoint 2: PATCH /api/searches/{id} ---------------------------------


def test_rename_search_updates_title_and_keeps_saved_results(saved_search):
    status, _, renamed = call("PATCH", f"/api/searches/{saved_search['id']}", {"title": "CI rename check"})

    assert status == 200, renamed
    assert renamed["title"] == "CI rename check"
    assert renamed["results"] == saved_search["results"]
    _, _, reopened = call("GET", f"/api/searches/{saved_search['id']}")
    assert reopened["title"] == "CI rename check"


def test_rename_search_rejects_blank_title(saved_search):
    status, _, body = call("PATCH", f"/api/searches/{saved_search['id']}", {"title": "   "})

    assert status == 400
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["fields"] == {"title": "Must be between 1 and 80 characters."}
    _, _, reopened = call("GET", f"/api/searches/{saved_search['id']}")
    assert reopened["title"] == DESTINATION


def test_rename_unknown_search_returns_not_found():
    status, _, body = call("PATCH", "/api/searches/2147483647", {"title": "Missing"})

    assert status == 404
    assert body["error"]["code"] == "not_found"
