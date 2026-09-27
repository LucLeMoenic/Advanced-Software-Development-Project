"""Client for the shared Release 1 RAG server, scoped to the "student-3"
feature. Follows database_client.py's shape: env URL, timeout, a
``_request``-style helper, and custom exceptions the routes map to
JSON/status codes.
"""

import os

import requests

RAG_SERVER_URL = os.environ.get("RAG_SERVER_URL", "http://localhost:5500")
REQUEST_TIMEOUT = 30  # the RAG server itself deadlines its /query handler at 25s
FEATURE = "student-3"


class RagDisabledError(Exception):
    """RAG is disabled (RAG_ENABLED is not "true"); no network call is made."""


class RagUnavailableError(Exception):
    """The RAG server could not be reached (connection/timeout)."""


class RagResponseError(Exception):
    """The RAG server responded, but not in the shape we expected, or
    reported its own domain error (a validation error, an unavailable or
    busy local model, and so on)."""

    def __init__(self, message, code="unknown"):
        super().__init__(message)
        self.code = code


def _enabled():
    # Read fresh each call (not cached at import time) so tests can toggle
    # RAG_ENABLED with monkeypatch.setenv without reloading this module.
    return os.environ.get("RAG_ENABLED", "true").lower() == "true"


def _error_message(response):
    try:
        body = response.json()
    except ValueError:
        return f"RAG server returned status {response.status_code}."
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict) and isinstance(error.get("message"), str):
        return error["message"]
    return f"RAG server returned status {response.status_code}."


def _error_code(response):
    try:
        body = response.json()
    except ValueError:
        return "unknown"
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict) and isinstance(error.get("code"), str):
        return error["code"]
    return "unknown"


def ask(question):
    if not _enabled():
        raise RagDisabledError("RAG is disabled.")

    try:
        response = requests.post(
            f"{RAG_SERVER_URL}/query",
            json={"feature": FEATURE, "question": question},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.exceptions.RequestException as exc:
        raise RagUnavailableError(str(exc)) from exc

    if response.status_code != 200:
        raise RagResponseError(_error_message(response), code=_error_code(response))

    try:
        body = response.json()
    except ValueError as exc:
        raise RagResponseError("RAG server returned invalid JSON.") from exc

    if not isinstance(body, dict) or set(body) != {"answer", "citations", "confidence"}:
        raise RagResponseError("RAG server returned an unexpected result shape.")

    return body
