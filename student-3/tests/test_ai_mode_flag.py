"""Release 2 cloud baseline: Student 3's explicit AI-Mode switch and capabilities endpoint.

The required cloud deployment runs with AI-Mode, MCP, RAG and Multi-Agent disabled
(scripts/deploy/prepare_cloud.py sets every *_ENABLED flag to "false"). These tests pin
down what "disabled" means for Student 3: reported by /api/capabilities, and no model call.
"""

import pytest

import recommend

ATTRACTIONS = [
    {"id": 1, "name": "Opera House", "category": "sight", "description": "Harbour icon.", "rating": 4.8},
    {"id": 2, "name": "Corner Cafe", "category": "restaurant", "description": "Great coffee.", "rating": 4.1},
]
ALL_FLAGS = ("AI_ENABLED", "MCP_ENABLED", "RAG_ENABLED", "MULTI_AGENT_ENABLED")


@pytest.fixture
def catalogue(monkeypatch):
    monkeypatch.setattr(recommend, "list_attractions", lambda category=None: ATTRACTIONS)


@pytest.fixture
def no_model(monkeypatch):
    def forbidden(prompt):
        raise AssertionError("Ollama was called while AI-Mode is disabled")

    monkeypatch.setattr(recommend, "_call_ollama", forbidden)


# -- capabilities --------------------------------------------------------------------------------------

def test_capabilities_report_everything_off_for_the_cloud_baseline(backend_client, monkeypatch):
    for flag in ALL_FLAGS:
        monkeypatch.setenv(flag, "false")

    response = backend_client.get("/api/capabilities")

    assert response.status_code == 200
    assert response.get_json() == {
        "aiEnabled": False, "mcpEnabled": False, "ragEnabled": False, "multiAgentEnabled": False}


def test_capabilities_report_each_flag_independently(backend_client, monkeypatch):
    for flag in ALL_FLAGS:
        monkeypatch.setenv(flag, "false")
    monkeypatch.setenv("RAG_ENABLED", "true")

    assert backend_client.get("/api/capabilities").get_json() == {
        "aiEnabled": False, "mcpEnabled": False, "ragEnabled": True, "multiAgentEnabled": False}


def test_local_defaults_keep_release_1_behaviour_and_multi_agent_stays_off(backend_client, monkeypatch):
    for flag in ALL_FLAGS:
        monkeypatch.delenv(flag, raising=False)

    assert backend_client.get("/api/capabilities").get_json() == {
        "aiEnabled": True, "mcpEnabled": True, "ragEnabled": True, "multiAgentEnabled": False}


@pytest.mark.parametrize("value", ["false", "", "0", "yes", "off"])
def test_only_the_literal_true_enables_ai_mode(monkeypatch, value):
    monkeypatch.setenv("AI_ENABLED", value)
    assert recommend.ai_enabled() is False


@pytest.mark.parametrize("value", ["true", "TRUE", "True"])
def test_true_in_any_case_enables_ai_mode(monkeypatch, value):
    monkeypatch.setenv("AI_ENABLED", value)
    assert recommend.ai_enabled() is True


# -- AI-Mode behaviour ---------------------------------------------------------------------------------

def test_disabled_ai_mode_answers_from_the_catalogue_without_calling_the_model(catalogue, no_model, monkeypatch):
    monkeypatch.setenv("AI_ENABLED", "false")

    result = recommend.get_recommendation("I like sights")

    assert result["source"] == "fallback"
    assert result["recommendation"].strip()
    assert result["attractions_considered"] == [1, 2]


def test_disabled_ai_mode_makes_no_network_call_at_all(catalogue, monkeypatch):
    monkeypatch.setenv("AI_ENABLED", "false")
    monkeypatch.setattr(recommend.requests, "post", lambda *a, **k: pytest.fail("network call while disabled"))

    assert recommend.get_recommendation("anything")["source"] == "fallback"


def test_disabled_ai_mode_still_works_when_the_catalogue_is_empty(monkeypatch, no_model):
    monkeypatch.setenv("AI_ENABLED", "false")
    monkeypatch.setattr(recommend, "list_attractions", lambda category=None: [])

    result = recommend.get_recommendation("street art")

    assert result["source"] == "fallback" and result["attractions_considered"] == []


def test_recommend_route_returns_200_fallback_when_disabled(backend_client, catalogue, no_model, monkeypatch):
    monkeypatch.setenv("AI_ENABLED", "false")

    response = backend_client.post("/api/recommend", json={"interest": "street art"})

    assert response.status_code == 200
    assert response.get_json()["source"] == "fallback"


def test_enabled_ai_mode_still_calls_the_model(catalogue, monkeypatch):
    monkeypatch.setenv("AI_ENABLED", "true")
    calls = []
    monkeypatch.setattr(
        recommend, "_call_ollama",
        lambda prompt: calls.append(prompt) or "Try the Opera House: a harbour icon rated 4.8, a great sight.")

    result = recommend.get_recommendation("I like sights")

    assert calls and result["source"] == "ai"
