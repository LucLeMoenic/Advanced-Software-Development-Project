"""Shared Release 2 Multi-Agent Server.

Runs natively on the host (not a Docker Compose service), like the MCP and RAG
servers. Feature backends reach it at ``MULTI_AGENT_SERVER_URL`` (default
``http://localhost:5600``), or ``http://host.docker.internal:5600`` from inside
a container. Callers supply the evidence; the server coordinates the Planner,
Worker and Reviewer agents and then waits for a human decision.

Run directly: ``uvicorn server:app --host 127.0.0.1 --port 5600``
"""

import asyncio
from typing import Literal

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

import workflow
from store import WORKFLOW_ID, Store

app = FastAPI(title="asd-shared-multi-agent-server")

_active = {"id": None}  # one workflow at a time: a single local model serves all three agents
_tasks = set()


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(pattern=r"^[A-Za-z0-9_.:#-]{1,60}$")
    title: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=800)


class WorkflowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    feature: Literal["student-1", "student-2", "student-3", "student-4", "student-5"]
    task: str = Field(min_length=3, max_length=500)
    evidence: list[EvidenceItem] = Field(min_length=1, max_length=30)
    submitted_by: str = Field(default="frontend", min_length=1, max_length=60)

    @model_validator(mode="after")
    def unique_evidence_ids(self):
        ids = [e.id for e in self.evidence]
        if len(ids) != len(set(ids)):
            raise ValueError("Evidence ids must be unique.")
        return self

    @field_validator("task")
    @classmethod
    def clean_task(cls, value):
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Task must not be blank.")
        return value


class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    decision: Literal["approve", "correct", "partial", "reject"]
    notes: str = Field(default="", max_length=1000)
    decided_by: str = Field(default="human", min_length=1, max_length=60)
    corrected_output: dict | None = None
    accepted_item_ids: list[str] | None = Field(default=None, max_length=8)


def _error(status, code, message):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "fields": {}}})


async def _run_and_release(store, workflow_id):
    try:
        await workflow.run(store, workflow_id)
    finally:
        _active["id"] = None


@app.post("/workflows", status_code=202)
async def create_workflow(request: WorkflowRequest):
    if _active["id"] is not None:
        return _error(503, "busy", "A workflow is already running. Try again when it finishes.")
    store = Store()
    record = workflow.create_record(
        request.feature, request.task, [e.model_dump() for e in request.evidence], request.submitted_by)
    store.save(record)
    _active["id"] = record["id"]
    task = asyncio.create_task(_run_and_release(store, record["id"]))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return {"id": record["id"], "status": record["status"]}


@app.get("/workflows")
def list_workflows():
    return Store().list()


def _load(workflow_id):
    return Store().load(workflow_id) if WORKFLOW_ID.match(workflow_id) else None


@app.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str):
    record = _load(workflow_id)
    if record is None:
        return _error(404, "not_found", "Workflow not found.")
    return record


@app.post("/workflows/{workflow_id}/decision")
def decide_workflow(workflow_id: str, request: DecisionRequest):
    store = Store()
    record = _load(workflow_id)
    if record is None:
        return _error(404, "not_found", "Workflow not found.")
    try:
        return workflow.decide(store, record, request.decision, request.notes, request.decided_by,
                               request.corrected_output, request.accepted_item_ids)
    except workflow.DecisionError as exc:
        return _error(exc.status, exc.code, exc.message)


@app.get("/audit")
def audit(workflow_id: str | None = None):
    if workflow_id is not None and not WORKFLOW_ID.match(workflow_id):
        return _error(400, "validation_error", "Invalid workflow id.")
    return Store().audit_entries(workflow_id)


@app.get("/audit/verify")
def verify_audit():
    return Store().verify()


@app.exception_handler(RequestValidationError)
async def validation_error(request, exception):
    first = exception.errors()[0] if exception.errors() else {}
    where = ".".join(str(p) for p in first.get("loc", [])[1:])
    return _error(400, "validation_error", f"Invalid request{': ' + where if where else ''}.")


@app.get("/health")
def health():
    return {"status": "ok", "busy": _active["id"] is not None}
