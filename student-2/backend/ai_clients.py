import json
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

import anyio
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from pydantic import BaseModel, ConfigDict, Field, ValidationError


ERRORS = {
    "invalid_edit": (400, "The edit or preview is invalid or expired. Request a new preview."),
    "edit_no_change": (400, "Those stops are already in that order."),
    "undo_unavailable": (400, "There is no unchanged confirmed itinerary edit to undo. Manual edits cannot be undone here."),
    "stale_preview": (409, "The trip changed. Refresh it and request a new preview."),
    "trip_not_found": (404, "The saved trip was not found."),
    "mode_disabled": (503, "This mode is disabled."),
    "dependency_unavailable": (503, "The requested service is unavailable."),
    "dependency_timeout": (504, "The requested service timed out."),
    "invalid_dependency_response": (502, "The service returned an invalid response."),
}
INSUFFICIENT_ANSWER = "Not enough information in the knowledge base to answer this."


class IntegrationError(Exception):
    def __init__(self, code):
        self.code = code if code in ERRORS else "invalid_dependency_response"
        self.status, self.message = ERRORS[self.code]
        super().__init__(self.message)


class Summary(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    tripId: int = Field(gt=0)
    destination: str = Field(min_length=1, max_length=100)
    startDate: str
    endDate: str
    dayCount: int = Field(ge=1, le=31)
    stopCount: int = Field(ge=0)
    plannedDayCount: int = Field(ge=0, le=31)
    unplannedDays: list[int] = Field(max_length=31)
    totalBudget: float = Field(ge=0, le=1000000)
    dailyBudgetAllocation: float = Field(ge=0, le=1000000)


def validate_summary(body, trip_id):
    try:
        summary = Summary.model_validate(body)
        duration = (date.fromisoformat(summary.endDate) - date.fromisoformat(summary.startDate)).days + 1
        if not 1 <= duration <= 31:
            raise ValueError("Invalid date range")
        allocation = float((Decimal(str(summary.totalBudget)) / duration).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        if (summary.tripId != trip_id or duration != summary.dayCount
                or summary.unplannedDays != sorted(set(summary.unplannedDays))
                or any(day < 1 or day > duration for day in summary.unplannedDays)
                or summary.plannedDayCount != duration - len(summary.unplannedDays)
                or summary.plannedDayCount > summary.stopCount
                or (summary.plannedDayCount == 0 and summary.stopCount != 0)
                or summary.dailyBudgetAllocation != allocation):
            raise ValueError("Inconsistent summary")
        return summary.model_dump()
    except (ValidationError, ValueError, TypeError, ZeroDivisionError):
        raise IntegrationError("invalid_dependency_response") from None


class WeatherLocation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=200)
    country: str = Field(max_length=200)
    admin1: str = Field(max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class WeatherDay(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    date: str
    weatherCode: int | None = Field(ge=0, le=99)
    minTemperature: float | None = Field(ge=-100, le=70)
    maxTemperature: float | None = Field(ge=-100, le=70)
    precipitationProbability: float | None = Field(ge=0, le=100)


class Weather(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: Literal["available", "partial", "outside_window", "choose_location", "not_found", "unavailable"]
    locations: list[WeatherLocation] = Field(max_length=5)
    location: WeatherLocation | None
    days: list[WeatherDay] = Field(max_length=16)
    unavailableDates: list[str] = Field(max_length=31)
    retrievedAt: str | None


def validate_overview(body, trip_id, location_id=None):
    try:
        if not isinstance(body, dict) or set(body) != {"summary", "weather"}:
            raise ValueError("Invalid overview")
        summary = validate_summary(body["summary"], trip_id)
        weather = Weather.model_validate(body["weather"])
        start = date.fromisoformat(summary["startDate"])
        dates = [(start + timedelta(days=offset)).isoformat() for offset in range(summary["dayCount"])]
        available = [day.date for day in weather.days]
        if (available != sorted(set(available)) or not set(available).issubset(dates)
                or weather.unavailableDates != [value for value in dates if value not in available]
                or len({item.id for item in weather.locations}) != len(weather.locations)):
            raise ValueError("Inconsistent weather dates or locations")
        if weather.location is not None:
            if weather.location not in weather.locations:
                raise ValueError("Unknown location")
            if ((location_id is not None and weather.location.id != location_id)
                    or (location_id is None and weather.location != weather.locations[0])):
                raise ValueError("Unconfirmed location")
        for day in weather.days:
            if (day.minTemperature is not None and day.maxTemperature is not None
                    and day.minTemperature > day.maxTemperature):
                raise ValueError("Invalid temperatures")
            if all(value is None for key, value in day.model_dump().items() if key != "date"):
                raise ValueError("Empty weather day")
        if weather.status in ("available", "partial", "outside_window"):
            if weather.location is None or weather.retrievedAt is None:
                raise ValueError("Missing forecast source")
            if datetime.fromisoformat(weather.retrievedAt).tzinfo is None:
                raise ValueError("Missing retrieval timezone")
            if (weather.status == "available" and len(available) != len(dates)
                    or weather.status == "partial" and not 0 < len(available) < len(dates)
                    or weather.status == "outside_window" and available):
                raise ValueError("Inconsistent forecast status")
        elif available or weather.retrievedAt is not None:
            raise ValueError("Unexpected forecast")
        if weather.status == "choose_location" and (not weather.locations or weather.location is not None):
            raise ValueError("Invalid location choice")
        if weather.status == "not_found" and (weather.locations or weather.location is not None):
            raise ValueError("Invalid missing location")
        return {"summary": summary, "weather": weather.model_dump()}
    except (ValidationError, ValueError, TypeError, KeyError):
        raise IntegrationError("invalid_dependency_response") from None


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    source: str = Field(min_length=1, max_length=200)
    chunk_id: str = Field(min_length=1, max_length=160, pattern=r"^[a-zA-Z0-9_-]+#\d+$")
    snippet: str = Field(min_length=1, max_length=2000)
    score: float = Field(gt=0, le=1)


def validate_advice(body):
    try:
        if not isinstance(body, dict) or set(body) != {"answer", "citations", "confidence"}:
            raise ValueError("Invalid advice")
        answer, citations, confidence = body["answer"], body["citations"], body["confidence"]
        if not isinstance(answer, str) or not 1 <= len(answer.strip()) <= 2000 or not isinstance(citations, list):
            raise ValueError("Invalid advice")
        if confidence == "insufficient":
            if citations or answer != INSUFFICIENT_ANSWER:
                raise ValueError("Invalid abstention")
            return body
        if confidence not in ("high", "medium", "low") or not 1 <= len(citations) <= 3:
            raise ValueError("Invalid confidence")
        validated = [Citation.model_validate(item) for item in citations]
        identifiers = [item.chunk_id for item in validated]
        if len(identifiers) != len(set(identifiers)) or set(re.findall(r"\[([^\[\]]+)\]", answer)) != set(identifiers):
            raise ValueError("Invalid references")
        return {"answer": answer, "citations": [item.model_dump() for item in validated], "confidence": confidence}
    except (ValidationError, ValueError, TypeError):
        raise IntegrationError("invalid_dependency_response") from None


class McpClient:
    def __init__(self, url):
        self.url = url

    def summary(self, trip_id):
        return anyio.run(self._call, "itinerary.get_summary", {"trip_id": trip_id}, 5)["summary"]

    def itinerary(self, trip_id):
        return anyio.run(self._call, "itinerary.get_itinerary", {"trip_id": trip_id}, 5)

    def preview_edit(self, trip_id, operation):
        return anyio.run(self._call, "itinerary.preview_edit", {"trip_id": trip_id, "operation": operation}, 5)

    def apply_edit(self, trip_id, token):
        return anyio.run(self._call, "itinerary.apply_edit", {"trip_id": trip_id, "token": token}, 5)

    def overview(self, trip_id, location_id=None):
        params = {"trip_id": trip_id}
        if location_id is not None:
            params["location_id"] = location_id
        return anyio.run(self._call, "itinerary.get_overview", params, 15)

    async def _call(self, tool, params, timeout):
        try:
            with anyio.fail_after(timeout):
                async with streamable_http_client(self.url) as streams:
                    async with ClientSession(*streams) as session:
                        await session.initialize()
                        result = await session.call_tool(tool, {"params": params})
                        if result.is_error or not isinstance(result.structured_content, dict):
                            raise IntegrationError("invalid_dependency_response")
                        body = result.structured_content
                        if body.get("ok") is False:
                            error = body.get("error")
                            code = error.get("code") if isinstance(error, dict) else None
                            raise IntegrationError(code)
                        expected = {"ok", "summary", "weather"} if tool == "itinerary.get_overview" else {"ok", "summary"}
                        if tool == "itinerary.get_itinerary":
                            expected = {"ok", "summary", "stops"}
                        elif tool == "itinerary.preview_edit":
                            expected = {"ok", "tripId", "token", "changes", "expiresIn"}
                        elif tool == "itinerary.apply_edit":
                            expected = {"ok", "tripId", "applied", "changes"}
                        if body.get("ok") is not True or set(body) != expected:
                            raise IntegrationError("invalid_dependency_response")
                        return {key: value for key, value in body.items() if key != "ok"}
        except IntegrationError:
            raise
        except TimeoutError:
            raise IntegrationError("dependency_timeout") from None
        except Exception as exception:
            if isinstance(exception, BaseExceptionGroup):
                matching = exception.subgroup(IntegrationError)
                if matching:
                    while isinstance(matching, BaseExceptionGroup):
                        matching = matching.exceptions[0]
                    raise matching from None
            raise IntegrationError("dependency_unavailable") from None


class RagClient:
    def __init__(self, url):
        self.url = url.rstrip("/")

    def advice(self, question, trip_context=None):
        return anyio.run(self._advice, question, trip_context)

    async def _advice(self, question, trip_context=None):
        try:
            payload = {"feature": "student-2", "question": question}
            if trip_context is not None:
                payload["tripContext"] = trip_context
            with anyio.fail_after(30):
                async with httpx.AsyncClient(timeout=28) as client:
                    async with client.stream("POST", f"{self.url}/query", json=payload) as response:
                        if response.status_code != 200:
                            code = {503: "dependency_unavailable", 504: "dependency_timeout"}.get(response.status_code, "invalid_dependency_response")
                            raise IntegrationError(code)
                        content = bytearray()
                        async for chunk in response.aiter_bytes(chunk_size=4096):
                            if len(content) + len(chunk) > 16000:
                                raise IntegrationError("invalid_dependency_response")
                            content.extend(chunk)
                        return json.loads(content)
        except IntegrationError:
            raise
        except (TimeoutError, httpx.TimeoutException):
            raise IntegrationError("dependency_timeout") from None
        except httpx.HTTPError:
            raise IntegrationError("dependency_unavailable") from None
        except ValueError:
            raise IntegrationError("invalid_dependency_response") from None