import sqlite3
import tempfile
from pathlib import Path

import pytest

from app import create_app


@pytest.mark.parametrize("action,details", [
    ("add_stop", {"activity": "Lunch break", "notes": "Vegetarian"}),
    ("remove_stop", {}),
    ("update_stop", {"notes": "Bring tickets"}),
    ("shift_dates", {"startDate": "2027-04-10"}),
])
def test_content_edit_preview_confirm_undo(tmp_path, action, details):
    database = str(tmp_path / "itinerary.db")
    client = create_app(database).test_client()
    before = client.get("/api/data/trips/1").json
    stop = before["stops"][0]
    operation = {"action": action, "sourceDay": 1, "targetDay": 1,
                 "stopId": stop["id"] if action in ("remove_stop", "update_stop") else 0, **details}
    preview = client.post("/api/data/trips/1/edit-preview", json=operation)
    assert preview.status_code == 200
    assert preview.json["changes"][0]["kind"] == action
    assert client.get("/api/data/trips/1").json == before
    token = {"token": preview.json["token"]}
    assert client.post("/api/data/trips/2/edit-apply", json=token).status_code == 400
    assert client.post("/api/data/trips/1/edit-apply", json=token).status_code == 200
    assert client.post("/api/data/trips/1/edit-apply", json=token).status_code == 409
    after = client.get("/api/data/trips/1").json
    if action == "add_stop":
        added = next(saved for saved in after["stops"] if saved["activity"] == "Lunch break")
        assert added["notes"] == "Vegetarian" and added["sortOrder"] == stop["sortOrder"] + 1
    elif action == "remove_stop":
        assert stop["id"] not in {saved["id"] for saved in after["stops"]}
    elif action == "update_stop":
        assert after["stops"][0]["notes"] == "Bring tickets"
        assert after["stops"][0]["activity"] == stop["activity"]
    else:
        assert (after["startDate"], after["endDate"]) == ("2027-04-10", "2027-04-11")
        assert after["stops"] == before["stops"]
    client = create_app(database).test_client()
    undo = {"action": "undo", "sourceDay": 1, "targetDay": 1, "stopId": 0}
    preview = client.post("/api/data/trips/1/edit-preview", json=undo)
    assert preview.status_code == 200
    assert client.post("/api/data/trips/1/edit-apply", json={"token": preview.json["token"]}).status_code == 200
    restored = client.get("/api/data/trips/1").json
    assert (restored["startDate"], restored["endDate"]) == (before["startDate"], before["endDate"])
    fields = ("id", "day", "sortOrder", "activity", "notes", "createdAt")
    assert [[saved[field] for field in fields] for saved in restored["stops"]] == [[saved[field] for field in fields] for saved in before["stops"]]
    assert client.post("/api/data/trips/1/edit-preview", json=undo).status_code == 400


@pytest.mark.parametrize("operation", [
    {"action": "add_stop", "activity": " "},
    {"action": "add_stop", "activity": "Lunch", "notes": False},
    {"action": "add_stop", "activity": "Lunch", "targetDay": 3},
    {"action": "add_stop", "activity": "Lunch", "stopId": 1},
    {"action": "add_stop", "activity": "Lunch", "notes": "x" * 1001},
    {"action": "update_stop", "stopId": 1, "activity": "x" * 161},
    {"action": "update_stop", "stopId": 1},
    {"action": "update_stop", "stopId": 3, "notes": "Other trip"},
    {"action": "remove_stop", "stopId": 1, "notes": "Unexpected"},
    {"action": "shift_dates", "startDate": "2027-02-29"},
    {"action": "shift_dates", "startDate": "9999-12-31"},
    {"action": "shift_dates", "startDate": "20270601"},
    {"action": "shift_dates", "startDate": "2027-06-01", "stopId": 1},
])
def test_invalid_content_edits_do_not_write(tmp_path, operation):
    client = create_app(str(tmp_path / "itinerary.db")).test_client()
    before = client.get("/api/data/trips/1").json
    operation = {"sourceDay": 1, "targetDay": 1, "stopId": 0, **operation}
    assert client.post("/api/data/trips/1/edit-preview", json=operation).status_code == 400
    assert client.get("/api/data/trips/1").json == before


