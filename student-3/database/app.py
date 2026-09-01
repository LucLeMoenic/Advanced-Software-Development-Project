from flask import Flask, jsonify, request

from db import ensure_schema, get_connection

app = Flask(__name__)
ensure_schema()


def row_to_attraction(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "description": row["description"],
        "rating": row["rating"],
    }


def row_to_review(row):
    return {
        "id": row["id"],
        "attraction_id": row["attraction_id"],
        "rating": row["rating"],
        "comment": row["comment"],
    }


@app.get("/")
def index():
    return jsonify({"service": "student3-database", "status": "ready", "provider": "sqlite"})


@app.get("/health")
def health():
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as exc:  # pragma: no cover - defensive, exercised via container healthcheck
        return jsonify({"status": "error", "detail": str(exc)}), 503


@app.get("/api/data/attractions")
def list_attractions():
    category = request.args.get("category")
    conn = get_connection()
    try:
        if category:
            rows = conn.execute(
                "SELECT * FROM attractions WHERE category = ? ORDER BY id", (category,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM attractions ORDER BY id").fetchall()
        return jsonify([row_to_attraction(r) for r in rows])
    finally:
        conn.close()


@app.get("/api/data/attractions/<int:attraction_id>")
def get_attraction(attraction_id):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM attractions WHERE id = ?", (attraction_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "not_found", "message": "Attraction not found."}), 404

        review_rows = conn.execute(
            "SELECT * FROM reviews WHERE attraction_id = ? ORDER BY id", (attraction_id,)
        ).fetchall()
        result = row_to_attraction(row)
        result["reviews"] = [row_to_review(r) for r in review_rows]
        return jsonify(result)
    finally:
        conn.close()


@app.post("/api/data/attractions")
def create_attraction():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    category = (body.get("category") or "").strip()
    if not name or not category:
        return jsonify({"error": "validation_error", "message": "name and category are required."}), 400

    description = body.get("description")
    rating = body.get("rating")

    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO attractions (name, category, description, rating) VALUES (?, ?, ?, ?)",
            (name, category, description, rating),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM attractions WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return jsonify(row_to_attraction(row)), 201
    finally:
        conn.close()


@app.put("/api/data/attractions/<int:attraction_id>")
def update_attraction(attraction_id):
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    category = (body.get("category") or "").strip()
    if not name or not category:
        return jsonify({"error": "validation_error", "message": "name and category are required."}), 400

    description = body.get("description")
    rating = body.get("rating")

    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM attractions WHERE id = ?", (attraction_id,)
        ).fetchone()
        if existing is None:
            return jsonify({"error": "not_found", "message": "Attraction not found."}), 404

        conn.execute(
            "UPDATE attractions SET name = ?, category = ?, description = ?, rating = ? WHERE id = ?",
            (name, category, description, rating, attraction_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM attractions WHERE id = ?", (attraction_id,)
        ).fetchone()
        return jsonify(row_to_attraction(row))
    finally:
        conn.close()


@app.delete("/api/data/attractions/<int:attraction_id>")
def delete_attraction(attraction_id):
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM attractions WHERE id = ?", (attraction_id,)
        ).fetchone()
        if existing is None:
            return jsonify({"error": "not_found", "message": "Attraction not found."}), 404

        conn.execute("DELETE FROM reviews WHERE attraction_id = ?", (attraction_id,))
        conn.execute("DELETE FROM attractions WHERE id = ?", (attraction_id,))
        conn.commit()
        return "", 204
    finally:
        conn.close()


@app.get("/api/data/reviews")
def list_reviews():
    attraction_id = request.args.get("attraction_id")
    conn = get_connection()
    try:
        if attraction_id:
            rows = conn.execute(
                "SELECT * FROM reviews WHERE attraction_id = ? ORDER BY id", (attraction_id,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM reviews ORDER BY id").fetchall()
        return jsonify([row_to_review(r) for r in rows])
    finally:
        conn.close()


@app.post("/api/data/reviews")
def create_review():
    body = request.get_json(silent=True) or {}
    attraction_id = body.get("attraction_id")
    if not isinstance(attraction_id, int):
        return jsonify({"error": "validation_error", "message": "attraction_id is required."}), 400

    rating = body.get("rating")
    comment = body.get("comment")

    conn = get_connection()
    try:
        attraction = conn.execute(
            "SELECT id FROM attractions WHERE id = ?", (attraction_id,)
        ).fetchone()
        if attraction is None:
            return jsonify({"error": "validation_error", "message": "attraction_id does not exist."}), 400

        cursor = conn.execute(
            "INSERT INTO reviews (attraction_id, rating, comment) VALUES (?, ?, ?)",
            (attraction_id, rating, comment),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM reviews WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return jsonify(row_to_review(row)), 201
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
