import hashlib
import json
import re
import time
from datetime import date
from typing import Literal

import httpx
from flask import Blueprint, jsonify, request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ai_clients import IntegrationError

WORKFLOW_ID = r"^wf-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$"
STATUSES = Literal["queued", "planning", "working", "reviewing", "awaiting_human_review",
                   "approved", "corrected", "partially_accepted", "rejected", "failed"]
DECISIONS = {"approve": "approved", "correct": "corrected", "partial": "partially_accepted", "reject": "rejected"}


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class Stop(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    id: int = Field(gt=0)
    tripId: int = Field(gt=0)
    day: int = Field(ge=1, le=31)
    activity: str = Field(min_length=1, max_length=160)
    notes: str = Field(max_length=1000)
    sortOrder: int = Field(ge=0)


class Snapshot(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True, allow_inf_nan=False)
    id: int = Field(gt=0)
    destination: str = Field(min_length=2, max_length=100)
    startDate: str
    endDate: str
    budget: float = Field(ge=0, le=1000000)
    interests: str = Field(max_length=500)
    stops: list[Stop]


class Evidence(Strict):
    id: str = Field(pattern=r"^[A-Za-z0-9_.:#-]{1,60}$")
    title: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=800)


class WorkItem(Strict):
    id: str = Field(pattern=r"^i[0-9]{1,2}$")
    subject: str = Field(min_length=1, max_length=120)
    detail: str = Field(min_length=1, max_length=400)
    evidence_ids: list[str] = Field(min_length=1, max_length=3)


class Work(Strict):
    summary: str = Field(min_length=1, max_length=400)
    items: list[WorkItem] = Field(min_length=1, max_length=8)


class PlanStep(Strict):
    id: str = Field(pattern=r"^s[0-9]{1,2}$")
    description: str = Field(min_length=1, max_length=200)


class Plan(Strict):
    objective: str = Field(min_length=1, max_length=300)
    steps: list[PlanStep] = Field(min_length=1, max_length=6)
    required_evidence_ids: list[str] = Field(min_length=1, max_length=10)
    success_criteria: list[str] = Field(min_length=1, max_length=5)


class Finding(Strict):
    severity: Literal["info", "warning", "blocking"]
    item_id: str | None
    message: str = Field(min_length=1, max_length=300)


class Review(Strict):
    verdict: Literal["pass", "concerns", "fail"]
    model_verdict: Literal["pass", "concerns", "fail"]
    degraded: bool
    automatic_findings: list[Finding]
    model_findings: list[Finding]
    findings: list[Finding]
    recommendations: list[str]


class Record(Strict):
    id: str = Field(pattern=WORKFLOW_ID)
    feature: Literal["student-2"]
    task: str = Field(min_length=3, max_length=500)
    submitted_by: str
    status: STATUSES
    created_at: str
    updated_at: str
    evidence: list[Evidence] = Field(min_length=1, max_length=30)
    plan: Plan | None
    work: Work | None
    review: Review | None
    human_decision: dict | None
    final_output: Work | None
    history: list[dict]
    error: dict | None


class Decision(Strict):
    decision: Literal["approve", "correct", "partial", "reject"]
    notes: str = Field(default="", max_length=1000)
    corrected_output: Work | None = None
    accepted_item_ids: list[str] | None = Field(default=None, max_length=8)