@pytest.mark.parametrize("action,details", [
    ("add_stop", {"activity": "Lunch"}), ("remove_stop", {"stopId": 1}),
    ("update_stop", {"stopId": 1, "notes": "Bring tickets"}), ("shift_dates", {"startDate": "2027-06-01"}),
])
def test_content_edits_reject_stale_preview_and_undo(tmp_path, action, details):
    client = create_app(str(tmp_path / "itinerary.db")).test_client()
    operation = {"action": action, "sourceDay": 1, "targetDay": 1, "stopId": 0, **details}
    preview = client.post("/api/data/trips/1/edit-preview", json=operation).json
    stop = client.get("/api/data/stops/2").json
    client.put("/api/data/stops/2", json={**stop, "notes": "Manual change"})
    assert client.post("/api/data/trips/1/edit-apply", json={"token": preview["token"]}).status_code == 409
    preview = client.post("/api/data/trips/1/edit-preview", json=operation).json
    assert client.post("/api/data/trips/1/edit-apply", json={"token": preview["token"]}).status_code == 200
    client.put("/api/data/stops/2", json={**stop, "notes": "Another manual change"})
    assert client.post("/api/data/trips/1/edit-preview", json={"action": "undo", "sourceDay": 1, "targetDay": 1, "stopId": 0}).status_code == 400


def test_remove_final_stop_and_restore_it_without_changing_identity(tmp_path):
    client = create_app(str(tmp_path / "itinerary.db")).test_client()
    client.delete("/api/data/stops/2")
    before = client.get("/api/data/stops/1").json
    operation = {"action": "remove_stop", "sourceDay": 1, "targetDay": 1, "stopId": 1}
    preview = client.post("/api/data/trips/1/edit-preview", json=operation).json
    assert client.post("/api/data/trips/1/edit-apply", json={"token": preview["token"]}).status_code == 200
    assert client.get("/api/data/trips/1").json["stops"] == []
    preview = client.post("/api/data/trips/1/edit-preview", json={**operation, "action": "undo", "stopId": 0}).json
    assert preview["changes"][0]["after"]["id"] == 1
    assert client.post("/api/data/trips/1/edit-apply", json={"token": preview["token"]}).status_code == 200
    restored = client.get("/api/data/stops/1").json
    for field in ("id", "tripId", "day", "activity", "notes", "sortOrder", "createdAt"):
        assert restored[field] == before[field]


def test_existing_database_migrates_without_changing_saved_trips(tmp_path):
    database = str(tmp_path / "itinerary.db")
    client = create_app(database).test_client()
    before = client.get("/api/data/trips/1").json
    with sqlite3.connect(database) as connection:
        connection.execute("ALTER TABLE trips DROP COLUMN last_edit")
    client = create_app(database).test_client()
    assert client.get("/api/data/trips/1").json == before
    with sqlite3.connect(database) as connection:
        assert "last_edit" in {row[1] for row in connection.execute("PRAGMA table_info(trips)")}


@pytest.mark.parametrize("action", ["reorder_before", "reorder_after"])
def test_reorder_and_undo_preserve_exact_order_across_restart(tmp_path, action):
    database = str(tmp_path / "itinerary.db")
    client = create_app(database).test_client()
    for activity, order in [("Lunch", 0), ("Gallery", 8)]:
        assert client.post("/api/data/stops", json={"tripId": 1, "day": 1, "activity": activity,
                                                   "notes": "Keep these notes", "sortOrder": order}).status_code == 201
    before = client.get("/api/data/trips/1").json
    day_stops = [stop for stop in before["stops"] if stop["day"] == 1]
    moving, anchor = (day_stops[-1], day_stops[0]) if action == "reorder_before" else (day_stops[0], day_stops[-1])
    operation = {"action": action, "sourceDay": 1, "targetDay": 1,
                 "stopId": moving["id"], "targetStopId": anchor["id"]}
    preview = client.post("/api/data/trips/1/edit-preview", json=operation)
    assert preview.status_code == 200
    assert client.get("/api/data/trips/1").json == before
    assert client.post("/api/data/trips/1/edit-apply", json={"token": preview.json["token"]}).status_code == 200
    after = client.get("/api/data/trips/1").json
    ordered = [stop["id"] for stop in after["stops"] if stop["day"] == 1]
    assert ordered == ([moving["id"]] + [stop["id"] for stop in day_stops[:-1]] if action == "reorder_before"
                       else [stop["id"] for stop in day_stops[1:]] + [moving["id"]])
    assert client.post("/api/data/trips/1/edit-preview", json=operation).status_code == 400
    client = create_app(database).test_client()
    undo = {"action": "undo", "sourceDay": 1, "targetDay": 1, "stopId": 0}
    preview = client.post("/api/data/trips/1/edit-preview", json=undo)
    assert preview.status_code == 200
    assert client.get("/api/data/trips/1").json == after
    assert client.post("/api/data/trips/1/edit-apply", json={"token": preview.json["token"]}).status_code == 200
    restored = client.get("/api/data/trips/1").json
    fields = ("id", "day", "sortOrder", "activity", "notes", "createdAt")
    assert [[stop[field] for field in fields] for stop in restored["stops"]] == [[stop[field] for field in fields] for stop in before["stops"]]
    assert "last_edit" not in restored
    assert client.post("/api/data/trips/1/edit-preview", json=undo).status_code == 400


