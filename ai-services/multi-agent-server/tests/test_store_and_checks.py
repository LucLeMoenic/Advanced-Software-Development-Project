import json

import pytest

import agents
import checks
from store import Store, _digest


def _plan(required):
    return agents.Plan(objective="o", steps=[agents.PlanStep(id="s1", description="d")],
                       required_evidence_ids=required, success_criteria=["c"])


def _work(*items):
    return agents.WorkerOutput(summary="s", items=[
        agents.WorkItem(id=f"i{n}", subject=subject, detail="d", evidence_ids=ids)
        for n, (subject, ids) in enumerate(items, start=1)])


# -- audit chain -----------------------------------------------------------

def test_audit_chain_is_valid_and_links_entries(data_dir):
    store = Store()
    first = store.audit("wf-x", "system", "one")
    second = store.audit("wf-x", "planner", "two", {"k": 1})

    assert second["prev_hash"] == first["hash"]
    assert store.verify() == {"valid": True, "entries": 2, "broken_at": None}


def test_empty_audit_log_verifies(data_dir):
    assert Store().verify() == {"valid": True, "entries": 0, "broken_at": None}


def test_verify_detects_edited_entry(data_dir):
    store = Store()
    for event in ("a", "b", "c"):
        store.audit("wf-x", "system", event)
    lines = store.audit_path.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[1])
    entry["details"] = {"tampered": True}
    lines[1] = json.dumps(entry, sort_keys=True)
    store.audit_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assert store.verify() == {"valid": False, "entries": 3, "broken_at": 2}


def test_verify_detects_edited_entry_whose_own_hash_was_recomputed(data_dir):
    # A forger who edits entry 2 and also recomputes its hash passes the per-entry digest
    # check; only the next entry's prev_hash link exposes it.
    store = Store()
    for event in ("a", "b", "c"):
        store.audit("wf-x", "system", event)
    lines = store.audit_path.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[1])
    entry["details"] = {"tampered": True}
    entry["hash"] = _digest({k: v for k, v in entry.items() if k != "hash"})
    lines[1] = json.dumps(entry, sort_keys=True)
    store.audit_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assert store.verify() == {"valid": False, "entries": 3, "broken_at": 3}


def test_verify_detects_deleted_entry(data_dir):
    store = Store()
    for event in ("a", "b", "c"):
        store.audit("wf-x", "system", event)
    lines = store.audit_path.read_text(encoding="utf-8").splitlines()
    store.audit_path.write_text("\n".join([lines[0], lines[2]]) + "\n", encoding="utf-8")

    assert store.verify()["valid"] is False


@pytest.mark.parametrize("bad_id", ["../etc/passwd", "wf-1", "", "wf-20260101T000000Z-ZZZZZZZZ"])
def test_load_rejects_malformed_workflow_ids(data_dir, bad_id):
    assert Store().load(bad_id) is None


# -- deterministic checks ---------------------------------------------------

def test_matching_subjects_produce_no_findings(evidence):
    findings = checks.check_work(_plan(["a1"]), _work(("Opera House", ["a1"]), ("corner cafe", ["a2"])), evidence)
    assert findings == []


def test_subject_not_in_cited_evidence_is_blocking(evidence):
    findings = checks.check_work(_plan(["a1"]), _work(("Opera House", ["a1"]), ("Secret Rooftop Bar", ["a2"])), evidence)

    blocking = [f for f in findings if f["severity"] == "blocking"]
    assert [f["item_id"] for f in blocking] == ["i2"]


def test_subject_must_match_the_cited_entry_not_just_any_entry(evidence):
    # "Corner Cafe" exists in the evidence, but this item cites the Opera House entry.
    findings = checks.check_work(_plan(["a1"]), _work(("Corner Cafe", ["a1"])), evidence)
    assert any(f["severity"] == "blocking" for f in findings)


def test_unused_required_evidence_and_repeated_subject_are_warnings(evidence):
    findings = checks.check_work(_plan(["a3"]), _work(("Opera House", ["a1"]), ("Opera House", ["a1"])), evidence)

    assert {f["severity"] for f in findings} == {"warning"}
    assert any("a3" in f["message"] for f in findings)
    assert any("repeated" in f["message"] for f in findings)


@pytest.mark.parametrize(
    ("model_verdict", "severities", "expected"),
    [
        ("pass", [], "pass"),
        ("pass", ["info"], "pass"),
        ("pass", ["warning"], "concerns"),
        ("concerns", [], "concerns"),
        ("pass", ["blocking"], "fail"),
        ("concerns", ["blocking", "warning"], "fail"),
        ("fail", [], "fail"),
    ],
)
def test_final_verdict_policy(model_verdict, severities, expected):
    findings = [{"severity": s, "item_id": None, "message": "m"} for s in severities]
    assert checks.final_verdict(model_verdict, findings) == expected