def evidence_for(body, trip_id):
    try:
        trip = Snapshot.model_validate(body)
        days = (date.fromisoformat(trip.endDate) - date.fromisoformat(trip.startDate)).days + 1
        if (trip.id != trip_id or not 1 <= days <= 31
                or len({stop.id for stop in trip.stops}) != len(trip.stops)
                or any(stop.tripId != trip_id or stop.day > days for stop in trip.stops)):
            raise ValueError("Inconsistent trip")
        trip.stops.sort(key=lambda stop: (stop.day, stop.sortOrder, stop.id))
        fingerprint = hashlib.sha256(json.dumps(
            trip.model_dump(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        summary = {"tripId": trip.id, "snapshot": fingerprint, "destination": trip.destination,
                   "startDate": trip.startDate, "endDate": trip.endDate, "totalBudget": trip.budget,
                   "stopCount": len(trip.stops), "omittedStops": max(0, len(trip.stops) - 28),
                   "notice": "Saved plans, not verified prices, availability or travel feasibility. Notes limited to 400 characters."}
        evidence = [
            {"id": f"trip-{trip_id}", "title": "Trip overview", "text": json.dumps(summary, ensure_ascii=False)},
            {"id": f"interests-{trip_id}", "title": "Saved interests", "text": trip.interests or "No interests supplied."},
        ]
        for stop in trip.stops[:28]:
            evidence.append({"id": f"stop-{stop.id}", "title": f"Day {stop.day}: {stop.activity}"[:120],
                             "text": f"Day {stop.day}. Activity: {stop.activity}. Notes: {stop.notes[:400]}"
                                     + (" [Notes truncated]" if len(stop.notes) > 400 else "")})
        return [Evidence.model_validate(item).model_dump() for item in evidence]
    except (ValueError, TypeError):
        raise IntegrationError("invalid_dependency_response") from None


def valid_work(work, evidence_ids):
    return (len({item.id for item in work.items}) == len(work.items)
            and all(set(item.evidence_ids).issubset(evidence_ids) for item in work.items))


def validate_record(body, workflow_id, trip_id):
    if isinstance(body, dict) and body.get("feature") != "student-2":
        raise IntegrationError("workflow_not_found")
    try:
        record = Record.model_validate(body)
        if record.id != workflow_id:
            raise ValueError("Wrong workflow")
        ids = {item.id for item in record.evidence}
        if len(ids) != len(record.evidence):
            raise ValueError("Duplicate evidence")
        summary = next((item for item in record.evidence if item.id == f"trip-{trip_id}"), None)
        if summary is None:
            raise IntegrationError("workflow_not_found")
        metadata = json.loads(summary.text)
        if summary != record.evidence[0]:
            raise ValueError("Trip summary must be first")
        if metadata.get("tripId") != trip_id:
            raise IntegrationError("workflow_not_found")
        if not re.fullmatch(r"[0-9a-f]{64}", metadata.get("snapshot", "")):
            raise ValueError("Missing snapshot")
        if record.plan and not set(record.plan.required_evidence_ids).issubset(ids):
            raise ValueError("Unknown plan evidence")
        if any(work and not valid_work(work, ids) for work in (record.work, record.final_output)):
            raise ValueError("Invalid work references")
        if record.status in ("awaiting_human_review", *DECISIONS.values()):
            if not record.plan or not record.work or not record.review:
                raise ValueError("Missing stages")
        if record.review:
            item_ids = {item.id for item in record.work.items} if record.work else set()
            if (any(f.item_id is not None and f.item_id not in item_ids for f in record.review.findings)
                    or (record.review.degraded and record.review.verdict == "pass")
                    or (any(f.severity == "blocking" for f in record.review.findings)
                        and record.review.verdict != "fail")):
                raise ValueError("Invalid review")
        if record.status in DECISIONS.values():
            if not record.human_decision or DECISIONS.get(record.human_decision.get("decision")) != record.status:
                raise ValueError("Missing human decision")
            if (record.status == "rejected") != (record.final_output is None):
                raise ValueError("Invalid final output")
        elif record.human_decision is not None or record.final_output is not None:
            raise ValueError("Premature decision")
        if record.status == "failed" and not record.error:
            raise ValueError("Missing failure")
        return record.model_dump()
    except (ValueError, TypeError, AttributeError):
        raise IntegrationError("invalid_dependency_response") from None


class MultiAgentClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")

    def request(self, method, path, payload=None, expected=200):
        deadline = time.monotonic() + 10
        try:
            with httpx.stream(method, self.base_url + path, json=payload, timeout=10, follow_redirects=False) as response:
                data = bytearray()
                for chunk in response.iter_bytes(chunk_size=4096):
                    if time.monotonic() > deadline:
                        raise IntegrationError("dependency_timeout")
                    data.extend(chunk)
                    if len(data) > 262144:
                        raise IntegrationError("invalid_dependency_response")
                try:
                    body = json.loads(data)
                except ValueError:
                    raise IntegrationError("invalid_dependency_response") from None
                if response.status_code != expected:
                    error = body.get("error") if isinstance(body, dict) else None
                    if not isinstance(error, dict) or not isinstance(error.get("code"), str):
                        raise IntegrationError("invalid_dependency_response")
                    code = error["code"]
                    mapped = {404: "workflow_not_found", 409: "workflow_conflict", 503: "dependency_unavailable",
                              504: "dependency_timeout", 400: "invalid_workflow"}
                    if response.status_code == 503 and code == "busy":
                        raise IntegrationError("workflow_busy")
                    raise IntegrationError(mapped.get(response.status_code, "invalid_dependency_response"))
                return body
        except httpx.TimeoutException:
            raise IntegrationError("dependency_timeout") from None
        except httpx.HTTPError:
            raise IntegrationError("dependency_unavailable") from None


def snapshot(evidence):
    return json.loads(evidence[0]["text"])["snapshot"]


class EditReview:
    def __init__(self, database, client):
        self.database, self.client = database, client

    def trip_evidence(self, trip_id):
        body, status = self.database.request("GET", f"/api/data/trips/{trip_id}")
        if status == 404:
            raise IntegrationError("trip_not_found")
        if status != 200:
            raise IntegrationError("invalid_dependency_response")
        return evidence_for(body, trip_id)

    def get_record(self, trip_id, workflow_id):
        if not isinstance(workflow_id, str) or not re.fullmatch(WORKFLOW_ID, workflow_id):
            raise IntegrationError("workflow_not_found")
        return validate_record(self.client.request("GET", f"/workflows/{workflow_id}"), workflow_id, trip_id)

    def start(self, trip_id, preview, question, evidence):
        if snapshot(evidence) != snapshot(self.trip_evidence(trip_id)):
            raise IntegrationError("stale_preview")
        candidate = []
        for title, text in [
            ("Requested edit", question),
            *[(f"Proposed change {i + 1}", json.dumps(change, ensure_ascii=False))
              for i, change in enumerate(preview["changes"])],
        ]:
            parts = [text[i:i + 800] for i in range(0, len(text), 800)]
            for i, part in enumerate(parts):
                candidate.append({"id": f"edit-{len(candidate) + 1}",
                                  "title": f"{title} (part {i + 1}/{len(parts)})", "text": part})
        if len(candidate) > 28:
            raise IntegrationError("edit_review_too_large")
        evidence = evidence[:30 - len(candidate)]
        metadata = json.loads(evidence[0]["text"])
        metadata["omittedStops"] = metadata["stopCount"] - (len(evidence) - 2)
        metadata["previewHash"] = hashlib.sha256(preview["token"].encode()).hexdigest()
        evidence[0] = {**evidence[0], "text": json.dumps(metadata, ensure_ascii=False)}
        created = self.client.request("POST", "/workflows", {
            "feature": "student-2",
            "task": "Assess the exact proposed edit against the requested edit and saved itinerary. "
                    "Identify supported changes, mismatches and evidence limits. Do not invent or execute edits.",
            "evidence": [Evidence.model_validate(item).model_dump() for item in evidence + candidate],
            "submitted_by": "student-2-frontend",
        }, expected=202)
        if (not isinstance(created, dict) or set(created) != {"id", "status"}
                or not isinstance(created["id"], str) or not re.fullmatch(WORKFLOW_ID, created["id"])
                or created["status"] != "queued"):
            raise IntegrationError("invalid_dependency_response")
        return created["id"]

    def require_accepted(self, trip_id, workflow_id, token):
        record = self.get_record(trip_id, workflow_id)
        metadata = json.loads(record["evidence"][0]["text"])
        if (metadata.get("previewHash") != hashlib.sha256(token.encode()).hexdigest()
                or record["status"] not in ("approved", "corrected", "partially_accepted")):
            raise IntegrationError("edit_review_required")
        if snapshot(record["evidence"]) != snapshot(self.trip_evidence(trip_id)):
            raise IntegrationError("stale_workflow")


def create_blueprint(service, enabled):
    routes = Blueprint("multi_agent", __name__)

    @routes.before_request
    def require_enabled():
        if not enabled:
            raise IntegrationError("mode_disabled")
        if request.content_length is not None and request.content_length > 16384:
            raise IntegrationError("invalid_workflow")

    @routes.get("/api/trips/<int:trip_id>/multi-agent-workflows/<workflow_id>")
    def poll(trip_id, workflow_id):
        record = service.get_record(trip_id, workflow_id)
        try:
            current = service.trip_evidence(trip_id)
            record["stale"] = snapshot(record["evidence"]) != snapshot(current)
        except IntegrationError as exc:
            if exc.code != "trip_not_found":
                raise
            record["stale"] = True
        return jsonify(record)

    @routes.post("/api/trips/<int:trip_id>/multi-agent-workflows/<workflow_id>/decision")
    def decide(trip_id, workflow_id):
        try:
            decision = Decision.model_validate(request.get_json(silent=True))
        except ValidationError:
            raise IntegrationError("invalid_workflow") from None
        record = service.get_record(trip_id, workflow_id)
        if record["status"] != "awaiting_human_review":
            raise IntegrationError("workflow_conflict")
        if snapshot(record["evidence"]) != snapshot(service.trip_evidence(trip_id)):
            raise IntegrationError("stale_workflow")
        item_ids = {item["id"] for item in record["work"]["items"]}
        if (decision.decision == "reject" and not decision.notes.strip()
                or decision.decision == "partial" and (
                    not decision.accepted_item_ids
                    or len(set(decision.accepted_item_ids)) != len(decision.accepted_item_ids)
                    or not set(decision.accepted_item_ids).issubset(item_ids))
                or decision.decision == "correct" and (
                    not decision.corrected_output
                    or not valid_work(decision.corrected_output, {item["id"] for item in record["evidence"]}))
                or decision.decision != "correct" and decision.corrected_output is not None
                or decision.decision != "partial" and decision.accepted_item_ids is not None):
            raise IntegrationError("invalid_workflow")
        result = service.client.request("POST", f"/workflows/{workflow_id}/decision",
                                       {**decision.model_dump(exclude_none=True), "decided_by": "human"})
        validated = validate_record(result, workflow_id, trip_id)
        if validated["status"] != DECISIONS[decision.decision] or validated["evidence"] != record["evidence"]:
            raise IntegrationError("invalid_dependency_response")
        expected_output = record["work"]
        if decision.decision == "reject":
            expected_output = None
        elif decision.decision == "correct":
            expected_output = decision.corrected_output.model_dump()
        elif decision.decision == "partial":
            expected_output = {**record["work"], "items": [
                item for item in record["work"]["items"] if item["id"] in decision.accepted_item_ids]}
        if validated["final_output"] != expected_output:
            raise IntegrationError("invalid_dependency_response")
        return jsonify({**validated, "stale": False})

    return routes
