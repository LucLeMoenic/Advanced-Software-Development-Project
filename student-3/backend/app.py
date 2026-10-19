import logging
import re

from flask import Flask, jsonify, request
from flask_cors import CORS

import agent_evidence
import database_client as db
import mcp_client
import multi_agent_client
import rag_client
from recommend import get_recommendation

logging.basicConfig(level=logging.INFO, format="%(message)s")

# Second boundary on top of the MCP server's own tool registration: even if
# the shared server later exposes more student-3 tools, this backend only
# ever invokes the ones explicitly allow-listed here.
ALLOWED_MCP_TOOLS = {"attractions.search", "attractions.get_reviews"}

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


@app.post("/api/recommend")
def recommend():
    # HTMX forms POST as x-www-form-urlencoded by default, so accept both.
    payload = request.get_json(silent=True) or request.form.to_dict() or {}
    interest_text = (payload.get("interest") or "").strip()
    if not interest_text:
        return jsonify({"error": "validation_error", "message": "interest is required."}), 400
    return jsonify(get_recommendation(interest_text))


@app.post("/api/itinerary")
def add_to_itinerary():
    # Release 0 stub: full itinerary service/wiring lands in a later release.
    # hx-vals is sent as x-www-form-urlencoded by default, so accept both.
    payload = request.get_json(silent=True) or request.form.to_dict() or {}
    app.logger.info("Add-to-itinerary requested: %s", payload)
    return jsonify({"status": "logged", "received": payload}), 202


@app.get("/api/mcp/tools")
def list_mcp_tools():
    try:
        tools = mcp_client.list_tools()
    except mcp_client.McpDisabledError:
        return jsonify({"error": "mcp_disabled", "message": "MCP is disabled."}), 503
    except (mcp_client.McpUnavailableError, mcp_client.McpResponseError) as exc:
        return jsonify({"error": "mcp_unavailable", "message": str(exc)}), 502
    return jsonify({"tools": tools})


@app.post("/api/mcp/invoke")
def invoke_mcp_tool():
    # hx-vals is sent as x-www-form-urlencoded by default, so accept both.
    payload = request.get_json(silent=True) or request.form.to_dict() or {}
    tool = payload.get("tool")
    arguments = payload.get("arguments", {})
    if tool not in ALLOWED_MCP_TOOLS:
        return jsonify({
            "error": "validation_error",
            "message": f"tool must be one of {sorted(ALLOWED_MCP_TOOLS)}.",
        }), 400
    if not isinstance(arguments, dict):
        return jsonify({"error": "validation_error", "message": "arguments must be an object."}), 400

    try:
        result = mcp_client.call_tool(tool, arguments)
    except mcp_client.McpDisabledError:
        return jsonify({"error": "mcp_disabled", "message": "MCP is disabled."}), 503
    except mcp_client.McpToolError as exc:
        return jsonify({"error": "validation_error", "message": str(exc)}), 400
    except (mcp_client.McpUnavailableError, mcp_client.McpResponseError) as exc:
        return jsonify({"error": "mcp_unavailable", "message": str(exc)}), 502
    return jsonify({"tool": tool, "result": result})


@app.post("/api/rag/ask")
def rag_ask():
    # hx-vals is sent as x-www-form-urlencoded by default, so accept both.
    payload = request.get_json(silent=True) or request.form.to_dict() or {}
    question = (payload.get("question") or "").strip()
    if not question:
        return jsonify({"error": "validation_error", "message": "question is required."}), 400

    try:
        result = rag_client.ask(question)
    except rag_client.RagDisabledError:
        return jsonify({"error": "rag_disabled", "message": "RAG is disabled."}), 503
    except (rag_client.RagUnavailableError, rag_client.RagResponseError) as exc:
        return jsonify({"error": "rag_unavailable", "message": str(exc)}), 502
    return jsonify(result)


# --- Release 2: shared Multi-Agent Server (Planner -> Worker -> Reviewer -> human) ---------------
# Disabled unless MULTI_AGENT_ENABLED=true. This backend, not the browser, chooses the evidence the
# agents may use (the catalogue), and relays the human reviewer's decision.

