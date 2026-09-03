"""Student 5 - Travel Logistics & Advisory Service: backend/API microservice.

This service is the middle tier of the stack. It owns no data of its own: the
frontend talks to it, and it talks to the database microservice over HTTP
(never to the SQLite file). Today it is a faithful JSON passthrough over the
database's CRUD API; the AI advisory endpoint and the HTML views are added in
later chunks at the extension points marked below.
"""

import os
from typing import Any, Optional

from flask import Blueprint, Flask, current_app, jsonify, request

from db_client import DatabaseClient, DatabaseResponse, DatabaseUnavailable

DEFAULT_DATABASE_API_URL = "http://student5-database:8080"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def db() -> DatabaseClient:
    """The database client built by create_app, from the active app context."""
    return current_app.config["DATABASE_CLIENT"]


def request_body() -> Any:
    """The decoded JSON request body, or None if there wasn't a valid one.

    We deliberately do not validate here. The database service already owns
    validation, so forwarding whatever the client sent (including nothing)
    means its 400 messages reach the caller unchanged instead of being
    second-guessed in two places.
    """
    return request.get_json(silent=True)


def relay(response: DatabaseResponse):
    """Translate a database-service reply into this service's HTTP response.

    Args:
        response: a DatabaseResponse -- ``status_code`` plus the decoded JSON
            ``payload``. ``payload`` is None when the database sent no JSON
            body, which is what a successful DELETE (204 No Content) looks
            like.

    Returns:
        A Flask return value: either ``(jsonify(...), status)`` or a
        ``(body, status)`` tuple for replies that must not carry a body.

    Policy: the status code is forwarded verbatim, including 4xx. The database
    owns validation and existence checks, so re-deciding those here would mean
    two sources of truth. Errors that originate in *this* service -- currently
    only an unreachable database -- are the ones that get a status of our own.
    """
    if response.payload is None:
        # A bodyless reply, i.e. the 204 from a successful DELETE. jsonify(None)
        # would emit the literal `null`, and a 204 must carry no body at all.
        return "", response.status_code
    return jsonify(response.payload), response.status_code


# ---------------------------------------------------------------------------
# JSON CRUD passthrough
#
# Shapes are identical to the database API on purpose, so the frontend can be
# pointed at either service. Extension point: new feature areas (the AI
# advisory endpoint, HTML views) should get their own blueprint rather than
# being bolted onto this one.
# ---------------------------------------------------------------------------

api = Blueprint("api", __name__, url_prefix="/api")


def _destination_filter() -> Optional[str]:
    """The raw ?destination_id= value, forwarded as-is for the database to validate."""
    return request.args.get("destination_id")


# -- destinations -----------------------------------------------------------


@api.get("/destinations")
def list_destinations():
    return relay(db().list_destinations(_destination_filter()))


@api.post("/destinations")
def create_destination():
    return relay(db().create_destination(request_body()))


@api.get("/destinations/<int:row_id>")
def get_destination(row_id: int):
    return relay(db().get_destination(row_id))


@api.put("/destinations/<int:row_id>")
def update_destination(row_id: int):
    return relay(db().update_destination(row_id, request_body()))


@api.delete("/destinations/<int:row_id>")
def delete_destination(row_id: int):
    return relay(db().delete_destination(row_id))


# -- weather notes ----------------------------------------------------------


@api.get("/weather-notes")
def list_weather_notes():
    return relay(db().list_weather_notes(_destination_filter()))


@api.post("/weather-notes")
def create_weather_note():
    return relay(db().create_weather_note(request_body()))


@api.get("/weather-notes/<int:row_id>")
def get_weather_note(row_id: int):
    return relay(db().get_weather_note(row_id))


@api.put("/weather-notes/<int:row_id>")
def update_weather_note(row_id: int):
    return relay(db().update_weather_note(row_id, request_body()))


@api.delete("/weather-notes/<int:row_id>")
def delete_weather_note(row_id: int):
    return relay(db().delete_weather_note(row_id))


# -- transit options --------------------------------------------------------


@api.get("/transit-options")
def list_transit_options():
    return relay(db().list_transit_options(_destination_filter()))


@api.post("/transit-options")
def create_transit_option():
    return relay(db().create_transit_option(request_body()))


@api.get("/transit-options/<int:row_id>")
def get_transit_option(row_id: int):
    return relay(db().get_transit_option(row_id))


@api.put("/transit-options/<int:row_id>")
def update_transit_option(row_id: int):
    return relay(db().update_transit_option(row_id, request_body()))


@api.delete("/transit-options/<int:row_id>")
def delete_transit_option(row_id: int):
    return relay(db().delete_transit_option(row_id))


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app(config: Optional[dict] = None) -> Flask:
    """Build the Flask app.

    Args:
        config: optional overrides applied after the environment defaults.
            Tests use this to inject a fake DATABASE_API_URL.
    """
    app = Flask(__name__)

    # Environment is read exactly once, here, rather than on every request.
    app.config["DATABASE_API_URL"] = os.environ.get(
        "DATABASE_API_URL", DEFAULT_DATABASE_API_URL
    )
    if config:
        app.config.update(config)

    app.config["DATABASE_CLIENT"] = DatabaseClient(app.config["DATABASE_API_URL"])

    @app.errorhandler(DatabaseUnavailable)
    def handle_database_unavailable(_exc):
        return jsonify({"error": "database service unavailable"}), 503

    @app.errorhandler(404)
    def handle_not_found(_exc):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(_exc):
        return jsonify({"error": "Method not allowed for this endpoint"}), 405

    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "service": "student5-backend"})

    app.register_blueprint(api)

    # Extension point: later chunks register the AI advisory blueprint and the
    # HTML view blueprint here.

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
