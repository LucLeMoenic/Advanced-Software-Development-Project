"""Student 4's read-only dashboard summary MCP tool."""

import asyncio
import json
import os
from decimal import Decimal, ROUND_HALF_UP, localcontext
from typing import Any
from urllib.parse import urlsplit

import httpx2
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field, field_validator

BACKEND_ENV = "STUDENT4_BACKEND_API_URL"
DEFAULT_BACKEND_ORIGIN = "http://127.0.0.1:5204"
MAX_RESPONSE_BYTES = 16 * 1024
SUMMARY_TIMEOUT_SECONDS = 10
LONG_MIN = -(2**63)
LONG_MAX = 2**63 - 1
CURRENCIES = {"AUD", "USD", "EUR", "GBP", "NZD", "CAD", "SGD"}
CATEGORIES = {"accommodation", "food", "transport", "activities", "shopping", "other"}
STATUSES = {"within_budget", "warning", "overspent"}


class BudgetSummaryParams(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    journey_label: str = Field(min_length=1, max_length=80)

    @field_validator("journey_label", mode="before")
    @classmethod
    def normalize_journey_label(cls, value):
        if not isinstance(value, str):
            raise ValueError("Journey label must be text.")
        value = value.strip()
        if not 1 <= len(value) <= 80:
            raise ValueError("Journey label must contain 1 to 80 characters.")
        return value


def failure(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _backend_origin() -> str:
    value = os.getenv(BACKEND_ENV, DEFAULT_BACKEND_ORIGIN)
    try:
        parsed = urlsplit(value)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
            raise ValueError("Invalid backend origin")
        _ = parsed.port
        return f"{parsed.scheme}://{parsed.netloc}"
    except (TypeError, ValueError):
        raise ValueError("Invalid backend origin") from None


def _long(value: Any) -> int:
    if type(value) is not int or not LONG_MIN <= value <= LONG_MAX:
        raise ValueError("Invalid money value")
    return value


def _percentage(value: Any, actual: int, planned: int) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        raise ValueError("Invalid percentage")
    received = Decimal(value)
    if not received.is_finite():
        raise ValueError("Invalid percentage")
    with localcontext() as context:
        context.prec = 50
        expected = (Decimal(actual) * Decimal(100) / Decimal(planned)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP)
    if received != expected:
        raise ValueError("Inconsistent percentage")
    return float(received)


def _status(actual: int, planned: int) -> str:
    if actual > planned:
        return "overspent"
    if actual * 100 >= planned * 80:
        return "warning"
    return "within_budget"


def _validate_summary(value: Any, requested_label: str) -> dict[str, Any]:
    expected_fields = {
        "journeyLabel", "baseCurrency", "plannedAmountMinor", "actualAmountMinor",
        "remainingAmountMinor", "percentageUsed", "categories",
    }
    if not isinstance(value, dict) or set(value) != expected_fields:
        raise ValueError("Invalid dashboard fields")

    label = value["journeyLabel"]
    currency = value["baseCurrency"]
    categories = value["categories"]
    if (not isinstance(label, str) or not 1 <= len(label.strip()) <= 80
            or label != label.strip() or label.casefold() != requested_label.casefold()):
        raise ValueError("Unexpected journey")
    if not isinstance(currency, str) or currency.upper() not in CURRENCIES:
        raise ValueError("Invalid base currency")
    if not isinstance(categories, list) or not 1 <= len(categories) <= len(CATEGORIES):
        raise ValueError("Invalid categories")

    total_planned = _long(value["plannedAmountMinor"])
    total_actual = _long(value["actualAmountMinor"])
    total_remaining = _long(value["remainingAmountMinor"])
    if total_planned <= 0 or total_actual < 0 or total_remaining != total_planned - total_actual:
        raise ValueError("Inconsistent dashboard totals")
    total_percentage = _percentage(value["percentageUsed"], total_actual, total_planned)

    seen: set[str] = set()
    planned_values = []
    actual_values = []
    remaining_values = []
    validated_categories = []
    for category in categories:
        category_fields = {
            "category", "plannedAmountMinor", "actualAmountMinor", "remainingAmountMinor",
            "percentageUsed", "status",
        }
        if not isinstance(category, dict) or set(category) != category_fields:
            raise ValueError("Invalid category fields")
        name = category["category"]
        if not isinstance(name, str) or name.strip() != name or name.casefold() not in CATEGORIES:
            raise ValueError("Invalid category")
        if name.casefold() in seen:
            raise ValueError("Duplicate category")
        seen.add(name.casefold())

        planned = _long(category["plannedAmountMinor"])
        actual = _long(category["actualAmountMinor"])
        remaining = _long(category["remainingAmountMinor"])
        if planned <= 0 or actual < 0 or remaining != planned - actual:
            raise ValueError("Inconsistent category totals")
        percentage = _percentage(category["percentageUsed"], actual, planned)
        status = category["status"]
        expected_status = _status(actual, planned)
        if not isinstance(status, str) or status not in STATUSES or status != expected_status:
            raise ValueError("Inconsistent category status")

        planned_values.append(planned)
        actual_values.append(actual)
        remaining_values.append(remaining)
        validated_categories.append({**category, "percentageUsed": percentage})

    if (sum(planned_values) != total_planned or sum(actual_values) != total_actual
            or sum(remaining_values) != total_remaining):
        raise ValueError("Inconsistent category totals")

    return {**value, "percentageUsed": total_percentage, "categories": validated_categories}


def _parse_constant(value: str):
    raise ValueError(f"Invalid JSON number: {value}")


async def _fetch_summary(journey_label: str) -> dict[str, Any]:
    try:
        origin = _backend_origin()
    except ValueError:
        return failure("dependency_unavailable", "The budget service is unavailable.")

    try:
        async with asyncio.timeout(SUMMARY_TIMEOUT_SECONDS):
            async with httpx2.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "GET",
                    f"{origin}/api/dashboard",
                    params={"journeyLabel": journey_label},
                    headers={"Accept": "application/json"},
                ) as response:
                    if response.status_code == 400:
                        return failure("invalid_input", "The journey label is invalid.")
                    if response.status_code == 404:
                        return failure("journey_not_found", "The journey was not found.")
                    if response.status_code == 503:
                        return failure("dependency_unavailable", "The budget service is unavailable.")
                    if response.status_code == 504:
                        return failure("dependency_timeout", "The budget service timed out.")
                    if response.status_code != 200:
                        return failure("invalid_dependency_response", "The budget service returned an unusable response.")

                    body = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=4096):
                        if len(body) + len(chunk) > MAX_RESPONSE_BYTES:
                            return failure("response_too_large", "The budget service response exceeded the size limit.")
                        body.extend(chunk)

            summary = json.loads(bytes(body), parse_float=Decimal, parse_constant=_parse_constant)
            return {"ok": True, "summary": _validate_summary(summary, journey_label)}
    except TimeoutError:
        return failure("dependency_timeout", "The budget service timed out.")
    except httpx2.TimeoutException:
        return failure("dependency_timeout", "The budget service timed out.")
    except httpx2.RequestError:
        return failure("dependency_unavailable", "The budget service is unavailable.")
    except (json.JSONDecodeError, ValueError, TypeError, KeyError, OverflowError):
        return failure("invalid_dependency_response", "The budget service returned an unusable response.")


def _strict_arguments(mcp: MCPServer) -> None:
    tool = mcp._tool_manager.get_tool("budget.get_summary")
    tool.fn_metadata.arg_model.model_config["extra"] = "forbid"
    tool.fn_metadata.arg_model.model_rebuild(force=True)
    tool.parameters = tool.fn_metadata.arg_model.model_json_schema(by_alias=True)


def register(mcp: MCPServer) -> None:
    read_only = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)

    @mcp.tool(name="budget.get_summary", annotations=read_only)
    async def get_summary(params: BudgetSummaryParams) -> dict[str, Any]:
        """Read the current authoritative budget totals and category statuses for one journey."""
        return await _fetch_summary(params.journey_label)

    _strict_arguments(mcp)