import asyncio

import pytest

import llm
import workflow
from store import Store


def _run(store, evidence, task="Plan a day"):
    record = workflow.create_record("student-3", task, evidence, "tests")
    store.save(record)
    asyncio.run(workflow.run(store, record["id"]))
    return store.load(record["id"])


# -- pipeline ----------------------------------------------------------------

def test_happy_path_runs_planner_worker_reviewer_then_waits_for_human(data_dir, fake_llm, evidence):
    store = Store()
    record = _run(store, evidence)

    assert record["status"] == "awaiting_human_review"
    assert [h["stage"] for h in record["history"]] == ["planner", "worker", "reviewer"]
    assert all(h["ok"] and h["duration_ms"] >= 0 and h["prompt"].startswith("multi-agent-") for h in record["history"])
    assert record["review"]["verdict"] == "pass"
    assert [c[0] for c in fake_llm.calls] == ["planner", "worker", "reviewer"]


def test_audit_log_records_the_full_coordination_sequence(data_dir, fake_llm, evidence):
    store = Store()
    record = _run(store, evidence)

    events = [(e["actor"], e["event"]) for e in store.audit_entries(record["id"])]
    assert events == [
        ("system", "workflow_created"),
        ("planner", "stage_started"), ("planner", "stage_completed"),
        ("worker", "stage_started"), ("worker", "stage_completed"),
        ("system", "automatic_checks"),
        ("reviewer", "stage_started"), ("reviewer", "stage_completed"),
        ("system", "awaiting_human_review"),
    ]
    assert store.verify()["valid"] is True


def test_each_agent_only_sees_validated_prior_output_and_supplied_evidence(data_dir, fake_llm, evidence):
    _run(Store(), evidence)

    planner, worker, reviewer = fake_llm.calls
    assert "plan" not in planner[1]
    assert worker[1]["plan"]["objective"]
    assert reviewer[1]["work"]["items"][0]["id"] == "i1"
    assert reviewer[1]["automatic_findings"] == []


def test_schema_sent_to_model_restricts_evidence_ids_to_supplied_ids(data_dir, fake_llm, evidence):
    _run(Store(), evidence)

    worker_schema = fake_llm.calls[1][2]
    item_ids = worker_schema["$defs"]["WorkItem"]["properties"]["evidence_ids"]["items"]
    assert item_ids == {"type": "string", "enum": ["a1", "a2", "a3"]}


def test_schema_sent_to_model_restricts_subject_to_the_exact_evidence_titles(data_dir, fake_llm, evidence):
    _run(Store(), evidence)

    subject = fake_llm.calls[1][2]["$defs"]["WorkItem"]["properties"]["subject"]
    assert subject["enum"] == ["Opera House", "Corner Cafe", "Harbour Kayak"]
    assert "minLength" not in subject and "maxLength" not in subject


def test_duplicate_evidence_titles_appear_once_in_the_subject_enum(data_dir, fake_llm, evidence):
    evidence[2]["title"] = "Opera House"
    _run(Store(), evidence)

    assert fake_llm.calls[1][2]["$defs"]["WorkItem"]["properties"]["subject"]["enum"] == [
        "Opera House", "Corner Cafe"]


def test_worker_uses_the_v2_prompt_which_names_the_subject_rule(data_dir, fake_llm, evidence):
    record = _run(Store(), evidence)

    assert [h["prompt"] for h in record["history"]] == [
        "multi-agent-planner-v1.txt", "multi-agent-worker-v2.txt", "multi-agent-reviewer-v1.txt"]
    import agents
    prompt = (agents.PROMPT_DIR / "multi-agent-worker-v2.txt").read_text(encoding="utf-8")
    assert "never a description" in prompt and "Worked example" in prompt


def test_hallucinated_subject_forces_fail_even_if_reviewer_model_says_pass(data_dir, fake_llm, evidence):
    fake_llm.worker = lambda p: {"summary": "s", "items": [
        {"id": "i1", "subject": "Imaginary Skybar", "detail": "Rooftop views.", "evidence_ids": ["a1"]}]}
    record = _run(Store(), evidence)

    assert record["status"] == "awaiting_human_review"  # a human still decides
    assert record["review"]["model_verdict"] == "pass"
    assert record["review"]["verdict"] == "fail"
    assert record["review"]["automatic_findings"][0]["severity"] == "blocking"


def test_invalid_model_output_is_retried_once_then_succeeds(data_dir, fake_llm, evidence):
    fake_llm.queue["worker"] = [{"summary": "bad", "items": []}]  # violates min_length
    record = _run(Store(), evidence)

    assert record["status"] == "awaiting_human_review"
    assert [c[0] for c in fake_llm.calls].count("worker") == 2


