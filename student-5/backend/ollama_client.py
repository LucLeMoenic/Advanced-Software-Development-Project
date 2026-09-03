"""HTTP client for the shared Ollama runtime.

Marked requirement: the AI workflow is Frontend -> Backend/API -> Ollama -> LLM.
The browser never calls Ollama itself, and this module is the only part of the
backend that knows how to.

Design note: this deliberately does *not* copy db_client.py's "return the
status code, don't raise" policy. Forwarding a database 404 is useful because
the absence of a row is a real answer; forwarding an Ollama 500 is not, because
there is no partial advisory to hand back. So every failure mode -- connection
refused, read timeout, HTTP error status, unparseable body -- collapses into
``OllamaUnavailable``, which app.py turns into
``503 {"error": "ai service unavailable"}``. That is a different message from
the database's 503 on purpose: the two dependencies fail independently and the
response body should say which one broke.
"""

from typing import Any

import requests

DEFAULT_OLLAMA_URL = "http://ollama:11434"

# Fallback for local runs only. The model tag is configuration -- compose sets
# APPLICATION_MODEL -- so no request-building code below names a model.
DEFAULT_APPLICATION_MODEL = "llama3.2:3b"

# Generation is the slow part of the stack: a cold 3B model on CPU can take
# well over a minute to write a full advisory. This is intentionally far more
# generous than db_client's 5s, because here a slow answer is still the answer.
DEFAULT_TIMEOUT_SECONDS = 120.0

GENERATE_PATH = "/api/generate"


class OllamaUnavailable(Exception):
    """Raised when Ollama could not be reached or would not complete a prompt."""


class OllamaClient:
    """Thin wrapper over Ollama's ``/api/generate`` endpoint."""

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        """Send one non-streaming prompt and return the completion text.

        Args:
            prompt: the fully assembled prompt, including any grounding data.

        Returns:
            The model's completion as plain text.

        Raises:
            OllamaUnavailable: on any transport failure, non-200 status, or a
                reply that does not carry completion text.
        """
        url = self.base_url + GENERATE_PATH
        # stream=False so the whole completion arrives in one JSON object;
        # streaming would need the frontend to hold an open connection through
        # this service, which the fragment/JSON contracts do not support.
        body = {"model": self.model, "prompt": prompt, "stream": False}

        try:
            response = requests.post(url, json=body, timeout=self.timeout)
        except requests.RequestException as exc:
            raise OllamaUnavailable("POST {} failed: {}".format(url, exc)) from exc

        if response.status_code != 200:
            raise OllamaUnavailable(
                "POST {} returned {}".format(url, response.status_code)
            )

        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise OllamaUnavailable(
                "POST {} returned a non-JSON body".format(url)
            ) from exc

        completion = payload.get("response") if isinstance(payload, dict) else None
        if not isinstance(completion, str):
            raise OllamaUnavailable(
                "POST {} returned no completion text".format(url)
            )
        return completion
