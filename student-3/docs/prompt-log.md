# Prompt Log — Local Experience & Attraction Recommender (student-3)

Record meaningful AI-assisted code, infrastructure, or prompt-design work here. This is the artefact for the Release 0 "Prompt Engineering and Context Management" marking criterion — keep updating it as the `/api/recommend` prompt or the Plan/Act/Observe/Adapt logic changes.

| Date | Task/prompt summary | Context supplied | AI output | Human decision | Validation/evidence |
|---|---|---|---|---|---|
| 2026-08-31 | Design the `/api/recommend` LLM prompt and the Plan → Act → Observe → Adapt loop around it. | Release 0 brief scope (Ollama + Qwen, no MCP/RAG/multi-agent yet), the `attractions` schema, and the sibling `student-1` service's grounding/fallback pattern for reference. | `recommend.py`: `_build_prompt()` injects only attractions actually returned by the database query (max 6) and instructs the model to recommend *only* from that list, in 2–3 sentences; `_build_narrow_prompt()` is the ADAPT-stage retry, cut to the top 2 candidates and a one-sentence instruction; `_is_response_usable()` treats a response as on-topic only if it names a candidate's `name` or `category` from the supplied context. | Kept the closed-context ("only from this list") instruction deliberately — it's the main defence against the model inventing attractions that don't exist in the seeded data, which would look broken in the live demo. Kept the on-topic check as a simple keyword-overlap heuristic rather than a second LLM call, since Release 0 explicitly excludes multi-agent/self-critique patterns. | Verified via `tests/test_recommend.py`, which mocks `_call_ollama`/`requests.post` to check: a normal on-topic response is accepted as-is; an empty response triggers the ADAPT retry with the narrower prompt; a response that mentions none of the supplied attractions is treated as off-topic and falls through to the retry/fallback path. |

## Why this prompt shape

The prompt is built as: role instruction → closed candidate list (name/category/rating/description, capped at 6 rows from the actual DB query) → the user's raw interest text → a length constraint. Two things drove this:

1. **Grounding, not free generation.** Qwen has no knowledge of this project's seeded attractions, so without an explicit "only recommend from this list" instruction it will happily invent plausible-sounding places. Capping context to what the `PLAN` stage's category filter actually returned keeps the prompt small and keeps every named attraction traceable back to a real database row.
2. **The narrower ADAPT prompt is a different shape, not just a repeat.** On a bad first response, retrying with the identical prompt rarely helps a local model. The retry cuts the candidate list to 2 items and drops the multi-sentence instruction, on the theory that the failure was model verbosity/confusion rather than missing information.

The `_is_response_usable()` heuristic (non-empty, minimum length, and — when candidates exist — mentions at least one candidate's name or category) is intentionally simple for Release 0. If it turns out to be too strict/loose during the demo, that's the function to revisit first.
