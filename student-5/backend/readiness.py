"""Release 2 trip readiness review: Student 5 on the shared Multi-Agent Server.

Marked requirement: Frontend -> Backend/API -> Multi-Agent Server -> Planner ->
Worker -> Reviewer -> Human Review -> frontend response. No agent runs here.
This module builds the evidence from the database service, hands it to the
shared server, and relays its record and the human decision back.

The server never reads application data, so the evidence below is the whole
of what the agents know. Two properties matter:

* **Bounded.** At most ``MAX_ROWS`` weather notes and transit options each,
  every text clipped to ``MAX_TEXT_LENGTH``, and the entry-requirement item
  says how many rows were supplied, so a long destination is a shorter review
  rather than a rejected one.
* **Distinctive titles.** The server's deterministic checks (``checks.py``)
  fail a Worker item whose subject does not match the title of the evidence it
  cites, using a substring test. So no title may be a substring of another, or
  an item could cite the wrong record and still pass.

A workflow is tied to its destination by its first evidence item, whose id is
``destination-<id>``. The server stores no other link, so every poll and
decision checks that item before anything is shown or written.

JSON contract (honest status codes, like ``integrations``):

    POST /api/destinations/<id>/readiness-reviews        -> 202 {"id", "status", "destination_id"}
    GET  /api/readiness-reviews/<wid>?destination_id=<id> -> 200 workflow record
    POST /api/readiness-reviews/<wid>/decision
         {"destination_id", "decision", "notes"?, "decided_by"?,
          "corrected_output"?, "accepted_item_ids"?}       -> 200 updated record

    400 {"error": "invalid_request" | <server decision code>}
    404 {"error": "review_not_found"}   (also: another feature's or destination's workflow)
    409 {"error": "review_not_awaiting_decision"}
    502 {"error": "multi_agent_unavailable"}
    503 {"error": "multi_agent_disabled" | "multi_agent_busy"}
"""

from typing import Any, Dict, List

from flask import Blueprint, current_app, jsonify, request

from advisory import AdvisoryContext, DestinationNotFound, load_context, parse_destination_id
from db_client import DatabaseUnavailable
from integrations import InvalidRequest
from multi_agent_client import (
    DECISIONS,
    MultiAgentClient,
    MultiAgentDisabled,
    MultiAgentRefused,
    MultiAgentUnavailable,
    review_not_found,
)

readiness_bp = Blueprint("readiness", __name__, url_prefix="/api")

MAX_ROWS = 6
MAX_TEXT_LENGTH = 400
MAX_LABEL_LENGTH = 50
MAX_COUNTRY_LENGTH = 40
# Fields a decision may carry to the server; anything else stays here.
DECISION_FIELDS = ("decision", "notes", "decided_by", "corrected_output", "accepted_item_ids")

TASK = (
    "Trip readiness review for {country}. Write a pre-departure checklist from the "
    "supplied records only: the entry requirement and documents to prepare, what to "
    "pack for each recorded season, and how to get around with each recorded transit "
    "option. One item per record. Where a record is missing or a rule must be "
    "confirmed, say to check Smartraveller or the official source."
)


def multi_agent() -> MultiAgentClient:
    return current_app.config["MULTI_AGENT_CLIENT"]


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------


