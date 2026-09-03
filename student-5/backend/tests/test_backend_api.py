"""Tests for the backend passthrough API.

The database service is mocked with the `responses` library, so the whole
suite runs with no network access and no SQLite file anywhere in sight -- which
is also a decent proof that the backend only ever talks HTTP.
"""

import json
from urllib.parse import parse_qs, urlparse

import pytest
import requests
import responses

# path, body a client would POST, row the database would return
RESOURCES = [
    pytest.param(
        "/api/destinations",
        {"country": "Japan", "visa_requirement": "eVisa"},
        {"id": 1, "country": "Japan", "visa_requirement": "eVisa", "notes": None},
        id="destinations",
    ),
    pytest.param(
        "/api/weather-notes",
        {"destination_id": 1, "season": "spring", "notes": "Mild and dry"},
        {"id": 1, "destination_id": 1, "season": "spring", "notes": "Mild and dry"},
        id="weather-notes",
    ),
    pytest.param(
        "/api/transit-options",
        {"destination_id": 1, "type": "rail", "details": "JR Pass"},
        {"id": 1, "destination_id": 1, "type": "rail", "details": "JR Pass"},
        id="transit-options",
    ),
]

FILTERABLE = ["/api/weather-notes", "/api/transit-options"]


def sent_body(call_index=0):
    """The JSON body the backend actually forwarded to the database."""
    return json.loads(responses.calls[call_index].request.body)


def sent_query(call_index=0):
    """The query string the backend actually forwarded to the database."""
    return parse_qs(urlparse(responses.calls[call_index].request.url).query)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health_reports_service_name(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "service": "student5-backend"}


def test_unknown_route_returns_json_404(client):
    response = client.get("/api/not-a-resource")

    assert response.status_code == 404
    assert "error" in response.get_json()


# ---------------------------------------------------------------------------
# CRUD passthrough
# ---------------------------------------------------------------------------


@responses.activate
@pytest.mark.parametrize("path, payload, row", RESOURCES)
def test_list_passthrough(client, database_url, path, payload, row):
    responses.add(responses.GET, database_url + path, json=[row], status=200)

    response = client.get(path)

    assert response.status_code == 200
    assert response.get_json() == [row]


@responses.activate
@pytest.mark.parametrize("path, payload, row", RESOURCES)
def test_get_passthrough(client, database_url, path, payload, row):
    responses.add(responses.GET, database_url + path + "/1", json=row, status=200)

    response = client.get(path + "/1")

    assert response.status_code == 200
    assert response.get_json() == row


@responses.activate
@pytest.mark.parametrize("path, payload, row", RESOURCES)
def test_create_passthrough_forwards_body_and_201(client, database_url, path, payload, row):
    responses.add(responses.POST, database_url + path, json=row, status=201)

    response = client.post(path, json=payload)

    assert response.status_code == 201
    assert response.get_json() == row
    assert sent_body() == payload


@responses.activate
@pytest.mark.parametrize("path, payload, row", RESOURCES)
def test_update_passthrough(client, database_url, path, payload, row):
    responses.add(responses.PUT, database_url + path + "/1", json=row, status=200)

    response = client.put(path + "/1", json=payload)

    assert response.status_code == 200
    assert response.get_json() == row
    assert sent_body() == payload


@responses.activate
@pytest.mark.parametrize("path, payload, row", RESOURCES)
def test_update_sends_only_the_fields_the_client_supplied(
    client, database_url, path, payload, row
):
    """The database PUT is a partial merge, so we must not pad the body out."""
    responses.add(responses.PUT, database_url + path + "/1", json=row, status=200)
    one_field = {"notes": "Updated"} if "notes" in payload else {"details": "Updated"}

    client.put(path + "/1", json=one_field)

    assert sent_body() == one_field


@responses.activate
@pytest.mark.parametrize("path, payload, row", RESOURCES)
def test_delete_passthrough_returns_204_without_a_body(
    client, database_url, path, payload, row
):
    responses.add(responses.DELETE, database_url + path + "/1", status=204)

    response = client.delete(path + "/1")

    assert response.status_code == 204
    assert response.get_data() == b""


# ---------------------------------------------------------------------------
# Query parameters
# ---------------------------------------------------------------------------


@responses.activate
@pytest.mark.parametrize("path", FILTERABLE)
def test_destination_id_filter_is_forwarded(client, database_url, path):
    responses.add(responses.GET, database_url + path, json=[], status=200)

    response = client.get(path + "?destination_id=7")

    assert response.status_code == 200
    assert sent_query() == {"destination_id": ["7"]}


@responses.activate
def test_no_filter_means_no_query_string(client, database_url):
    responses.add(responses.GET, database_url + "/api/weather-notes", json=[], status=200)

    client.get("/api/weather-notes")

    assert sent_query() == {}


# ---------------------------------------------------------------------------
# Error passthrough
# ---------------------------------------------------------------------------


@responses.activate
@pytest.mark.parametrize("path, payload, row", RESOURCES)
def test_404_from_database_is_passed_through(client, database_url, path, payload, row):
    body = {"error": "No rows with id 999"}
    responses.add(responses.GET, database_url + path + "/999", json=body, status=404)

    response = client.get(path + "/999")

    assert response.status_code == 404
    assert response.get_json() == body


@responses.activate
def test_400_from_database_is_passed_through(client, database_url):
    body = {"error": "Missing required field(s): country"}
    responses.add(
        responses.POST, database_url + "/api/destinations", json=body, status=400
    )

    response = client.post("/api/destinations", json={})

    assert response.status_code == 400
    assert response.get_json() == body


# ---------------------------------------------------------------------------
# Database unavailable
# ---------------------------------------------------------------------------


@responses.activate
def test_connection_error_returns_503(client):
    # No mock is registered, so `responses` raises a ConnectionError.
    response = client.get("/api/destinations")

    assert response.status_code == 503
    assert response.get_json() == {"error": "database service unavailable"}


@responses.activate
def test_timeout_returns_503(client, database_url):
    responses.add(
        responses.GET,
        database_url + "/api/destinations/1",
        body=requests.exceptions.ReadTimeout("timed out"),
    )

    response = client.get("/api/destinations/1")

    assert response.status_code == 503
    assert response.get_json() == {"error": "database service unavailable"}


@responses.activate
def test_write_paths_also_return_503_when_database_is_down(client):
    response = client.post("/api/transit-options", json={"type": "bus"})

    assert response.status_code == 503
    assert response.get_json() == {"error": "database service unavailable"}
