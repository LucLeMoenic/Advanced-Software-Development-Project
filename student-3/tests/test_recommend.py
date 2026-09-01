"""Tests /api/recommend's Plan -> Act -> Observe -> Adapt loop.

Never calls a live Ollama instance: _call_ollama / requests.post are always
mocked here so these tests run offline and deterministically.
"""

import recommend

SAMPLE_ATTRACTIONS = [
    {"id": 1, "name": "Sydney Opera House", "category": "sight", "description": "d", "rating": 4.7},
    {"id": 2, "name": "Chat Thai", "category": "restaurant", "description": "d", "rating": 4.3},
]


class FakeOllamaResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise recommend.requests.exceptions.HTTPError("bad status")

    def json(self):
        return self._payload


def test_get_recommendation_returns_ai_source_on_usable_response(monkeypatch):
    monkeypatch.setattr(recommend, "list_attractions", lambda category=None: SAMPLE_ATTRACTIONS)
    monkeypatch.setattr(
        recommend, "_call_ollama", lambda prompt: "You should visit Sydney Opera House for the views."
    )

    result = recommend.get_recommendation("I like sightseeing")

    assert result["source"] == "ai"
    assert "Sydney Opera House" in result["recommendation"]
    assert result["attractions_considered"] == [1, 2]


def test_get_recommendation_retries_then_falls_back_when_llm_empty(monkeypatch):
    monkeypatch.setattr(recommend, "list_attractions", lambda category=None: SAMPLE_ATTRACTIONS)
    monkeypatch.setattr(recommend, "_call_ollama", lambda prompt: "")

    result = recommend.get_recommendation("I like sightseeing")

    assert result["source"] == "fallback"
    assert "Sydney Opera House" in result["recommendation"]


def test_get_recommendation_succeeds_on_retry(monkeypatch):
    monkeypatch.setattr(recommend, "list_attractions", lambda category=None: SAMPLE_ATTRACTIONS)

    call_count = {"n": 0}

    def fake_call(prompt):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return ""  # first attempt: unusable
        return "Chat Thai is a great pick for restaurant lovers."

    monkeypatch.setattr(recommend, "_call_ollama", fake_call)

    result = recommend.get_recommendation("I like restaurant food")

    assert result["source"] == "ai_retry"
    assert call_count["n"] == 2


def test_get_recommendation_off_topic_response_triggers_adapt(monkeypatch):
    monkeypatch.setattr(recommend, "list_attractions", lambda category=None: SAMPLE_ATTRACTIONS)
    # Long enough to pass the length check, but mentions neither candidate.
    monkeypatch.setattr(recommend, "_call_ollama", lambda prompt: "The weather today is sunny and mild.")

    result = recommend.get_recommendation("I like sightseeing")

    assert result["source"] == "fallback"


def test_call_ollama_posts_expected_payload_and_parses_response(monkeypatch):
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeOllamaResponse({"response": "  Try Chat Thai.  ", "done": True})

    monkeypatch.setattr(recommend.requests, "post", fake_post)

    result = recommend._call_ollama("some prompt")

    assert result == "Try Chat Thai."
    assert captured["url"] == f"{recommend.OLLAMA_URL}/api/generate"
    assert captured["json"]["model"] == recommend.OLLAMA_MODEL
    assert captured["json"]["stream"] is False


def test_call_ollama_returns_empty_string_on_request_failure(monkeypatch):
    def fake_post(url, json=None, timeout=None):
        raise recommend.requests.exceptions.ConnectionError("ollama unreachable")

    monkeypatch.setattr(recommend.requests, "post", fake_post)

    assert recommend._call_ollama("some prompt") == ""


def test_recommend_endpoint_returns_ai_payload(backend_client, monkeypatch):
    import student3_backend_app

    monkeypatch.setattr(
        student3_backend_app,
        "get_recommendation",
        lambda interest_text: {"recommendation": "Try Chat Thai.", "source": "ai", "attractions_considered": [2]},
    )

    response = backend_client.post("/api/recommend", json={"interest": "I like restaurant food"})

    assert response.status_code == 200
    body = response.get_json()
    assert body["source"] == "ai"
    assert body["recommendation"] == "Try Chat Thai."


def test_recommend_endpoint_requires_interest(backend_client):
    response = backend_client.post("/api/recommend", json={"interest": "  "})
    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"
