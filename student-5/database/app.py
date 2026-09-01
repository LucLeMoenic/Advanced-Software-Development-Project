"""Student 5 - Travel Logistics & Advisory Service: database microservice.

A small Flask application that owns the SQLite database for the travel
logistics service and exposes it to the rest of the stack as a JSON API.
Only this service talks to SQLite directly; the backend service consumes
these HTTP endpoints.
"""

import os
import sqlite3

from flask import Flask, g, jsonify, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")
SEED_PATH = os.path.join(BASE_DIR, "seed.sql")
DEFAULT_DATABASE_PATH = "/data/logistics.db"

# Table metadata. These names are hard coded constants and are never taken from
# request data, which is why it is safe to interpolate them into SQL strings
# below. Values are always passed as bound parameters.
REQUIRED_FIELDS = {
    "destinations": ("country", "visa_requirement"),
    "weather_notes": ("destination_id", "season", "notes"),
    "transit_options": ("destination_id", "type", "details"),
}

# Every column a client is allowed to write, in the order used for INSERT.
WRITABLE_FIELDS = {
    "destinations": ("country", "visa_requirement", "notes"),
    "weather_notes": ("destination_id", "season", "notes"),
    "transit_options": ("destination_id", "type", "details"),
}


class ValidationError(Exception):
    """Raised when a request body fails validation. Maps to HTTP 400."""


# ---------------------------------------------------------------------------
# Database plumbing
# ---------------------------------------------------------------------------


def connect(database_path):
    """Open a SQLite connection that returns dict-like rows and enforces FKs.

    SQLite disables foreign key enforcement by default and the setting is
    per-connection, so ON DELETE CASCADE only works if we set it every time.
    """
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(database_path):
    """Create the schema if needed and seed only when destinations is empty."""
    directory = os.path.dirname(os.path.abspath(database_path))
    os.makedirs(directory, exist_ok=True)

    with open(SCHEMA_PATH, encoding="utf-8") as handle:
        schema_sql = handle.read()

    connection = connect(database_path)
    try:
        connection.executescript(schema_sql)
        already_seeded = connection.execute(
            "SELECT COUNT(*) FROM destinations"
        ).fetchone()[0]
        if not already_seeded:
            with open(SEED_PATH, encoding="utf-8") as handle:
                connection.executescript(handle.read())
        connection.commit()
    finally:
        connection.close()


def get_db():
    """Return the request-scoped connection, opening one on first use."""
    if "db" not in g:
        g.db = connect(g.database_path)
    return g.db


def rows_to_list(rows):
    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def read_json_body():
    """Return the request body as a dict, or raise ValidationError."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object")
    return payload


def clean_text(field, value):
    """Reject values that are missing, not a string, or only whitespace."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"Field '{field}' must be a non-empty string")
    return value.strip()


