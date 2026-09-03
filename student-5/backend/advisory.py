"""AI travel advisory: the Frontend -> Backend/API -> Ollama -> LLM workflow.

The advisory is *grounded*: before the model is asked anything, this module
pulls the destination row and its weather notes and transit options out of the
database service and pastes them into the prompt verbatim. The model's job is
to turn stored facts into traveller-facing advice, not to recall them, so a
wrong visa rule in the database shows up as a wrong advisory rather than the
model quietly inventing a plausible one.

This lives in its own blueprint rather than on the ``api`` passthrough
blueprint because it does not share that blueprint's semantics: the passthrough
forwards whatever the database says, while this endpoint owns a contract of its
own (destination_id is required) and has a second dependency that can fail.
"""

from typing import Any, List, NamedTuple, Optional

from flask import Blueprint, current_app, jsonify, request

from db_client import DatabaseClient, DatabaseResponse
from ollama_client import OllamaClient

advisory_bp = Blueprint("advisory", __name__, url_prefix="/api")


# ---------------------------------------------------------------------------
# Wiring helpers
# ---------------------------------------------------------------------------


def db() -> DatabaseClient:
    """The database client built by create_app, from the active app context."""
    return current_app.config["DATABASE_CLIENT"]


def ai() -> OllamaClient:
    """The Ollama client built by create_app, from the active app context."""
    return current_app.config["OLLAMA_CLIENT"]


class DestinationNotFound(Exception):
    """The database would not hand back the destination we were asked about.

    Carries the database's own reply so the JSON route can forward its status
    and message unchanged, while the HTML route can render a friendly fragment
    instead.
    """

    def __init__(self, response: DatabaseResponse) -> None:
        super().__init__("destination lookup returned {}".format(response.status_code))
        self.response = response


class AdvisoryContext(NamedTuple):
    """Everything the database knows about one destination."""

    destination: dict
    weather_notes: List[dict]
    transit_options: List[dict]


class Advisory(NamedTuple):
    """One generated advisory, plus the provenance the caller needs."""

    text: str
    model: str
    destination: dict


def parse_destination_id(raw: Any) -> Optional[int]:
    """Coerce a submitted destination_id to an int, or None if it isn't one.

    Unlike the CRUD passthrough -- where Flask's ``<int:row_id>`` converter has
    already done this -- the advisory endpoints take the id from a JSON body or
    a form field and interpolate it into a database URL. Coercing here keeps a
    value like ``1/../weather-notes/1`` from steering that URL somewhere else.
    """
    if isinstance(raw, bool):  # bools are ints in Python; not a valid row id.
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Grounding data
# ---------------------------------------------------------------------------


def load_context(destination_id: int) -> AdvisoryContext:
    """Fetch the destination and its child rows from the database service.

    Raises:
        DestinationNotFound: if the destination row could not be read.
        DatabaseUnavailable: if the database service is unreachable (handled
            app-wide, exactly as it is for the passthrough routes).
    """
    found = db().get_destination(destination_id)
    if found.status_code != 200:
        raise DestinationNotFound(found)

    # Both child resources support ?destination_id=, so the database does the
    # filtering. (Destinations themselves do not -- see db_client.)
    weather = db().list_weather_notes(destination_id)
    transit = db().list_transit_options(destination_id)
    return AdvisoryContext(found.payload, weather.payload, transit.payload)


def describe_destination(destination: dict) -> str:
    """The destination row as plain text, field names and all."""
    lines = [
        "Country: {}".format(destination.get("country")),
        "Visa requirement on record: {}".format(destination.get("visa_requirement")),
    ]
    if destination.get("notes"):
        lines.append("Entry notes on record: {}".format(destination["notes"]))
    return "\n".join(lines)


def describe_weather(notes: List[dict]) -> str:
    """Stored weather notes as plain text, one bullet per season."""
    if not notes:
        return "No weather notes are recorded for this destination."
    return "\n".join(
        "- {}: {}".format(note.get("season"), note.get("notes")) for note in notes
    )


def describe_transit(options: List[dict]) -> str:
    """Stored transit options as plain text, one bullet per option."""
    if not options:
        return "No transit options are recorded for this destination."
    return "\n".join(
        "- {}: {}".format(option.get("type"), option.get("details"))
        for option in options
    )


def describe_traveller(month: Optional[str], interests: Optional[str]) -> str:
    """The optional trip details, or a note that none were supplied."""
    lines = []
    if month:
        lines.append("Month of travel: {}".format(month))
    if interests:
        lines.append("Traveller interests: {}".format(interests))
    if not lines:
        return "No month of travel or interests were supplied."
    return "\n".join(lines)


