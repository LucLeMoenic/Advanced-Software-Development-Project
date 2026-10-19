"""Client for the shared Release 2 Multi-Agent Server, scoped to the
"student-3" feature. Follows rag_client.py's shape: env URL, a short timeout,
a ``_request`` helper, and custom exceptions the routes map to JSON/status codes.

The server runs workflows asynchronously (a Planner -> Worker -> Reviewer run on
a local model takes minutes), so every call here returns quickly: start a
workflow, poll it, then send the human decision.

Disabled by default: MULTI_AGENT_ENABLED must be "true" for any network call.
"""

import os

import requests

MULTI_AGENT_SERVER_URL = os.environ.get("MULTI_AGENT_SERVER_URL", "http://localhost:5600")
REQUEST_TIMEOUT = 15  # the server answers immediately; it does not hold the request open
FEATURE = "student-3"


class MultiAgentDisabledError(Exception):
    """Multi-Agent is disabled (MULTI_AGENT_ENABLED is not "true"); no network call is made."""


class MultiAgentUnavailableError(Exception):
    """The Multi-Agent Server could not be reached (connection/timeout)."""


class MultiAgentResponseError(Exception):
    """The server responded with an error, or with an unexpected shape.

    `status` and `code` carry the server's own HTTP status and error code
    (for example 409 not_awaiting_review, 503 busy) so routes can pass them on.
    """

    def __init__(self, message, code="unknown", status=502):
        super().__init__(message)
        self.code = code
        self.status = status


def enabled():
    # Read fresh each call so tests can toggle it with monkeypatch.setenv.
    return os.environ.get("MULTI_AGENT_ENABLED", "false").lower() == "true"


def require_enabled():
    if not enabled():
        raise MultiAgentDisabledError("Multi-Agent is disabled.")


def _request(method, path, **kwargs):
    require_enabled()
    try:
        response = requests.request(
            method, f"{MULTI_AGENT_SERVER_URL}{path}", timeout=REQUEST_TIMEOUT, **kwargs
        )
    except requests.exceptions.RequestException as exc:
        raise MultiAgentUnavailableError(str(exc)) from exc

    try:
        body = response.json()
    except ValueError:
        body = None

    if response.status_code >= 400:
        error = body.get("error") if isinstance(body, dict) else None
        if isinstance(error, dict):
            raise MultiAgentResponseError(
                str(error.get("message") or f"Multi-Agent Server returned status {response.status_code}."),
                code=str(error.get("code") or "unknown"),
                status=response.status_code,
            )
        raise MultiAgentResponseError(
            f"Multi-Agent Server returned status {response.status_code}.", status=response.status_code
        )
    if not isinstance(body, dict):
        raise MultiAgentResponseError("Multi-Agent Server returned an unexpected result shape.")
    return body


def health():
    body = _request("GET", "/health")
    if body.get("status") != "ok":
        raise MultiAgentResponseError("Multi-Agent Server reported it is not healthy.")
    return {"status": "ok", "busy": bool(body.get("busy"))}


def start_workflow(task, evidence):
    body = _request(
        "POST", "/workflows",
        json={"feature": FEATURE, "task": task, "evidence": evidence, "submitted_by": "student-3-ui"},
    )
    if "id" not in body or "status" not in body:
        raise MultiAgentResponseError("Multi-Agent Server returned an unexpected result shape.")
    return {"id": body["id"], "status": body["status"]}


def get_workflow(workflow_id):
    return _request("GET", f"/workflows/{workflow_id}")


def decide(workflow_id, decision):
    return _request("POST", f"/workflows/{workflow_id}/decision", json=decision)
