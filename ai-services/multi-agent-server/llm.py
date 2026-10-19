"""Ollama client for the three agents.

One native Ollama model serves Planner, Worker and Reviewer (different system
prompts, not different models): this host has limited RAM and a second resident
model has caused out-of-memory crashes before.
"""

import json
import os

import httpx

MAX_RESPONSE_BYTES = 64_000


class AgentError(Exception):
    """A model call failed or returned something unusable."""

    def __init__(self, code, message, detail=None, raw=None):
        self.code, self.message = code, message
        self.detail, self.raw = detail, raw  # why validation failed / the model's rejected output
        super().__init__(message)


def model_name():
    return os.getenv("MULTI_AGENT_MODEL", "llama3.2:3b")


async def generate_json(system, payload, schema, *, num_predict=800):
    """Ask Ollama for JSON constrained by `schema`; returns the parsed object."""
    url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/") + "/api/generate"
    timeout = float(os.getenv("MULTI_AGENT_TIMEOUT", "180"))
    body = {
        "model": model_name(),
        "stream": False,
        "system": system,
        "prompt": json.dumps(payload),
        "format": schema,
        "options": {"temperature": 0, "num_predict": num_predict, "num_ctx": 4096},
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=body)
            response.raise_for_status()
    except httpx.TimeoutException:
        raise AgentError("dependency_timeout", "The local model timed out.") from None
    except httpx.HTTPError:
        raise AgentError("dependency_unavailable", "The local model is unavailable.") from None
    if len(response.content) > MAX_RESPONSE_BYTES:
        raise AgentError("invalid_dependency_response", "Oversized model response.")
    try:
        data = response.json()
        if data.get("done") is not True:
            raise ValueError("incomplete")
        return json.loads(data["response"])
    except (ValueError, KeyError, TypeError):
        raise AgentError("invalid_dependency_response", "The model returned invalid JSON.") from None
