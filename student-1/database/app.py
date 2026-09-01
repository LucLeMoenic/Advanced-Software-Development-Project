import os
import sqlite3
from contextlib import closing
from datetime import UTC, date, datetime, timedelta

from flask import Flask, jsonify, request


def create_app(database_path=None):
    app = Flask(__name__)
    app.config["DATABASE_PATH"] = database_path or os.getenv("DATABASE_PATH", "/data/itinerary.db")

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
            count = connection.execute("SELECT COUNT(*) FROM trips").fetchone()[0]
            if count == 0:
                destinations = ["Kyoto", "Lisbon", "Melbourne", "Seoul", "Edinburgh", "Hanoi", "Montreal", "Florence", "Auckland", "Copenhagen"]
                base = date.today() + timedelta(days=30)
                for index, destination in enumerate(destinations):
                    created = now()
                    cursor = connection.execute(
                        "INSERT INTO trips(user_name,destination,start_date,end_date,budget,interests,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                        ("Demo Traveller", destination, (base + timedelta(days=index)).isoformat(), (base + timedelta(days=index + 2)).isoformat(), 1200 + index * 150, "food, culture, walking", created, created),
                    )
                    for day_number in range(1, 3):
                        connection.execute(
                            "INSERT INTO trip_stops(trip_id,day,activity,notes,sort_order,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                            (cursor.lastrowid, day_number, f"Explore {destination} - day {day_number}", "Seeded demonstration stop", 0, created, created),
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

    @app.put("/api/data/trips/<int:trip_id>")
    def update_trip(trip_id):
        fields, trip = validate_trip(request.get_json(silent=True) or {})
        if fields:
            return error("Check the trip details.", fields=fields)
        with closing(connect()) as connection:
            cursor = connection.execute(
                "UPDATE trips SET user_name=?,destination=?,start_date=?,end_date=?,budget=?,interests=?,updated_at=? WHERE id=?",
                (trip["user"], trip["destination"], trip["startDate"], trip["endDate"], trip["budget"], trip["interests"], now(), trip_id),
            )
            connection.commit()
            row = connection.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)).fetchone()
        if cursor.rowcount == 0:
            return error("Trip not found.", 404)
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
        try:
            with closing(connect()) as connection:
                cursor = connection.execute(
                    "INSERT INTO trip_stops(trip_id,day,activity,notes,sort_order,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                    (stop["tripId"], stop["day"], stop["activity"], stop["notes"], stop["sortOrder"], timestamp, timestamp),
                )
                connection.commit()
                row = connection.execute("SELECT * FROM trip_stops WHERE id = ?", (cursor.lastrowid,)).fetchone()
        except sqlite3.IntegrityError:
            return error("Trip not found.", 404)
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
        fields, stop = validate_stop(request.get_json(silent=True) or {})
        if fields:
            return error("Check the stop details.", fields=fields)
        with closing(connect()) as connection:
            cursor = connection.execute(
                "UPDATE trip_stops SET trip_id=?,day=?,activity=?,notes=?,sort_order=?,updated_at=? WHERE id=?",
                (stop["tripId"], stop["day"], stop["activity"], stop["notes"], stop["sortOrder"], now(), stop_id),
            )
            connection.commit()
            row = connection.execute("SELECT * FROM trip_stops WHERE id = ?", (stop_id,)).fetchone()
        if cursor.rowcount == 0:
            return error("Stop not found.", 404)
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