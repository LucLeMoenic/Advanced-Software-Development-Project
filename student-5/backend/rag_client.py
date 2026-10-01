"""Client for the shared Release 1 RAG server, scoped to ``student-5``.

Marked requirement: Frontend -> Backend/API -> RAG server -> knowledge base.
The browser never calls the RAG server; this module is the only part of the
backend that does.

The reply is validated against the shared contract before it is returned, so
the routes can trust that a citation really has a source, chunk id, snippet and
score, and that an ``insufficient`` answer carries no citations.
"""

import math
from typing import Any, Dict

import requests

DEFAULT_RAG_SERVER_URL = "http://host.docker.internal:5500"
FEATURE = "student-5"
# The RAG server deadlines its own /query handler at 25 s, so this only fires
# when the server itself is wedged.
DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_QUESTION_LENGTH = 500
CONFIDENCE_LEVELS = ("high", "medium", "low", "insufficient")
INSUFFICIENT_ANSWER = "Not enough information in the knowledge base to answer this."


class RagDisabled(Exception):
    """RAG is switched off for this deployment."""


class RagUnavailable(Exception):
    """The RAG server could not answer (unreachable, failed or malformed)."""

    def __init__(self, message: str, code: str = "rag_unavailable") -> None:
        super().__init__(message)
        self.code = code


class RagTimeout(RagUnavailable):
    """The RAG server, or the model behind it, ran out of time."""

    def __init__(self, message: str = "The knowledge base took too long to answer.") -> None:
        super().__init__(message, "rag_timeout")


def _citation(item: Any) -> Dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError("citation")
    for field in ("source", "chunk_id", "snippet"):
        if not isinstance(item.get(field), str) or not item[field].strip():
            raise ValueError(field)
    score = item.get("score")
    if type(score) not in (int, float) or not math.isfinite(score):
        raise ValueError("score")
    return {field: item[field] for field in ("source", "chunk_id", "snippet", "score")}


def validate_answer(body: Any) -> Dict[str, Any]:
    """Return the contract fields of a RAG reply, or raise ValueError."""
    if not isinstance(body, dict):
        raise ValueError("body")
    answer, citations, confidence = body.get("answer"), body.get("citations"), body.get("confidence")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("answer")
    if confidence not in CONFIDENCE_LEVELS or not isinstance(citations, list):
        raise ValueError("confidence")
    cleaned = [_citation(item) for item in citations]
    if (confidence == "insufficient") != (not cleaned):
        raise ValueError("citations do not match confidence")
    return {"answer": answer, "citations": cleaned, "confidence": confidence}


def _server_error(response: requests.Response) -> RagUnavailable:
    try:
        error = response.json().get("error")
        code = error.get("code") if isinstance(error, dict) else None
    except (ValueError, AttributeError):
        code = None
    if response.status_code == 504 or code == "dependency_timeout":
        return RagTimeout()
    return RagUnavailable("The knowledge base could not answer right now.")


class RagClient:
    """Asks the shared RAG server questions over the ``student-5`` knowledge."""

    def __init__(self, url: str, enabled: bool, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.url = url.rstrip("/")
        self.enabled = enabled
        self.timeout = timeout

    def ask(self, question: str) -> Dict[str, Any]:
        if not self.enabled:
            raise RagDisabled("RAG is disabled.")
        try:
            response = requests.post(
                self.url + "/query",
                json={"feature": FEATURE, "question": question},
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise RagTimeout() from exc
        except requests.RequestException as exc:
            raise RagUnavailable("The knowledge base is unavailable.") from exc

        if response.status_code != 200:
            raise _server_error(response)
        try:
            return validate_answer(response.json())
        except ValueError as exc:
            raise RagUnavailable("The knowledge base returned an unexpected answer.") from exc
