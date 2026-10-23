"""Offline tests for the Student 4 section of scripts/deploy/smoke_cloud.py."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("smoke_cloud", Path(__file__).resolve().parents[1] / "deploy" / "smoke_cloud.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

API = "/budget-api"
OFF = {"aiEnabled": False, "mcpEnabled": False, "ragEnabled": False, "multiAgentEnabled": False}


class FakeGateway:
    """Answers the Student 4 routes like a baseline cloud deployment and records each call."""

    def __init__(self, capabilities=OFF, budgets=12, source="fallback", guidance_status=503, check_status=503,
                 limit_sticks=True, convert=lambda amount: amount, workflow_status=503,
                 preview_transform=lambda response: response, preview_mutation=None):
        self.capabilities, self.budgets, self.source = capabilities, budgets, source
        self.guidance_status, self.check_status = guidance_status, check_status
        self.limit_sticks, self.convert = limit_sticks, convert
        self.workflow_status = workflow_status
        self.preview_transform, self.preview_mutation = preview_transform, preview_mutation
        self.preview_bodies = []
        self.calls = []
        self.budget = None
        self.expense = None
        self.budget_deleted = False
        self.expense_deleted = False

    def __call__(self, path, method="GET", body=None, expected=200):
        self.calls.append((method, path))
        status, response = self.route(path, method, body)
        if status != expected:
            raise RuntimeError(f"{method} {path}: expected {expected}, received {status}")
        return response

    def route(self, path, method, body):
        if (method, path) == ("POST", f"{API}/what-if/preview"):
            self.preview_bodies.append(body)
            assert body["journeyLabel"] == self.budget["journeyLabel"]
            assert body["limits"][0]["category"] == self.budget["category"]
            actual = self.expense["convertedAmountMinor"]
            response = {"snapshotHash": "a" * 64}
            for name, limit in (("original", self.budget["limitAmountMinor"]),
                                ("proposed", body["limits"][0]["limitAmountMinor"])):
                amounts = {"plannedAmountMinor": limit, "actualAmountMinor": actual, "remainingAmountMinor": limit - actual}
                response[name] = {"journeyLabel": self.budget["journeyLabel"], "baseCurrency": "AUD", **amounts,
                                  "categories": [{"category": self.budget["category"], **amounts}]}
            if self.preview_mutation:
                self.preview_mutation(self)
            return 200, self.preview_transform(response)
        if (method, path) == ("POST", f"{API}/budgets"):
            self.budget = dict(body, id=14)
            return 201, dict(self.budget)
        if path == f"{API}/budgets/14":
            if method == "PUT":
                if self.limit_sticks:
                    self.budget = dict(body, id=14)
                return 200, {"id": 14}
            if method == "DELETE":
                self.budget_deleted = True
                return 204, None
            return (404, None) if self.budget_deleted else (200, dict(self.budget))
        if (method, path) == ("POST", f"{API}/expenses"):
            self.expense = dict(body, id=26, convertedAmountMinor=self.convert(body["originalAmountMinor"]))
            return 201, dict(self.expense)
        if path == f"{API}/expenses/26":
            if method == "PUT":
                self.expense = dict(body, id=26, convertedAmountMinor=self.convert(body["originalAmountMinor"]))
                return 200, {"id": 26}
            if method == "DELETE":
                self.expense_deleted = True
                return 204, None
            return (404, None) if self.expense_deleted else (200, dict(self.expense))
        return {
            ("GET", f"{API}/capabilities"): (200, self.capabilities),
            ("GET", f"{API}/budgets"): (200, [{}] * self.budgets),
            ("GET", f"{API}/journeys"): (200, [{"journeyLabel": "Europe Escape"}]),
            ("POST", f"{API}/insights"): (200, {"source": self.source, "summary": "s", "suggestions": [{"text": "t"}]}),
            ("POST", f"{API}/budget-guidance"): (self.guidance_status, None),
            ("POST", f"{API}/budget-check"): (self.check_status, None),
            ("POST", f"{API}/what-if/workflows"): (self.workflow_status, None),
        }[(method, path)]


def test_student4_check_passes_for_baseline_and_removes_both_rows():
    gateway = FakeGateway()

    module.check_student4(gateway)

    assert gateway.expense_deleted and gateway.budget_deleted
    assert gateway.preview_bodies == [{"journeyLabel": gateway.budget["journeyLabel"],
                                       "limits": [{"category": "food", "limitAmountMinor": 30000}]}] * 2
    assert gateway.budget["limitAmountMinor"] == 25000
    assert gateway.expense["originalAmountMinor"] == gateway.expense["convertedAmountMinor"] == 1800
    assert gateway.calls.count(("POST", f"{API}/budgets")) == gateway.calls.count(("POST", f"{API}/expenses")) == 1
    assert gateway.calls.index(("POST", f"{API}/what-if/workflows")) < gateway.calls.index(("POST", f"{API}/budgets"))
    assert gateway.calls[-6:-2] == [("GET", f"{API}/budgets/14"), ("GET", f"{API}/expenses/26"),
                                    ("DELETE", f"{API}/expenses/26"), ("DELETE", f"{API}/budgets/14")]
    assert gateway.calls.index(("DELETE", f"{API}/expenses/26")) < gateway.calls.index(("DELETE", f"{API}/budgets/14"))
    assert gateway.calls[-2:] == [("GET", f"{API}/expenses/26"), ("GET", f"{API}/budgets/14")]  # 404 readbacks


@pytest.mark.parametrize("source", ["ai", "ai_retry", "fallback"])
def test_ai_profile_requires_model_advice_and_retains_crud(source):
    gateway = FakeGateway(capabilities={key: True for key in OFF}, source=source)
    if source == "fallback":
        with pytest.raises(RuntimeError, match="AI budget advice failed"):
            module.check_student4(gateway, {"ai", "mcp", "rag", "multi-agent"})
    else:
        module.check_student4(gateway, {"ai", "mcp", "rag", "multi-agent"})
        assert gateway.budget_deleted and gateway.expense_deleted
        assert ("POST", f"{API}/what-if/workflows") not in gateway.calls


def test_multi_agent_profile_keeps_preview_and_crud_without_starting_a_workflow():
    gateway = FakeGateway(capabilities={**OFF, "multiAgentEnabled": True})

    module.check_student4(gateway, {"multi-agent"})

    assert gateway.budget_deleted and gateway.expense_deleted
    assert len(gateway.preview_bodies) == 2
    assert ("POST", f"{API}/what-if/workflows") not in gateway.calls


@pytest.mark.parametrize("flag", list(OFF))
def test_student4_check_fails_when_any_ai_capability_is_enabled(flag):
    gateway = FakeGateway(capabilities={**OFF, flag: True})

    with pytest.raises(RuntimeError, match="disable every Student 4 AI capability"):
        module.check_student4(gateway)

    assert not any(method == "POST" for method, _ in gateway.calls)  # nothing was created


def test_student4_check_requires_the_seeded_demonstration_budgets():
    with pytest.raises(RuntimeError, match="At least ten demonstration budgets"):
        module.check_student4(FakeGateway(budgets=9))


def test_student4_check_fails_when_disabled_ai_does_not_return_fallback_advice():
    with pytest.raises(RuntimeError, match="deterministic budget advice"):
        module.check_student4(FakeGateway(source="ai"))


@pytest.mark.parametrize("leaky, endpoint", [({"guidance_status": 200}, "budget-guidance"),
                                            ({"check_status": 200}, "budget-check"),
                                            ({"workflow_status": 200}, "what-if/workflows")])
def test_student4_check_fails_when_an_ai_route_answers_instead_of_503(leaky, endpoint):
    gateway = FakeGateway(**leaky)

    with pytest.raises(RuntimeError, match=rf"^POST {API}/{endpoint}: expected 503, received 200$"):
        module.check_student4(gateway)

    assert gateway.budget is None and gateway.expense is None


@pytest.mark.parametrize("name", ["original", "proposed"])
@pytest.mark.parametrize("category", [False, True], ids=["totals", "category"])
@pytest.mark.parametrize("field", ["plannedAmountMinor", "actualAmountMinor", "remainingAmountMinor"])
def test_student4_check_rejects_bogus_preview_financials(name, category, field):
    def corrupt(response):
        summary = response[name]["categories"][0] if category else response[name]
        summary[field] += 1
        return response

    gateway = FakeGateway(preview_transform=corrupt)
    scope = "category financials" if category else "totals"

    with pytest.raises(RuntimeError, match=rf"^What-if {name} {scope} did not match the temporary budget and expense\.$"):
        module.check_student4(gateway)

    assert gateway.expense_deleted and gateway.budget_deleted


@pytest.mark.parametrize("row, field, value", [("budget", "startDate", "2026-09-02"),
                                             ("expense", "description", "Unexpected preview write")])
def test_student4_check_rejects_preview_writes_and_still_cleans_up(row, field, value):
    def mutate(gateway):
        getattr(gateway, row)[field] = value

    gateway = FakeGateway(preview_mutation=mutate)

    with pytest.raises(RuntimeError, match=r"^What-if preview must not mutate the saved budget or expense\.$"):
        module.check_student4(gateway)

    assert gateway.expense_deleted and gateway.budget_deleted


@pytest.mark.parametrize("snapshot_hash", [None, "", "z" * 64])
def test_student4_check_requires_a_preview_snapshot_hash(snapshot_hash):
    gateway = FakeGateway(preview_transform=lambda response: {**response, "snapshotHash": snapshot_hash})

    with pytest.raises(RuntimeError, match=r"^What-if preview must include a valid snapshot hash\.$"):
        module.check_student4(gateway)

    assert gateway.expense_deleted and gateway.budget_deleted


def test_student4_check_rejects_a_nondeterministic_preview():
    gateway = FakeGateway(preview_transform=lambda response: {**response, "snapshotHash": str(len(gateway.preview_bodies)) * 64})

    with pytest.raises(RuntimeError, match=r"^What-if preview must be deterministic for an unchanged snapshot\.$"):
        module.check_student4(gateway)

    assert gateway.expense_deleted and gateway.budget_deleted


def test_student4_check_removes_both_rows_when_the_budget_update_is_not_saved():
    gateway = FakeGateway(limit_sticks=False)

    with pytest.raises(RuntimeError, match="Budget update/readback"):
        module.check_student4(gateway)

    assert gateway.budget_deleted and gateway.expense is None  # no expense was ever created


def test_student4_check_removes_both_rows_when_the_conversion_is_wrong():
    gateway = FakeGateway(convert=lambda amount: amount + 1)

    with pytest.raises(RuntimeError, match="same-currency expense must keep its amount"):
        module.check_student4(gateway)

    assert gateway.expense_deleted and gateway.budget_deleted


def test_student4_check_removes_both_rows_when_the_expense_update_is_not_recomputed():
    gateway = FakeGateway(convert=lambda amount: 1500)  # conversion never follows the edit

    with pytest.raises(RuntimeError, match="did not recompute the conversion"):
        module.check_student4(gateway)

    assert gateway.expense_deleted and gateway.budget_deleted
