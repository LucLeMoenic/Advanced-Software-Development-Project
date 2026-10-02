"""Shared Release 1 RAG server.

Runs natively on the host (not a Docker Compose service, per the Release 1
brief). Backends reach it at ``RAG_SERVER_URL`` (default
``http://localhost:5500``), or ``http://host.docker.internal:5500`` from
inside a container.

Run directly: ``uvicorn server:app --host 127.0.0.1 --port 5500``
"""

import os
from typing import Literal

import anyio
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

import confidence
import retrieval
import generation

TOP_K = int(os.environ.get("RAG_TOP_K", "3"))
if not 1 <= TOP_K <= 3:
    raise ValueError("RAG_TOP_K must be between one and three.")

app = FastAPI(title="asd-shared-rag-server")


class ContextStop(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    day: int = Field(ge=1, le=31)
    activity: str = Field(min_length=1, max_length=160)
    notes: str = Field(max_length=160)


class ContextForecast(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    weatherCode: int | None = Field(ge=0, le=99)
    minTemperature: float | None = Field(ge=-100, le=70)
    maxTemperature: float | None = Field(ge=-100, le=70)
    precipitationProbability: float | None = Field(ge=0, le=100)


class ContextWeather(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: Literal["available", "partial", "outside_window", "not_found", "unavailable"]
    location: str | None = Field(max_length=605)
    retrievedAt: str | None = Field(max_length=50)
    days: list[ContextForecast] = Field(max_length=16)


class TripContext(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    destination: str = Field(min_length=2, max_length=100)
    startDate: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    endDate: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    stops: list[ContextStop] = Field(max_length=20)
    omittedStops: int = Field(ge=0)
    weather: ContextWeather | None


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    feature: Literal["student-1", "student-2", "student-3", "student-4", "student-5"]
    question: str = Field(min_length=1, max_length=1000)
    tripContext: TripContext | None = None

    @model_validator(mode="after")
    def context_feature(self):
        if self.tripContext is not None and self.feature != "student-2":
            raise ValueError("Trip context is only supported for itinerary advice.")
        return self

    @field_validator("question")
    @classmethod
    def clean_question(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Question must not be blank.")
        return value


class Citation(BaseModel):
    source: str
    chunk_id: str
    snippet: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: str


INSUFFICIENT_ANSWER = "Not enough information in the knowledge base to answer this."


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    try:
        with anyio.fail_after(25):
            index = retrieval.get_index(request.feature)
            ranked = []
            length = 0
            for chunk, score in index.top_k(request.question, k=TOP_K):
                if (confidence.categorize(score) != "insufficient" and len(chunk.text) <= 2000
                        and len(chunk.source) <= 200 and len(chunk.chunk_id) <= 160
                        and length + len(chunk.text) <= 6000):
                    ranked.append((chunk, score))
                    length += len(chunk.text)
            if not ranked:
                return generation.insufficient()
            if request.feature == "student-4":
                return await generation.generate(request.question, ranked, selection_mode=True)
            if request.tripContext is not None:
                result = await generation.generate(
                    request.question, ranked, request.tripContext.model_dump()
                )
            else:
                result = await generation.generate(request.question, ranked)
            if request.feature == "student-2":
                passages = {chunk.chunk_id: chunk.text for chunk, score in ranked}
                result = {**result, "citations": [
                    {**citation, "snippet": passages[citation["chunk_id"]]}
                    for citation in result["citations"]
                ]}
            return result
    except TimeoutError:
        raise generation.GenerationError(504, "dependency_timeout", "The grounded response timed out.") from None


@app.exception_handler(generation.GenerationError)
async def generation_error(request, exception):
    return JSONResponse(status_code=exception.status, content={"error": {
        "code": exception.code, "message": exception.message, "fields": {},
    }})


@app.exception_handler(RequestValidationError)
async def validation_error(request, exception):
    return JSONResponse(status_code=400, content={"error": {
        "code": "validation_error", "message": "Supply a known feature and a question of 1-1000 characters.", "fields": {},
    }})


@app.get("/health")
def health():
    return {"status": "ok"}
