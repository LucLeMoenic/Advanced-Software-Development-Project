import hashlib
import json
import os
import sqlite3
from contextlib import closing
from datetime import UTC, date, datetime, timedelta

from flask import Flask, jsonify, request
from itsdangerous import BadSignature, URLSafeTimedSerializer


def create_app(database_path=None):
    app = Flask(__name__)
    app.config["DATABASE_PATH"] = database_path or os.getenv("DATABASE_PATH", "/data/itinerary.db")
    previews = URLSafeTimedSerializer(os.urandom(32), salt="itinerary-edit-v1")

    def connect():
        connection = sqlite3.connect(app.config["DATABASE_PATH"])
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def now():
        return datetime.now(UTC).isoformat()

    def error(message, status=400, fields=None):
        return jsonify({"error": {"code": "validation_error" if status == 400 else "not_found", "message": message, "fields": fields or {}}}), status

    def validate_trip(payload):
        fields = {}
        user_name = str(payload.get("user", "")).strip()
        destination = str(payload.get("destination", "")).strip()
        start_date = str(payload.get("startDate", "")).strip()
        end_date = str(payload.get("endDate", "")).strip()
        interests = str(payload.get("interests", "")).strip()
        try:
            budget = round(float(payload.get("budget", -1)), 2)
        except (TypeError, ValueError):
            budget = -1
        if not 1 <= len(user_name) <= 80:
            fields["user"] = "User must be 1-80 characters."
        if not 2 <= len(destination) <= 100:
            fields["destination"] = "Destination must be 2-100 characters."
        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
            if end < start:
                fields["endDate"] = "End date must be on or after the start date."
            if (end - start).days > 30:
                fields["endDate"] = "Trips may be at most 31 days."
        except ValueError:
            fields["dates"] = "Dates must use YYYY-MM-DD."
        if budget < 0 or budget > 1_000_000:
            fields["budget"] = "Budget must be between 0 and 1,000,000."
        if len(interests) > 500:
            fields["interests"] = "Interests must be at most 500 characters."
        return fields, {
            "user": user_name,
            "destination": destination,
            "startDate": start_date,
            "endDate": end_date,
            "budget": budget,
            "interests": interests,
        }

    def validate_stop(payload):
        fields = {}
        try:
            trip_id = int(payload.get("tripId", 0))
            day = int(payload.get("day", 0))
            sort_order = int(payload.get("sortOrder", 0))
        except (TypeError, ValueError):
            trip_id = day = sort_order = 0
        activity = str(payload.get("activity", "")).strip()
        notes = str(payload.get("notes", "")).strip()
        if trip_id < 1:
            fields["tripId"] = "Trip ID must be positive."
        if not 1 <= day <= 31:
            fields["day"] = "Day must be between 1 and 31."
        if not 1 <= len(activity) <= 160:
            fields["activity"] = "Activity must be 1-160 characters."
        if len(notes) > 1000:
            fields["notes"] = "Notes must be at most 1000 characters."
        if sort_order < 0:
            fields["sortOrder"] = "Sort order cannot be negative."
        return fields, {"tripId": trip_id, "day": day, "activity": activity, "notes": notes, "sortOrder": sort_order}

    def trip_dict(row):
        return {
            "id": row["id"], "user": row["user_name"], "destination": row["destination"],
            "startDate": row["start_date"], "endDate": row["end_date"], "budget": row["budget"],
            "interests": row["interests"], "createdAt": row["created_at"], "updatedAt": row["updated_at"],
        }

    def stop_dict(row):
        return {
            "id": row["id"], "tripId": row["trip_id"], "day": row["day"],
            "activity": row["activity"], "notes": row["notes"], "sortOrder": row["sort_order"],
            "createdAt": row["created_at"], "updatedAt": row["updated_at"],
        }

    def validate_itinerary_stops(payloads, trip_id, day_count):
        if not isinstance(payloads, list) or not payloads:
            return {"stops": "Provide at least one itinerary stop."}, []
        cleaned_stops = []
        fields = {}
        for index, payload in enumerate(payloads):
            stop_fields, stop = validate_stop({**payload, "tripId": trip_id}) if isinstance(payload, dict) else ({"stop": "Stop must be an object."}, {})
            if not stop_fields and stop["day"] > day_count:
                stop_fields["day"] = f"Day must be within the {day_count}-day trip."
            if stop_fields:
                fields[f"stops[{index}]"] = " ".join(stop_fields.values())
            else:
                cleaned_stops.append(stop)
        return fields, cleaned_stops

    def insert_stop(connection, stop, timestamp):
        cursor = connection.execute(
            "INSERT INTO trip_stops(trip_id,day,activity,notes,sort_order,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            (stop["tripId"], stop["day"], stop["activity"], stop["notes"], stop["sortOrder"], timestamp, timestamp),
        )
        return connection.execute("SELECT * FROM trip_stops WHERE id = ?", (cursor.lastrowid,)).fetchone()

    def initialise():
        directory = os.path.dirname(app.config["DATABASE_PATH"])
        if directory:
            os.makedirs(directory, exist_ok=True)
        with closing(connect()) as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS trips (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT NOT NULL CHECK(length(user_name) BETWEEN 1 AND 80),
                    destination TEXT NOT NULL CHECK(length(destination) BETWEEN 2 AND 100),
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    budget REAL NOT NULL CHECK(budget BETWEEN 0 AND 1000000),
                    interests TEXT NOT NULL DEFAULT '' CHECK(length(interests) <= 500),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS trip_stops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id INTEGER NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
                    day INTEGER NOT NULL CHECK(day BETWEEN 1 AND 31),
                    activity TEXT NOT NULL CHECK(length(activity) BETWEEN 1 AND 160),
                    notes TEXT NOT NULL DEFAULT '' CHECK(length(notes) <= 1000),
                    sort_order INTEGER NOT NULL DEFAULT 0 CHECK(sort_order >= 0),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS ix_trip_stops_trip_day ON trip_stops(trip_id, day, sort_order);
            """)
            if "last_edit" not in {column["name"] for column in connection.execute("PRAGMA table_info(trips)")}:
                connection.execute("ALTER TABLE trips ADD COLUMN last_edit TEXT")
            count = connection.execute("SELECT COUNT(*) FROM trips").fetchone()[0]
            if count == 0:
                seed_trips = [
                    ("Culture Explorer", "Kyoto", 0, 1800, "temples, gardens, traditional crafts", [
                        ("Walk the Philosopher's Path", "Start early, then visit the nearby temples and small craft shops."),
                        ("Explore Nishiki Market", "Sample local specialities and allow time for the surrounding arcades."),
                    ]),
                    ("Coastal Foodie", "Lisbon", 4, 1450, "seafood, viewpoints, historic streets", [
                        ("Ride to Alfama and explore on foot", "Use the morning for quieter lanes and stop at the viewpoints."),
                        ("Visit Belem's riverside landmarks", "Book popular sights ahead and leave time for a local bakery."),
                    ]),
                    ("Design Weekender", "Melbourne", 8, 1250, "coffee, galleries, architecture", [
                        ("Tour the laneways and arcades", "Combine street art, independent shops, and a relaxed coffee stop."),
                        ("Spend an afternoon in Fitzroy", "Browse local design stores and finish with an early dinner."),
                    ]),
                    ("Night Market Fan", "Seoul", 12, 2100, "markets, contemporary art, neighbourhoods", [
                        ("Explore Gyeongbokgung and Bukchon", "Arrive early and respect signs around residential streets."),
                        ("Discover Hongdae after dark", "Plan dinner at the market and use the metro for the return journey."),
                    ]),
                    ("History Walker", "Edinburgh", 16, 1100, "castles, literature, scenic walks", [
                        ("Walk the Royal Mile", "Begin at the castle and allow time for closes and museum stops."),
                        ("Climb Arthur's Seat", "Check the weather, wear suitable shoes, and carry water."),
                    ]),
                    ("Street Food Seeker", "Hanoi", 20, 950, "street food, history, lakes", [
                        ("Explore the Old Quarter", "Join a small food walk or note busy stalls to revisit later."),
                        ("Visit the Temple of Literature", "Go in the morning, then take a relaxed walk around Hoan Kiem Lake."),
                    ]),
                    ("Museum Hopper", "Montreal", 24, 1650, "museums, bakeries, cycling", [
                        ("Cycle along the Lachine Canal", "Reserve a bike and stop in Atwater Market for lunch."),
                        ("Explore Old Montreal", "Combine the history museum with an evening walk by the waterfront."),
                    ]),
                    ("Art Trail Planner", "Florence", 28, 1950, "Renaissance art, markets, viewpoints", [
                        ("Visit the Uffizi Gallery", "Reserve a timed ticket and keep the rest of the morning flexible."),
                        ("Walk to Piazzale Michelangelo", "Cross through Oltrarno and arrive before sunset for the city view."),
                    ]),
                    ("Outdoor Adventurer", "Auckland", 32, 2400, "coastal walks, islands, local food", [
                        ("Take the ferry to Waiheke Island", "Confirm the return timetable and choose one coastal walking route."),
                        ("Explore Mount Eden and nearby cafes", "Walk the summit loop early and spend the afternoon locally."),
                    ]),
                    ("Urban Cyclist", "Copenhagen", 36, 2200, "cycling, modern design, bakeries", [
                        ("Cycle the harbour route", "Use a marked cycle lane and pause at the waterfront public spaces."),
                        ("Explore Norrebro and the Designmuseum", "Allow time for neighbourhood shops and a bakery stop."),
                    ]),
                ]
                base = date.today() + timedelta(days=30)
                for user, destination, start_offset, budget, interests, stops in seed_trips:
                    created = now()
                    start_date = base + timedelta(days=start_offset)
                    cursor = connection.execute(
                        "INSERT INTO trips(user_name,destination,start_date,end_date,budget,interests,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                        (user, destination, start_date.isoformat(), (start_date + timedelta(days=1)).isoformat(), budget, interests, created, created),
                    )
                    for day_number, (activity, notes) in enumerate(stops, start=1):
                        connection.execute(
                            "INSERT INTO trip_stops(trip_id,day,activity,notes,sort_order,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                            (cursor.lastrowid, day_number, activity, notes, 0, created, created),
                        )
            connection.commit()

    @app.get("/health")
    def health():
        try:
            with closing(connect()) as connection:
                connection.execute("SELECT 1").fetchone()
            return jsonify({"status": "healthy"})
        except sqlite3.Error:
            return jsonify({"status": "unhealthy"}), 503

    @app.get("/api/data/trips")
    def list_trips():
        with closing(connect()) as connection:
            rows = connection.execute("SELECT * FROM trips ORDER BY created_at DESC, id DESC").fetchall()
        return jsonify([trip_dict(row) for row in rows])

    @app.post("/api/data/trips")
    def create_trip():
        fields, trip = validate_trip(request.get_json(silent=True) or {})
        if fields:
            return error("Check the trip details.", fields=fields)
        timestamp = now()
        with closing(connect()) as connection:
            cursor = connection.execute(
                "INSERT INTO trips(user_name,destination,start_date,end_date,budget,interests,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                (trip["user"], trip["destination"], trip["startDate"], trip["endDate"], trip["budget"], trip["interests"], timestamp, timestamp),
            )
            connection.commit()
            row = connection.execute("SELECT * FROM trips WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return jsonify(trip_dict(row)), 201

    @app.post("/api/data/itineraries")
    def create_itinerary():
        payload = request.get_json(silent=True) or {}
        fields, trip = validate_trip(payload.get("trip", {}))
        if fields:
            return error("Check the trip details.", fields=fields)
        day_count = (date.fromisoformat(trip["endDate"]) - date.fromisoformat(trip["startDate"])).days + 1
        stop_fields, stops = validate_itinerary_stops(payload.get("stops"), 1, day_count)
        if stop_fields:
            return error("Check the itinerary stops.", fields=stop_fields)
        timestamp = now()
        with closing(connect()) as connection:
            cursor = connection.execute(
                "INSERT INTO trips(user_name,destination,start_date,end_date,budget,interests,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                (trip["user"], trip["destination"], trip["startDate"], trip["endDate"], trip["budget"], trip["interests"], timestamp, timestamp),
            )
            trip_id = cursor.lastrowid
            saved_stops = [insert_stop(connection, {**stop, "tripId": trip_id}, timestamp) for stop in stops]
            connection.commit()
            row = connection.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)).fetchone()
        result = trip_dict(row)
        result["stops"] = [stop_dict(stop) for stop in saved_stops]
        return jsonify(result), 201

    @app.get("/api/data/trips/<int:trip_id>")
    def get_trip(trip_id):
        with closing(connect()) as connection:
            row = connection.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)).fetchone()
            stops = connection.execute("SELECT * FROM trip_stops WHERE trip_id = ? ORDER BY day, sort_order, id", (trip_id,)).fetchall()
        if row is None:
            return error("Trip not found.", 404)
        result = trip_dict(row)
        result["stops"] = [stop_dict(stop) for stop in stops]
        return jsonify(result)

    def edit_snapshot(connection, trip_id):
        row = connection.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)).fetchone()
        if row is None:
            return None
        trip = trip_dict(row)
        trip["stops"] = [stop_dict(stop) for stop in connection.execute(
            "SELECT * FROM trip_stops WHERE trip_id = ? ORDER BY day, sort_order, id", (trip_id,))]
        return trip

    def revision(trip):
        return hashlib.sha256(json.dumps(trip, sort_keys=True).encode()).hexdigest()

    def stop_state(stop):
        return {key: stop[key] for key in ("id", "day", "activity", "notes", "sortOrder")}

    def detail_change(before, after):
        return {"kind": "add_stop" if before is None else "remove_stop" if after is None else "update_stop",
                "id": (before or after)["id"],
                "before": stop_state(before) if before else None,
                "after": stop_state(after) if after else None}

    def date_change(trip, start, end):
        return {"kind": "shift_dates", "fromStartDate": trip["startDate"], "fromEndDate": trip["endDate"],
                "toStartDate": start, "toEndDate": end}

    def edit_changes(trip, operation, connection):
        required = {"action", "sourceDay", "targetDay", "stopId"}
        if not isinstance(operation, dict) or not required <= set(operation) or set(operation) - required - {"targetStopId", "activity", "notes", "startDate"}:
            raise ValueError("Invalid edit operation.")
        action = operation["action"]
        source, target, stop_id = operation["sourceDay"], operation["targetDay"], operation["stopId"]
        target_stop_id = operation.get("targetStopId", 0)
        days = (date.fromisoformat(trip["endDate"]) - date.fromisoformat(trip["startDate"])).days + 1
        if action not in ("move_day", "swap_days", "move_stop", "reorder_before", "reorder_after", "undo", "add_stop", "remove_stop", "update_stop", "shift_dates") or any(type(value) is not int for value in (source, target, stop_id, target_stop_id)):
            raise ValueError("Choose a supported itinerary edit.")
        if len(trip["stops"]) > 200:
            raise ValueError("Too many stops to edit.")
        allowed = {"add_stop": {"activity", "notes"}, "update_stop": {"activity", "notes"}, "shift_dates": {"startDate"}}.get(action, set())
        if any(operation.get(field) is not None for field in {"activity", "notes", "startDate"} - allowed):
            raise ValueError("Unexpected edit details.")
        if action == "shift_dates":
            if (source, target, stop_id, target_stop_id) != (1, 1, 0, 0):
                raise ValueError("Date shifts cannot select stops or days.")
            start_text = operation.get("startDate")
            if not isinstance(start_text, str):
                raise ValueError("Provide a new start date in YYYY-MM-DD format.")
            try:
                start = date.fromisoformat(start_text)
                end = start + timedelta(days=days - 1)
            except (ValueError, OverflowError):
                raise ValueError("Invalid trip dates.") from None
            if start.isoformat() != start_text or start_text == trip["startDate"]:
                raise ValueError("Choose a different start date in YYYY-MM-DD format.")
            return [date_change(trip, start_text, end.isoformat())]
        if action in ("add_stop", "remove_stop", "update_stop"):
            if not 1 <= source == target <= days or target_stop_id != 0:
                raise ValueError("Choose a day within this trip.")
            if action == "add_stop":
                if stop_id != 0 or len(trip["stops"]) >= 200:
                    raise ValueError("Cannot add this stop.")
                before = None
                after = {"id": 0, "day": target, "activity": operation.get("activity"),
                         "notes": operation["notes"] if operation.get("notes") is not None else "",
                         "sortOrder": max((stop["sortOrder"] for stop in trip["stops"] if stop["day"] == target), default=-1) + 1}
            else:
                before = next((stop for stop in trip["stops"] if stop["id"] == stop_id and stop["day"] == source), None)
                if before is None:
                    raise ValueError("Choose an existing stop on the selected day.")
                if action == "remove_stop":
                    return [detail_change(before, None)]
                after = {**before, **{field: operation[field] for field in ("activity", "notes") if operation.get(field) is not None}}
            if (not isinstance(after["activity"], str) or not 1 <= len(after["activity"].strip()) <= 160
                    or not isinstance(after["notes"], str) or len(after["notes"]) > 1000):
                raise ValueError("Invalid activity or notes.")
            after["activity"] = after["activity"].strip()
            if before and stop_state(before) == stop_state(after):
                raise ValueError("The stop already has these details.")
            return [detail_change(before, after)]
        if action == "undo":
            if (source, target, stop_id, target_stop_id) != (1, 1, 0, 0):
                raise ValueError("Undo cannot select days or stops.")
            saved = connection.execute("SELECT last_edit FROM trips WHERE id=?", (trip["id"],)).fetchone()["last_edit"]
            last_edit = json.loads(saved) if saved else None
            if not last_edit or last_edit["revision"] != revision(trip):
                raise ValueError("No unchanged itinerary edit is available to undo.")
            if "snapshot" in last_edit:
                original = last_edit["snapshot"]
                current = {stop["id"]: stop for stop in trip["stops"]}
                originals = {stop["id"]: stop for stop in original["stops"]}
                changes = []
                for identifier in sorted(current.keys() | originals.keys()):
                    before, after = current.get(identifier), originals.get(identifier)
                    if before is None or after is None or (before["activity"], before["notes"]) != (after["activity"], after["notes"]):
                        changes.append(detail_change(before, after))
                    elif (before["day"], before["sortOrder"]) != (after["day"], after["sortOrder"]):
                        changes.append({"id": identifier, "activity": before["activity"], "notes": before["notes"],
                                        "fromDay": before["day"], "toDay": after["day"],
                                        "fromOrder": before["sortOrder"], "toOrder": after["sortOrder"]})
                if (trip["startDate"], trip["endDate"]) != (original["startDate"], original["endDate"]):
                    changes.append(date_change(trip, original["startDate"], original["endDate"]))
                return changes
            originals = {stop["id"]: stop for stop in last_edit["stops"]}
            return [{"id": stop["id"], "activity": stop["activity"], "notes": stop["notes"],
                     "fromDay": stop["day"], "toDay": originals[stop["id"]]["day"],
                     "fromOrder": stop["sortOrder"], "toOrder": originals[stop["id"]]["sortOrder"]}
                    for stop in trip["stops"] if stop["id"] in originals]
        if action in ("reorder_before", "reorder_after"):
            if not 1 <= source == target <= days or stop_id == target_stop_id:
                raise ValueError("Choose two different stops on the same day.")
            ordered = [stop for stop in trip["stops"] if stop["day"] == source]
            identifiers = [stop["id"] for stop in ordered]
            if stop_id not in identifiers or target_stop_id not in identifiers:
                raise ValueError("Choose two stops on the selected day.")
            selected = next(stop for stop in ordered if stop["id"] == stop_id)
            ordered.remove(selected)
            anchor = next(index for index, stop in enumerate(ordered) if stop["id"] == target_stop_id)
            ordered.insert(anchor + (action == "reorder_after"), selected)
            if [stop["id"] for stop in ordered] == identifiers:
                raise ValueError("The stops are already in that order.")
            return [{"id": stop["id"], "activity": stop["activity"], "notes": stop["notes"],
                     "fromDay": source, "toDay": source, "fromOrder": stop["sortOrder"], "toOrder": index}
                    for index, stop in enumerate(ordered)]
        if target_stop_id != 0:
            raise ValueError("Only reordering accepts a target stop.")
        if not 1 <= source <= days or not 1 <= target <= days or source == target:
            raise ValueError("Choose two different days within this trip.")
        if len(trip["stops"]) > 200 or (action != "move_stop" and stop_id != 0):
            raise ValueError("Invalid stop selection.")
        selected = [stop for stop in trip["stops"] if stop["day"] == source and (action != "move_stop" or stop["id"] == stop_id)]
        if action == "swap_days":
            selected += [stop for stop in trip["stops"] if stop["day"] == target]
        if not selected:
            raise ValueError("No matching stops on the selected days.")
        changes = []
        next_order = max((stop["sortOrder"] for stop in trip["stops"] if stop["day"] == target), default=-1) + 1
        for index, stop in enumerate(selected):
            changes.append({"id": stop["id"], "activity": stop["activity"], "notes": stop["notes"],
                            "fromDay": stop["day"], "toDay": target if stop["day"] == source else source,
                            "fromOrder": stop["sortOrder"],
                            "toOrder": stop["sortOrder"] if action == "swap_days" else next_order + index})
        return changes

    @app.post("/api/data/trips/<int:trip_id>/edit-preview")
    def preview_edit(trip_id):
        if request.content_length is not None and request.content_length > 8192:
            return error("Edit request is too large.")
        operation = request.get_json(silent=True)
        with closing(connect()) as connection:
            connection.execute("BEGIN")
            trip = edit_snapshot(connection, trip_id)
            if trip is None:
                return error("Trip not found.", 404)
            try:
                changes = edit_changes(trip, operation, connection)
            except ValueError as exception:
                return error(str(exception))
        token = previews.dumps({"tripId": trip_id, "revision": revision(trip), "operation": operation})
        return jsonify({"tripId": trip_id, "token": token, "changes": changes, "expiresIn": 600})

    @app.post("/api/data/trips/<int:trip_id>/edit-apply")
    def apply_edit(trip_id):
        payload = request.get_json(silent=True)
        if (request.content_length is not None and request.content_length > 8192) or not isinstance(payload, dict) or set(payload) != {"token"} or not isinstance(payload["token"], str):
            return error("Provide the confirmed preview token.")
        try:
            preview = previews.loads(payload["token"], max_age=600)
        except BadSignature:
            return error("Preview expired or invalid. Request a new preview.")
        if preview["tripId"] != trip_id:
            return error("Preview belongs to another trip.")
        with closing(connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            trip = edit_snapshot(connection, trip_id)
            if trip is None:
                return error("Trip not found.", 404)
            if revision(trip) != preview["revision"]:
                return jsonify({"error": {"code": "stale_preview", "message": "The trip changed. Request a new preview.", "fields": {}}}), 409
            try:
                changes = edit_changes(trip, preview["operation"], connection)
            except ValueError as exception:
                return error(str(exception))
            timestamp = now()
            for change in changes:
                kind = change.get("kind")
                if kind == "shift_dates":
                    connection.execute("UPDATE trips SET start_date=?,end_date=? WHERE id=?",
                                       (change["toStartDate"], change["toEndDate"], trip_id))
                elif kind == "add_stop":
                    stop = change["after"]
                    if preview["operation"]["action"] == "undo":
                        journal = json.loads(connection.execute("SELECT last_edit FROM trips WHERE id=?", (trip_id,)).fetchone()["last_edit"])
                        original = next(saved for saved in journal["snapshot"]["stops"] if saved["id"] == change["id"])
                        connection.execute("INSERT INTO trip_stops(id,trip_id,day,activity,notes,sort_order,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                                           (original["id"], trip_id, original["day"], original["activity"], original["notes"], original["sortOrder"], original["createdAt"], timestamp))
                    else:
                        insert_stop(connection, {**stop, "tripId": trip_id}, timestamp)
                elif kind == "remove_stop":
                    connection.execute("DELETE FROM trip_stops WHERE id=? AND trip_id=?", (change["id"], trip_id))
                elif kind == "update_stop":
                    stop = change["after"]
                    connection.execute("UPDATE trip_stops SET activity=?,notes=?,updated_at=? WHERE id=? AND trip_id=?",
                                       (stop["activity"], stop["notes"], timestamp, change["id"], trip_id))
                else:
                    connection.execute("UPDATE trip_stops SET day=?,sort_order=?,updated_at=? WHERE id=? AND trip_id=?",
                                       (change["toDay"], change["toOrder"], timestamp, change["id"], trip_id))
            connection.execute("UPDATE trips SET updated_at=? WHERE id=?", (timestamp, trip_id))
            last_edit = None if preview["operation"]["action"] == "undo" else json.dumps({
                "revision": revision(edit_snapshot(connection, trip_id)),
                "snapshot": {key: trip[key] for key in ("startDate", "endDate", "stops")},
            })
            connection.execute("UPDATE trips SET last_edit=? WHERE id=?", (last_edit, trip_id))
            connection.commit()
        return jsonify({"tripId": trip_id, "applied": True, "changes": changes})

    @app.put("/api/data/trips/<int:trip_id>")
    def update_trip(trip_id):
        fields, trip = validate_trip(request.get_json(silent=True) or {})
        if fields:
            return error("Check the trip details.", fields=fields)
        with closing(connect()) as connection:
            existing = connection.execute("SELECT id FROM trips WHERE id = ?", (trip_id,)).fetchone()
            if existing is None:
                return error("Trip not found.", 404)
            day_count = (date.fromisoformat(trip["endDate"]) - date.fromisoformat(trip["startDate"])).days + 1
            latest_stop_day = connection.execute(
                "SELECT MAX(day) FROM trip_stops WHERE trip_id = ?", (trip_id,)
            ).fetchone()[0]
            if latest_stop_day is not None and latest_stop_day > day_count:
                return error(
                    "Trip dates cannot exclude existing stops.",
                    fields={"endDate": f"Trip must include existing stop day {latest_stop_day}."},
                )
            cursor = connection.execute(
                "UPDATE trips SET user_name=?,destination=?,start_date=?,end_date=?,budget=?,interests=?,updated_at=? WHERE id=?",
                (trip["user"], trip["destination"], trip["startDate"], trip["endDate"], trip["budget"], trip["interests"], now(), trip_id),
            )
            connection.commit()
            row = connection.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)).fetchone()
        return jsonify(trip_dict(row))

    @app.delete("/api/data/trips/<int:trip_id>")
    def delete_trip(trip_id):
        with closing(connect()) as connection:
            cursor = connection.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
            connection.commit()
        if cursor.rowcount == 0:
            return error("Trip not found.", 404)
        return "", 204

    @app.post("/api/data/stops")
    def create_stop():
        fields, stop = validate_stop(request.get_json(silent=True) or {})
        if fields:
            return error("Check the stop details.", fields=fields)
        timestamp = now()
        with closing(connect()) as connection:
            trip_row = connection.execute(
                "SELECT start_date, end_date FROM trips WHERE id = ?", (stop["tripId"],)
            ).fetchone()
            if trip_row is None:
                return error("Trip not found.", 404)
            day_count = (date.fromisoformat(trip_row["end_date"]) - date.fromisoformat(trip_row["start_date"])).days + 1
            if stop["day"] > day_count:
                return error(
                    "Check the stop details.",
                    fields={"day": f"Day must be within the {day_count}-day trip."},
                )
            cursor = connection.execute(
                "INSERT INTO trip_stops(trip_id,day,activity,notes,sort_order,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                (stop["tripId"], stop["day"], stop["activity"], stop["notes"], stop["sortOrder"], timestamp, timestamp),
            )
            connection.commit()
            row = connection.execute("SELECT * FROM trip_stops WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return jsonify(stop_dict(row)), 201

    @app.put("/api/data/trips/<int:trip_id>/stops")
    def replace_trip_stops(trip_id):
        with closing(connect()) as connection:
            trip_row = connection.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)).fetchone()
            if trip_row is None:
                return error("Trip not found.", 404)
            trip = trip_dict(trip_row)
            day_count = (date.fromisoformat(trip["endDate"]) - date.fromisoformat(trip["startDate"])).days + 1
            fields, stops = validate_itinerary_stops((request.get_json(silent=True) or {}).get("stops"), trip_id, day_count)
            if fields:
                return error("Check the itinerary stops.", fields=fields)
            timestamp = now()
            connection.execute("DELETE FROM trip_stops WHERE trip_id = ?", (trip_id,))
            saved_stops = [insert_stop(connection, stop, timestamp) for stop in stops]
            connection.commit()
        return jsonify([stop_dict(stop) for stop in saved_stops])

    @app.get("/api/data/stops/<int:stop_id>")
    def get_stop(stop_id):
        with closing(connect()) as connection:
            row = connection.execute("SELECT * FROM trip_stops WHERE id = ?", (stop_id,)).fetchone()
        if row is None:
            return error("Stop not found.", 404)
        return jsonify(stop_dict(row))

    @app.put("/api/data/stops/<int:stop_id>")
    def update_stop(stop_id):
        with closing(connect()) as connection:
            existing = connection.execute("SELECT * FROM trip_stops WHERE id = ?", (stop_id,)).fetchone()
            if existing is None:
                return error("Stop not found.", 404)
            fields, stop = validate_stop({
                **(request.get_json(silent=True) or {}),
                "tripId": existing["trip_id"],
                "sortOrder": existing["sort_order"],
            })
            if fields:
                return error("Check the stop details.", fields=fields)
            trip_row = connection.execute(
                "SELECT start_date, end_date FROM trips WHERE id = ?", (existing["trip_id"],)
            ).fetchone()
            day_count = (date.fromisoformat(trip_row["end_date"]) - date.fromisoformat(trip_row["start_date"])).days + 1
            if stop["day"] > day_count:
                return error(
                    "Check the stop details.",
                    fields={"day": f"Day must be within the {day_count}-day trip."},
                )
            cursor = connection.execute(
                "UPDATE trip_stops SET day=?,activity=?,notes=?,sort_order=?,updated_at=? WHERE id=?",
                (stop["day"], stop["activity"], stop["notes"], stop["sortOrder"], now(), stop_id),
            )
            connection.commit()
            row = connection.execute("SELECT * FROM trip_stops WHERE id = ?", (stop_id,)).fetchone()
        return jsonify(stop_dict(row))

    @app.delete("/api/data/stops/<int:stop_id>")
    def delete_stop(stop_id):
        with closing(connect()) as connection:
            cursor = connection.execute("DELETE FROM trip_stops WHERE id = ?", (stop_id,))
            connection.commit()
        if cursor.rowcount == 0:
            return error("Stop not found.", 404)
        return "", 204

    initialise()
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))