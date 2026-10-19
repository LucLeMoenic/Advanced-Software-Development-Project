"""Planner -> Worker -> Reviewer pipeline and the human review decision.

Status lifecycle:
    queued -> planning -> working -> reviewing -> awaiting_human_review
           -> approved | corrected | partially_accepted | rejected
    (any stage can end in `failed`; the human decision is the only way out of
    awaiting_human_review)
"""

import time
import uuid
from datetime import datetime, timezone

import agents
import checks
import llm
from store import now

HUMAN_DECISIONS = {
    "approve": "approved",
    "correct": "corrected",
    "partial": "partially_accepted",
    "reject": "rejected",
}


class DecisionError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message
        super().__init__(message)


def new_id():
    return "wf-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]


def create_record(feature, task, evidence, submitted_by):
    return {
        "id": new_id(), "feature": feature, "task": task, "submitted_by": submitted_by,
        "status": "queued", "created_at": now(), "updated_at": now(),
        "evidence": evidence, "plan": None, "work": None, "review": None,
        "human_decision": None, "final_output": None, "history": [], "error": None,
    }


async def _stage(store, record, role, status, call):
    record["status"] = status
    store.save(record)
    store.audit(record["id"], role, "stage_started", {"prompt": agents.prompt_name(role), "model": llm.model_name()})
    started, clock = now(), time.monotonic()
    result = await call()
    duration = int((time.monotonic() - clock) * 1000)
    return result, {"stage": role, "agent": role, "prompt": agents.prompt_name(role), "model": llm.model_name(),
                    "started_at": started, "finished_at": now(), "duration_ms": duration}


async def run(store, workflow_id):
    """Execute the three agent stages; ends in awaiting_human_review or failed."""
    record = store.load(workflow_id)
    evidence, task = record["evidence"], record["task"]
    store.audit(workflow_id, "system", "workflow_created", {
        "feature": record["feature"], "evidence_ids": [e["id"] for e in evidence], "submitted_by": record["submitted_by"]})
    try:
        plan, entry = await _stage(store, record, "planner", "planning", lambda: agents.plan(task, evidence))
        record["plan"] = plan.model_dump()
        record["history"].append({**entry, "ok": True, "output": record["plan"]})
        store.audit(workflow_id, "planner", "stage_completed", {
            "steps": len(plan.steps), "required_evidence_ids": plan.required_evidence_ids})

        work, entry = await _stage(store, record, "worker", "working", lambda: agents.work(task, plan, evidence))
        record["work"] = work.model_dump()
        record["history"].append({**entry, "ok": True, "output": record["work"]})
        store.audit(workflow_id, "worker", "stage_completed", {
            "items": [{"id": i.id, "subject": i.subject, "evidence_ids": i.evidence_ids} for i in work.items]})

        automatic = checks.check_work(plan, work, evidence)
        store.audit(workflow_id, "system", "automatic_checks", {"findings": automatic})
        try:
            reviewed, entry = await _stage(
                store, record, "reviewer", "reviewing", lambda: agents.review(task, plan, work, evidence, automatic))
            seen = {a["message"] for a in automatic}  # the model often restates an automatic finding
            model_findings = []
            for finding in reviewed.findings:  # ...and sometimes repeats itself
                if finding.message not in seen:
                    seen.add(finding.message)
                    model_findings.append(finding.model_dump())
            model_verdict, recommendations, degraded = reviewed.verdict, reviewed.recommendations, False
            record["history"].append({**entry, "ok": True, "output": None})
        except llm.AgentError as exc:
            # The Planner and Worker results are still valid. Do not discard them: hand over to the
            # human with the automatic checks only, clearly marked, and never with a "pass".
            note = {"severity": "warning", "item_id": None, "message": (
                f"Reviewer model unavailable ({exc.code}); this review is automatic checks only.")}
            model_findings, model_verdict, recommendations, degraded = [note], "concerns", [
                "The Reviewer agent did not produce a valid review; check every item against the evidence yourself."], True
            record["history"].append({"stage": "reviewer", "ok": False, "degraded": True, "at": now(),
                                      "error": {"code": exc.code, "message": exc.message,
                                                "detail": exc.detail, "raw_output": exc.raw}})
            store.audit(workflow_id, "reviewer", "stage_failed_degraded", {
                "code": exc.code, "detail": exc.detail, "raw_output": exc.raw})
        findings = automatic + model_findings
        record["review"] = {
            "verdict": checks.final_verdict(model_verdict, findings), "model_verdict": model_verdict,
            "degraded": degraded, "automatic_findings": automatic, "model_findings": model_findings,
            "findings": findings, "recommendations": recommendations,
        }
        if not degraded:
            record["history"][-1]["output"] = record["review"]
        if not degraded:
            store.audit(workflow_id, "reviewer", "stage_completed", {
                "verdict": record["review"]["verdict"], "model_verdict": model_verdict,
                "blocking": sum(f["severity"] == "blocking" for f in findings)})

        record["status"] = "awaiting_human_review"
        store.save(record)
        store.audit(workflow_id, "system", "awaiting_human_review", {"verdict": record["review"]["verdict"]})
    except llm.AgentError as exc:
        failed_stage = record["status"]  # planning | working | reviewing
        record["status"] = "failed"
        record["error"] = {"code": exc.code, "message": exc.message, "stage": failed_stage,
                           "detail": exc.detail, "raw_output": exc.raw}
        record["history"].append({"stage": failed_stage, "ok": False, "error": record["error"], "at": now()})
        store.save(record)
        store.audit(workflow_id, "system", "workflow_failed", record["error"])


