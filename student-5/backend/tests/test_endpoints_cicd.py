"""Release 2 post-commit CI/CD endpoint tests for the Student 5 backend/API.

The two endpoint functions under test (run by the "Post-commit endpoint tests"
step of .github/workflows/student-5.yml, TL-NFR-11):

    1. POST /api/destinations        (create a destination)
    2. PUT  /api/destinations/<id>   (partial update of a destination)

Both routes are passthroughs: the database service owns validation and
existence checks, and the backend relays its status and body unchanged. So
each test pins down the exact request forwarded to the database API as well as
the reply, and the only status the backend decides for itself is the 503 for
an unreachable database. The database is mocked with `responses`; the live
container path is covered by live_endpoint_check.py in the same workflow.

Every test uses the cloud/CI baseline app: AI-Mode, MCP, RAG and Multi-Agent
all switched off.
"""

import json

import pytest
import requests
import responses

DATABASE_UNAVAILABLE = {"error": "database service unavailable"}

NEW_DESTINATION = {
    "country": "Portugal",
    "visa_requirement": "visa-free",
    "notes": "Schengen area; 90 days in any 180.",
}
STORED_DESTINATION = {"id": 13, **NEW_DESTINATION}


@pytest.fixture
def api(ai_off_client):
    """The backend as CI and the cloud baseline run it: every AI flag false."""
    return ai_off_client


def forwarded():
    """The single request the backend sent to the database API."""
    assert len(responses.calls) == 1, [call.request.url for call in responses.calls]
    return responses.calls[0].request


def forwarded_json():
    body = forwarded().body
    return None if body is None else json.loads(body)


# ---------------------------------------------------------------------------
# Endpoint 1: POST /api/destinations
# ---------------------------------------------------------------------------


@responses.activate
def test_create_destination_returns_201_with_the_stored_row(api, database_url):
    responses.add(
        responses.POST, database_url + "/api/destinations", json=STORED_DESTINATION, status=201
    )

    response = api.post("/api/destinations", json=NEW_DESTINATION)

    assert response.status_code == 201
    assert response.get_json() == STORED_DESTINATION
    request = forwarded()
    assert request.method == "POST"
    assert request.url == database_url + "/api/destinations"
    assert request.headers["Content-Type"] == "application/json"
    assert forwarded_json() == NEW_DESTINATION


@responses.activate
@pytest.mark.parametrize(
    "payload, database_error",
    [
        ({}, "Missing required field(s): country, visa_requirement"),
        ({"country": "Portugal"}, "Missing required field(s): visa_requirement"),
        (
            {"country": "   ", "visa_requirement": "visa-free"},
            "Field 'country' must be a non-empty string",
        ),
    ],
    ids=["empty-body", "missing-visa-requirement", "blank-country"],
)
def test_create_destination_relays_database_400_for_invalid_input(
    api, database_url, payload, database_error
):
    responses.add(
        responses.POST,
        database_url + "/api/destinations",
        json={"error": database_error},
        status=400,
    )

    response = api.post("/api/destinations", json=payload)

    assert response.status_code == 400
    assert response.get_json() == {"error": database_error}
    # Forwarded as sent, so the database's message is about the caller's input.
    assert forwarded_json() == payload


@responses.activate
def test_create_destination_with_non_json_body_relays_database_400(api, database_url):
    error = {"error": "Request body must be a JSON object"}
    responses.add(responses.POST, database_url + "/api/destinations", json=error, status=400)

    response = api.post("/api/destinations", data="country=Portugal")

    assert response.status_code == 400
    assert response.get_json() == error
    # An undecodable body is forwarded as no body, never as form text.
    assert forwarded_json() is None


@responses.activate
def test_create_destination_returns_503_when_database_is_down(api):
    # No mock is registered, so `responses` raises a ConnectionError.
    response = api.post("/api/destinations", json=NEW_DESTINATION)

    assert response.status_code == 503
    assert response.get_json() == DATABASE_UNAVAILABLE


# ---------------------------------------------------------------------------
# Endpoint 2: PUT /api/destinations/<id>
# ---------------------------------------------------------------------------


@responses.activate
def test_update_destination_forwards_only_supplied_fields_and_returns_200(api, database_url):
    change = {"visa_requirement": "eVisa", "notes": "ETIAS from late 2026."}
    updated = {**STORED_DESTINATION, **change}
    responses.add(responses.PUT, database_url + "/api/destinations/13", json=updated, status=200)

    response = api.put("/api/destinations/13", json=change)

    assert response.status_code == 200
    assert response.get_json() == updated
    request = forwarded()
    assert request.method == "PUT"
    assert request.url == database_url + "/api/destinations/13"
    # The database PUT is a partial merge: padding the body would overwrite fields.
    assert forwarded_json() == change


@responses.activate
@pytest.mark.parametrize(
    "payload, database_error",
    [
        ({"visa_requirement": ""}, "Field 'visa_requirement' must be a non-empty string"),
        ({"country": 42}, "Field 'country' must be a non-empty string"),
    ],
    ids=["blank-visa-requirement", "non-string-country"],
)
def test_update_destination_relays_database_400_for_invalid_input(
    api, database_url, payload, database_error
):
    responses.add(
        responses.PUT,
        database_url + "/api/destinations/13",
        json={"error": database_error},
        status=400,
    )

    response = api.put("/api/destinations/13", json=payload)

    assert response.status_code == 400
    assert response.get_json() == {"error": database_error}
    assert forwarded_json() == payload


@responses.activate
def test_update_unknown_destination_relays_database_404(api, database_url):
    error = {"error": "No destinations row with id 999"}
    responses.add(responses.PUT, database_url + "/api/destinations/999", json=error, status=404)

    response = api.put("/api/destinations/999", json={"notes": "Missing"})

    assert response.status_code == 404
    assert response.get_json() == error
    assert forwarded().url == database_url + "/api/destinations/999"


@responses.activate
def test_update_destination_with_non_integer_id_is_404_without_database_call(api):
    response = api.put("/api/destinations/not-a-number", json={"notes": "Missing"})

    assert response.status_code == 404
    assert response.get_json() == {"error": "Resource not found"}
    assert len(responses.calls) == 0


@responses.activate
@pytest.mark.parametrize(
    "failure",
    [requests.exceptions.ConnectionError("refused"), requests.exceptions.ReadTimeout("timed out")],
    ids=["connection-refused", "read-timeout"],
)
def test_update_destination_returns_503_when_database_is_down(api, database_url, failure):
    responses.add(responses.PUT, database_url + "/api/destinations/13", body=failure)

    response = api.put("/api/destinations/13", json={"notes": "Unreachable"})

    assert response.status_code == 503
    assert response.get_json() == DATABASE_UNAVAILABLE
