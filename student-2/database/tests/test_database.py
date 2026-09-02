import tempfile

from app import create_app


def test_seed_and_trip_stop_crud():
    with tempfile.NamedTemporaryFile(suffix=".db") as database:
        client = create_app(database.name).test_client()
        assert client.get("/health").status_code == 200
        seeded = client.get("/api/data/trips").get_json()
        assert len(seeded) == 10
        assert len(client.get(f"/api/data/trips/{seeded[0]['id']}").get_json()["stops"]) == 2

        trip_response = client.post("/api/data/trips", json={
            "user": "Alex", "destination": "Osaka", "startDate": "2026-10-10",
            "endDate": "2026-10-12", "budget": 1500, "interests": "food, design",
        })
        assert trip_response.status_code == 201
        trip = trip_response.get_json()

        stop_response = client.post("/api/data/stops", json={
            "tripId": trip["id"], "day": 1, "activity": "Kuromon Market",
            "notes": "Try seasonal produce", "sortOrder": 0,
        })
        assert stop_response.status_code == 201
        stop = stop_response.get_json()
        assert client.get(f"/api/data/stops/{stop['id']}").get_json()["activity"] == "Kuromon Market"
        stop["activity"] = "Osaka Castle"
        assert client.put(f"/api/data/stops/{stop['id']}", json=stop).get_json()["activity"] == "Osaka Castle"
        assert client.delete(f"/api/data/stops/{stop['id']}").status_code == 204
        cascade_stop = client.post("/api/data/stops", json={
            "tripId": trip["id"], "day": 2, "activity": "Dotonbori walk",
            "notes": "Visit after sunset", "sortOrder": 0,
        }).get_json()
        assert client.delete(f"/api/data/trips/{trip['id']}").status_code == 204
        assert client.get(f"/api/data/stops/{cascade_stop['id']}").status_code == 404


def test_validation_rejects_invalid_trip_without_writing():
    with tempfile.NamedTemporaryFile(suffix=".db") as database:
        client = create_app(database.name).test_client()
        response = client.post("/api/data/trips", json={"destination": "X", "budget": -1})
        assert response.status_code == 400
        assert "destination" in response.get_json()["error"]["fields"]
        assert len(client.get("/api/data/trips").get_json()) == 10


def test_atomic_itinerary_create_and_replace_preserve_valid_state():
    with tempfile.NamedTemporaryFile(suffix=".db") as database:
        client = create_app(database.name).test_client()
        response = client.post("/api/data/itineraries", json={
            "trip": {
                "user": "Alex", "destination": "Osaka", "startDate": "2026-10-10",
                "endDate": "2026-10-11", "budget": 1500, "interests": "food",
            },
            "stops": [
                {"day": 1, "activity": "Market walk", "notes": "Try local food", "sortOrder": 0},
                {"day": 2, "activity": "Museum visit", "notes": "Book ahead", "sortOrder": 0},
            ],
        })
        assert response.status_code == 201
        trip = response.get_json()
        assert len(trip["stops"]) == 2

        invalid = client.put(f"/api/data/trips/{trip['id']}/stops", json={
            "stops": [{"day": 3, "activity": "Outside trip", "notes": "", "sortOrder": 0}],
        })
        assert invalid.status_code == 400
        assert [stop["activity"] for stop in client.get(f"/api/data/trips/{trip['id']}").get_json()["stops"]] == ["Market walk", "Museum visit"]

        replacement = client.put(f"/api/data/trips/{trip['id']}/stops", json={
            "stops": [{"day": 1, "activity": "Castle visit", "notes": "Morning", "sortOrder": 0}],
        })
        assert replacement.status_code == 200
        assert [stop["activity"] for stop in replacement.get_json()] == ["Castle visit"]


def test_stop_days_and_trip_updates_respect_trip_duration():
    with tempfile.NamedTemporaryFile(suffix=".db") as database:
        client = create_app(database.name).test_client()
        trip = client.post("/api/data/trips", json={
            "user": "Alex", "destination": "Osaka", "startDate": "2026-10-10",
            "endDate": "2026-10-12", "budget": 1500, "interests": "food",
        }).get_json()
        stop = {
            "tripId": trip["id"], "day": 3, "activity": "Museum visit",
            "notes": "Book ahead", "sortOrder": 0,
        }
        assert client.post("/api/data/stops", json=stop).status_code == 201

        outside_trip = client.post("/api/data/stops", json={**stop, "day": 4})
        assert outside_trip.status_code == 400
        assert "3-day trip" in outside_trip.get_json()["error"]["fields"]["day"]

        shortened = client.put(f"/api/data/trips/{trip['id']}", json={
            **trip, "endDate": "2026-10-10",
        })
        assert shortened.status_code == 400
        saved = client.get(f"/api/data/trips/{trip['id']}").get_json()
        assert saved["endDate"] == "2026-10-12"
        assert [item["day"] for item in saved["stops"]] == [3]


def test_stop_update_preserves_existing_trip_ownership():
    with tempfile.NamedTemporaryFile(suffix=".db") as database:
        client = create_app(database.name).test_client()
        trip = client.post("/api/data/trips", json={
            "user": "Alex", "destination": "Osaka", "startDate": "2026-10-10",
            "endDate": "2026-10-11", "budget": 1500, "interests": "food",
        }).get_json()
        stop = client.post("/api/data/stops", json={
            "tripId": trip["id"], "day": 1, "activity": "Market walk",
            "notes": "Try local food", "sortOrder": 0,
        }).get_json()

        response = client.put(f"/api/data/stops/{stop['id']}", json={**stop, "tripId": 999999, "sortOrder": 99})
        assert response.status_code == 200
        saved = client.get(f"/api/data/stops/{stop['id']}").get_json()
        assert saved["tripId"] == trip["id"]
        assert saved["sortOrder"] == 0
        assert saved["activity"] == "Market walk"