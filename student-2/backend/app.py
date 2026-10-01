import json
import os
import re
from datetime import date
from pathlib import Path

import requests
from flask import Flask, g, jsonify, request

from ai_clients import IntegrationError, McpClient, RagClient, validate_advice, validate_overview, validate_summary
from itinerary_review import ItineraryEditor, ItineraryReviewer, ReviewModel


class DependencyError(Exception):
    pass


class DatabaseClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")

    def request(self, method, path, payload=None):
        try:
            response = requests.request(method, f"{self.base_url}{path}", json=payload, timeout=3)
        except requests.RequestException as exception:
            raise DependencyError("The itinerary database is unavailable.") from exception
        if response.status_code == 204:
            return None, 204
        try:
            body = response.json()
        except ValueError as exception:
            raise DependencyError("The itinerary database returned an invalid response.") from exception
        return body, response.status_code


class ItineraryGenerator:
    def __init__(self, ollama_url, model, prompt_path=None):
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        path = prompt_path or Path(__file__).parent / "prompts" / "itinerary-v1.txt"
        self.instructions = Path(path).read_text(encoding="utf-8")

    @staticmethod
    def output_schema(trip, target_day=None):
        day_count = (date.fromisoformat(trip["endDate"]) - date.fromisoformat(trip["startDate"])).days + 1
        stop_count = 1 if target_day is not None else day_count * 2
        return {
            "type": "array",
            "minItems": stop_count,
            "maxItems": stop_count,
            "items": {
                "type": "object",
                "properties": {
                    "day": {"type": "integer", "minimum": target_day or 1, "maximum": target_day or day_count},
                    "activity": {"type": "string", "minLength": 1, "maxLength": 160},
                    "notes": {"type": "string", "maxLength": 1000},
                },
                "required": ["day", "activity", "notes"],
                "additionalProperties": False,
            },
        }

    def generate(self, trip, existing_stops=None, target_day=None):
        context = {
            "trip": {key: trip[key] for key in ("destination", "startDate", "endDate", "budget", "interests")},
            "existingStops": existing_stops or [],
            "targetDay": target_day,
        }
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": f"{self.instructions}\nINPUT DATA:\n{json.dumps(context)}",
                    "stream": False,
                    "format": self.output_schema(trip, target_day),
                },
                timeout=20,
            )
            response.raise_for_status()
            output = json.loads(response.json()["response"])
            return self.validate(output, trip, target_day), "ai"
        except (requests.RequestException, ValueError, KeyError, TypeError):
            return self.fallback(trip, target_day), "fallback"

    @staticmethod
    def validate(output, trip, target_day=None):
        day_count = (date.fromisoformat(trip["endDate"]) - date.fromisoformat(trip["startDate"])).days + 1
        if not isinstance(output, list) or not output:
            raise ValueError("Itinerary must be a non-empty array.")
        cleaned = []
        for index, item in enumerate(output):
            if not isinstance(item, dict) or set(item) != {"day", "activity", "notes"}:
                raise ValueError("Invalid itinerary item.")
            day_number = item["day"]
            activity = item["activity"].strip() if isinstance(item["activity"], str) else ""
            notes = item["notes"].strip() if isinstance(item["notes"], str) else ""
            if not isinstance(day_number, int) or not 1 <= day_number <= day_count:
                raise ValueError("Invalid itinerary day.")
            if target_day is not None and day_number != target_day:
                raise ValueError("Regenerated stop uses the wrong day.")
            if not 1 <= len(activity) <= 160 or len(notes) > 1000:
                raise ValueError("Invalid itinerary text.")
            cleaned.append({"day": day_number, "activity": activity, "notes": notes, "sortOrder": index})
        expected_per_day = 1 if target_day is not None else 2
        expected_days = [target_day] if target_day is not None else range(1, day_count + 1)
        if any(sum(stop["day"] == day_number for stop in cleaned) != expected_per_day for day_number in expected_days):
            raise ValueError("Itinerary must contain the required stops for every day.")
        if len(cleaned) != len(list(expected_days)) * expected_per_day:
            raise ValueError("Itinerary contains unexpected stops.")
        return cleaned

    @staticmethod
    def fallback(trip, target_day=None):
        day_count = (date.fromisoformat(trip["endDate"]) - date.fromisoformat(trip["startDate"])).days + 1
        days = [target_day] if target_day is not None else range(1, day_count + 1)
        destination = trip["destination"]
        interests = trip["interests"] or "local highlights"
        stops = []
        for day_number in days:
            stops.append({"day": day_number, "activity": f"Explore {destination}'s central district", "notes": f"A flexible introduction shaped around {interests}.", "sortOrder": 0})
            if target_day is None:
                stops.append({"day": day_number, "activity": f"Discover a local {destination} neighbourhood", "notes": "Keep timing flexible and confirm local details before visiting.", "sortOrder": 1})
        return stops


