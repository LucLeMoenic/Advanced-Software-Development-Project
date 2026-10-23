import asyncio

import httpx
import pytest

import llm


@pytest.mark.parametrize("configured,expected", [(None, 180), ("360", 360)])
def test_model_deadline_is_configurable_without_changing_native_default(monkeypatch, configured, expected):
    monkeypatch.delenv("MULTI_AGENT_TIMEOUT", raising=False)
    if configured is not None:
        monkeypatch.setenv("MULTI_AGENT_TIMEOUT", configured)
    original = httpx.AsyncClient

    def respond(request):
        assert request.extensions["timeout"]["read"] == expected
        return httpx.Response(200, json={"done": True, "response": '{"ok":true}'})

    monkeypatch.setattr(httpx, "AsyncClient",
                        lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs))
    assert asyncio.run(llm.generate_json("WORKER", {}, {"type": "object"})) == {"ok": True}


def test_cloud_model_timeout_still_fails_without_retry_or_success_fallback(monkeypatch):
    monkeypatch.setenv("MULTI_AGENT_TIMEOUT", "360")
    original = httpx.AsyncClient
    calls = []

    def respond(request):
        calls.append(request)
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr(httpx, "AsyncClient",
                        lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs))
    with pytest.raises(llm.AgentError) as error:
        asyncio.run(llm.generate_json("WORKER", {}, {"type": "object"}))
    assert error.value.code == "dependency_timeout"
    assert len(calls) == 1
