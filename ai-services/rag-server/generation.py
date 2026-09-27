import json
import os
from pathlib import Path
from threading import BoundedSemaphore
from typing import Literal

import anyio
import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

import confidence

INSUFFICIENT_ANSWER = "Not enough information in the knowledge base to answer this."
PROMPT_PATH = Path(__file__).resolve().parents[1] / "agentic-loop" / "prompts" / "rag-grounding-v1.txt"
_capacity = BoundedSemaphore(1)


class GenerationError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message
        super().__init__(message)


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    text: str = Field(min_length=1, max_length=350, pattern=r"^[^\[\]]+$")
    chunk_ids: list[str] = Field(min_length=1, max_length=3)


class GeneratedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: Literal["answered", "insufficient"]
    claims: list[Claim] = Field(max_length=4)


def insufficient():
    return {"answer": INSUFFICIENT_ANSWER, "citations": [], "confidence": "insufficient"}


def render_answer(payload, ranked):
    try:
        generated = GeneratedAnswer.model_validate(payload)
        if generated.status == "insufficient":
            if generated.claims:
                raise ValueError("Abstention has claims")
            return insufficient()
        if not generated.claims:
            raise ValueError("Empty answer")
        chunks = {chunk.chunk_id: (chunk, score) for chunk, score in ranked}
        used = []
        sentences = []
        for claim in generated.claims:
            if not claim.text.strip() or "http://" in claim.text or "https://" in claim.text:
                raise ValueError("Invalid claim text")
            if len(claim.chunk_ids) != len(set(claim.chunk_ids)):
                raise ValueError("Repeated source")
            for identifier in claim.chunk_ids:
                if identifier not in chunks:
                    raise ValueError("Unknown source")
                if identifier not in used:
                    used.append(identifier)
            sentences.append(f"{claim.text.strip()} " + " ".join(f"[{identifier}]" for identifier in claim.chunk_ids))
        answer = "\n\n".join(sentences)
        if len(answer) > 2000:
            raise ValueError("Answer too long")
        citations = [{"source": chunks[identifier][0].source, "chunk_id": identifier,
                      "snippet": chunks[identifier][0].text[:280], "score": round(float(chunks[identifier][1]), 4)} for identifier in used]
        return {"answer": answer, "citations": citations,
                "confidence": confidence.categorize(min(chunks[identifier][1] for identifier in used))}
    except (ValidationError, ValueError, TypeError):
        raise GenerationError(502, "invalid_dependency_response", "The model returned an invalid grounded answer.") from None


async def generate(question, ranked):
    if not _capacity.acquire(blocking=False):
        raise GenerationError(503, "dependency_unavailable", "The local model is busy. Try again shortly.")
    try:
        context = [{"chunk_id": chunk.chunk_id, "source": chunk.source, "text": chunk.text} for chunk, score in ranked]
        with anyio.fail_after(20):
            async with httpx.AsyncClient(timeout=18) as client:
                async with client.stream(
                    "POST", os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/") + "/api/generate",
                    json={"model": os.getenv("RAG_MODEL", "llama3.2:3b"), "stream": False,
                          "system": PROMPT_PATH.read_text(encoding="utf-8"),
                          "prompt": json.dumps({"question": question, "context": context}),
                          "format": GeneratedAnswer.model_json_schema(),
                          "options": {"temperature": 0, "num_predict": 600, "num_ctx": 4096}},
                ) as response:
                    response.raise_for_status()
                    content = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=4096):
                        if len(content) + len(chunk) > 16000:
                            raise ValueError("Oversized model response")
                        content.extend(chunk)
                    body = json.loads(content)
                    if not isinstance(body, dict) or body.get("done") is not True:
                        raise ValueError("Incomplete generation")
                    return render_answer(json.loads(body["response"]), ranked)
    except GenerationError:
        raise
    except (TimeoutError, httpx.TimeoutException):
        raise GenerationError(504, "dependency_timeout", "The local model timed out.") from None
    except httpx.HTTPError:
        raise GenerationError(503, "dependency_unavailable", "The local model is unavailable.") from None
    except (ValueError, KeyError, TypeError):
        raise GenerationError(502, "invalid_dependency_response", "The model returned an invalid response.") from None
    finally:
        _capacity.release()