@pytest.mark.parametrize("action", ["move_day", "swap_days", "move_stop"])
def test_undo_rejects_intervening_changes_and_wrong_trip(tmp_path, action):
    client = create_app(str(tmp_path / "itinerary.db")).test_client()
    trip = client.get("/api/data/trips/1").json
    operation = {"action": action, "sourceDay": 1, "targetDay": 2,
                 "stopId": trip["stops"][0]["id"] if action == "move_stop" else 0}
    undo = {"action": "undo", "sourceDay": 1, "targetDay": 1, "stopId": 0}
    assert client.post("/api/data/trips/1/edit-preview", json=undo).status_code == 400
    token = client.post("/api/data/trips/1/edit-preview", json=operation).json["token"]
    assert client.post("/api/data/trips/1/edit-apply", json={"token": token}).status_code == 200
    preview = client.post("/api/data/trips/1/edit-preview", json=undo)
    assert preview.status_code == 200
    assert client.post("/api/data/trips/2/edit-apply", json={"token": preview.json["token"]}).status_code == 400
    stop = client.get("/api/data/trips/1").json["stops"][0]
    client.put(f"/api/data/stops/{stop['id']}", json={**stop, "notes": "Manual change"})
    assert client.post("/api/data/trips/1/edit-apply", json={"token": preview.json["token"]}).status_code == 409
    assert client.post("/api/data/trips/1/edit-preview", json=undo).status_code == 400


def test_reordering_rejects_invalid_stop_selection(tmp_path):
    client = create_app(str(tmp_path / "itinerary.db")).test_client()
    trip = client.get("/api/data/trips/1").json
    first, second = trip["stops"]
    operation = {"action": "reorder_before", "sourceDay": 1, "targetDay": 1,
                 "stopId": first["id"], "targetStopId": second["id"]}
    for invalid in [operation, {**operation, "targetStopId": first["id"]},
                    {**operation, "targetStopId": True}, {**operation, "targetStopId": 99999},
                    {**operation, "action": "undo"}, {**operation, "targetDay": 2}]:
        assert client.post("/api/data/trips/1/edit-preview", json=invalid).status_code == 400
    assert client.get("/api/data/trips/1").json == trip


@pytest.mark.parametrize("action", ["move_day", "swap_days", "move_stop"])
def test_confirmed_edit_preserves_ids_and_rejects_replay(tmp_path, action):
    client = create_app(str(tmp_path / "itinerary.db")).test_client()
    before = client.get("/api/data/trips/1").json
    operation = {"action": action, "sourceDay": 1, "targetDay": 2,
                 "stopId": before["stops"][0]["id"] if action == "move_stop" else 0}
    preview = client.post("/api/data/trips/1/edit-preview", json=operation)
    assert preview.status_code == 200
    assert client.get("/api/data/trips/1").json == before
    token = {"token": preview.json["token"]}
    assert client.post("/api/data/trips/2/edit-apply", json=token).status_code == 400
    applied = client.post("/api/data/trips/1/edit-apply", json=token)
    assert applied.status_code == 200
    assert applied.json["changes"] == preview.json["changes"]
    after = client.get("/api/data/trips/1").json
    assert {stop["id"] for stop in before["stops"]} == {stop["id"] for stop in after["stops"]}
    for change in preview.json["changes"]:
        stop = next(stop for stop in after["stops"] if stop["id"] == change["id"])
        assert (stop["day"], stop["sortOrder"]) == (change["toDay"], change["toOrder"])
        assert stop["activity"] == change["activity"]
    assert client.post("/api/data/trips/1/edit-apply", json=token).status_code == 409


