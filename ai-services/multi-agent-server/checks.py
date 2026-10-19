"""Deterministic review checks and verdict policy.

These run alongside the Reviewer model so a small model cannot talk its way to
a pass: an item about something that is not in the evidence it cites is always a
blocking finding, whatever the model says.
"""


def _norm(text):
    return " ".join(text.lower().split())


def check_work(the_plan, the_work, evidence):
    """Return deterministic findings (dicts shaped like agents.Finding)."""
    titles = {e["id"]: _norm(e["title"]) for e in evidence}
    findings = []
    used_ids = set()
    seen_subjects = set()
    for item in the_work.items:
        used_ids.update(item.evidence_ids)
        subject = _norm(item.subject)
        cited_titles = [titles[i] for i in item.evidence_ids if i in titles]
        if not any(subject in t or t in subject for t in cited_titles):
            findings.append({
                "severity": "blocking", "item_id": item.id,
                "message": f"Subject '{item.subject}' does not match any evidence entry this item cites.",
            })
        if subject in seen_subjects:
            findings.append({
                "severity": "warning", "item_id": item.id,
                "message": f"Subject '{item.subject}' is repeated.",
            })
        seen_subjects.add(subject)
    unused = [i for i in the_plan.required_evidence_ids if i not in used_ids]
    if unused:
        findings.append({
            "severity": "warning", "item_id": None,
            "message": "Plan-required evidence was not used: " + ", ".join(unused) + ".",
        })
    return findings


def final_verdict(model_verdict, findings):
    """Combine the model's verdict with all findings; blocking always means fail."""
    severities = {f["severity"] for f in findings}
    if "blocking" in severities or model_verdict == "fail":
        return "fail"
    if "warning" in severities or model_verdict == "concerns":
        return "concerns"
    return "pass"
