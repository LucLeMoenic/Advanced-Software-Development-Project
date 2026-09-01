"""Tests for the Student 5 travel logistics database microservice."""

import pytest

from app import create_app

COLLECTIONS = ("destinations", "weather-notes", "transit-options")


def make_weather_note(destination_id=1, **overrides):
    payload = {
        "destination_id": destination_id,
        "season": "Shoulder (Sep-Oct)",
        "notes": "Quieter trails and stable weather before the winter closures.",
    }
    payload.update(overrides)
    return payload


def make_transit_option(destination_id=1, **overrides):
    payload = {
        "destination_id": destination_id,
        "type": "bus",
        "details": "Airport limousine buses run to the main hotel districts every 20 minutes.",
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# Health and seeding
# ---------------------------------------------------------------------------


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "service": "student5-database"}


@pytest.mark.parametrize("collection", COLLECTIONS)
def test_seed_creates_at_least_ten_rows(client, collection):
    rows = client.get(f"/api/{collection}").get_json()
    assert len(rows) >= 10


def test_seed_creates_twelve_destinations(client):
    assert len(client.get("/api/destinations").get_json()) == 12


def test_seed_is_idempotent_across_restarts(database_path):
    first = create_app(database_path=database_path)
    with first.test_client() as test_client:
        before = len(test_client.get("/api/destinations").get_json())

    # Simulate a container restart against the same volume.
    second = create_app(database_path=database_path)
    with second.test_client() as test_client:
        after = len(test_client.get("/api/destinations").get_json())

    assert before == after == 12


# ---------------------------------------------------------------------------
# CRUD round trips
# ---------------------------------------------------------------------------


def test_destination_crud_round_trip(client):
    created = client.post(
        "/api/destinations",
        json={
            "country": "Singapore",
            "visa_requirement": "visa-free",
            "notes": "Short-stay entry with automated immigration gates.",
        },
    )
    assert created.status_code == 201
    row = created.get_json()
    assert row["country"] == "Singapore"
    row_id = row["id"]

    fetched = client.get(f"/api/destinations/{row_id}")
    assert fetched.status_code == 200
    assert fetched.get_json()["visa_requirement"] == "visa-free"

    updated = client.put(
        f"/api/destinations/{row_id}",
        json={
            "country": "Singapore",
            "visa_requirement": "eVisa",
            "notes": "Updated advisory text.",
        },
    )
    assert updated.status_code == 200
    assert updated.get_json()["visa_requirement"] == "eVisa"

    assert client.delete(f"/api/destinations/{row_id}").status_code == 204
    assert client.get(f"/api/destinations/{row_id}").status_code == 404


def test_weather_note_crud_round_trip(client):
    created = client.post("/api/weather-notes", json=make_weather_note())
    assert created.status_code == 201
    row_id = created.get_json()["id"]

    assert client.get(f"/api/weather-notes/{row_id}").status_code == 200

    updated = client.put(
        f"/api/weather-notes/{row_id}",
        json=make_weather_note(season="Winter (Dec-Feb)", notes="Heavy snow inland."),
    )
    assert updated.status_code == 200
    assert updated.get_json()["season"] == "Winter (Dec-Feb)"

    assert client.delete(f"/api/weather-notes/{row_id}").status_code == 204
    assert client.get(f"/api/weather-notes/{row_id}").status_code == 404


def test_transit_option_crud_round_trip(client):
    created = client.post("/api/transit-options", json=make_transit_option())
    assert created.status_code == 201
    row_id = created.get_json()["id"]

    assert client.get(f"/api/transit-options/{row_id}").status_code == 200

    updated = client.put(
        f"/api/transit-options/{row_id}",
        json=make_transit_option(type="ferry", details="Harbour ferries run until midnight."),
    )
    assert updated.status_code == 200
    assert updated.get_json()["type"] == "ferry"

    assert client.delete(f"/api/transit-options/{row_id}").status_code == 204
    assert client.get(f"/api/transit-options/{row_id}").status_code == 404


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("collection", COLLECTIONS)
def test_get_missing_id_returns_json_404(client, collection):
    response = client.get(f"/api/{collection}/999999")
    assert response.status_code == 404
    assert "error" in response.get_json()


@pytest.mark.parametrize("collection", COLLECTIONS)
def test_delete_missing_id_returns_404(client, collection):
    assert client.delete(f"/api/{collection}/999999").status_code == 404


def test_post_missing_required_field_returns_400(client):
    response = client.post("/api/destinations", json={"country": "Nepal"})
    assert response.status_code == 400
    assert "visa_requirement" in response.get_json()["error"]


def test_post_weather_note_with_unknown_destination_returns_400(client):
    response = client.post("/api/weather-notes", json=make_weather_note(999999))
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_post_transit_option_with_unknown_destination_returns_400(client):
    response = client.post("/api/transit-options", json=make_transit_option(999999))
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_put_with_unknown_destination_returns_400(client):
    created = client.post("/api/weather-notes", json=make_weather_note())
    row_id = created.get_json()["id"]

    response = client.put(
        f"/api/weather-notes/{row_id}", json=make_weather_note(999999)
    )
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_put_merges_partial_body_and_keeps_omitted_fields(client):
    original = client.get("/api/destinations/1").get_json()

    updated = client.put(
        "/api/destinations/1", json={"visa_requirement": "embassy-visa"}
    )
    assert updated.status_code == 200

    row = updated.get_json()
    assert row["visa_requirement"] == "embassy-visa"
    assert row["country"] == original["country"]
    assert row["notes"] == original["notes"]


def test_blank_required_field_is_rejected(client):
    response = client.post(
        "/api/destinations", json={"country": "   ", "visa_requirement": "visa-free"}
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Filtering and cascade behaviour
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("collection", ("weather-notes", "transit-options"))
def test_list_filter_by_destination_id(client, collection):
    rows = client.get(f"/api/{collection}?destination_id=1").get_json()
    assert rows, "seed data should include child rows for destination 1"
    assert all(row["destination_id"] == 1 for row in rows)


@pytest.mark.parametrize("collection", ("weather-notes", "transit-options"))
def test_list_filter_rejects_non_integer(client, collection):
    assert client.get(f"/api/{collection}?destination_id=abc").status_code == 400


def test_deleting_destination_cascades_to_children(client):
    destination_id = client.post(
        "/api/destinations",
        json={"country": "Samoa", "visa_requirement": "visa-free", "notes": None},
    ).get_json()["id"]

    note_id = client.post(
        "/api/weather-notes", json=make_weather_note(destination_id)
    ).get_json()["id"]
    option_id = client.post(
        "/api/transit-options", json=make_transit_option(destination_id)
    ).get_json()["id"]

    assert client.delete(f"/api/destinations/{destination_id}").status_code == 204

    assert client.get(f"/api/weather-notes/{note_id}").status_code == 404
    assert client.get(f"/api/transit-options/{option_id}").status_code == 404
