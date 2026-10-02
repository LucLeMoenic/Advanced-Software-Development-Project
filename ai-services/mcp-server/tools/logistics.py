"""Student 5 (Travel Logistics & Advisory Service) read-only MCP tools.

Every tool only issues GET requests to the Student 5 database API
(``STUDENT5_DATABASE_API_URL``, default ``http://127.0.0.1:5305``) with a
3-second timeout, validates each dependency record, and returns
``{ok:true, ...}`` or ``{ok:false, error:{code, message}}``. Arguments use the
shared ``{"params": {...}}`` wrapper so unknown fields are rejected.

    logistics.check_visa_requirement({"params": {"destination_id": 1}})
    logistics.get_weather({"params": {"destination_id": 1}})
    logistics.get_transit({"params": {"destination_id": 1, "type": "rail"}})

Visa results are general guidance from the seeded data, not legal advice, so
every visa result carries the official-source reminder.
"""

import os
from typing import Any, Literal, Optional

import requests
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field

MAX_ITEMS = 20
TRANSIT_TYPES = ("metro", "rail", "bus", "rideshare", "ferry", "airport-link")
OFFICIAL_SOURCE_REMINDER = (
    "General guidance only. Confirm entry requirements with Smartraveller "
    "and the destination's official immigration authority before booking."
)


class DestinationParams(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    destination_id: int = Field(gt=0, le=2**31 - 1)


class TransitParams(DestinationParams):
    type: Optional[Literal[TRANSIT_TYPES]] = None


def _text(value, maximum):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= maximum:
        raise ValueError("Invalid text")
    return value.strip()


def _optional_text(value, maximum):
    return None if value is None else _text(value, maximum)


def _id(value):
    if type(value) is not int or not 1 <= value <= 2**31 - 1:
        raise ValueError("Invalid id")
    return value


def destination_item(record, destination_id):
    if not isinstance(record, dict) or _id(record["id"]) != destination_id:
        raise ValueError("Invalid destination")
    return {
        "id": destination_id,
        "country": _text(record["country"], 100),
        "visa_requirement": _text(record["visa_requirement"], 100),
        "notes": _optional_text(record.get("notes"), 500),
    }


def _children(records, destination_id, fields):
    if not isinstance(records, list):
        raise ValueError("Invalid list")
    items = []
    for record in records:
        if not isinstance(record, dict) or _id(record["destination_id"]) != destination_id:
            raise ValueError("Record for another destination")
        items.append({"id": _id(record["id"]), **{name: _text(record[name], limit) for name, limit in fields}})
    items.sort(key=lambda item: item["id"])
    return items


def visa_result(destination):
    return {"ok": True, "destination": destination, "official_source_reminder": OFFICIAL_SOURCE_REMINDER}


def weather_result(destination, records):
    notes = _children(records, destination["id"], (("season", 60), ("notes", 500)))[:MAX_ITEMS]
    return {"ok": True, "destination": {"id": destination["id"], "country": destination["country"]},
            "count": len(notes), "weather_notes": notes}


def transit_result(destination, records, transit_type):
    options = _children(records, destination["id"], (("type", 40), ("details", 500)))
    # Filter before capping so a matching row past the cap is not dropped.
    if transit_type is not None:
        options = [option for option in options if option["type"] == transit_type]
    options = options[:MAX_ITEMS]
    return {"ok": True, "destination": {"id": destination["id"], "country": destination["country"]},
            "count": len(options), "transit_options": options}


def failure(code, message):
    return {"ok": False, "error": {"code": code, "message": message}}


def _get(path, query=None):
    base_url = os.getenv("STUDENT5_DATABASE_API_URL", "http://127.0.0.1:5305").rstrip("/")
    return requests.get(f"{base_url}{path}", params=query, timeout=3)


def _read(call, not_found=None):
    try:
        response = call()
        if response.status_code == 404 and not_found:
            return failure(*not_found)
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        return failure("dependency_timeout", "The logistics database timed out.")
    except requests.exceptions.JSONDecodeError:
        return failure("invalid_dependency_response", "The logistics database returned invalid data.")
    except requests.RequestException:
        return failure("dependency_unavailable", "The logistics database is unavailable.")


def _is_failure(body):
    return isinstance(body, dict) and body.get("ok") is False


def _strict_arguments(mcp, name):
    tool = mcp._tool_manager.get_tool(name)
    tool.fn_metadata.arg_model.model_config["extra"] = "forbid"
    tool.fn_metadata.arg_model.model_rebuild(force=True)
    tool.parameters = tool.fn_metadata.arg_model.model_json_schema(by_alias=True)


def register(mcp):
    read_only = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
    invalid = failure("invalid_dependency_response", "The logistics database returned invalid data.")
    not_found = ("destination_not_found", "The destination was not found.")

    def destination(destination_id):
        body = _read(lambda: _get(f"/api/destinations/{destination_id}"), not_found)
        if _is_failure(body):
            return body
        try:
            return destination_item(body, destination_id)
        except (ValueError, TypeError, KeyError):
            return invalid

    def with_children(params, path, build):
        parent = destination(params.destination_id)
        if _is_failure(parent):
            return parent
        body = _read(lambda: _get(path, {"destination_id": params.destination_id}))
        if _is_failure(body):
            return body
        try:
            return build(parent, body)
        except (ValueError, TypeError, KeyError):
            return invalid

    @mcp.tool(name="logistics.check_visa_requirement", annotations=read_only)
    def check_visa_requirement(params: DestinationParams) -> dict[str, Any]:
        """Read one destination's visa requirement category and entry notes for Australian passport holders, with an official-source reminder."""
        parent = destination(params.destination_id)
        return parent if _is_failure(parent) else visa_result(parent)

    @mcp.tool(name="logistics.get_weather", annotations=read_only)
    def get_weather(params: DestinationParams) -> dict[str, Any]:
        """List up to 20 seasonal weather and packing notes for one destination."""
        return with_children(params, "/api/weather-notes", weather_result)

    @mcp.tool(name="logistics.get_transit", annotations=read_only)
    def get_transit(params: TransitParams) -> dict[str, Any]:
        """List up to 20 local transit options for one destination, optionally filtered to one transit type."""
        return with_children(params, "/api/transit-options",
                             lambda parent, body: transit_result(parent, body, params.type))

    for name in ("logistics.check_visa_requirement", "logistics.get_weather", "logistics.get_transit"):
        _strict_arguments(mcp, name)
