"""Client for the shared Release 2 Multi-Agent Server, scoped to ``student-5``.

Marked requirement: Frontend -> Backend/API -> Multi-Agent Server -> Planner ->
Worker -> Reviewer -> Human Review. The browser never calls the server; this
module is the only part of the backend that does.

The server is asynchronous: ``POST /workflows`` answers ``202`` at once and the
three agents run in the background, so callers poll ``GET /workflows/{id}``.
Every call here is therefore short and bounded, even though a whole review
takes minutes.

Three outcomes, three exceptions, like the MCP and RAG clients:

* ``MultiAgentDisabled``  -- switched off for this deployment; nothing is sent.
* ``MultiAgentRefused``   -- the server answered with a meaningful refusal
  (busy, not found, already decided, a decision it would not accept). Carries
  a status and code the routes can return honestly.
* ``MultiAgentUnavailable`` -- unreachable, timed out, or a reply that breaks
  the shared contract.
"""

import re
from typing import Any, Dict, List, Optional

import requests

DEFAULT_MULTI_AGENT_SERVER_URL = "http://host.docker.internal:5600"
FEATURE = "student-5"
# Every call returns immediately on the server side (the agents run in the
# background), so this only fires when the server itself is wedged.
DEFAULT_TIMEOUT_SECONDS = 10.0

# Same pattern as the server's store.py. A workflow id is interpolated into a
# server URL, so anything else is refused before a request is built.
WORKFLOW_ID = re.compile(r"^wf-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")

RUNNING_STATUSES = ("queued", "planning", "working", "reviewing")
DECIDED_STATUSES = ("approved", "corrected", "partially_accepted", "rejected")
STATUSES = RUNNING_STATUSES + ("awaiting_human_review",) + DECIDED_STATUSES + ("failed",)
DECISIONS = ("approve", "correct", "partial", "reject")

# The list fields each stage must carry, so a template can iterate them safely.
STAGE_LISTS = {
    "plan": ("steps", "required_evidence_ids", "success_criteria"),
    "work": ("items",),
    "final_output": ("items",),
    "review": ("findings", "recommendations"),
}


class MultiAgentDisabled(Exception):
    """Multi-Agent is switched off for this deployment."""


class MultiAgentUnavailable(Exception):
    """The Multi-Agent Server could not answer (unreachable, failed or malformed)."""