def test_unknown_evidence_id_is_rejected_and_retried(data_dir, fake_llm, evidence):
    fake_llm.queue["worker"] = [{"summary": "s", "items": [
        {"id": "i1", "subject": "Opera House", "detail": "d", "evidence_ids": ["zzz"]}]}]
    record = _run(Store(), evidence)

    assert record["status"] == "awaiting_human_review"
    assert record["work"]["items"][0]["evidence_ids"] == ["a1"]


def test_persistent_invalid_output_fails_the_workflow_at_that_stage(data_dir, fake_llm, evidence):
    fake_llm.queue["worker"] = [{"nope": 1}, {"nope": 2}]
    store = Store()
    record = _run(store, evidence)

    assert record["status"] == "failed"
    assert record["error"]["code"] == "invalid_agent_output"
    assert record["error"]["stage"] == "working"
    assert record["history"][-1]["stage"] == "working" and record["history"][-1]["ok"] is False
    assert store.audit_entries(record["id"])[-1]["event"] == "workflow_failed"


def test_model_unavailable_fails_the_workflow(data_dir, fake_llm, evidence):
    fake_llm.queue["planner"] = [llm.AgentError("dependency_unavailable", "The local model is unavailable.")]
    record = _run(Store(), evidence)

    assert record["status"] == "failed"
    assert record["error"]["code"] == "dependency_unavailable"
    assert record["error"]["stage"] == "planning"
    assert record["work"] is None


def test_failure_records_why_validation_failed_and_the_rejected_output(data_dir, fake_llm, evidence):
    fake_llm.queue["worker"] = [{"nope": 1}, {"nope": 2}]
    store = Store()
    record = _run(store, evidence)

    assert "nope" in record["error"]["raw_output"] and record["error"]["detail"]
    assert record["history"][-1]["error"]["raw_output"] == record["error"]["raw_output"]
    assert store.audit_entries(record["id"])[-1]["details"]["raw_output"] == record["error"]["raw_output"]


# -- reviewer robustness ------------------------------------------------------

def test_reviewer_schema_restricts_item_id_to_real_worker_items(data_dir, fake_llm, evidence):
    _run(Store(), evidence)

    finding = fake_llm.calls[2][2]["$defs"]["Finding"]["properties"]["item_id"]
    assert finding == {"anyOf": [{"type": "string", "enum": ["i1", "i2"]}, {"type": "null"}]}


def test_finding_citing_unknown_item_is_kept_but_detached(data_dir, fake_llm, evidence):
    fake_llm.reviewer = lambda p: {
        "verdict": "concerns", "recommendations": [],
        "findings": [{"severity": "warning", "item_id": "i9", "message": "Rating looks high."}]}
    record = _run(Store(), evidence)

    assert record["status"] == "awaiting_human_review" and record["review"]["degraded"] is False
    finding = record["review"]["model_findings"][0]
    assert finding["item_id"] is None
    assert "unknown item 'i9'" in finding["message"] and "Rating looks high." in finding["message"]


def test_model_finding_that_restates_an_automatic_finding_is_not_duplicated(data_dir, fake_llm, evidence):
    fake_llm.planner = lambda p: {
        "objective": "o", "steps": [{"id": "s1", "description": "d"}],
        "required_evidence_ids": ["a3"], "success_criteria": ["c"]}  # a3 is never used by the worker
    unused = "Plan-required evidence was not used: a3."
    fake_llm.reviewer = lambda p: {"verdict": "concerns", "recommendations": [], "findings": [
        {"severity": "info", "item_id": None, "message": unused},
        {"severity": "warning", "item_id": "i1", "message": "Rating not verified."}]}
    record = _run(Store(), evidence)

    messages = [f["message"] for f in record["review"]["findings"]]
    assert messages.count(unused) == 1
    assert "Rating not verified." in messages


def test_identical_model_findings_are_shown_once(data_dir, fake_llm, evidence):
    repeated = {"severity": "info", "item_id": None, "message": "No mention of cuisine in the evidence."}
    fake_llm.reviewer = lambda p: {"verdict": "pass", "recommendations": [], "findings": [repeated] * 4}
    record = _run(Store(), evidence)

    assert [f["message"] for f in record["review"]["model_findings"]] == [repeated["message"]]


def test_reviewer_failure_degrades_to_automatic_checks_and_never_passes(data_dir, fake_llm, evidence):
    fake_llm.queue["reviewer"] = [{"junk": 1}, {"junk": 2}]
    store = Store()
    record = _run(store, evidence)

    assert record["status"] == "awaiting_human_review"  # planner + worker results are not thrown away
    assert record["plan"] and record["work"]
    assert record["review"]["degraded"] is True
    assert record["review"]["verdict"] == "concerns"  # never "pass" without a real review
    assert "automatic checks only" in record["review"]["findings"][-1]["message"]
    reviewer_entry = record["history"][-1]
    assert reviewer_entry["stage"] == "reviewer" and reviewer_entry["ok"] is False and reviewer_entry["degraded"]
    assert [e["event"] for e in store.audit_entries(record["id"])][-2:] == [
        "stage_failed_degraded", "awaiting_human_review"]