def _clip(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _rows(rows: Any) -> List[dict]:
    """Child rows sorted by id. A non-list reply means the database misbehaved."""
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise DatabaseUnavailable("unexpected child-row reply")
    return sorted(rows, key=lambda row: row.get("id") or 0)


def _norm(title: str) -> str:
    # Same normalisation as the server's checks.py.
    return " ".join(title.lower().split())


def distinct_titles(evidence: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Suffix any title that contains, or is contained in, another one.

    Two transit options of the same type, or a season label that extends
    another ("Spring" / "Spring (Mar-May)"), would otherwise pass the server's
    substring subject check for each other. The suffix is the evidence id in
    brackets, which is unique and closed, so suffixed titles cannot overlap.
    """
    titles = [_norm(item["title"]) for item in evidence]
    clashing = {
        i for i, title in enumerate(titles)
        if any(j != i and (title in other or other in title) for j, other in enumerate(titles))
    }
    return [
        {**item, "title": "{} [{}]".format(item["title"], item["id"])} if i in clashing else item
        for i, item in enumerate(evidence)
    ]


def build_evidence(destination_id: int, context: AdvisoryContext) -> List[Dict[str, str]]:
    """One evidence item per stored record for one destination, bounded."""
    destination = context.destination
    country = _clip(destination.get("country"), MAX_COUNTRY_LENGTH)
    weather, transit = _rows(context.weather_notes), _rows(context.transit_options)

    supplied = "Records supplied: {} of {} weather notes, {} of {} transit options.".format(
        min(len(weather), MAX_ROWS), len(weather), min(len(transit), MAX_ROWS), len(transit))
    entry = "Visa requirement on record: {}. Entry notes: {}".format(
        destination.get("visa_requirement"), destination.get("notes") or "none recorded.")
    # The supplied count goes first so clipping long notes can never drop it.
    evidence = [{
        "id": "destination-{}".format(destination_id),
        "title": "{} — entry requirement".format(country),
        "text": _clip(supplied + " " + entry, MAX_TEXT_LENGTH),
    }]

    for note in weather[:MAX_ROWS]:
        evidence.append({
            "id": "weather-{}".format(note.get("id")),
            "title": "{} — weather: {}".format(country, _clip(note.get("season"), MAX_LABEL_LENGTH)),
            "text": _clip("Season: {}. {}".format(note.get("season"), note.get("notes")), MAX_TEXT_LENGTH),
        })
    if not weather:
        evidence.append({
            "id": "weather-none",
            "title": "{} — weather: none recorded".format(country),
            "text": "No weather notes are recorded for {}.".format(country),
        })

    for option in transit[:MAX_ROWS]:
        evidence.append({
            "id": "transit-{}".format(option.get("id")),
            "title": "{} — transit: {}".format(country, _clip(option.get("type"), MAX_LABEL_LENGTH)),
            "text": _clip("Transit type: {}. {}".format(option.get("type"), option.get("details")), MAX_TEXT_LENGTH),
        })
    if not transit:
        evidence.append({
            "id": "transit-none",
            "title": "{} — transit: none recorded".format(country),
            "text": "No transit options are recorded for {}.".format(country),
        })

    return distinct_titles(evidence)


def task_for(destination: dict) -> str:
    return TASK.format(country=_clip(destination.get("country"), MAX_COUNTRY_LENGTH))


# ---------------------------------------------------------------------------
# Workflow operations, shared by the JSON routes and the ui fragments
# ---------------------------------------------------------------------------


def belongs_to(record: Dict[str, Any], destination_id: int) -> bool:
    """True if this is a Student 5 review of exactly this destination."""
    return (record.get("feature") == "student-5"
            and record["evidence"][0].get("id") == "destination-{}".format(destination_id))


def start_review(destination_id: int, submitted_by: str) -> Dict[str, str]:
    """Build the evidence and queue one review on the shared server.

    Raises:
        MultiAgentDisabled: before the database read, so "off" costs no call.
        DestinationNotFound / DatabaseUnavailable: from the database read.
        MultiAgentRefused (busy) / MultiAgentUnavailable: from the server.
    """
    client = multi_agent()
    client.ensure_enabled()
    context = load_context(destination_id)
    evidence = build_evidence(destination_id, context)
    return client.start(task_for(context.destination), evidence, submitted_by)


def load_review(workflow_id: str, destination_id: int) -> Dict[str, Any]:
    record = multi_agent().get(workflow_id)
    if not belongs_to(record, destination_id):
        # Same answer as a missing id: another feature's workflow is not ours to show.
        raise review_not_found()
    return record


def decide_review(workflow_id: str, destination_id: int, decision: Dict[str, Any]) -> Dict[str, Any]:
    """Check the binding first, then let the server apply its decision rules."""
    load_review(workflow_id, destination_id)
    record = multi_agent().decide(workflow_id, decision)
    if not belongs_to(record, destination_id):
        raise MultiAgentUnavailable("The Multi-Agent Server returned an unexpected reply.")
    return record


# ---------------------------------------------------------------------------
# JSON routes
# ---------------------------------------------------------------------------


def _error(code: str, message: str, status: int):
    return jsonify({"error": code, "message": message}), status


def _destination_id(raw: Any) -> int:
    destination_id = parse_destination_id(raw)
    if destination_id is None:
        raise InvalidRequest("invalid_request", "destination_id is required and must be an integer.")
    return destination_id


@readiness_bp.errorhandler(InvalidRequest)
def handle_invalid_request(exc: InvalidRequest):
    return _error(exc.code, exc.message, 400)


@readiness_bp.errorhandler(MultiAgentDisabled)
def handle_multi_agent_disabled(_exc):
    # Same shape as the MCP/RAG/AI "disabled" responses.
    return _error("multi_agent_disabled", "Multi-Agent is disabled.", 503)


@readiness_bp.errorhandler(MultiAgentUnavailable)
def handle_multi_agent_unavailable(exc):
    return _error("multi_agent_unavailable", str(exc), 502)


@readiness_bp.errorhandler(MultiAgentRefused)
def handle_multi_agent_refused(exc: MultiAgentRefused):
    return _error(exc.code, exc.message, exc.status)


@readiness_bp.post("/destinations/<int:destination_id>/readiness-reviews")
def create_review(destination_id: int):
    try:
        created = start_review(destination_id, "student-5-api")
    except DestinationNotFound as exc:
        # The database's own 404 body, forwarded like the passthrough would.
        return jsonify(exc.response.payload), exc.response.status_code
    return jsonify({**created, "destination_id": destination_id}), 202


@readiness_bp.get("/readiness-reviews/<workflow_id>")
def get_review(workflow_id: str):
    destination_id = _destination_id(request.args.get("destination_id"))
    return jsonify(load_review(workflow_id, destination_id))


@readiness_bp.post("/readiness-reviews/<workflow_id>/decision")
def post_decision(workflow_id: str):
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise InvalidRequest("invalid_request", "Send a JSON object body.")
    destination_id = _destination_id(body.get("destination_id"))
    if body.get("decision") not in DECISIONS:
        raise InvalidRequest("invalid_request", "decision must be one of {}.".format(", ".join(DECISIONS)))
    # The server validates every field strictly (reject needs notes, partial
    # needs real item ids, a correction must cite supplied evidence), so its
    # own 400 is relayed rather than those rules being repeated here.
    decision = {field: body[field] for field in DECISION_FIELDS if field in body}
    return jsonify(decide_review(workflow_id, destination_id, decision))