def validate_trip(payload):
    fields = {}
    cleaned = {
        "user": str(payload.get("user", "")).strip(),
        "destination": str(payload.get("destination", "")).strip(),
        "startDate": str(payload.get("startDate", "")).strip(),
        "endDate": str(payload.get("endDate", "")).strip(),
        "interests": str(payload.get("interests", "")).strip(),
    }
    try:
        cleaned["budget"] = round(float(payload.get("budget", -1)), 2)
    except (TypeError, ValueError):
        cleaned["budget"] = -1
    if not 1 <= len(cleaned["user"]) <= 80:
        fields["user"] = "Enter a traveller name."
    if not 2 <= len(cleaned["destination"]) <= 100:
        fields["destination"] = "Destination must be 2-100 characters."
    try:
        start = date.fromisoformat(cleaned["startDate"])
        end = date.fromisoformat(cleaned["endDate"])
        if end < start:
            fields["endDate"] = "End date must be on or after the start date."
        if (end - start).days > 30:
            fields["endDate"] = "Trips may be at most 31 days."
    except ValueError:
        fields["dates"] = "Enter valid start and end dates."
    if not 0 <= cleaned["budget"] <= 1_000_000:
        fields["budget"] = "Budget must be between 0 and 1,000,000."
    if len(cleaned["interests"]) > 500:
        fields["interests"] = "Interests must be at most 500 characters."
    return fields, cleaned


def validate_stop(payload, trip_id=None):
    fields = {}
    try:
        cleaned = {
            "tripId": int(trip_id if trip_id is not None else payload.get("tripId", 0)),
            "day": int(payload.get("day", 0)),
            "sortOrder": int(payload.get("sortOrder", 0)),
            "activity": str(payload.get("activity", "")).strip(),
            "notes": str(payload.get("notes", "")).strip(),
        }
    except (TypeError, ValueError):
        return {"stop": "Stop fields use invalid values."}, {}
    if cleaned["tripId"] < 1:
        fields["tripId"] = "Trip ID must be positive."
    if not 1 <= cleaned["day"] <= 31:
        fields["day"] = "Day must be between 1 and 31."
    if not 1 <= len(cleaned["activity"]) <= 160:
        fields["activity"] = "Activity must be 1-160 characters."
    if len(cleaned["notes"]) > 1000:
        fields["notes"] = "Notes must be at most 1000 characters."
    if cleaned["sortOrder"] < 0:
        fields["sortOrder"] = "Sort order cannot be negative."
    return fields, cleaned


