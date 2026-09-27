"""Tests rag_client.py's request handling and error mapping.

Never calls the live RAG server: requests.post is always mocked, the same
convention test_recommend.py uses for Ollama.
"""

import pytest
import requests

import rag_client


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


def test_ask_returns_body_on_success(monkeypatch):
    body = {"answer": "The Opera House is rated 4.7.", "citations": [], "confidence": "high"}
    monkeypatch.setattr(rag_client.requests, "post", lambda *a, **k: FakeResponse(body))

    result = rag_client.ask("How is the Opera House rated?")

    assert result == body


def test_ask_returns_insufficient_context_body(monkeypatch):
    body = {"answer": "Not enough information in the knowledge base to answer this.", "citations": [], "confidence": "insufficient"}
    monkeypatch.setattr(rag_client.requests, "post", lambda *a, **k: FakeResponse(body))

    result = rag_client.ask("What is the capital of France?")

    assert result["confidence"] == "insufficient"
    assert result["citations"] == []


def test_ask_sends_the_student3_feature_scope(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return FakeResponse({"answer": "a", "citations": [], "confidence": "low"})

    monkeypatch.setattr(rag_client.requests, "post", fake_post)

    rag_client.ask("Is Chin Chin busy?")

    assert captured["json"]["feature"] == "student-3"
    assert captured["json"]["question"] == "Is Chin Chin busy?"


def test_ask_raises_disabled_without_any_network_call(monkeypatch):
    monkeypatch.setenv("RAG_ENABLED", "false")

    def fail_if_called(*a, **k):
        raise AssertionError("requests.post should not be called when disabled")

    monkeypatch.setattr(rag_client.requests, "post", fail_if_called)

    with pytest.raises(rag_client.RagDisabledError):
        rag_client.ask("anything")


def test_ask_raises_unavailable_when_server_unreachable(monkeypatch):
    def raise_connection_error(*a, **k):
        raise requests.exceptions.ConnectionError("refused")

    monkeypatch.setattr(rag_client.requests, "post", raise_connection_error)

    with pytest.raises(rag_client.RagUnavailableError):
        rag_client.ask("anything")


def test_ask_raises_response_error_on_non_200_status(monkeypatch):
    error_body = {"error": {"code": "dependency_unavailable", "message": "The local model is busy."}}
    monkeypatch.setattr(rag_client.requests, "post", lambda *a, **k: FakeResponse(error_body, status_code=503))

    with pytest.raises(rag_client.RagResponseError, match="busy"):
        rag_client.ask("anything")


def test_ask_raises_response_error_on_unexpected_body_shape(monkeypatch):
    monkeypatch.setattr(rag_client.requests, "post", lambda *a, **k: FakeResponse({"unexpected": True}))

    with pytest.raises(rag_client.RagResponseError):
        rag_client.ask("anything")
