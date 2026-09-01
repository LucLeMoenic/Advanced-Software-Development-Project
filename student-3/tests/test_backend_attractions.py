"""Tests the backend's public /api/attractions and /api/reviews routes,
mocking database_client so no real database service is required."""

import database_client


def test_list_attractions_proxies_database_client(backend_client, monkeypatch):
    sample = [{"id": 1, "name": "Test Sight", "category": "sight", "description": "d", "rating": 4.5}]
    monkeypatch.setattr(database_client, "list_attractions", lambda category=None: sample)

    response = backend_client.get("/api/attractions")
    assert response.status_code == 200
    assert response.get_json() == sample


def test_list_attractions_returns_502_when_database_unavailable(backend_client, monkeypatch):
    def raise_unavailable(category=None):
        raise database_client.DatabaseUnavailableError("connection refused")

    monkeypatch.setattr(database_client, "list_attractions", raise_unavailable)

    response = backend_client.get("/api/attractions")
    assert response.status_code == 502
    assert response.get_json()["error"] == "database_unavailable"


def test_get_attraction_not_found(backend_client, monkeypatch):
    monkeypatch.setattr(database_client, "get_attraction", lambda attraction_id: None)

    response = backend_client.get("/api/attractions/999")
    assert response.status_code == 404


def test_create_attraction_happy_path(backend_client, monkeypatch):
    created = {"id": 5, "name": "New Spot", "category": "activity", "description": None, "rating": None}
    monkeypatch.setattr(database_client, "create_attraction", lambda payload: (created, None))

    response = backend_client.post("/api/attractions", json={"name": "New Spot", "category": "activity"})
    assert response.status_code == 201
    assert response.get_json() == created


def test_create_attraction_validation_error(backend_client, monkeypatch):
    error = {"error": "validation_error", "message": "name and category are required."}
    monkeypatch.setattr(database_client, "create_attraction", lambda payload: (None, error))

    response = backend_client.post("/api/attractions", json={})
    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"


def test_list_reviews_optionally_filtered(backend_client, monkeypatch):
    captured = {}

    def fake_list_reviews(attraction_id=None):
        captured["attraction_id"] = attraction_id
        return []

    monkeypatch.setattr(database_client, "list_reviews", fake_list_reviews)

    response = backend_client.get("/api/reviews?attraction_id=3")
    assert response.status_code == 200
    assert captured["attraction_id"] == "3"


def test_create_review_happy_path(backend_client, monkeypatch):
    created = {"id": 1, "attraction_id": 1, "rating": 5.0, "comment": "Great"}
    monkeypatch.setattr(database_client, "create_review", lambda payload: (created, None))

    response = backend_client.post(
        "/api/reviews", json={"attraction_id": 1, "rating": 5.0, "comment": "Great"}
    )
    assert response.status_code == 201
    assert response.get_json() == created


def test_add_to_itinerary_stub_logs_and_returns_202(backend_client):
    response = backend_client.post("/api/itinerary", json={"attraction_id": 1})
    assert response.status_code == 202
    assert response.get_json()["status"] == "logged"