def create_app(database_client=None, generator=None, *, settings=None, mcp_client=None, rag_client=None, review_model=None):
    app = Flask(__name__)
    settings = settings or {}

    def enabled(name, default):
        value = settings.get(name, os.getenv(name, default))
        if isinstance(value, bool):
            return value
        if value not in ("true", "false"):
            raise ValueError(f"{name} must be true or false.")
        return value == "true"

    modes = {
        "aiEnabled": enabled("AI_ENABLED", "true"),
        "mcpEnabled": enabled("MCP_ENABLED", "false"),
        "ragEnabled": enabled("RAG_ENABLED", "false"),
    }
    mcp_client = mcp_client or McpClient(os.getenv("MCP_SERVER_URL", "http://host.docker.internal:5400/mcp"))
    rag_client = rag_client or RagClient(os.getenv("RAG_SERVER_URL", "http://host.docker.internal:5500"))
    reviewer = ItineraryReviewer(mcp_client, review_model or ReviewModel(
        os.getenv("OLLAMA_URL", "http://ollama:11434"), os.getenv("APPLICATION_MODEL", "llama3.2:3b")))
    editor = ItineraryEditor(mcp_client, reviewer.model)
    database = database_client or DatabaseClient(os.getenv("DATABASE_URL", "http://student2-database:8080"))
    itinerary_generator = generator or ItineraryGenerator(
        os.getenv("OLLAMA_URL", "http://ollama:11434"), os.getenv("APPLICATION_MODEL", "llama3.2:3b")
    )

    def generate(trip, existing_stops=None, target_day=None):
        if not modes["aiEnabled"]:
            return ItineraryGenerator.fallback(trip, target_day), "fallback"
        return itinerary_generator.generate(trip, existing_stops, target_day)

    def respond(body, status):
        return ("", 204) if status == 204 else (jsonify(body), status)

    def dependency_error(exception):
        return jsonify({"error": {"code": "dependency_unavailable", "message": str(exception), "fields": {}}}), 503

    def validate_stop_day(stop):
        trip, status = database.request("GET", f"/api/data/trips/{stop['tripId']}")
        if status != 200:
            return respond(trip, status)
        day_count = (date.fromisoformat(trip["endDate"]) - date.fromisoformat(trip["startDate"])).days + 1
        if stop["day"] > day_count:
            return jsonify({"error": {
                "code": "validation_error",
                "message": "Check the stop details.",
                "fields": {"day": f"Day must be within the {day_count}-day trip."},
            }}), 400
        return None

    @app.before_request
    def correlation_id():
        g.correlation_id = request.headers.get("X-Correlation-ID", os.urandom(8).hex())

    @app.after_request
    def add_correlation_id(response):
        response.headers["X-Correlation-ID"] = g.correlation_id
        return response

    @app.get("/health")
    def health():
        return jsonify({"status": "healthy"})

    @app.get("/api/capabilities")
    def capabilities():
        return jsonify(modes)

    @app.errorhandler(IntegrationError)
    def integration_error(exception):
        return jsonify({"error": {"code": exception.code, "message": exception.message, "fields": {}}}), exception.status

    def invalid_integration_input():
        return jsonify({"error": {"code": "validation_error", "message": "Check the request details.", "fields": {}}}), 400

    @app.post("/api/trips/<int:trip_id>/mcp-summary")
    def mcp_summary(trip_id):
        if not modes["mcpEnabled"]:
            raise IntegrationError("mode_disabled")
        if trip_id < 1 or (request.get_data() and request.get_json(silent=True) != {}):
            return invalid_integration_input()
        return jsonify({"tool": "itinerary.get_summary", "summary": validate_summary(mcp_client.summary(trip_id), trip_id)})

    @app.post("/api/trips/<int:trip_id>/review")
    def review_itinerary(trip_id):
        if not modes["mcpEnabled"] or not modes["aiEnabled"]:
            raise IntegrationError("mode_disabled")
        if request.content_length is not None and request.content_length > 8192:
            return invalid_integration_input()
        payload = request.get_json(silent=True)
        if trip_id < 1 or not isinstance(payload, dict) or set(payload) != {"question"}:
            return invalid_integration_input()
        question = payload["question"]
        if not isinstance(question, str) or not 1 <= len(question.strip()) <= 1000:
            return invalid_integration_input()
        return jsonify(reviewer.review(trip_id, question.strip()))

    @app.post("/api/trips/<int:trip_id>/edit-preview")
    def edit_preview(trip_id):
        if not modes["mcpEnabled"] or not modes["aiEnabled"]:
            raise IntegrationError("mode_disabled")
        payload = request.get_json(silent=True)
        if (request.content_length is not None and request.content_length > 8192) or trip_id < 1 or not isinstance(payload, dict) or set(payload) != {"question"}:
            return invalid_integration_input()
        question = payload["question"]
        if not isinstance(question, str) or not 1 <= len(question.strip()) <= 1000:
            return invalid_integration_input()
        return jsonify(editor.preview(trip_id, question.strip()))

    @app.post("/api/trips/<int:trip_id>/edit-operation-preview")
    def edit_operation_preview(trip_id):
        if not modes["mcpEnabled"] or not modes["aiEnabled"]:
            raise IntegrationError("mode_disabled")
        payload = request.get_json(silent=True)
        if (request.content_length is not None and request.content_length > 8192) or trip_id < 1 or not isinstance(payload, dict) or set(payload) != {"operation"}:
            return invalid_integration_input()
        return jsonify(editor.preview_operation(trip_id, payload["operation"]))

    @app.post("/api/trips/<int:trip_id>/edit-confirm")
    def edit_confirm(trip_id):
        if not modes["mcpEnabled"] or not modes["aiEnabled"]:
            raise IntegrationError("mode_disabled")
        payload = request.get_json(silent=True)
        if (request.content_length is not None and request.content_length > 8192) or trip_id < 1 or not isinstance(payload, dict) or set(payload) != {"token"}:
            return invalid_integration_input()
        if not isinstance(payload["token"], str) or not 1 <= len(payload["token"]) <= 4096:
            return invalid_integration_input()
        return jsonify(editor.apply(trip_id, payload["token"]))

    @app.post("/api/trips/<int:trip_id>/mcp-overview")
    def mcp_overview(trip_id):
        if not modes["mcpEnabled"]:
            raise IntegrationError("mode_disabled")
        if request.content_length is not None and request.content_length > 1024:
            return invalid_integration_input()
        payload = request.get_json(silent=True) if request.get_data() else {}
        if trip_id < 1 or not isinstance(payload, dict) or set(payload) - {"locationId"}:
            return invalid_integration_input()
        location_id = payload.get("locationId")
        if "locationId" in payload and (type(location_id) is not int or not 0 < location_id <= 2147483647):
            return invalid_integration_input()
        overview = validate_overview(mcp_client.overview(trip_id, location_id), trip_id, location_id)
        return jsonify({"tool": "itinerary.get_overview", **overview})

    @app.post("/api/itinerary-advice")
    def itinerary_advice():
        if not modes["ragEnabled"]:
            raise IntegrationError("mode_disabled")
        if request.content_length is not None and request.content_length > 8192:
            return invalid_integration_input()
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or "question" not in payload or set(payload) - {"question", "tripId"}:
            return invalid_integration_input()
        question = payload["question"]
        if not isinstance(question, str) or not 1 <= len(question.strip()) <= 1000:
            return invalid_integration_input()
        if "tripId" not in payload:
            return jsonify(validate_advice(rag_client.advice(question.strip())))
        trip_id = payload["tripId"]
        if type(trip_id) is not int or trip_id < 1:
            return invalid_integration_input()
        try:
            trip, status = database.request("GET", f"/api/data/trips/{trip_id}")
        except DependencyError as exception:
            return dependency_error(exception)
        if status != 200:
            return respond(trip, status)
        try:
            if not isinstance(trip, dict) or trip.get("id") != trip_id or not isinstance(trip.get("stops"), list):
                raise ValueError("Invalid trip")
            fields, cleaned = validate_trip(trip)
            if fields:
                raise ValueError("Invalid trip")
            context = {key: cleaned[key] for key in ("destination", "startDate", "endDate")}
            context["stops"] = []
            for stop in trip["stops"][:20]:
                if not isinstance(stop, dict) or stop.get("tripId") != trip_id:
                    raise ValueError("Invalid stop")
                fields, cleaned_stop = validate_stop(stop, trip_id)
                if fields or cleaned_stop["day"] > (date.fromisoformat(cleaned["endDate"]) - date.fromisoformat(cleaned["startDate"])).days + 1:
                    raise ValueError("Invalid stop")
                context["stops"].append({"day": cleaned_stop["day"], "activity": cleaned_stop["activity"], "notes": cleaned_stop["notes"][:160]})
            context["omittedStops"] = max(0, len(trip["stops"]) - 20)
        except (ValueError, TypeError, KeyError):
            raise IntegrationError("invalid_dependency_response") from None
        weather = None
        weather_related = bool(re.search(
            r"\b(?:weather|forecasts?|rain(?:y|ing|fall)?|showers?|thunderstorms?|storms?|"
            r"snow(?:y|ing|fall)?|temperatures?|precipitation|humidity|humid|wind(?:y)?|"
            r"sunny|sunshine|cloudy|heatwaves?|climate|freezing|celsius|fahrenheit)\b"
            r"|\b(?:how|too|very)\s+(?:hot|cold|wet)\b",
            question, re.IGNORECASE,
        ))
        weather_notice = "Weather context is unavailable because MCP is disabled." if weather_related else ""
        if weather_related and modes["mcpEnabled"]:
            try:
                overview = validate_overview(mcp_client.overview(trip_id), trip_id)
                if any(overview["summary"][key] != context[key] for key in ("destination", "startDate", "endDate")):
                    raise IntegrationError("stale_preview")
                weather = overview["weather"]
                weather_notice = ""
            except IntegrationError:
                weather_notice = "Weather could not be retrieved. Advice uses saved-plan context and knowledge-base guidance only."
        context["weather"] = None if weather is None else {
            "status": weather["status"], "location": ", ".join(filter(None, [weather["location"][key] for key in ("name", "admin1", "country")])) if weather["location"] else None,
            "retrievedAt": weather["retrievedAt"], "days": weather["days"],
        }
        result = validate_advice(rag_client.advice(question.strip(), context))
        return jsonify({**result, "tripId": trip_id, "weather": weather, "weatherNotice": weather_notice,
                        "contextNotice": f"Advice used {len(context['stops'])} saved stops; notes are limited to 160 characters. {context['omittedStops']} stops omitted."})

    @app.get("/api/trips")
    def list_trips():
        try:
            body, status = database.request("GET", "/api/data/trips")
            return respond(body, status)
        except DependencyError as exception:
            return dependency_error(exception)

    @app.post("/api/trips")
    def create_trip():
        fields, trip = validate_trip(request.get_json(silent=True) or {})
        if fields:
            return jsonify({"error": {"code": "validation_error", "message": "Check the trip details.", "fields": fields}}), 400
        try:
            stops, mode = generate(trip)
            saved_trip, status = database.request("POST", "/api/data/itineraries", {"trip": trip, "stops": stops})
            if status != 201:
                return respond(saved_trip, status)
            saved_trip["generationMode"] = mode
            saved_trip["agentTrace"] = [
                {"stage": "Plan", "outcome": "Validated trip constraints and day count."},
                {"stage": "Act", "outcome": f"Generated {len(saved_trip['stops'])} itinerary stops."},
                {"stage": "Observe", "outcome": "Checked day ranges, text limits, and persistence results."},
                {"stage": "Adapt", "outcome": "Used deterministic fallback." if mode == "fallback" else "Accepted validated AI output."},
            ]
            return jsonify(saved_trip), 201
        except DependencyError as exception:
            return dependency_error(exception)

    @app.get("/api/trips/<int:trip_id>")
    def get_trip(trip_id):
        try:
            body, status = database.request("GET", f"/api/data/trips/{trip_id}")
            return respond(body, status)
        except DependencyError as exception:
            return dependency_error(exception)

    @app.put("/api/trips/<int:trip_id>")
    def update_trip(trip_id):
        fields, trip = validate_trip(request.get_json(silent=True) or {})
        if fields:
            return jsonify({"error": {"code": "validation_error", "message": "Check the trip details.", "fields": fields}}), 400
        try:
            body, status = database.request("PUT", f"/api/data/trips/{trip_id}", trip)
            return respond(body, status)
        except DependencyError as exception:
            return dependency_error(exception)

    @app.delete("/api/trips/<int:trip_id>")
    def delete_trip(trip_id):
        try:
            body, status = database.request("DELETE", f"/api/data/trips/{trip_id}")
            return respond(body, status)
        except DependencyError as exception:
            return dependency_error(exception)

    @app.post("/api/trips/<int:trip_id>/stops")
    def add_stop(trip_id):
        fields, stop = validate_stop(request.get_json(silent=True) or {}, trip_id)
        if fields:
            return jsonify({"error": {"code": "validation_error", "message": "Check the stop details.", "fields": fields}}), 400
        try:
            invalid_day = validate_stop_day(stop)
            if invalid_day:
                return invalid_day
            body, status = database.request("POST", "/api/data/stops", stop)
            return respond(body, status)
        except DependencyError as exception:
            return dependency_error(exception)

    @app.put("/api/stops/<int:stop_id>")
    def update_stop(stop_id):
        try:
            existing, existing_status = database.request("GET", f"/api/data/stops/{stop_id}")
            if existing_status != 200:
                return respond(existing, existing_status)
            payload = {**(request.get_json(silent=True) or {}), "sortOrder": existing["sortOrder"]}
            fields, stop = validate_stop(payload, existing["tripId"])
            if fields:
                return jsonify({"error": {"code": "validation_error", "message": "Check the stop details.", "fields": fields}}), 400
            invalid_day = validate_stop_day(stop)
            if invalid_day:
                return invalid_day
            body, status = database.request("PUT", f"/api/data/stops/{stop_id}", stop)
            return respond(body, status)
        except DependencyError as exception:
            return dependency_error(exception)

    @app.delete("/api/stops/<int:stop_id>")
    def delete_stop(stop_id):
        try:
            body, status = database.request("DELETE", f"/api/data/stops/{stop_id}")
            return respond(body, status)
        except DependencyError as exception:
            return dependency_error(exception)

    @app.post("/api/stops/<int:stop_id>/regenerate")
    def regenerate_stop(stop_id):
        try:
            stop, stop_status = database.request("GET", f"/api/data/stops/{stop_id}")
            if stop_status != 200:
                return respond(stop, stop_status)
            trip, trip_status = database.request("GET", f"/api/data/trips/{stop['tripId']}")
            if trip_status != 200:
                return respond(trip, trip_status)
            generated, mode = generate(trip, trip.get("stops", []), stop["day"])
            replacement = {**generated[0], "tripId": stop["tripId"], "sortOrder": stop["sortOrder"]}
            saved, status = database.request("PUT", f"/api/data/stops/{stop_id}", replacement)
            if status != 200:
                return respond(saved, status)
            return jsonify({"stop": saved, "generationMode": mode})
        except DependencyError as exception:
            return dependency_error(exception)

    @app.post("/api/trips/<int:trip_id>/regenerate")
    def regenerate_trip(trip_id):
        try:
            trip, status = database.request("GET", f"/api/data/trips/{trip_id}")
            if status != 200:
                return respond(trip, status)
            stops, mode = generate(trip)
            saved, replace_status = database.request("PUT", f"/api/data/trips/{trip_id}/stops", {"stops": stops})
            if replace_status != 200:
                return respond(saved, replace_status)
            return jsonify({"stops": saved, "generationMode": mode})
        except DependencyError as exception:
            return dependency_error(exception)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))