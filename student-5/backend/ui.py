"""Server-rendered HTML fragments for the HTMX frontend.

Every route here returns a fragment, never a whole page: the frontend owns the
document and the CSS, and swaps these pieces into it. Templates therefore carry
classes only -- no inline styles, no ids the frontend did not ask for -- with
the single exception of ``#destinations-manage``, which the manage table's own
controls need as a swap target.

Two policies worth stating, because they differ from the JSON API next door:

1. **Writes go through this blueprint, not the JSON API.** A row's Save and
   Delete controls post to ``/ui/destinations/<id>`` and
   ``/ui/destinations/<id>/delete``, which perform the change through
   db_client and re-render the table from what the database now holds. The
   alternative -- pointing hx-put/hx-delete at ``/api/...`` -- would hand the
   browser a JSON body it cannot swap, and would let the visible table drift
   away from stored state.

2. **Fragments answer 200 even when something went wrong.** HTMX does not swap
   a non-2xx response by default, so a 404 or 503 here would leave the page
   silently unchanged -- the worst possible feedback. These routes render the
   problem *as content* instead. The JSON API keeps the honest status codes;
   this blueprint optimises for the traveller seeing what happened.
"""

from typing import Any, Optional

from flask import Blueprint, render_template, request

from advisory import (
    DestinationNotFound,
    db,
    generate_advisory,
    parse_destination_id,
)
from db_client import DatabaseUnavailable
from integrations import InvalidRequest, clean_question, invoke_tool, rag
from mcp_client import McpDisabled, McpToolError, McpUnavailable
from ollama_client import OllamaUnavailable
from rag_client import RagDisabled, RagTimeout, RagUnavailable

ui_bp = Blueprint("ui", __name__, url_prefix="/ui")


# ---------------------------------------------------------------------------
# Shared rendering helpers
# ---------------------------------------------------------------------------


def notice(text: str) -> str:
    """A readable one-line fragment, used wherever real content can't render."""
    return render_template("fragment_message.html", message=text)


def database_error(reply, fallback: str) -> str:
    """The database's own error message when it sent one, else `fallback`.

    The database service owns validation, so its wording ("Missing required
    field(s): country") is more useful to show than anything invented here.
    """
    if isinstance(reply.payload, dict) and reply.payload.get("error"):
        return reply.payload["error"]
    return fallback


def render_destinations_table(message: Optional[str] = None) -> str:
    """The manage table, always rebuilt from a fresh read of the database."""
    reply = db().list_destinations()
    return render_template(
        "destinations_table.html", destinations=reply.payload, message=message
    )


def requested_destination_id() -> Optional[int]:
    """The ?destination_id= query value as an int, or None if absent/invalid."""
    return parse_destination_id(request.args.get("destination_id"))


def form_value(field: str) -> Optional[str]:
    """A trimmed form field, or None when it was blank or absent."""
    value: Any = request.form.get(field)
    if value is None:
        return None
    value = value.strip()
    return value or None


# ---------------------------------------------------------------------------
# Dependency failures, rendered as fragments
#
# Blueprint-scoped handlers take precedence over the app-wide ones in app.py,
# so an unreachable dependency becomes readable HTML here while the JSON API
# still returns its 503.
# ---------------------------------------------------------------------------


@ui_bp.errorhandler(DatabaseUnavailable)
def fragment_database_unavailable(_exc):
    return notice("The travel database is unavailable right now. Please try again shortly.")


@ui_bp.errorhandler(OllamaUnavailable)
def fragment_ai_unavailable(_exc):
    return notice("The travel adviser is unavailable right now. Please try again shortly.")


@ui_bp.errorhandler(McpDisabled)
def fragment_mcp_disabled(_exc):
    return notice("Live tool lookups are switched off for this deployment (MCP is disabled).")


@ui_bp.errorhandler(McpUnavailable)
def fragment_mcp_unavailable(_exc):
    return notice("The shared tool server is unavailable right now. Please try again shortly.")


@ui_bp.errorhandler(RagDisabled)
def fragment_rag_disabled(_exc):
    return notice("Knowledge-base answers are switched off for this deployment (RAG is disabled).")


@ui_bp.errorhandler(RagUnavailable)
def fragment_rag_unavailable(exc):
    if isinstance(exc, RagTimeout):
        return notice("The knowledge base took too long to answer. Please try again.")
    return notice("The knowledge base is unavailable right now. Please try again shortly.")


@ui_bp.errorhandler(InvalidRequest)
def fragment_invalid_request(exc):
    return notice(exc.message)


# ---------------------------------------------------------------------------
# Read-only fragments
# ---------------------------------------------------------------------------


@ui_bp.get("/destinations/options")
def destination_options():
    """<option> list for a destination <select>."""
    reply = db().list_destinations()
    return render_template("destination_options.html", destinations=reply.payload)


@ui_bp.get("/weather")
def weather_fragment():
    """Stored weather notes for one destination, as a definition list."""
    destination_id = requested_destination_id()
    if destination_id is None:
        return notice("Choose a destination to see its weather notes.")

    reply = db().list_weather_notes(destination_id)
    return render_template("weather.html", notes=reply.payload)


