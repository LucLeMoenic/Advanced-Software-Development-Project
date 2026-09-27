# Shared RAG Server (Release 1)

One native shared service retrieves feature-isolated Markdown knowledge and
uses native Ollama for constrained grounded generation. Student 1, Student 2 and
Student 3 knowledge is present. Automated model-double tests pass; native model generation
and cross-feature grounding evaluation remain release gates, not completed evidence.

## Contract

```
POST /query
{"feature": "student-3", "question": "..."}

200 OK
{
  "answer": "...",
  "citations": [
    {"source": "...", "chunk_id": "...", "snippet": "...", "score": 0.4}
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
  knows about. Retrieval does not require a second embedding model.
- Retain at most three chunks scoring at least 0.15, each at most 2000 characters
  and at most 6000 characters combined. Below-threshold results skip generation.
- Ollama returns structured claims using the versioned
  [grounding prompt](../agentic-loop/prompts/rag-grounding-v1.txt). Only retrieved
  IDs are accepted. Citation titles, snippets and scores come from the index;
  public answer markers are assembled from validated claims.
- Confidence is the lowest cited retrieval score: low from 0.15, medium from
  0.30, high from 0.40. These provisional thresholds were measured on the small
  Student 2 fixture set, not a statistically independent or cross-feature
  calibration. Scores measure lexical relevance, not truth or entailment.
- Malformed output/unknown references return 502, unavailable/busy models 503,
  timeouts 504. A valid model abstention returns the fixed insufficient response.
  One model generation is admitted at a time, with a 20-second model deadline
  inside a 25-second query deadline. Cold loading may exceed this budget.
- Model responses and backend RAG responses are read in 4096-byte chunks, rejecting
  output above 16000 bytes before buffering the whole body and closing the stream.
  Citation validation does not establish that claims are supported;
  human source checks and adversarial/live-model evaluation remain necessary.

## Grounding Evaluation

The [grounding dataset](tests/grounding-questions.json) covers the real Student 2
and Student 3 corpora, including live-data questions and instruction injection
with misleading lexical overlap. Offline tests verify retained candidates, not
answerability. These are development regressions, not an untouched held-out
evaluation. Unrelated government-budget and live hotel-price questions score
above 0.40; a higher threshold is not an entailment check.

After starting native Ollama with the approved model, run from this directory:

```powershell
$env:RAG_LIVE_EVAL = '1'
try { python -m pytest tests/test_query.py -k live_grounding -s -v }
finally { Remove-Item Env:RAG_LIVE_EVAL -ErrorAction SilentlyContinue }
```

This calls the real model through the native query handler, requires abstention
for unsupported cases, and prints model/prompt/corpus identifiers, responses,
sources and review rubrics. It is not an integrated browser test. A human must
check every generated claim against its cited full source; passing citation IDs
alone do not pass that gate. Retain the output and human decisions with the
commit/model identity, and evaluate a separately authored, untouched hold-out set
before accepting or recalibrating the shared thresholds. Normal CI skips these
nine live cases explicitly and never downloads a model.

Student 1's ten destination guides (`knowledge/student-1/`, one per catalogue city)
keep review metadata in the heading paragraph so it is never indexed, and start
every paragraph with `<City> <topic>:`. `tests/test_student1_retrieval.py` checks
city-accurate retrieval offline. Unsupported cities that share generic words
still retrieve at low confidence; see the
[Student 1 RAG HLD](../../student-1/docs/release-1-rag-hld.md) calibration note.

## Adding a feature's knowledge base

1. Create `knowledge/<feature>/*.md` — 6–10 short docs, one clear topic
   each, with a `# Title` heading.
2. Add labelled relevant/irrelevant questions and evaluate retrieval and generated
  claim support. Recalibrate shared thresholds across every available feature.
3. Restart the server after knowledge edits because indexes are cached. Record
  the corpus commit: paragraph-derived chunk IDs can change after edits.

## Running it

```powershell
python -m pip install -r ai-services/rag-server/requirements.txt
python -m uvicorn server:app --host 127.0.0.1 --port 5500 --app-dir ai-services/rag-server
```

## Env vars

| Var | Default | Purpose |
|---|---|---|
| `RAG_KNOWLEDGE_ROOT` | `ai-services/rag-server/knowledge` | Where feature folders live |
| `RAG_TOP_K` | `3` | Max citations returned per query |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Native model server |
| `RAG_MODEL` | `llama3.2:3b` | Approved local generation model |

Backends consume `RAG_SERVER_URL` / `RAG_ENABLED`; browsers call only their backend.
Requests accept only `feature` (student-1 through student-5) and a nonblank question
of at most 1000 characters. Unknown fields/features return 400. Empty feature
corpora return insufficient context.

See [Student 2 deployment](../../student-2/docs/release-1-runbook.md) for private
host bindings, VM routing limitations, and reproducible checks. Do not expose
this unauthenticated development service on a public interface.
