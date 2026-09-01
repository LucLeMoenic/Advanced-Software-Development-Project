"""AI-Mode recommendation logic: an explicit Plan -> Act -> Observe -> Adapt loop.

Release 0 scope: the backend calls Ollama directly (no MCP/RAG/multi-agent
layers yet - RAG-grounding for this feature is Release 1 scope). Each stage
prints a clearly labelled line so the loop can be demoed live in a terminal,
per the Release 0 marking rubric.
"""

import os

import requests

from database_client import DatabaseResponseError, DatabaseUnavailableError, list_attractions

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
# Generous: a local model's first call after container start pays a one-off
# cost to load into memory, which regularly exceeds 30s on CPU-only hosts.
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "120"))
MAX_CONTEXT_ATTRACTIONS = 6
KNOWN_CATEGORIES = {"sight", "restaurant", "activity"}
MIN_USABLE_RESPONSE_LENGTH = 15


def get_recommendation(interest_text):
    """Runs the full Plan -> Act -> Observe -> Adapt loop and returns a JSON-ready dict."""

    # PLAN: parse the interest/category input, decide which attractions to pull as context
    category_hint = _extract_category_hint(interest_text)
    print(f"PLAN: interest={interest_text!r} -> category filter={category_hint!r}")

    # ACT: query the database, then call the LLM with that context
    try:
        candidates = list_attractions(category=category_hint) if category_hint else list_attractions()
    except (DatabaseUnavailableError, DatabaseResponseError) as exc:
        print(f"ACT: database query failed ({exc}); using empty context")
        candidates = []

    candidates = candidates[:MAX_CONTEXT_ATTRACTIONS]
    print(f"ACT: pulled {len(candidates)} attraction(s) as context, calling Ollama model={OLLAMA_MODEL}")

    prompt = _build_prompt(interest_text, candidates)
    raw_response = _call_ollama(prompt)

    # OBSERVE: validate the LLM response is non-empty and roughly on-topic
    usable, reason = _is_response_usable(raw_response, candidates)
    print(f"OBSERVE: usable={usable} ({reason})")

    if usable:
        return _success_payload(raw_response, candidates, source="ai")

    # ADAPT: on a bad/empty response, retry once with a narrower prompt, else fall back
    print("ADAPT: retrying once with a narrower prompt")
    narrow_prompt = _build_narrow_prompt(interest_text, candidates)
    retry_response = _call_ollama(narrow_prompt)
    retry_usable, retry_reason = _is_response_usable(retry_response, candidates)
    print(f"ADAPT: retry usable={retry_usable} ({retry_reason})")

    if retry_usable:
        return _success_payload(retry_response, candidates, source="ai_retry")

    print("ADAPT: retry also unusable, falling back to templated response")
    return _success_payload(_fallback_text(interest_text, candidates), candidates, source="fallback")


def _extract_category_hint(interest_text):
    lowered = (interest_text or "").lower()
    for category in KNOWN_CATEGORIES:
        if category in lowered or f"{category}s" in lowered:
            return category
    return None


def _build_prompt(interest_text, candidates):
    context_lines = "\n".join(
        f"- {c['name']} ({c['category']}, rating {c['rating']}): {c['description']}"
        for c in candidates
    ) or "No matching attractions were found in the database."

    return (
        "You are a local experience recommender for a travel app. "
        "Recommend ONLY from the attractions listed below - do not invent new places. "
        "Keep the answer to 2-3 sentences.\n\n"
        f"Traveller interests: {interest_text}\n\n"
        f"Available attractions:\n{context_lines}\n\n"
        "Recommendation:"
    )


def _build_narrow_prompt(interest_text, candidates):
    top = candidates[:2]
    context_lines = "\n".join(f"- {c['name']} ({c['category']})" for c in top) or "no attractions available"
    return (
        "In one short sentence, recommend ONE attraction from this list that best matches "
        f"'{interest_text}': {context_lines}"
    )


def _call_ollama(prompt):
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=OLLAMA_TIMEOUT,
        )
        response.raise_for_status()
        return (response.json().get("response") or "").strip()
    except (requests.exceptions.RequestException, ValueError) as exc:
        print(f"ACT: Ollama call failed ({exc})")
        return ""


def _is_response_usable(response_text, candidates):
    if not response_text:
        return False, "empty response"
    if len(response_text) < MIN_USABLE_RESPONSE_LENGTH:
        return False, "response too short"
    if candidates:
        lowered = response_text.lower()
        on_topic = any(c["name"].lower() in lowered or c["category"].lower() in lowered for c in candidates)
        if not on_topic:
            return False, "no candidate attraction mentioned"
    return True, "ok"


def _fallback_text(interest_text, candidates):
    if not candidates:
        return (
            f"We couldn't find attractions matching '{interest_text}' right now. "
            "Try a broader interest like 'sight', 'restaurant', or 'activity'."
        )
    lines = [f"Here are a few options that might suit '{interest_text}':"]
    for c in candidates[:3]:
        lines.append(f"- {c['name']} ({c['category']}, rating {c['rating']}): {c['description']}")
    return "\n".join(lines)


def _success_payload(text, candidates, source):
    return {
        "recommendation": text,
        "source": source,
        "attractions_considered": [c["id"] for c in candidates],
    }