class MultiAgentRefused(Exception):
    """The server answered, but refused the request for a reason worth showing."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def review_not_found() -> MultiAgentRefused:
    return MultiAgentRefused(404, "review_not_found", "No readiness review with that id for this destination.")


def _work_items(work: Dict[str, Any]) -> None:
    for item in work["items"]:
        if not isinstance(item, dict):
            raise ValueError("item")
        for field in ("id", "subject", "detail"):
            if not isinstance(item.get(field), str):
                raise ValueError(field)
        if not isinstance(item.get("evidence_ids"), list):
            raise ValueError("evidence_ids")


def validate_record(body: Any, workflow_id: str) -> Dict[str, Any]:
    """Return a workflow record that is safe to render, or raise ValueError.

    Checks shape only. Whether the record belongs to Student 5 and to the
    requested destination is decided by the caller, which knows the evidence
    convention.
    """
    if not isinstance(body, dict) or body.get("id") != workflow_id:
        raise ValueError("id")
    status = body.get("status")
    if status not in STATUSES:
        raise ValueError("status")
    evidence = body.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("evidence")
    for item in evidence:
        if not isinstance(item, dict) or not all(isinstance(item.get(f), str) for f in ("id", "title", "text")):
            raise ValueError("evidence item")
    for stage, fields in STAGE_LISTS.items():
        value = body.get(stage)
        if value is None:
            continue
        if not isinstance(value, dict) or any(not isinstance(value.get(f), list) for f in fields):
            raise ValueError(stage)
    for stage in ("work", "final_output"):
        if body.get(stage) is not None:
            _work_items(body[stage])
    if status == "awaiting_human_review" or status in DECIDED_STATUSES:
        if not all(body.get(stage) for stage in ("plan", "work", "review")):
            raise ValueError("missing stages")
    if status in DECIDED_STATUSES and not isinstance(body.get("human_decision"), dict):
        raise ValueError("human_decision")
    return body


def _server_error(response: requests.Response) -> Exception:
    """Map a non-success reply onto a refusal worth relaying, or unavailable."""
    try:
        error = response.json().get("error")
        code, message = error.get("code"), error.get("message")
    except (ValueError, AttributeError):
        code, message = None, None
    if not isinstance(message, str):
        message = ""
    if response.status_code == 503 and code == "busy":
        return MultiAgentRefused(
            503, "multi_agent_busy", "Another review is already running. Try again when it finishes.")
    if response.status_code == 404:
        return review_not_found()
    if response.status_code == 409:
        return MultiAgentRefused(409, "review_not_awaiting_decision", message[:300] or "This review is not awaiting a decision.")
    if response.status_code == 400 and isinstance(code, str):
        # The server owns the decision rules (reject needs notes, partial needs
        # real item ids...), so its own code and wording reach the caller.
        return MultiAgentRefused(400, code, message[:300] or "The Multi-Agent Server rejected the request.")
    return MultiAgentUnavailable("The Multi-Agent Server could not complete the request.")


class MultiAgentClient:
    """Starts, polls and decides ``student-5`` workflows on the shared server."""

    def __init__(self, url: str, enabled: bool, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.url = url.rstrip("/")
        self.enabled = enabled
        self.timeout = timeout

    def ensure_enabled(self) -> None:
        """Raise ``MultiAgentDisabled`` if the feature is off, before any other work."""
        if not self.enabled:
            raise MultiAgentDisabled("Multi-Agent is disabled.")

    def _request(self, method: str, path: str, expected: int, body: Optional[Dict[str, Any]] = None) -> Any:
        self.ensure_enabled()
        try:
            response = requests.request(method, self.url + path, json=body, timeout=self.timeout)
        except requests.Timeout as exc:
            raise MultiAgentUnavailable("The Multi-Agent Server timed out.") from exc
        except requests.RequestException as exc:
            raise MultiAgentUnavailable("The Multi-Agent Server is unavailable.") from exc
        if response.status_code != expected:
            raise _server_error(response)
        try:
            return response.json()
        except ValueError as exc:
            raise MultiAgentUnavailable("The Multi-Agent Server returned an unexpected reply.") from exc

    def start(self, task: str, evidence: List[Dict[str, str]], submitted_by: str) -> Dict[str, str]:
        """Queue one workflow; returns ``{"id", "status"}``."""
        try:
            body = self._request("POST", "/workflows", 202, {
                "feature": FEATURE, "task": task, "evidence": evidence, "submitted_by": submitted_by,
            })
        except MultiAgentRefused as exc:
            # The caller only names a destination; the evidence is built here,
            # so a 400 means this backend broke the contract, not the caller.
            if exc.status == 400:
                raise MultiAgentUnavailable("The Multi-Agent Server rejected the review evidence.") from exc
            raise
        if (not isinstance(body, dict) or not isinstance(body.get("id"), str)
                or not WORKFLOW_ID.match(body["id"]) or body.get("status") not in STATUSES):
            raise MultiAgentUnavailable("The Multi-Agent Server returned an unexpected reply.")
        return {"id": body["id"], "status": body["status"]}

    def get(self, workflow_id: str) -> Dict[str, Any]:
        """The full workflow record, shape-checked."""
        if not isinstance(workflow_id, str) or not WORKFLOW_ID.match(workflow_id):
            self.ensure_enabled()
            raise review_not_found()
        return self._validated(self._request("GET", "/workflows/" + workflow_id, 200), workflow_id)

    def decide(self, workflow_id: str, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Record the human decision; returns the updated record."""
        if not isinstance(workflow_id, str) or not WORKFLOW_ID.match(workflow_id):
            self.ensure_enabled()
            raise review_not_found()
        body = self._request("POST", "/workflows/{}/decision".format(workflow_id), 200, decision)
        return self._validated(body, workflow_id)

    @staticmethod
    def _validated(body: Any, workflow_id: str) -> Dict[str, Any]:
        try:
            return validate_record(body, workflow_id)
        except ValueError as exc:
            raise MultiAgentUnavailable("The Multi-Agent Server returned an unexpected reply.") from exc