AGENT_WORKFLOW_ID = re.compile(r"^wf-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")
AGENT_CATEGORIES = {"sight", "restaurant", "activity"}
AGENT_DECISION_FIELDS = {"decision", "notes", "corrected_output", "accepted_item_ids"}


def _agent_error(exc):
    """Map a multi_agent_client exception to a JSON error response."""
    if isinstance(exc, multi_agent_client.MultiAgentDisabledError):
        return jsonify({"error": "multi_agent_disabled", "message": "Multi-Agent is disabled."}), 503
    if isinstance(exc, multi_agent_client.MultiAgentUnavailableError):
        return jsonify({"error": "multi_agent_unavailable",
                        "message": "The Multi-Agent Server is not reachable."}), 502
    # The server answered with its own error: keep its code and any status the UI can act on.
    status = exc.status if exc.status in {400, 404, 409, 503} else 502
    return jsonify({"error": exc.code, "message": str(exc)}), status


@app.get("/api/agents/status")
def agents_status():
    try:
        return jsonify(multi_agent_client.health())
    except (multi_agent_client.MultiAgentDisabledError, multi_agent_client.MultiAgentUnavailableError,
            multi_agent_client.MultiAgentResponseError) as exc:
        return _agent_error(exc)


@app.post("/api/agents/workflows")
def start_agent_workflow():
    payload = request.get_json(silent=True) or request.form.to_dict() or {}
    task = (payload.get("task") or "").strip()
    category = payload.get("category") or None
    if not 3 <= len(task) <= 500:
        return jsonify({"error": "validation_error", "message": "task must be 3 to 500 characters."}), 400
    if category is not None and category not in AGENT_CATEGORIES:
        return jsonify({"error": "validation_error",
                        "message": f"category must be one of {sorted(AGENT_CATEGORIES)}."}), 400

    try:
        multi_agent_client.require_enabled()  # fail fast, before any database work
        attractions = db.list_attractions(category=category)
        reviews = db.list_reviews()
    except multi_agent_client.MultiAgentDisabledError as exc:
        return _agent_error(exc)
    except (db.DatabaseUnavailableError, db.DatabaseResponseError) as exc:
        return jsonify({"error": "database_unavailable", "message": str(exc)}), 502

    evidence = agent_evidence.build_evidence(attractions, reviews)
    if not evidence:
        return jsonify({"error": "no_evidence",
                        "message": "There are no attractions to plan from for that category."}), 400

    try:
        started = multi_agent_client.start_workflow(task, evidence)
    except (multi_agent_client.MultiAgentDisabledError, multi_agent_client.MultiAgentUnavailableError,
            multi_agent_client.MultiAgentResponseError) as exc:
        return _agent_error(exc)
    return jsonify({**started, "evidence_count": len(evidence)}), 202


@app.get("/api/agents/workflows/<workflow_id>")
def get_agent_workflow(workflow_id):
    if not AGENT_WORKFLOW_ID.match(workflow_id):
        return jsonify({"error": "not_found", "message": "Workflow not found."}), 404
    try:
        return jsonify(multi_agent_client.get_workflow(workflow_id))
    except (multi_agent_client.MultiAgentDisabledError, multi_agent_client.MultiAgentUnavailableError,
            multi_agent_client.MultiAgentResponseError) as exc:
        return _agent_error(exc)


@app.post("/api/agents/workflows/<workflow_id>/decision")
def decide_agent_workflow(workflow_id):
    if not AGENT_WORKFLOW_ID.match(workflow_id):
        return jsonify({"error": "not_found", "message": "Workflow not found."}), 404
    payload = request.get_json(silent=True) or {}
    if payload.get("decision") not in {"approve", "correct", "partial", "reject"}:
        return jsonify({"error": "validation_error",
                        "message": "decision must be approve, correct, partial or reject."}), 400
    # Only relay known fields; the reviewer identity is fixed by this backend, not chosen by the browser.
    decision = {k: v for k, v in payload.items() if k in AGENT_DECISION_FIELDS}
    decision["decided_by"] = "student-3-ui"
    try:
        return jsonify(multi_agent_client.decide(workflow_id, decision))
    except (multi_agent_client.MultiAgentDisabledError, multi_agent_client.MultiAgentUnavailableError,
            multi_agent_client.MultiAgentResponseError) as exc:
        return _agent_error(exc)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
