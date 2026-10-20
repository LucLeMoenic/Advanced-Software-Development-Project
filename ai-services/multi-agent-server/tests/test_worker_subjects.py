import asyncio

import agents


def test_worker_schema_uses_only_supplied_evidence_titles(fake_llm, evidence):
    plan = agents.Plan(objective="Review evidence", steps=[{"id": "s1", "description": "Inspect"}],
                       required_evidence_ids=["a1"], success_criteria=["Ground claims"])
    asyncio.run(agents.work("Review this plan", plan, evidence))
    role, payload, schema = fake_llm.calls[0]
    assert role == "worker"
    assert schema["$defs"]["WorkItem"]["properties"]["subject"]["enum"] == [entry["title"] for entry in evidence]
    assert payload["evidence"] == evidence
