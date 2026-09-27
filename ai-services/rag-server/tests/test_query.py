from pathlib import Path

import anyio
import httpx
import json
import os
import hashlib
import pytest
from fastapi.testclient import TestClient

import generation
import retrieval
from server import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(retrieval, "KNOWLEDGE_ROOT", Path(__file__).resolve().parents[1] / "knowledge")
    retrieval.reset_cache()
    return TestClient(app)


def test_relevant_query_uses_retained_context_and_real_source_metadata(client, monkeypatch):
    async def generate(question, ranked):
        assert question == "Is budget the total for the trip?"
        assert all(score >= 0.15 for chunk, score in ranked)
        assert all(len(chunk.text) <= 2000 for chunk, score in ranked)
        return generation.render_answer({"status": "answered", "claims": [
            {"text": "Budget is the total for the trip.", "chunk_ids": [ranked[0][0].chunk_id]},
        ]}, ranked)

    monkeypatch.setattr(generation, "generate", generate)
    response = client.post("/query", json={"feature": "student-2", "question": "Is budget the total for the trip?"})
    assert response.status_code == 200
    assert response.json()["citations"][0]["source"] == "Itinerary budget basics"
    assert "[budget-basics#1]" in response.json()["answer"]


def test_unrelated_query_skips_model(client, monkeypatch):
    async def forbidden(*args):
        pytest.fail("No-context queries must not call the model")

    monkeypatch.setattr(generation, "generate", forbidden)
    response = client.post("/query", json={"feature": "student-2", "question": "Who won the cricket championship?"})
    assert response.status_code == 200
    assert response.json() == generation.insufficient()


@pytest.mark.parametrize("payload", [
    {"feature": "../student-2", "question": "budget"}, {"feature": "student-2", "question": " "},
    {"feature": "student-2", "question": "budget", "url": "http://other"},
    {"feature": "student-2", "question": "a" * 1001},
])
def test_query_rejects_invalid_input(client, payload):
    assert client.post("/query", json=payload).status_code == 400


@pytest.mark.parametrize("payload", [
    {"status": "answered", "claims": []},
    {"status": "answered", "claims": [{"text": "Invented", "chunk_ids": ["missing#1"]}]},
    {"status": "insufficient", "claims": [{"text": "A guess", "chunk_ids": ["budget#1"]}]},
])
def test_invalid_model_output_is_not_accepted(payload):
    with pytest.raises(generation.GenerationError) as caught:
        generation.render_answer(payload, [(retrieval.Chunk("Budget", "budget#1", "Budget is total."), 0.5)])
    assert caught.value.status == 502


def test_model_abstention_and_dependency_failure_are_distinct(client, monkeypatch):
    assert generation.render_answer({"status": "insufficient", "claims": []}, []) == generation.insufficient()

    async def failed(*args):
        raise generation.GenerationError(503, "dependency_unavailable", "The local model is unavailable.")

    monkeypatch.setattr(generation, "generate", failed)
    response = client.post("/query", json={"feature": "student-2", "question": "budget total"})
    assert response.status_code == 503
    assert "answer" not in response.json()


@pytest.mark.parametrize("body", [[], None, {"done": False}, {"done": True, "response": "invalid"}])
def test_model_transport_rejects_malformed_envelopes(monkeypatch, body):
    client_type = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=body))
    monkeypatch.setattr(generation.httpx, "AsyncClient", lambda **kwargs: client_type(transport=transport, **kwargs))
    with pytest.raises(generation.GenerationError) as caught:
        anyio.run(generation.generate, "budget", [])
    assert caught.value.status == 502


def test_model_transport_constructs_bounded_grounding_request(monkeypatch):
    def respond(request):
        body = json.loads(request.content)
        assert request.url.path == "/api/generate"
        assert body["stream"] is False
        assert body["format"]["additionalProperties"] is False
        prompt = json.loads(body["prompt"])
        assert prompt == {"question": "budget", "context": [
            {"chunk_id": "budget#1", "source": "Budget", "text": "Budget is total."}
        ]}
        return httpx.Response(200, json={"done": True, "response": json.dumps({
            "status": "answered", "claims": [{"text": "Budget is total.", "chunk_ids": ["budget#1"]}]
        })})

    client_type = httpx.AsyncClient
    monkeypatch.setattr(generation.httpx, "AsyncClient", lambda **kwargs: client_type(transport=httpx.MockTransport(respond), **kwargs))
    result = anyio.run(generation.generate, "budget", [(retrieval.Chunk("Budget", "budget#1", "Budget is total."), 0.5)])
    assert result["confidence"] == "high"
    assert result["answer"] == "Budget is total. [budget#1]"


def test_model_transport_timeout_releases_capacity(monkeypatch):
    def timeout(request):
        raise httpx.ReadTimeout("timeout", request=request)

    client_type = httpx.AsyncClient
    monkeypatch.setattr(generation.httpx, "AsyncClient", lambda **kwargs: client_type(transport=httpx.MockTransport(timeout), **kwargs))
    for attempt in range(2):
        with pytest.raises(generation.GenerationError) as caught:
            anyio.run(generation.generate, "budget", [])
        assert caught.value.status == 504


def test_model_transport_stops_oversized_stream_and_closes_it(monkeypatch):
    class LargeStream(httpx.AsyncByteStream):
        consumed = 0
        closed = False

        async def __aiter__(self):
            for index in range(100):
                self.consumed += 1024
                yield b"x" * 1024

        async def aclose(self):
            self.closed = True

    stream = LargeStream()
    client_type = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(200, stream=stream))
    monkeypatch.setattr(generation.httpx, "AsyncClient", lambda **kwargs: client_type(transport=transport, **kwargs))
    with pytest.raises(generation.GenerationError) as caught:
        anyio.run(generation.generate, "budget", [])
    assert caught.value.status == 502
    assert stream.consumed == 16384
    assert stream.closed


@pytest.mark.skipif(os.getenv("RAG_LIVE_EVAL") != "1", reason="Requires an explicitly enabled native Ollama evaluation")
@pytest.mark.parametrize("case", json.loads(Path(__file__).with_name("grounding-questions.json").read_text()), ids=lambda case: case["id"])
def test_live_grounding_requires_source_review(client, case):
    response = client.post("/query", json={"feature": case["feature"], "question": case["question"]})
    corpus = retrieval.KNOWLEDGE_ROOT / case["feature"]
    print(json.dumps({"id": case["id"], "model": os.getenv("RAG_MODEL", "llama3.2:3b"),
                      "prompt_sha256": hashlib.sha256(generation.PROMPT_PATH.read_bytes()).hexdigest(),
                      "corpus_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(corpus.glob("*.md"))},
                      "question": case["question"], "status": response.status_code,
                      "response": response.json(), "rubric": case["rubric"],
                      "sources": {chunk.chunk_id: chunk.text for chunk in retrieval.get_index(case["feature"]).chunks},
                      "human_source_review": "pending"}))
    assert response.status_code == 200
    result = response.json()
    if not case["answerable"]:
        assert result == generation.insufficient()
    else:
        assert result["confidence"] != "insufficient"
        assert case["candidate"] in {citation["chunk_id"] for citation in result["citations"]}