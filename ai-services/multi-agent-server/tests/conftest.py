import asyncio
import os
import sys

import pytest

SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

import llm  # noqa: E402

EVIDENCE = [
    {"id": "a1", "title": "Opera House", "text": "Opera House is a sight. Harbour icon. Rating: 4.8."},
    {"id": "a2", "title": "Corner Cafe", "text": "Corner Cafe is a restaurant. Great coffee. Rating: 4.1."},
    {"id": "a3", "title": "Harbour Kayak", "text": "Harbour Kayak is an activity. Paddle tour. Rating: 4.5."},
]


class FakeModel:
    """Scripted stand-in for Ollama. Picks the response from the agent's prompt.

    Override per-test by assigning to `planner`, `worker` or `reviewer`
    (callables taking the payload), or queue raw replies in `queue[role]`.
    """

    def __init__(self):
        self.calls = []
        self.queue = {"planner": [], "worker": [], "reviewer": []}
        self.delay = 0
        self.planner = lambda p: {
            "objective": "Suggest a day plan from the catalogue.",
            "steps": [{"id": "s1", "description": "Pick grounded attractions."},
                      {"id": "s2", "description": "Summarise each."}],
            "required_evidence_ids": [p["evidence"][0]["id"]],
            "success_criteria": ["Every item cites evidence."],
        }
        self.worker = lambda p: {
            "summary": "Two grounded suggestions.",
            "items": [
                {"id": "i1", "subject": "Opera House", "detail": "A harbour icon rated 4.8.", "evidence_ids": ["a1"]},
                {"id": "i2", "subject": "Corner Cafe", "detail": "Great coffee, rated 4.1.", "evidence_ids": ["a2"]},
            ],
        }
        self.reviewer = lambda p: {"verdict": "pass", "findings": [], "recommendations": ["Confirm opening hours."]}

    async def __call__(self, system, payload, schema, **_):
        role = next(r for r in ("planner", "worker", "reviewer") if r.upper() in system)
        self.calls.append((role, payload, schema))
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.queue[role]:
            reply = self.queue[role].pop(0)
            if isinstance(reply, Exception):
                raise reply
            return reply
        return getattr(self, role)(payload)


@pytest.fixture
def fake_llm(monkeypatch):
    fake = FakeModel()
    monkeypatch.setattr(llm, "generate_json", fake)
    return fake


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("MULTI_AGENT_DATA_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def evidence():
    return [dict(e) for e in EVIDENCE]
