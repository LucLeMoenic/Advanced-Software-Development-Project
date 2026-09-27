import json
import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

import anyio
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from pydantic import BaseModel, ConfigDict, Field, ValidationError


ERRORS = {
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


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    source: str = Field(min_length=1, max_length=200)
    chunk_id: str = Field(min_length=1, max_length=160, pattern=r"^[a-zA-Z0-9_-]+#\d+$")
    snippet: str = Field(min_length=1, max_length=280)
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
        return anyio.run(self._summary, trip_id)

    async def _summary(self, trip_id):
        try:
            with anyio.fail_after(5):
                async with streamable_http_client(self.url) as streams:
                    async with ClientSession(*streams) as session:
                        await session.initialize()
                        result = await session.call_tool("itinerary.get_summary", {"params": {"trip_id": trip_id}})
                        if result.is_error or not isinstance(result.structured_content, dict):
                            raise IntegrationError("invalid_dependency_response")
                        body = result.structured_content
                        if body.get("ok") is False:
                            error = body.get("error")
                            code = error.get("code") if isinstance(error, dict) else None
                            raise IntegrationError(code)
                        if body.get("ok") is not True or set(body) != {"ok", "summary"}:
                            raise IntegrationError("invalid_dependency_response")
                        return body["summary"]
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

    def advice(self, question):
        return anyio.run(self._advice, question)

    async def _advice(self, question):
        try:
            with anyio.fail_after(30):
                async with httpx.AsyncClient(timeout=28) as client:
                    async with client.stream("POST", f"{self.url}/query", json={"feature": "student-2", "question": question}) as response:
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