import os
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Literal

import requests
from pydantic import BaseModel, ConfigDict, Field

from tools.itinerary_weather import trip_weather


class SummaryParams(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    trip_id: int = Field(gt=0)


class OverviewParams(SummaryParams):
    location_id: int | None = Field(default=None, gt=0)


class EditOperation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    action: Literal["move_day", "swap_days", "move_stop", "reorder_before", "reorder_after", "undo", "add_stop", "remove_stop", "update_stop", "shift_dates"]
    sourceDay: int = Field(ge=1, le=31)
    targetDay: int = Field(ge=1, le=31)
    stopId: int = Field(ge=0)
    targetStopId: int = Field(default=0, ge=0)
    activity: str | None = Field(default=None, min_length=1, max_length=160)
    notes: str | None = Field(default=None, max_length=1000)
    startDate: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class PreviewParams(SummaryParams):
    operation: EditOperation


class ApplyParams(SummaryParams):
    token: str = Field(min_length=1, max_length=4096)


class ReviewStop(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    id: int = Field(gt=0)
    day: int = Field(ge=1, le=31)
    activity: str = Field(min_length=1, max_length=160)
    notes: str = Field(max_length=1000)
    sortOrder: int = Field(default=0, ge=0)


def summarize(trip, trip_id):
    if not isinstance(trip, dict) or type(trip.get("id")) is not int or trip["id"] != trip_id:
        raise ValueError("Invalid trip")
    destination = trip["destination"]
    if not isinstance(destination, str) or not 1 <= len(destination) <= 100:
        raise ValueError("Invalid destination")
    start = date.fromisoformat(trip["startDate"])
    end = date.fromisoformat(trip["endDate"])
    day_count = (end - start).days + 1
    if not 1 <= day_count <= 31 or type(trip["budget"]) not in (int, float):
        raise ValueError("Invalid trip bounds")
    budget = Decimal(str(trip["budget"]))
    if not budget.is_finite() or not 0 <= budget <= 1000000:
        raise ValueError("Invalid budget")
    stops = trip["stops"]
    if not isinstance(stops, list):
        raise ValueError("Invalid stops")
    planned_days = set()
    for stop in stops:
        if (not isinstance(stop, dict) or type(stop.get("tripId")) is not int
                or stop["tripId"] != trip_id or type(stop.get("day")) is not int
                or not 1 <= stop["day"] <= day_count):
            raise ValueError("Invalid stop")
        planned_days.add(stop["day"])
    return {
        "tripId": trip_id, "destination": destination,
        "startDate": start.isoformat(), "endDate": end.isoformat(),
        "dayCount": day_count, "stopCount": len(stops),
        "plannedDayCount": len(planned_days),
        "unplannedDays": [day for day in range(1, day_count + 1) if day not in planned_days],
        "totalBudget": float(budget),
        "dailyBudgetAllocation": float((budget / day_count).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
    }


def failure(code, message):
    return {"ok": False, "error": {"code": code, "message": message}}


def register(mcp):
    def read_trip(params, include_stops=False):
        base_url = os.getenv("STUDENT2_DATABASE_API_URL", "http://127.0.0.1:5302").rstrip("/")
        try:
            response = requests.get(f"{base_url}/api/data/trips/{params.trip_id}", timeout=3)
            if response.status_code == 404:
                return failure("trip_not_found", "The saved trip was not found.")
            response.raise_for_status()
            trip = response.json()
            result = {"ok": True, "summary": summarize(trip, params.trip_id)}
            if include_stops:
                if len(trip["stops"]) > 200:
                    raise ValueError("Too many stops to review")
                stops = [ReviewStop.model_validate(stop).model_dump() for stop in trip["stops"]]
                if len({stop["id"] for stop in stops}) != len(stops):
                    raise ValueError("Duplicate stop IDs")
                result["stops"] = stops
            return result
        except requests.Timeout:
            return failure("dependency_timeout", "The itinerary database timed out.")
        except requests.exceptions.JSONDecodeError:
            return failure("invalid_dependency_response", "The itinerary database returned invalid data.")
        except requests.RequestException:
            return failure("dependency_unavailable", "The itinerary database is unavailable.")
        except (ValueError, TypeError, KeyError, InvalidOperation):
            return failure("invalid_dependency_response", "The itinerary database returned invalid data.")

    @mcp.tool(name="itinerary.get_summary")
    def get_summary(params: SummaryParams) -> dict[str, Any]:
        """Read a saved itinerary's day coverage and indicative budget allocation."""
        return read_trip(params)

    @mcp.tool(name="itinerary.get_itinerary")
    def get_itinerary(params: SummaryParams) -> dict[str, Any]:
        """Read the saved itinerary's summary and up to 200 stops and notes, without traveller identity."""
        return read_trip(params, include_stops=True)

    @mcp.tool(name="itinerary.get_overview")
    def get_overview(params: OverviewParams) -> dict[str, Any]:
        """Read saved trip coverage and budget with Open-Meteo destination weather."""
        result = get_summary(SummaryParams(trip_id=params.trip_id))
        if result["ok"]:
            result["weather"] = trip_weather(result["summary"], params.location_id)
        return result

    def edit_request(params, path, payload):
        base_url = os.getenv("STUDENT2_DATABASE_API_URL", "http://127.0.0.1:5302").rstrip("/")
        try:
            response = requests.post(f"{base_url}/api/data/trips/{params.trip_id}/{path}", json=payload, timeout=3, allow_redirects=False)
            if response.status_code in (400, 404, 409):
                code = {400: "invalid_edit", 404: "trip_not_found", 409: "stale_preview"}[response.status_code]
                return failure(code, "Request a new edit preview.")
            if response.status_code != 200:
                return failure("dependency_unavailable", "The itinerary database is unavailable.")
            body = response.json()
            expected = {"tripId", "token", "changes", "expiresIn"} if path == "edit-preview" else {"tripId", "applied", "changes"}
            if not isinstance(body, dict) or set(body) != expected or body["tripId"] != params.trip_id:
                raise ValueError("Invalid edit response")
            return {"ok": True, **body}
        except requests.Timeout:
            return failure("dependency_timeout", "The itinerary database timed out. Refresh the trip before retrying a save.")
        except requests.exceptions.JSONDecodeError:
            return failure("invalid_dependency_response", "The itinerary database returned invalid data.")
        except requests.RequestException:
            return failure("dependency_unavailable", "The itinerary database is unavailable.")
        except (ValueError, TypeError, KeyError):
            return failure("invalid_dependency_response", "The itinerary database returned invalid data.")

    @mcp.tool(name="itinerary.preview_edit")
    def preview_edit(params: PreviewParams) -> dict[str, Any]:
        """Preview adding, removing or updating an activity, shifting trip dates, moving/reordering stops, swapping days, or undo. No changes are saved."""
        return edit_request(params, "edit-preview", params.operation.model_dump(exclude_defaults=True))

    @mcp.tool(name="itinerary.apply_edit")
    def apply_edit(params: ApplyParams) -> dict[str, Any]:
        """Apply an explicitly user-confirmed signed preview. Reject expired or changed itineraries."""
        return edit_request(params, "edit-apply", {"token": params.token})

    for name in ("itinerary.get_summary", "itinerary.get_itinerary", "itinerary.get_overview", "itinerary.preview_edit", "itinerary.apply_edit"):
        tool = mcp._tool_manager.get_tool(name)
        tool.fn_metadata.arg_model.model_config["extra"] = "forbid"
        tool.fn_metadata.arg_model.model_rebuild(force=True)
        tool.parameters = tool.fn_metadata.arg_model.model_json_schema(by_alias=True)