@ui_bp.get("/visa")
def visa_fragment():
    """The stored visa requirement for one destination, as a callout."""
    destination_id = requested_destination_id()
    if destination_id is None:
        return notice("Choose a destination to see its entry requirements.")

    reply = db().get_destination(destination_id)
    if reply.status_code != 200:
        return notice(database_error(reply, "That destination could not be found."))
    return render_template("visa.html", destination=reply.payload)


@ui_bp.get("/transit")
def transit_fragment():
    """Stored transit options for one destination, as a table."""
    destination_id = requested_destination_id()
    if destination_id is None:
        return notice("Choose a destination to see its transit options.")

    reply = db().list_transit_options(destination_id)
    return render_template("transit.html", options=reply.payload)


@ui_bp.get("/destinations/table")
def destinations_table():
    """The manage table: every destination, with edit and delete controls."""
    return render_destinations_table()


# ---------------------------------------------------------------------------
# Writes -- each performs the change, then returns the refreshed table
# ---------------------------------------------------------------------------


@ui_bp.post("/destinations")
def create_destination_fragment():
    """Create a destination from the manage form."""
    body = {
        "country": form_value("country"),
        "visa_requirement": form_value("visa_requirement"),
    }
    # notes is the one nullable column, so a blank box is omitted entirely and
    # the row stores NULL rather than an empty string.
    notes = form_value("notes")
    if notes is not None:
        body["notes"] = notes

    reply = db().create_destination(body)
    if reply.status_code != 201:
        return render_destinations_table(
            database_error(reply, "That destination could not be added.")
        )
    return render_destinations_table()


@ui_bp.post("/destinations/<int:row_id>")
def update_destination_fragment(row_id: int):
    """Save one row's inline edits.

    The database PUT is a partial merge, but the row always sends all three
    fields, so every box is forwarded and the stored row ends up matching what
    is on screen.

    An emptied notes box is sent as JSON null rather than "": notes is the one
    nullable column, and the database rejects an empty string for any field
    while accepting null for this one. Sending "" would mean notes could be
    edited but never cleared. A required field left blank is forwarded as-is
    so the database's own complaint is what the user sees.
    """
    notes = request.form.get("notes", "").strip()
    body = {
        "country": request.form.get("country", "").strip(),
        "visa_requirement": request.form.get("visa_requirement", "").strip(),
        "notes": notes or None,
    }

    reply = db().update_destination(row_id, body)
    if reply.status_code != 200:
        return render_destinations_table(
            database_error(reply, "That destination could not be updated.")
        )
    return render_destinations_table()


@ui_bp.post("/destinations/<int:row_id>/delete")
def delete_destination_fragment(row_id: int):
    """Delete one destination.

    POST rather than DELETE because this is a fragment endpoint reached from a
    button, and its reply is a rendered table rather than the 204 the JSON API
    returns.
    """
    reply = db().delete_destination(row_id)
    if reply.status_code != 204:
        return render_destinations_table(
            database_error(reply, "That destination could not be deleted.")
        )
    return render_destinations_table()


# ---------------------------------------------------------------------------
# AI advisory fragment
# ---------------------------------------------------------------------------


@ui_bp.post("/advisory")
def advisory_fragment():
    """Run the advisory workflow and return the result as an <article>."""
    destination_id = parse_destination_id(request.form.get("destination_id"))
    if destination_id is None:
        return notice("Choose a destination before asking for an advisory.")

    try:
        result = generate_advisory(
            destination_id, form_value("month"), form_value("interests")
        )
    except DestinationNotFound as exc:
        return notice(
            database_error(exc.response, "That destination could not be found.")
        )

    return render_template(
        "advisory_result.html",
        advisory=result.text,
        model=result.model,
        destination=result.destination,
    )


# ---------------------------------------------------------------------------
# Release 1: MCP tool and RAG knowledge-base fragments
#
# Same calls as the JSON routes in integrations.py, rendered as content. Every
# outcome -- disabled, unavailable, a rejected argument, an insufficient
# answer -- is still a 200 fragment the traveller can read.
# ---------------------------------------------------------------------------

MCP_DOMAIN_MESSAGES = {
    "destination_not_found": "That destination could not be found.",
}


@ui_bp.post("/mcp")
def mcp_fragment():
    """Call one Student 5 MCP tool for the selected destination."""
    destination_id = parse_destination_id(request.form.get("destination_id"))
    if destination_id is None:
        return notice("Choose a destination before running a tool.")

    tool = request.form.get("tool")
    arguments = {"destination_id": destination_id}
    transit_type = form_value("transit_type")
    if tool == "logistics.get_transit" and transit_type:
        arguments["type"] = transit_type

    try:
        result = invoke_tool(tool, arguments)
    except McpToolError:
        return notice("The tool rejected that request. Check the destination and transit type.")

    if result.get("ok") is False:
        error = result.get("error")
        code = error.get("code") if isinstance(error, dict) else None
        return notice(MCP_DOMAIN_MESSAGES.get(
            code, "The tool could not read the travel database right now."))
    return render_template("mcp_result.html", tool=tool, result=result)


@ui_bp.post("/rag")
def rag_fragment():
    """Answer a travel logistics question from the curated knowledge base."""
    question = clean_question(request.form.get("question"))
    answer = rag().ask(question)
    return render_template("rag_answer.html", question=question, **answer)