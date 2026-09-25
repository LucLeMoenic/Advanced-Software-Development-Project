"""Shared Release 1 RAG server.

Runs natively on the host (not a Docker Compose service, per the Release 1
brief). Backends reach it at ``RAG_SERVER_URL`` (default
``http://localhost:5500``), or ``http://host.docker.internal:5500`` from
inside a container.

Run directly: ``uvicorn server:app --host 127.0.0.1 --port 5500``
"""

import os

from fastapi import FastAPI
from pydantic import BaseModel

import confidence
import retrieval

TOP_K = int(os.environ.get("RAG_TOP_K", "3"))

app = FastAPI(title="asd-shared-rag-server")


class QueryRequest(BaseModel):
    feature: str
    question: str


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
def query(request: QueryRequest):
    index = retrieval.get_index(request.feature)
    ranked = index.top_k(request.question, k=TOP_K)

    if not ranked:
        return QueryResponse(answer=INSUFFICIENT_ANSWER, citations=[], confidence="insufficient")

    top_score = float(ranked[0][1])
    second_score = float(ranked[1][1]) if len(ranked) > 1 else None
    level = confidence.categorize(top_score, second_score)

    if level == "insufficient":
        return QueryResponse(answer=INSUFFICIENT_ANSWER, citations=[], confidence="insufficient")

    citations = [
        Citation(
            source=chunk.source,
            chunk_id=chunk.chunk_id,
            snippet=chunk.text[:280],
            score=round(float(score), 4),
        )
        for chunk, score in ranked
    ]
    # Extractive, not generative: the answer is the best-matching chunk
    # verbatim, so every claim in it is directly traceable to a citation.
    # No LLM call here — keeps this server independent of Ollama/loop RAM.
    return QueryResponse(answer=ranked[0][0].text, citations=citations, confidence=level)


@app.get("/health")
def health():
    return {"status": "ok"}
