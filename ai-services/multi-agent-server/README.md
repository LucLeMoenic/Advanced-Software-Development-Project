# Shared Multi-Agent Server (Release 2)

One native, non-containerised service coordinates three agents and a human:

```
caller (feature backend or terminal) --evidence--> POST /workflows
   Planner  -> plan, required evidence, success criteria
   Worker   -> items, each citing the evidence it used
   Reviewer -> verdict + findings, plus deterministic automatic checks
   Human    -> approve | correct | partial | reject   (POST /workflows/{id}/decision)
```

It is **not** a Docker Compose service, like Ollama, MCP, RAG and the agentic loop. Feature backends
reach it at `MULTI_AGENT_SERVER_URL` (`http://127.0.0.1:5600`, or `http://host.docker.internal:5600`
from a container).

## Run

```powershell
cd ai-services/multi-agent-server
pip install -r requirements.txt
ollama pull llama3.2:3b          # one model serves all three agents
python -m uvicorn server:app --host 127.0.0.1 --port 5600
```

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Native Ollama |
| `MULTI_AGENT_MODEL` | `llama3.2:3b` | Model for Planner, Worker and Reviewer |
| `MULTI_AGENT_TIMEOUT` | `180` | Seconds per model call |
| `MULTI_AGENT_DATA_DIR` | `./data` (git-ignored) | Workflow records and `audit.log.jsonl` |

## Design decisions

- **The caller supplies the evidence.** The server never reads application data. Every claim the Worker
  makes must cite supplied evidence ids, so the evidence trail is explicit and auditable.
- **One model, three prompts.** Prompts are versioned under `../agentic-loop/prompts/multi-agent-*-v1.txt`.
  A second resident model has caused out-of-memory crashes on the development host.
- **Constrained output.** Each agent returns JSON validated by Pydantic. The JSON schema sent to Ollama
  restricts every evidence id to the supplied ids (and Reviewer `item_id` to real Worker items).
  Invalid output is retried once, then the stage fails.
- **The Reviewer cannot be talked into a pass.** Deterministic checks (`checks.py`) run beside the model:
  an item whose subject does not match the evidence entry it cites is a *blocking* finding, and any
  blocking finding forces the verdict to `fail` whatever the model says.
- **A Reviewer failure does not discard good work.** If only the Reviewer fails, the workflow still goes to
  human review with the automatic checks only, marked `degraded: true`, never with a `pass`.
  A Planner or Worker failure ends the workflow as `failed`.
- **The human is the only way out of `awaiting_human_review`.** `reject` requires notes; `partial` needs
  existing item ids; `correct` needs a valid output citing only supplied evidence (automatic checks are
  re-run and recorded). A second decision returns `409`.
- **Asynchronous.** Three CPU-bound model calls take minutes, so `POST /workflows` returns `202`
  immediately and callers poll. One workflow runs at a time (`503 busy` otherwise).
- **Tamper-evident audit log.** Each entry stores the SHA-256 of the previous one; `GET /audit/verify`
  recomputes the chain and reports the first broken entry.

## API

| Method | Path | Notes |
|---|---|---|
| `POST` | `/workflows` | `{feature, task, evidence:[{id,title,text}], submitted_by?}` -> `202 {id,status}` |
| `GET` | `/workflows` | Summaries, newest first |
| `GET` | `/workflows/{id}` | Full record: `plan`, `work`, `review`, `human_decision`, `final_output`, `history`, `error` |
| `POST` | `/workflows/{id}/decision` | `{decision, notes?, decided_by?, corrected_output?, accepted_item_ids?}` |
| `GET` | `/audit?workflow_id=` | Hash-chained entries |
| `GET` | `/audit/verify` | `{valid, entries, broken_at}` |
| `GET` | `/health` | `{status, busy}` |

Status lifecycle: `queued -> planning -> working -> reviewing -> awaiting_human_review ->
approved | corrected | partially_accepted | rejected` (or `failed`).

Errors use the shared shape `{"error": {"code", "message", "fields"}}`: `validation_error` (400),
`not_found` (404), `not_awaiting_review` (409), `busy` (503), `notes_required`, `invalid_selection`,
`correction_required`, `invalid_correction` (400).

## Terminal

The CLI uses the same HTTP API as the application.

```powershell
python cli.py run --feature student-3 --task "Suggest a relaxed food-focused afternoon" `
    --student3-backend http://localhost:5203 --category restaurant   # builds evidence from the catalogue
python cli.py review <id>        # shows plan/work/review, then asks for the human decision
python cli.py decide <id> --decision partial --accept i1,i2 --notes "Dropped the loud venue"
python cli.py show <id> [--json] | list | audit [<id>] | verify
```

## Tests

```powershell
cd ai-services/multi-agent-server
pip install -r requirements.txt
python -m pytest
```

62 tests run offline against a scripted fake model: pipeline and audit sequence, evidence-id schema
constraints, retries, the deterministic checks and verdict policy, Reviewer degradation, every human
decision rule, the hash chain (including tamper and deletion detection), and the HTTP API.
Live evidence against a real model is in `student-3/docs/evidence/release-2/multi-agent-server/`.

## Limits

- A 3B model on CPU takes roughly 1-2 minutes per workflow, and its Planner output is generic.
- The Reviewer model is weaker than the automatic checks; it mostly restates them. The human decision
  and the deterministic checks are the real controls.
- Single-process and file-backed: not for concurrent multi-user production use.
- The Student 3 backend routes and UI panel (`MULTI_AGENT_ENABLED`, default `false`) are a later chunk.
