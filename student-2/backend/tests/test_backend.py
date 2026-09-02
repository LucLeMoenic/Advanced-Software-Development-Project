import pytest

from app import ItineraryGenerator, create_app


class FakeDatabase:
    def __init__(self):
        self.calls = []
        self.trip = {"id": 11, "user": "Alex", "destination": "Osaka", "startDate": "2026-10-10", "endDate": "2026-10-11", "budget": 1500, "interests": "food"}

    def request(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if method == "POST" and path == "/api/data/itineraries":
            return {**self.trip, "stops": [{"id": 12, **payload["stops"][0]}]}, 201
        if method == "POST" and path == "/api/data/stops":
            return {"id": len(self.calls), **payload}, 201
        if method == "GET" and path == "/api/data/stops/7":
            return {"id": 7, "tripId": 11, "day": 1, "activity": "Old stop", "notes": "", "sortOrder": 0}, 200
        if method == "PUT" and path == "/api/data/stops/7":
            return {"id": 7, **payload}, 200
        if method == "PUT" and path == "/api/data/trips/11/stops":
            return [{"id": index + 20, "tripId": 11, **stop} for index, stop in enumerate(payload["stops"])], 200
        if method == "GET" and path.endswith("/11"):
            return {**self.trip, "stops": []}, 200
        return [], 200


class FakeGenerator:
    def generate(self, trip, existing_stops=None, target_day=None):
        if target_day is not None:
            return [{"day": target_day, "activity": "Market walk", "notes": "Taste local food.", "sortOrder": 0}], "ai"
        return [
            {"day": 1, "activity": "Market walk", "notes": "Taste local food.", "sortOrder": 0},
            {"day": 1, "activity": "Castle visit", "notes": "Visit the grounds.", "sortOrder": 1},
            {"day": 2, "activity": "Museum visit", "notes": "See local exhibits.", "sortOrder": 0},
            {"day": 2, "activity": "Canal walk", "notes": "Walk before dinner.", "sortOrder": 1},
        ], "ai"


def valid_trip():
    return {"user": "Alex", "destination": "Osaka", "startDate": "2026-10-10", "endDate": "2026-10-11", "budget": 1500, "interests": "food"}


def test_create_runs_orchestration_and_persists_stops():
    database = FakeDatabase()
    response = create_app(database, FakeGenerator()).test_client().post("/api/trips", json=valid_trip())
    assert response.status_code == 201
    body = response.get_json()
    assert body["generationMode"] == "ai"
    assert [stage["stage"] for stage in body["agentTrace"]] == ["Plan", "Act", "Observe", "Adapt"]
    assert any(call[1] == "/api/data/itineraries" for call in database.calls)
    assert not any(call[1] == "/api/data/trips" for call in database.calls)


def test_invalid_trip_does_not_call_dependencies():
    database = FakeDatabase()
    response = create_app(database, FakeGenerator()).test_client().post("/api/trips", json={"destination": "X"})
    assert response.status_code == 400
    assert database.calls == []


def test_generator_validation_and_fallback_cover_every_day():
    trip = valid_trip()
    with pytest.raises(ValueError):
        ItineraryGenerator.validate([{"day": 1, "activity": "Museum", "notes": "Morning visit"}], trip)
    fallback = ItineraryGenerator.fallback(trip)
    assert len(fallback) == 4
    assert {stop["day"] for stop in fallback} == {1, 2}


def test_regenerate_one_stop_preserves_its_day_and_identity():
    response = create_app(FakeDatabase(), FakeGenerator()).test_client().post("/api/stops/7/regenerate")
    assert response.status_code == 200
    assert response.get_json()["stop"]["id"] == 7
    assert response.get_json()["stop"]["activity"] == "Market walk"


def test_regenerate_trip_uses_one_atomic_replace_without_deleting_first():
    database = FakeDatabase()
    response = create_app(database, FakeGenerator()).test_client().post("/api/trips/11/regenerate")
    assert response.status_code == 200
    assert any(call[0:2] == ("PUT", "/api/data/trips/11/stops") for call in database.calls)
    assert not any(call[0] == "DELETE" for call in database.calls)


def test_invalid_stop_is_rejected_before_database_call():
    database = FakeDatabase()
    response = create_app(database, FakeGenerator()).test_client().post("/api/trips/11/stops", json={"day": 0})
    assert response.status_code == 400
    assert database.calls == []


def test_stop_outside_trip_is_rejected_before_database_write():
    database = FakeDatabase()
    response = create_app(database, FakeGenerator()).test_client().post("/api/trips/11/stops", json={
        "day": 3, "activity": "Outside trip", "notes": "", "sortOrder": 0,
    })
    assert response.status_code == 400
    assert "2-day trip" in response.get_json()["error"]["fields"]["day"]
    assert [call[0:2] for call in database.calls] == [("GET", "/api/data/trips/11")]


def test_stop_update_validates_target_trip_before_write():
    database = FakeDatabase()
    response = create_app(database, FakeGenerator()).test_client().put("/api/stops/7", json={
        "tripId": 11, "day": 3, "activity": "Outside trip", "notes": "", "sortOrder": 0,
    })
    assert response.status_code == 400
    assert not any(call[0] == "PUT" for call in database.calls)