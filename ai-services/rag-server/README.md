# Shared RAG Server (Release 1)

**Status: scaffolding only.** No knowledge base content yet — each student
adds their own `knowledge/<feature>/*.md` docs in their own Stage 1 branch,
and `confidence.categorize()` still needs real thresholds (see the TODO in
`confidence.py`) before `/query` will return anything but a 500. Built on
`KSS/shared-mcp-rag-setup`; ownership of this shared component is an
**assumption** pending group sign-off — flag this in the report if it
changes.

## Contract

```
POST /query
{"feature": "student-3", "question": "..."}

200 OK
{
  "answer": "...",
  "citations": [
    {"source": "...", "chunk_id": "...", "snippet": "...", "score": 0.0}
  ],
  "confidence": "high" | "medium" | "low" | "insufficient"
}
```

When nothing relevant is found, `confidence` is `"insufficient"`,
`citations` is `[]`, and `answer` is a fixed
"Not enough information in the knowledge base to answer this." string —
never a guess dressed up as fact.

## How retrieval works

- Each `knowledge/<feature>/` folder holds short Markdown docs, one topic
  per file, starting with a `# Heading` (used as the citation `source`).
- Each file is split into paragraph chunks at blank lines. `chunk_id` is
  `<filename>#<paragraph index>`.
- Chunks are ranked with **TF-IDF + cosine similarity**, implemented with
  the standard library only (no scikit-learn/numpy), not Ollama embeddings.
  Two reasons: this host has 8 GB RAM and the agentic loop already loads two
  Ollama models, so a third model just for embeddings (`nomic-embed-text`)
  would fight them for memory; and scikit-learn has no prebuilt wheel for
  Python 3.14 (this machine) and failed to build from source here, which
  would also risk failing on a grader's machine or a CI Python version we
  don't control. This is a documented trade-off, not a shortcut nobody
  knows about — raise it if the group wants generative or embedding-based
  retrieval instead.
- The **answer is extractive**: it is the best-matching chunk's text
  verbatim, not an LLM-generated summary. Every word in `answer` is
  therefore directly traceable to the single citation it came from. No
  Ollama call happens in this server at all. If the group wants a
  generated answer instead, that would add an Ollama call here (extra RAM
  and latency) — flag it as a group decision before adding it.

## Adding a feature's knowledge base

1. Create `knowledge/<feature>/*.md` — 6–10 short docs, one clear topic
   each, with a `# Title` heading.
2. Pick real confidence thresholds in `confidence.py` by running a few real
   questions through `retrieval.get_index("<feature>")` and looking at the
   actual scores — don't guess numbers before the docs exist.

## Running it

```powershell
pip install -r ai-services/rag-server/requirements.txt
uvicorn server:app --host 127.0.0.1 --port 5500 --app-dir ai-services/rag-server
```

## Env vars

| Var | Default | Purpose |
|---|---|---|
| `RAG_KNOWLEDGE_ROOT` | `ai-services/rag-server/knowledge` | Where feature folders live |
| `RAG_TOP_K` | `3` | Max citations returned per query |

Backends consume `RAG_SERVER_URL` / `RAG_ENABLED` (Stage 2) — those are
backend-side settings documented in each feature's own backend client.