def test_degraded_review_still_fails_on_blocking_automatic_finding(data_dir, fake_llm, evidence):
    fake_llm.worker = lambda p: {"summary": "s", "items": [
        {"id": "i1", "subject": "Imaginary Skybar", "detail": "d", "evidence_ids": ["a1"]}]}
    fake_llm.queue["reviewer"] = [{"junk": 1}, {"junk": 2}]
    record = _run(Store(), evidence)

    assert record["review"]["degraded"] is True and record["review"]["verdict"] == "fail"


# -- human decision -----------------------------------------------------------

@pytest.fixture
def awaiting(data_dir, fake_llm, evidence):
    store = Store()
    return store, _run(store, evidence)


def test_approve_accepts_worker_output_unchanged(awaiting):
    store, record = awaiting
    result = workflow.decide(store, record, "approve", "Good", "alex", None, None)

    assert result["status"] == "approved"
    assert result["final_output"] == record["work"]
    assert result["human_decision"]["decided_by"] == "alex"
    assert store.audit_entries(record["id"])[-1]["event"] == "decision_approve"


def test_reject_requires_notes_and_clears_final_output(awaiting):
    store, record = awaiting
    with pytest.raises(workflow.DecisionError) as blocked:
        workflow.decide(store, record, "reject", "   ", "alex", None, None)
    assert blocked.value.code == "notes_required"

    result = workflow.decide(store, record, "reject", "Unsupported claim", "alex", None, None)
    assert result["status"] == "rejected" and result["final_output"] is None


def test_partial_keeps_only_selected_items_and_records_the_rest(awaiting):
    store, record = awaiting
    result = workflow.decide(store, record, "partial", "Keep the first", "alex", None, ["i1"])

    assert result["status"] == "partially_accepted"
    assert [i["id"] for i in result["final_output"]["items"]] == ["i1"]
    assert result["human_decision"]["rejected_item_ids"] == ["i2"]


@pytest.mark.parametrize("selection", [None, [], ["i9"], ["i1", "nope"]])
def test_partial_rejects_empty_or_unknown_selection(awaiting, selection):
    store, record = awaiting
    with pytest.raises(workflow.DecisionError) as blocked:
        workflow.decide(store, record, "partial", "", "alex", None, selection)
    assert blocked.value.code == "invalid_selection"
    assert store.load(record["id"])["status"] == "awaiting_human_review"


def test_correct_replaces_output_with_validated_human_version(awaiting):
    store, record = awaiting
    correction = {"summary": "Edited by a human.", "items": [
        {"id": "i1", "subject": "Harbour Kayak", "detail": "Paddle tour.", "evidence_ids": ["a3"]}]}
    result = workflow.decide(store, record, "correct", "Swapped the activity", "alex", correction, None)

    assert result["status"] == "corrected"
    assert result["final_output"]["items"][0]["subject"] == "Harbour Kayak"
    # The human's version is accepted, but the automatic checks are re-run and recorded:
    # the plan required evidence a1, which the correction no longer uses.
    findings = result["human_decision"]["correction_findings"]
    assert [f["severity"] for f in findings] == ["warning"] and "a1" in findings[0]["message"]


@pytest.mark.parametrize(
    "correction",
    [None, {"summary": "", "items": []},
     {"summary": "s", "items": [{"id": "i1", "subject": "x", "detail": "d", "evidence_ids": ["not-supplied"]}]}],
)
def test_correct_rejects_missing_malformed_or_ungrounded_correction(awaiting, correction):
    store, record = awaiting
    with pytest.raises(workflow.DecisionError) as blocked:
        workflow.decide(store, record, "correct", "", "alex", correction, None)
    assert blocked.value.code in {"correction_required", "invalid_correction"}


def test_second_decision_is_refused(awaiting):
    store, record = awaiting
    workflow.decide(store, record, "approve", "", "alex", None, None)
    with pytest.raises(workflow.DecisionError) as blocked:
        workflow.decide(store, store.load(record["id"]), "reject", "changed my mind", "alex", None, None)
    assert blocked.value.status == 409


def test_failed_workflow_cannot_be_decided(data_dir, fake_llm, evidence):
    fake_llm.queue["planner"] = [llm.AgentError("dependency_timeout", "timeout")]
    store = Store()
    record = _run(store, evidence)
    with pytest.raises(workflow.DecisionError) as blocked:
        workflow.decide(store, record, "approve", "", "alex", None, None)
    assert blocked.value.code == "not_awaiting_review"