def clean_destination_id(value):
    """Validate destination_id is an int that points at a real destination."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("Field 'destination_id' must be an integer")
    exists = get_db().execute(
        "SELECT 1 FROM destinations WHERE id = ?", (value,)
    ).fetchone()
    if exists is None:
        raise ValidationError(f"destination_id {value} does not exist")
    return value


def clean_field(table, field, value):
    """Normalise and validate a single column value for the given table."""
    if field == "destination_id":
        return clean_destination_id(value)
    if field == "notes" and table == "destinations":
        # destinations.notes is the one nullable column in the schema.
        if value is None:
            return None
        return clean_text(field, value)
    return clean_text(field, value)


def build_insert_values(table, payload):
    """Validate a POST body and return {column: value} ready to insert."""
    missing = [f for f in REQUIRED_FIELDS[table] if f not in payload]
    if missing:
        raise ValidationError(f"Missing required field(s): {', '.join(missing)}")

    values = {}
    for field in WRITABLE_FIELDS[table]:
        if field in payload:
            values[field] = clean_field(table, field, payload[field])
        else:
            values[field] = None
    return values


def build_update_values(table, existing, payload):
    """Validate a PUT body and return the full {column: value} row to store.

    Args:
        table: one of "destinations", "weather_notes", "transit_options".
        existing: dict of the row currently in the database.
        payload: the decoded JSON request body sent by the client.

    Returns:
        A dict containing every column in WRITABLE_FIELDS[table] mapped to the
        value that should be written back to the database.

    Raises:
        ValidationError: if any supplied value is invalid.

    Semantics: partial merge. Columns the client omits keep their current
    value, so the backend service can update a single field without having to
    re-send the whole row. Required fields therefore cannot go missing, because
    the stored row already satisfies them.
    """
    values = {}
    for field in WRITABLE_FIELDS[table]:
        if field in payload:
            values[field] = clean_field(table, field, payload[field])
        else:
            values[field] = existing[field]
    return values


# ---------------------------------------------------------------------------
# Generic CRUD handlers (shared by all three resources)
# ---------------------------------------------------------------------------


def error(message, status):
    return jsonify({"error": message}), status


def fetch_row(table, row_id):
    return get_db().execute(
        f"SELECT * FROM {table} WHERE id = ?", (row_id,)  # noqa: S608 - fixed name
    ).fetchone()


def list_resource(table, allow_filter):
    """GET collection, optionally filtered by ?destination_id=<int>."""
    sql = f"SELECT * FROM {table}"  # noqa: S608 - table name is a constant
    params = ()

    raw_filter = request.args.get("destination_id")
    if allow_filter and raw_filter is not None:
        try:
            destination_id = int(raw_filter)
        except ValueError:
            return error("Query parameter 'destination_id' must be an integer", 400)
        sql += " WHERE destination_id = ?"
        params = (destination_id,)

    sql += " ORDER BY id"
    return jsonify(rows_to_list(get_db().execute(sql, params).fetchall()))


def get_resource(table, row_id):
    row = fetch_row(table, row_id)
    if row is None:
        return error(f"No {table} row with id {row_id}", 404)
    return jsonify(dict(row))


def create_resource(table):
    values = build_insert_values(table, read_json_body())
    columns = ", ".join(values)
    placeholders = ", ".join("?" for _ in values)

    db = get_db()
    cursor = db.execute(
        f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",  # noqa: S608
        tuple(values.values()),
    )
    db.commit()
    return jsonify(dict(fetch_row(table, cursor.lastrowid))), 201


def update_resource(table, row_id):
    existing = fetch_row(table, row_id)
    if existing is None:
        return error(f"No {table} row with id {row_id}", 404)

    values = build_update_values(table, dict(existing), read_json_body())
    assignments = ", ".join(f"{column} = ?" for column in values)

    db = get_db()
    db.execute(
        f"UPDATE {table} SET {assignments} WHERE id = ?",  # noqa: S608
        tuple(values.values()) + (row_id,),
    )
    db.commit()
    return jsonify(dict(fetch_row(table, row_id)))


def delete_resource(table, row_id):
    db = get_db()
    cursor = db.execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))  # noqa: S608
    db.commit()
    if cursor.rowcount == 0:
        return error(f"No {table} row with id {row_id}", 404)
    return "", 204


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app(database_path=None):
    app = Flask(__name__)
    app.config["DATABASE_PATH"] = database_path or os.environ.get(
        "DATABASE_PATH", DEFAULT_DATABASE_PATH
    )

    init_db(app.config["DATABASE_PATH"])

    @app.before_request
    def attach_database_path():
        g.database_path = app.config["DATABASE_PATH"]

    @app.teardown_appcontext
    def close_db(_exception):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.errorhandler(ValidationError)
    def handle_validation_error(exc):
        return error(str(exc), 400)

    @app.errorhandler(404)
    def handle_not_found(_exc):
        return error("Resource not found", 404)

    @app.errorhandler(405)
    def handle_method_not_allowed(_exc):
        return error("Method not allowed for this endpoint", 405)

    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "service": "student5-database"})

    # -- destinations -------------------------------------------------------
    @app.get("/api/destinations")
    def list_destinations():
        return list_resource("destinations", allow_filter=False)

    @app.post("/api/destinations")
    def create_destination():
        return create_resource("destinations")

    @app.get("/api/destinations/<int:row_id>")
    def get_destination(row_id):
        return get_resource("destinations", row_id)

    @app.put("/api/destinations/<int:row_id>")
    def update_destination(row_id):
        return update_resource("destinations", row_id)

    @app.delete("/api/destinations/<int:row_id>")
    def delete_destination(row_id):
        return delete_resource("destinations", row_id)

    # -- weather notes ------------------------------------------------------
    @app.get("/api/weather-notes")
    def list_weather_notes():
        return list_resource("weather_notes", allow_filter=True)

    @app.post("/api/weather-notes")
    def create_weather_note():
        return create_resource("weather_notes")

    @app.get("/api/weather-notes/<int:row_id>")
    def get_weather_note(row_id):
        return get_resource("weather_notes", row_id)

    @app.put("/api/weather-notes/<int:row_id>")
    def update_weather_note(row_id):
        return update_resource("weather_notes", row_id)

    @app.delete("/api/weather-notes/<int:row_id>")
    def delete_weather_note(row_id):
        return delete_resource("weather_notes", row_id)

    # -- transit options ----------------------------------------------------
    @app.get("/api/transit-options")
    def list_transit_options():
        return list_resource("transit_options", allow_filter=True)

    @app.post("/api/transit-options")
    def create_transit_option():
        return create_resource("transit_options")

    @app.get("/api/transit-options/<int:row_id>")
    def get_transit_option(row_id):
        return get_resource("transit_options", row_id)

    @app.put("/api/transit-options/<int:row_id>")
    def update_transit_option(row_id):
        return update_resource("transit_options", row_id)

    @app.delete("/api/transit-options/<int:row_id>")
    def delete_transit_option(row_id):
        return delete_resource("transit_options", row_id)

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
