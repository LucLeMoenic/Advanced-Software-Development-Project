"""Planner, Worker and Reviewer agents.

Each agent is one constrained Ollama call. The only data an agent sees is what
the caller supplied as evidence plus the previous agent's validated output; the
server never fetches application data itself, so the evidence trail is explicit.
"""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

import llm

PROMPT_DIR = Path(__file__).resolve().parents[1] / "agentic-loop" / "prompts"
PROMPTS = {
    "planner": "multi-agent-planner-v1.txt",
    "worker": "multi-agent-worker-v2.txt",
    "reviewer": "multi-agent-reviewer-v1.txt",
}
ATTEMPTS = 2  # one retry when the model returns output that fails validation


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class PlanStep(_Strict):
    id: str = Field(pattern=r"^s[0-9]{1,2}$")
    description: str = Field(min_length=1, max_length=200)


class Plan(_Strict):
    objective: str = Field(min_length=1, max_length=300)
    steps: list[PlanStep] = Field(min_length=1, max_length=6)
    required_evidence_ids: list[str] = Field(min_length=1, max_length=10)
    success_criteria: list[str] = Field(min_length=1, max_length=5)


class WorkItem(_Strict):
    id: str = Field(pattern=r"^i[0-9]{1,2}$")
    subject: str = Field(min_length=1, max_length=120)
    detail: str = Field(min_length=1, max_length=400)
    evidence_ids: list[str] = Field(min_length=1, max_length=3)


class WorkerOutput(_Strict):
    summary: str = Field(min_length=1, max_length=400)
    items: list[WorkItem] = Field(min_length=1, max_length=8)


class Finding(_Strict):
    severity: Literal["info", "warning", "blocking"]
    item_id: str | None
    message: str = Field(min_length=1, max_length=300)


class ReviewerOutput(_Strict):
    verdict: Literal["pass", "concerns", "fail"]
    findings: list[Finding] = Field(max_length=8)
    recommendations: list[str] = Field(max_length=5)


def _prompt(role):
    return (PROMPT_DIR / PROMPTS[role]).read_text(encoding="utf-8")


def prompt_name(role):
    return PROMPTS[role]


def _restrict_item_ids(node, item_ids):
    """Constrain Finding.item_id to the Worker's real item ids (or null)."""
    finding = node.get("$defs", {}).get("Finding", {}).get("properties", {})
    if "item_id" in finding:
        finding["item_id"] = {"anyOf": [{"type": "string", "enum": item_ids}, {"type": "null"}]}


def _restrict_subjects(schema, titles):
    """Constrain WorkItem.subject to the exact evidence titles.

    Found in the first live UI run: a 3B model copied each entry's description into `subject`
    instead of its name. Structured decoding makes that impossible; checks.py still verifies that
    the subject belongs to the entry the item actually cites.
    """
    subject = schema.get("$defs", {}).get("WorkItem", {}).get("properties", {}).get("subject")
    if subject is not None:
        subject.pop("minLength", None)
        subject.pop("maxLength", None)
        subject["enum"] = list(dict.fromkeys(titles))


def _restrict_ids(node, ids):
    """Constrain every evidence-id array in a JSON schema to the supplied ids."""
    if isinstance(node, dict):
        props = node.get("properties")
        if isinstance(props, dict):
            for key in ("evidence_ids", "required_evidence_ids"):
                if key in props:
                    props[key]["items"] = {"type": "string", "enum": ids}
        for value in node.values():
            _restrict_ids(value, ids)
    elif isinstance(node, list):
        for value in node:
            _restrict_ids(value, ids)


async def _run(role, model_cls, payload, evidence_ids, extra_check=None, item_ids=None, subjects=None):
    schema = model_cls.model_json_schema()
    _restrict_ids(schema, evidence_ids)
    if subjects is not None:
        _restrict_subjects(schema, subjects)
    if item_ids is not None:
        _restrict_item_ids(schema, item_ids)
    last, last_raw = None, None
    for _ in range(ATTEMPTS):
        raw = await llm.generate_json(_prompt(role), payload, schema)
        try:
            result = model_cls.model_validate(raw)
            if extra_check:
                extra_check(result)
            return result
        except (ValidationError, ValueError) as exc:
            last, last_raw = exc, raw
    raise llm.AgentError(
        "invalid_agent_output", f"{role} output failed validation after {ATTEMPTS} attempts.",
        detail=str(last)[:400], raw=json.dumps(last_raw)[:1500])


def _evidence_payload(evidence):
    return [{"id": e["id"], "title": e["title"], "text": e["text"]} for e in evidence]


async def plan(task, evidence):
    ids = [e["id"] for e in evidence]

    def check(result):
        if any(i not in ids for i in result.required_evidence_ids):
            raise ValueError("unknown evidence id in plan")

    return await _run("planner", Plan, {"task": task, "evidence": _evidence_payload(evidence)}, ids, check)


async def work(task, the_plan, evidence):
    ids = [e["id"] for e in evidence]

    def check(result):
        item_ids = [i.id for i in result.items]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("duplicate item id")
        if any(e not in ids for i in result.items for e in i.evidence_ids):
            raise ValueError("unknown evidence id in work")

    payload = {"task": task, "plan": the_plan.model_dump(), "evidence": _evidence_payload(evidence)}
    titles = [e["title"] for e in evidence]
    return await _run("worker", WorkerOutput, payload, ids, check, subjects=titles)


async def review(task, the_plan, the_work, evidence, automatic_findings):
    ids = [e["id"] for e in evidence]
    item_ids = [i.id for i in the_work.items]

    payload = {
        "task": task,
        "plan": the_plan.model_dump(),
        "work": the_work.model_dump(),
        "evidence": _evidence_payload(evidence),
        "automatic_findings": automatic_findings,
    }
    result = await _run("reviewer", ReviewerOutput, payload, ids, item_ids=item_ids)
    # A small model sometimes cites an item that does not exist. Keep the finding (it is
    # still information for the human) but detach it from the bogus id and say so.
    for finding in result.findings:
        if finding.item_id is not None and finding.item_id not in item_ids:
            finding.message = f"(model cited unknown item '{finding.item_id}') {finding.message}"[:300]
            finding.item_id = None
    return result
