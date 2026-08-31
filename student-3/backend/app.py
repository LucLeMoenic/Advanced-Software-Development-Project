import logging

from flask import Flask, jsonify, request
from flask_cors import CORS

import database_client as db

logging.basicConfig(level=logging.INFO, format="%(message)s")

app = Flask(__name__)
CORS(app)  # Release 0: frontend and backend are served from different origins/ports.


@app.get("/")
def index():
    return jsonify({"service": "student3-backend", "status": "ready"})


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/api/attractions")
def list_attractions():
    category = request.args.get("category")
    try:
        return jsonify(db.list_attractions(category=category))
    except (db.DatabaseUnavailableError, db.DatabaseResponseError) as exc:
        return jsonify({"error": "database_unavailable", "message": str(exc)}), 502


@app.get("/api/attractions/<int:attraction_id>")
def get_attraction(attraction_id):
    try:
        attraction = db.get_attraction(attraction_id)
    except (db.DatabaseUnavailableError, db.DatabaseResponseError) as exc:
        return jsonify({"error": "database_unavailable", "message": str(exc)}), 502
    if attraction is None:
        return jsonify({"error": "not_found", "message": "Attraction not found."}), 404
    return jsonify(attraction)


@app.post("/api/attractions")
def create_attraction():
    payload = request.get_json(silent=True) or {}
    try:
        attraction, error = db.create_attraction(payload)
    except db.DatabaseUnavailableError as exc:
        return jsonify({"error": "database_unavailable", "message": str(exc)}), 502
    if error:
        return jsonify(error), 400
    return jsonify(attraction), 201


@app.put("/api/attractions/<int:attraction_id>")
def update_attraction(attraction_id):
    payload = request.get_json(silent=True) or {}
    try:
        attraction, error = db.update_attraction(attraction_id, payload)
    except db.DatabaseUnavailableError as exc:
        return jsonify({"error": "database_unavailable", "message": str(exc)}), 502
    if error == "not_found":
        return jsonify({"error": "not_found", "message": "Attraction not found."}), 404
    if error:
        return jsonify(error), 400
    return jsonify(attraction)


@app.delete("/api/attractions/<int:attraction_id>")
def delete_attraction(attraction_id):
    try:
        deleted = db.delete_attraction(attraction_id)
    except db.DatabaseUnavailableError as exc:
        return jsonify({"error": "database_unavailable", "message": str(exc)}), 502
    if not deleted:
        return jsonify({"error": "not_found", "message": "Attraction not found."}), 404
    return "", 204


@app.get("/api/reviews")
def list_reviews():
    attraction_id = request.args.get("attraction_id")
    try:
        return jsonify(db.list_reviews(attraction_id=attraction_id))
    except (db.DatabaseUnavailableError, db.DatabaseResponseError) as exc:
        return jsonify({"error": "database_unavailable", "message": str(exc)}), 502


@app.post("/api/reviews")
def create_review():
    payload = request.get_json(silent=True) or {}
    try:
        review, error = db.create_review(payload)
    except db.DatabaseUnavailableError as exc:
        return jsonify({"error": "database_unavailable", "message": str(exc)}), 502
    if error:
        return jsonify(error), 400
    return jsonify(review), 201


@app.post("/api/itinerary")
def add_to_itinerary():
    # Release 0 stub: full itinerary service/wiring lands in a later release.
    # hx-vals is sent as x-www-form-urlencoded by default, so accept both.
    payload = request.get_json(silent=True) or request.form.to_dict() or {}
    app.logger.info("Add-to-itinerary requested: %s", payload)
    return jsonify({"status": "logged", "received": payload}), 202


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
