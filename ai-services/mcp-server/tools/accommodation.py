"""Student 1 (AI Accommodation Recommender) read-only MCP tools.

Both tools only issue GET requests to the Student 1 database API
(``STUDENT1_DATABASE_API_URL``, default ``http://127.0.0.1:5301``) with a
3-second timeout, validate every dependency record, and return
``{ok:true, ...}`` or ``{ok:false, error:{code, message}}``. Arguments use the
shared ``{"params": {...}}`` wrapper so unknown fields are rejected.

    accommodation.find({"params": {"destination": "Tokyo", "guests": 2, "max_nightly_price": 200}})
    accommodation.get_search({"params": {"search_id": 11}})
"""

import math
import os
from typing import Any, Optional

import requests
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_RESULTS = 20
RANKING_MODES = {"programmatic", "ai", "fallback"}


class FindParams(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    destination: str = Field(min_length=1, max_length=100)
    guests: Optional[int] = Field(default=None, ge=1, le=20)
    max_nightly_price: Optional[float] = Field(default=None, gt=0, le=100000)

    @field_validator("destination")
    @classmethod
    def destination_not_blank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Destination must not be blank.")
        return value


class GetSearchParams(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    search_id: int = Field(gt=0)


def _text(value, maximum):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= maximum:
        raise ValueError("Invalid text")
    return value


def _integer(value, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError("Invalid integer")
    return value


def _price(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 100000:
        raise ValueError("Invalid price")
    return value


def accommodation_item(record, destination):
    if not isinstance(record, dict) or record.get("isActive") is not True:
        raise ValueError("Invalid accommodation")
    amenities = record["amenities"]
    if not isinstance(amenities, list) or len(amenities) > 30:
        raise ValueError("Invalid amenities")
    item = {
        "id": _integer(record["id"], 1, 2**31 - 1),
        "name": _text(record["name"], 120),
        "destination": _text(record["destination"], 100),
        "nightlyPrice": _price(record["nightlyPrice"]),
        "maxGuests": _integer(record["maxGuests"], 1, 20),
        "amenities": [_text(amenity, 100) for amenity in amenities],
    }
    if item["destination"].casefold() != destination.casefold():
        raise ValueError("Unexpected destination")
    return item


def find_result(records, params):
    if not isinstance(records, list):
        raise ValueError("Invalid accommodation list")
    items = [accommodation_item(record, params.destination) for record in records]
    for item in items:
        if ((params.guests is not None and item["maxGuests"] < params.guests)
                or (params.max_nightly_price is not None and item["nightlyPrice"] > params.max_nightly_price)):
            raise ValueError("Record outside the requested filters")
    items.sort(key=lambda item: (item["nightlyPrice"], item["id"]))
    items = items[:MAX_RESULTS]
    return {"ok": True, "count": len(items), "accommodations": items}


def search_result(record, search_id):
    if not isinstance(record, dict) or type(record.get("id")) is not int or record["id"] != search_id:
        raise ValueError("Invalid search")
    if record["rankingMode"] not in RANKING_MODES:
        raise ValueError("Invalid ranking mode")
    results = record["results"]
    if not isinstance(results, list):
        raise ValueError("Invalid results")
    snapshot = [{
        "rank": _integer(result["rank"], 1, len(results)),
        "accommodationId": _integer(result["accommodationId"], 1, 2**31 - 1),
        "name": _text(result["name"], 120),
        "nightlyPrice": _price(result["nightlyPrice"]),
        "reason": _text(result["reason"], 200),
    } for result in results if isinstance(result, dict)]
    if len(snapshot) != len(results) or sorted(r["rank"] for r in snapshot) != list(range(1, len(results) + 1)):
        raise ValueError("Invalid ranks")
    snapshot.sort(key=lambda result: result["rank"])
    minimum, maximum = _price(record["minimumPrice"]), _price(record["maximumPrice"])
    if minimum > maximum:
        raise ValueError("Invalid price range")
    # Preferences are traveller free text the lookup does not need, so they are omitted.
    return {"ok": True, "search": {
        "id": search_id,
        "title": _text(record["title"], 80),
        "criteria": {
            "destination": _text(record["destination"], 100),
            "checkIn": _text(record["checkIn"], 10),
            "checkOut": _text(record["checkOut"], 10),
            "guests": _integer(record["guests"], 1, 20),
            "minimumPrice": minimum,
            "maximumPrice": maximum,
        },
        "rankingMode": record["rankingMode"],
        "results": snapshot,
    }}


def failure(code, message):
    return {"ok": False, "error": {"code": code, "message": message}}


def _get(path, query=None):
    base_url = os.getenv("STUDENT1_DATABASE_API_URL", "http://127.0.0.1:5301").rstrip("/")
    return requests.get(f"{base_url}{path}", params=query, timeout=3)


def _read(call, not_found=None):
    try:
        response = call()
        if response.status_code == 404 and not_found:
            return failure(*not_found)
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        return failure("dependency_timeout", "The accommodation database timed out.")
    except requests.exceptions.JSONDecodeError:
        return failure("invalid_dependency_response", "The accommodation database returned invalid data.")
    except requests.RequestException:
        return failure("dependency_unavailable", "The accommodation database is unavailable.")


def _strict_arguments(mcp, name):
    tool = mcp._tool_manager.get_tool(name)
    tool.fn_metadata.arg_model.model_config["extra"] = "forbid"
    tool.fn_metadata.arg_model.model_rebuild(force=True)
    tool.parameters = tool.fn_metadata.arg_model.model_json_schema(by_alias=True)


def register(mcp):
    read_only = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
    invalid = failure("invalid_dependency_response", "The accommodation database returned invalid data.")

    @mcp.tool(name="accommodation.find", annotations=read_only)
    def find(params: FindParams) -> dict[str, Any]:
        """List up to 20 active accommodations in one destination, cheapest first, optionally filtered by guests and maximum nightly price."""
        query = {"destination": params.destination, "active": "true"}
        if params.guests is not None:
            query["guests"] = params.guests
        if params.max_nightly_price is not None:
            query["maxPrice"] = params.max_nightly_price
        body = _read(lambda: _get("/api/data/accommodations", query))
        if isinstance(body, dict) and body.get("ok") is False:
            return body
        try:
            return find_result(body, params)
        except (ValueError, TypeError, KeyError):
            return invalid

    @mcp.tool(name="accommodation.get_search", annotations=read_only)
    def get_search(params: GetSearchParams) -> dict[str, Any]:
        """Read one saved accommodation search: its criteria, ranking mode and ranked results (preferences are omitted)."""
        body = _read(lambda: _get(f"/api/data/searches/{params.search_id}"),
                     ("search_not_found", "The saved search was not found."))
        if isinstance(body, dict) and body.get("ok") is False:
            return body
        try:
            return search_result(body, params.search_id)
        except (ValueError, TypeError, KeyError):
            return invalid

    _strict_arguments(mcp, "accommodation.find")
    _strict_arguments(mcp, "accommodation.get_search")
