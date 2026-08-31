"""Exercises the database microservice's own CRUD API directly, against a
throwaway SQLite file per test (see the `database_client` fixture)."""


def _create_attraction(database_client, name="Test Museum", category="sight"):
    response = database_client.post(
        "/api/data/attractions",
        json={"name": name, "category": category, "description": "A place.", "rating": 4.0},
    )
    assert response.status_code == 201
    return response.get_json()


def test_list_attractions_empty(database_client):
    response = database_client.get("/api/data/attractions")
    assert response.status_code == 200
    assert response.get_json() == []


def test_create_and_list_attraction(database_client):
    created = _create_attraction(database_client)
    response = database_client.get("/api/data/attractions")
    assert response.status_code == 200
    body = response.get_json()
    assert len(body) == 1
    assert body[0]["id"] == created["id"]
    assert body[0]["name"] == "Test Museum"


def test_list_attractions_filters_by_category(database_client):
    _create_attraction(database_client, name="Art Gallery", category="sight")
    _create_attraction(database_client, name="Noodle Bar", category="restaurant")

    response = database_client.get("/api/data/attractions?category=restaurant")
    body = response.get_json()
    assert len(body) == 1
    assert body[0]["name"] == "Noodle Bar"


def test_create_attraction_missing_fields_returns_400(database_client):
    response = database_client.post("/api/data/attractions", json={"description": "no name"})
    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"


def test_get_attraction_includes_reviews(database_client):
    created = _create_attraction(database_client)
    database_client.post(
        "/api/data/reviews",
        json={"attraction_id": created["id"], "rating": 5.0, "comment": "Loved it"},
    )

    response = database_client.get(f"/api/data/attractions/{created['id']}")
    assert response.status_code == 200
    body = response.get_json()
    assert len(body["reviews"]) == 1
    assert body["reviews"][0]["comment"] == "Loved it"


def test_get_attraction_not_found(database_client):
    response = database_client.get("/api/data/attractions/999")
    assert response.status_code == 404


def test_update_attraction(database_client):
    created = _create_attraction(database_client)
    response = database_client.put(
        f"/api/data/attractions/{created['id']}",
        json={"name": "Renamed Museum", "category": "sight", "description": "Updated.", "rating": 4.5},
    )
    assert response.status_code == 200
    assert response.get_json()["name"] == "Renamed Museum"


def test_update_attraction_not_found(database_client):
    response = database_client.put(
        "/api/data/attractions/999",
        json={"name": "X", "category": "sight"},
    )
    assert response.status_code == 404


def test_delete_attraction(database_client):
    created = _create_attraction(database_client)
    response = database_client.delete(f"/api/data/attractions/{created['id']}")
    assert response.status_code == 204

    follow_up = database_client.get(f"/api/data/attractions/{created['id']}")
    assert follow_up.status_code == 404


def test_delete_attraction_not_found(database_client):
    response = database_client.delete("/api/data/attractions/999")
    assert response.status_code == 404


def test_list_reviews_filtered_by_attraction(database_client):
    a = _create_attraction(database_client, name="A")
    b = _create_attraction(database_client, name="B")
    database_client.post("/api/data/reviews", json={"attraction_id": a["id"], "rating": 4.0, "comment": "ok"})
    database_client.post("/api/data/reviews", json={"attraction_id": b["id"], "rating": 3.0, "comment": "meh"})

    response = database_client.get(f"/api/data/reviews?attraction_id={a['id']}")
    body = response.get_json()
    assert len(body) == 1
    assert body[0]["attraction_id"] == a["id"]


def test_create_review_for_unknown_attraction_returns_400(database_client):
    response = database_client.post(
        "/api/data/reviews", json={"attraction_id": 999, "rating": 5.0, "comment": "no such place"}
    )
    assert response.status_code == 400


def test_health_endpoint(database_client):
    response = database_client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