def test_edit_rejects_stale_tampered_expired_and_invalid_requests(tmp_path, monkeypatch):
    client = create_app(str(tmp_path / "itinerary.db")).test_client()
    operation = {"action": "swap_days", "sourceDay": 1, "targetDay": 2, "stopId": 0}
    token = client.post("/api/data/trips/1/edit-preview", json=operation).json["token"]
    assert client.post("/api/data/trips/1/edit-apply", json={"token": token + "tampered"}).status_code == 400
    with monkeypatch.context() as patch:
        patch.setattr("itsdangerous.timed.TimestampSigner.get_timestamp", lambda self: 9999999999)
        assert client.post("/api/data/trips/1/edit-apply", json={"token": token}).status_code == 400
    trip = client.get("/api/data/trips/1").json
    stop = trip["stops"][0]
    client.put(f"/api/data/stops/{stop['id']}", json={**stop, "notes": "Changed since preview"})
    assert client.post("/api/data/trips/1/edit-apply", json={"token": token}).status_code == 409
    for invalid in [None, [], {**operation, "targetDay": 3}, {**operation, "sourceDay": True},
                    {**operation, "action": "delete"}, {**operation, "extra": 1},
                    {**operation, "action": "move_stop", "stopId": 99999}]:
        assert client.post("/api/data/trips/1/edit-preview", json=invalid).status_code == 400


def test_swap_with_an_empty_source_day_and_move_appends(tmp_path):
    client = create_app(str(tmp_path / "itinerary.db")).test_client()
    operation = {"action": "move_day", "sourceDay": 1, "targetDay": 2, "stopId": 0}
    preview = client.post("/api/data/trips/1/edit-preview", json=operation).json
    assert preview["changes"][0]["toOrder"] == 1
    assert client.post("/api/data/trips/1/edit-apply", json={"token": preview["token"]}).status_code == 200
    preview = client.post("/api/data/trips/1/edit-preview", json={**operation, "action": "swap_days"}).json
    assert len(preview["changes"]) == 2
    assert all(change["toDay"] == 1 for change in preview["changes"])
    assert client.post("/api/data/trips/1/edit-apply", json={"token": preview["token"]}).status_code == 200


def test_seed_and_trip_stop_crud():
    with tempfile.TemporaryDirectory() as directory:
        client = create_app(str(Path(directory) / "itinerary.db")).test_client()
        assert client.get("/health").status_code == 200
        seeded = client.get("/api/data/trips").get_json()
        assert len(seeded) == 10
        assert len({trip["user"] for trip in seeded}) == 10
        assert len({trip["interests"] for trip in seeded}) == 10
        seeded_details = [client.get(f"/api/data/trips/{trip['id']}").get_json() for trip in seeded]
        assert all(len(trip["stops"]) == 2 for trip in seeded_details)
        assert all("Seeded demonstration" not in stop["notes"] for trip in seeded_details for stop in trip["stops"])

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
    with tempfile.TemporaryDirectory() as directory:
        client = create_app(str(Path(directory) / "itinerary.db")).test_client()
        response = client.post("/api/data/trips", json={"destination": "X", "budget": -1})
        assert response.status_code == 400
        assert "destination" in response.get_json()["error"]["fields"]
        assert len(client.get("/api/data/trips").get_json()) == 10


def test_atomic_itinerary_create_and_replace_preserve_valid_state():
    with tempfile.TemporaryDirectory() as directory:
        client = create_app(str(Path(directory) / "itinerary.db")).test_client()
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
    with tempfile.TemporaryDirectory() as directory:
        client = create_app(str(Path(directory) / "itinerary.db")).test_client()
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
    with tempfile.TemporaryDirectory() as directory:
        client = create_app(str(Path(directory) / "itinerary.db")).test_client()
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