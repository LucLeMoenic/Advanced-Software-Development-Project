import os
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

import requests
from pydantic import BaseModel, ConfigDict, Field


class SummaryParams(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    trip_id: int = Field(gt=0)


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
    @mcp.tool(name="itinerary.get_summary")
    def get_summary(params: SummaryParams) -> dict[str, Any]:
        """Read a saved itinerary's day coverage and indicative budget allocation."""
        base_url = os.getenv("STUDENT2_DATABASE_API_URL", "http://127.0.0.1:5302").rstrip("/")
        try:
            response = requests.get(f"{base_url}/api/data/trips/{params.trip_id}", timeout=3)
            if response.status_code == 404:
                return failure("trip_not_found", "The saved trip was not found.")
            response.raise_for_status()
            return {"ok": True, "summary": summarize(response.json(), params.trip_id)}
        except requests.Timeout:
            return failure("dependency_timeout", "The itinerary database timed out.")
        except requests.exceptions.JSONDecodeError:
            return failure("invalid_dependency_response", "The itinerary database returned invalid data.")
        except requests.RequestException:
            return failure("dependency_unavailable", "The itinerary database is unavailable.")
        except (ValueError, TypeError, KeyError, InvalidOperation):
            return failure("invalid_dependency_response", "The itinerary database returned invalid data.")

    tool = mcp._tool_manager.get_tool("itinerary.get_summary")
    tool.fn_metadata.arg_model.model_config["extra"] = "forbid"
    tool.fn_metadata.arg_model.model_rebuild(force=True)
    tool.parameters = tool.fn_metadata.arg_model.model_json_schema(by_alias=True)