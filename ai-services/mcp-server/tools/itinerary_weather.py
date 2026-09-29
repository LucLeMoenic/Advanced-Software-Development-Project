import json
from datetime import date, datetime, timedelta, timezone
from time import monotonic

import requests
from pydantic import BaseModel, ConfigDict, Field


class Location(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True, allow_inf_nan=False)
    id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=200)
    country: str = Field(default="", max_length=200)
    admin1: str = Field(default="", max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class ForecastDay(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    date: str
    weatherCode: int | None = Field(ge=0, le=99)
    minTemperature: float | None = Field(ge=-100, le=70)
    maxTemperature: float | None = Field(ge=-100, le=70)
    precipitationProbability: float | None = Field(ge=0, le=100)


def read_provider(url, params, deadline):
    remaining = deadline - monotonic()
    if remaining <= 0:
        raise requests.Timeout()
    with requests.get(url, params=params, timeout=(min(2, remaining), min(3, remaining)),
                      stream=True, allow_redirects=False) as response:
        if response.status_code != 200:
            raise ValueError("Weather provider failed")
        content = bytearray()
        for chunk in response.iter_content(chunk_size=4096):
            if monotonic() > deadline:
                raise requests.Timeout()
            if len(content) + len(chunk) > 65536:
                raise ValueError("Weather response too large")
            content.extend(chunk)
        body = json.loads(content)
        if not isinstance(body, dict) or body.get("error"):
            raise ValueError("Invalid weather response")
        return body


def trip_weather(summary, location_id=None):
    start = date.fromisoformat(summary["startDate"])
    dates = [(start + timedelta(days=offset)).isoformat() for offset in range(summary["dayCount"])]
    result = {"status": "unavailable", "locations": [], "location": None, "days": [],
              "unavailableDates": dates, "retrievedAt": None}
    deadline = monotonic() + 8
    try:
        geocoding = read_provider("https://geocoding-api.open-meteo.com/v1/search", {
            "name": summary["destination"], "count": 5, "language": "en", "format": "json",
        }, deadline)
        candidates = geocoding.get("results", [])
        if not isinstance(candidates, list) or len(candidates) > 5:
            raise ValueError("Invalid locations")
        locations = [Location.model_validate(item).model_dump() for item in candidates]
        if len({item["id"] for item in locations}) != len(locations):
            raise ValueError("Duplicate locations")
        result["locations"] = locations
        if not locations:
            result["status"] = "not_found"
            return result
        selected = next((item for item in locations if item["id"] == location_id), None)
        if location_id is None and len(locations) == 1:
            selected = locations[0]
        if selected is None:
            result["status"] = "choose_location"
            return result
        result["location"] = selected
        fields = {"weather_code": "weatherCode", "temperature_2m_min": "minTemperature",
                  "temperature_2m_max": "maxTemperature", "precipitation_probability_max": "precipitationProbability"}
        forecast = read_provider("https://api.open-meteo.com/v1/forecast", {
            "latitude": selected["latitude"], "longitude": selected["longitude"],
            "daily": ",".join(fields), "forecast_days": 16, "timezone": "auto", "temperature_unit": "celsius",
        }, deadline)
        daily = forecast["daily"]
        units = forecast["daily_units"]
        if (units.get("temperature_2m_min") != "\u00b0C" or units.get("temperature_2m_max") != "\u00b0C"
                or units.get("precipitation_probability_max") != "%" or units.get("weather_code") != "wmo code"):
            raise ValueError("Unexpected forecast units")
        forecast_dates = daily["time"]
        if not isinstance(forecast_dates, list) or not 1 <= len(forecast_dates) <= 16:
            raise ValueError("Invalid forecast dates")
        parsed_dates = [date.fromisoformat(value) for value in forecast_dates]
        if any(value.isoformat() != raw for value, raw in zip(parsed_dates, forecast_dates)):
            raise ValueError("Invalid date format")
        if abs((parsed_dates[0] - datetime.now(timezone.utc).date()).days) > 1:
            raise ValueError("Stale forecast")
        if parsed_dates != [parsed_dates[0] + timedelta(days=offset) for offset in range(len(parsed_dates))]:
            raise ValueError("Nonconsecutive forecast")
        if any(not isinstance(daily[key], list) or len(daily[key]) != len(forecast_dates) for key in fields):
            raise ValueError("Mismatched forecast arrays")
        days = []
        for index, forecast_date in enumerate(forecast_dates):
            day = ForecastDay.model_validate({"date": forecast_date, **{
                target: daily[source][index] for source, target in fields.items()
            }})
            if (day.minTemperature is not None and day.maxTemperature is not None
                    and day.minTemperature > day.maxTemperature):
                raise ValueError("Invalid temperature range")
            if forecast_date in dates and any(getattr(day, field) is not None for field in fields.values()):
                days.append(day.model_dump())
        result["days"] = days
        result["unavailableDates"] = [value for value in dates if value not in {day["date"] for day in days}]
        result["status"] = ("available" if len(days) == len(dates) else "partial" if days
                            else "outside_window" if not set(dates).intersection(forecast_dates) else "unavailable")
        result["retrievedAt"] = datetime.now(timezone.utc).isoformat() if result["status"] != "unavailable" else None
    except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError):
        result.update(status="unavailable", days=[], unavailableDates=dates, retrievedAt=None)
    return result