def build_prompt(
    context: AdvisoryContext,
    month: Optional[str] = None,
    interests: Optional[str] = None,
) -> str:
    """Assemble the prompt sent to the model.

    The four ``describe_*`` helpers above have already rendered the stored rows
    as plain text; this function decides what the model is told to do with them.

    Three choices are worth spelling out, because they are the difference
    between advice and fiction:

    * **The stored data is the only source of facts.** Visa rules are the most
      dangerous thing a travel model can invent, so the instructions pin the
      answer to the recorded ``visa_requirement`` and forbid adding rules from
      the model's own memory. Where a destination has no rows -- Fiji has no
      transit options -- saying so is the required answer.
    * **Three named sections, plain text.** The frontend renders each non-blank
      line as its own paragraph, so markdown headers and asterisks would show
      up literally. Hyphen-prefixed lines are allowed, because the packing
      advice genuinely is a list and renders one item per paragraph. Naming the
      sections keeps a small model on task.
    * **A word budget.** A 3B model left unbounded writes several hundred words
      of preamble; the fragment has to stay readable in a page panel.

    Args:
        context: the destination row plus its weather notes and transit options.
        month: free-text month of travel, if the traveller gave one.
        interests: free-text interests, if the traveller gave any.

    Returns:
        The complete prompt string.
    """
    destination_block = describe_destination(context.destination)
    weather_block = describe_weather(context.weather_notes)
    transit_block = describe_transit(context.transit_options)
    traveller_block = describe_traveller(month, interests)

    return "\n".join(
        [
            "You are a travel logistics assistant writing a short advisory for "
            "an Australian traveller.",
            "",
            "Use only the recorded information below. Every fact, number and "
            "length of stay you state must appear in that recorded text. If a "
            "section has no recorded information, say so in one sentence "
            "instead of guessing.",
            "",
            "RECORDED DESTINATION",
            destination_block,
            "",
            "RECORDED WEATHER NOTES",
            weather_block,
            "",
            "RECORDED TRANSIT OPTIONS",
            transit_block,
            "",
            "TRAVELLER",
            traveller_block,
            "",
            "Write the advisory as plain text under 200 words, in exactly three "
            "labelled sections in this order:",
            "Packing: what to pack, one item per line, each line starting with "
            "a single hyphen and a space, justified by the recorded weather "
            "notes and by the traveller's month and interests where those were "
            "given.",
            "Documents: state the recorded visa requirement exactly as it is "
            "written above, then restate the recorded entry notes in your own "
            "words. Every sentence in this section must correspond to "
            "something in the recorded destination text.",
            "Transit: practical tips drawn from the recorded transit options.",
            "",
            "Address the traveller directly. Write in plain text only: no "
            "markdown, no asterisks, no '#' headings. Do not repeat these "
            "instructions. End with one sentence telling the traveller to "
            "confirm entry requirements with Smartraveller before booking.",
        ]
    )


def generate_advisory(
    destination_id: int,
    month: Optional[str] = None,
    interests: Optional[str] = None,
) -> Advisory:
    """Run the full workflow: database -> prompt -> Ollama -> advisory text.

    Shared by the JSON endpoint and the HTML fragment endpoint so both are
    guaranteed to be grounded in the same data and phrased the same way.
    """
    context = load_context(destination_id)
    client = ai()
    text = client.generate(build_prompt(context, month, interests))
    return Advisory(text, client.model, context.destination)


# ---------------------------------------------------------------------------
# JSON endpoint
# ---------------------------------------------------------------------------


@advisory_bp.post("/advisory")
def create_advisory():
    """POST /api/advisory -- generate an advisory for one destination."""
    body = request.get_json(silent=True) or {}
    destination_id = parse_destination_id(body.get("destination_id"))
    if destination_id is None:
        # This endpoint validates, unlike the passthrough: there is no prompt
        # to build without an id, so there is nothing to forward and let the
        # database reject.
        return jsonify({"error": "destination_id is required and must be an integer"}), 400

    try:
        result = generate_advisory(
            destination_id, body.get("month"), body.get("interests")
        )
    except DestinationNotFound as exc:
        # The database's own 404 body, forwarded like the passthrough would.
        return jsonify(exc.response.payload), exc.response.status_code

    return jsonify(
        {
            "advisory": result.text,
            "model": result.model,
            "destination": result.destination,
        }
    )