def decide(store, record, decision, notes, decided_by, corrected_output, accepted_item_ids):
    """Apply the human decision to a workflow awaiting review; returns the saved record."""
    if record["status"] != "awaiting_human_review":
        raise DecisionError(409, "not_awaiting_review", f"Workflow is {record['status']}, not awaiting human review.")
    if decision == "reject" and not notes.strip():
        raise DecisionError(400, "notes_required", "A rejection must include notes explaining why.")

    work = record["work"]
    extra = {}
    if decision == "approve":
        final = work
    elif decision == "reject":
        final = None
    elif decision == "partial":
        wanted = accepted_item_ids or []
        known = {i["id"] for i in work["items"]}
        if not wanted or any(i not in known for i in wanted):
            raise DecisionError(400, "invalid_selection", "Partial acceptance needs a non-empty list of existing item ids.")
        final = {**work, "items": [i for i in work["items"] if i["id"] in wanted]}
        extra["accepted_item_ids"] = wanted
        extra["rejected_item_ids"] = [i["id"] for i in work["items"] if i["id"] not in wanted]
    else:  # correct
        if corrected_output is None:
            raise DecisionError(400, "correction_required", "A correction must include corrected_output.")
        try:
            corrected = agents.WorkerOutput.model_validate(corrected_output)
        except ValueError:
            raise DecisionError(400, "invalid_correction", "corrected_output must match the worker output shape.") from None
        ids = {e["id"] for e in record["evidence"]}
        if any(e not in ids for i in corrected.items for e in i.evidence_ids):
            raise DecisionError(400, "invalid_correction", "corrected_output cites evidence that was not supplied.")
        final = corrected.model_dump()
        extra["correction_findings"] = checks.check_work(agents.Plan.model_validate(record["plan"]), corrected, record["evidence"])

    record["status"] = HUMAN_DECISIONS[decision]
    record["human_decision"] = {"decision": decision, "notes": notes, "decided_by": decided_by, "decided_at": now(), **extra}
    record["final_output"] = final
    store.save(record)
    store.audit(record["id"], "human", f"decision_{decision}", {"decided_by": decided_by, "notes": notes, **extra})
    return record
