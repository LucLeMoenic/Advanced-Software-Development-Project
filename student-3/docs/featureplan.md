# Local Experience & Attraction Recommender Feature Plan

## Goal

Build an integrated attraction-recommendation feature where a traveller:

1. browses and filters a seeded attraction catalogue by category;
2. creates, edits, and deletes attractions, and leaves reviews, entirely through the browser;
3. describes their interests in free text and receives an AI recommendation grounded in the actual catalogue, with a deterministic fallback if the model is unavailable or unusable.

The feature is complete only when its HTMX frontend, Flask backend, Flask database API, SQLite data, Ollama integration, shared navigation, Docker Compose configuration, and Student 3 CI work together inside the integrated group application — a standalone feature scores zero per the Release 0 rubric.

Detailed contracts are in `requirements.md`.

## Fixed Implementation Contracts

| Contract | Value |
|---|---|
| Final folder | `student-3/` |
| Frontend service / host port | `student3-frontend` / `5103` |
| Backend service / host port | `student3-backend` / `5203` |
| Database service / host port | `student3-database` / `5303` |
| One-shot init job | `student3-db-init` (runs `init_db.py` then `seed.py`) |
| Internal ports | Frontend `80` (nginx); backend and database `8080` |
| Frontend | Static HTML/CSS + HTMX (no build step) |
| Backend | Flask (Python) |
| Database API | Flask (Python) + SQLite (`attractions.db`) |
| Application model | `qwen2.5:3b` (overridable via `STUDENT3_MODEL`) |
| Theme | Shared visual conventions from `shared/style.css`, reconciled with `student-3/frontend/style.css` |

Boundary rules:
- The frontend calls only the backend (via nginx reverse proxy to `student3-backend`).
- The backend calls the database API for all persistence and calls Ollama only for `/api/recommend`.
- Only the database service opens `attractions.db`.
- All services use Compose DNS names internally (`student3-database`, `ollama`).
- Secrets and environment-specific values come from environment variables (`DATABASE_API_URL`, `OLLAMA_URL`, `OLLAMA_MODEL`).

## Implementation Sequence (as actually built)

### Chunk 1 — Attraction CRUD Core (`#17`, `8525cae`)

**Implemented**
- `student-3/database`: `schema.sql` (`attractions`, `reviews`), `db.py` connection helper, `init_db.py`, `seed.py` (12 attractions, 14 reviews, idempotent), and the Flask CRUD API (`/api/data/attractions/*`, `/api/data/reviews/*`).
- `student-3/backend`: Flask proxy API (`/api/attractions/*`, `/api/reviews/*`) via `database_client.py`, translating database errors into `502 database_unavailable`.
- Dockerfiles for both services, wired into the root `docker-compose.yml`.

**Done when:** full attraction CRUD and review create/list work through HTTP, backed by real SQLite, with the database owning the schema exclusively.

### Chunk 2 — AI-Mode Recommendation (`#23`, `#24`, `1d8f0b0`, `0d11095`)

**Implemented**
- `recommend.py`: the `/api/recommend` Plan → Act → Observe → Adapt loop — Plan infers a category hint from the interest text, Act queries the database and calls Ollama, Observe checks the response is non-empty and names a supplied candidate, Adapt retries once with a narrower prompt and falls back to a deterministic templated response if that also fails.
- Removed a dangling placeholder AI form from the frontend that pre-dated the real recommend integration.

**Done when:** a real Ollama call returns a grounded recommendation; a forced-bad response demonstrably falls through retry to the deterministic fallback without ever surfacing a raw error to the user.

### Chunk 3 — CI Hardening (`#35`, `7e8578d`)

**Implemented**
- Finished attraction card rendering on the frontend (read-only browse/filter view).
- Hardened `student-3.yml`: pytest stage, `docker compose config --quiet`, image builds, `student3-db-init` run, service startup with `--wait`, and a smoke test asserting all three `/health` endpoints plus `≥10` seeded attractions via `/api/attractions`.

**Done when:** `student-3.yml` passes end-to-end on a clean checkout, including the live-container smoke stage.

### Chunk 4 — Frontend CRUD UI (PR `#38`)

**Implemented**
- "Add an Attraction" form (`#manage` section) wired to `POST /api/attractions`.
- Per-card Edit (inline form swap, `PUT`) and Delete (`hx-confirm`, `DELETE`) actions.
- Per-card collapsible review form (`POST /api/reviews`).
- A small inline `json-body` htmx extension, discovered as necessary because `create_attraction`/`update_attraction`/`create_review` only accept a JSON body (`request.get_json(silent=True)`, no form-data fallback) — a plain HTMX form submission was silently rejected as an empty payload without it.

**Done when:** create, edit, delete, and review-submission are all demonstrable through the browser against the integrated app, not just via `curl`.

### Chunk 5 — Release 0 Report and Demonstration Evidence (done)

**Produced**
- The Release 0 documentation set, plus a finalised agentic-loop record (`20260906T104055Z-f52cc6be69164e07b0502a263671ee67.json`, `formatElapsed`, PR #55).
- Screenshots: browse/filter, create/edit/delete in the browser, review submission, AI loading state — `docs/evidence/01-*.png` through `12-*.png`.

**Done when:** every checklist row in `known-issues.md` has an exact evidence location — met for Release 0 as of PR #55.

## Release 1 Implementation Sequence (as actually built)

Detailed contracts for each stage are in `requirements.md` §§1.3–1.4, 3.6–3.7, 4.4, and NFR-07–11. Every stage's agentic-loop evidence is in `prompt-log.md` and analysed phase by phase in `reviewrecord.md`.

### Stage 0 — Shared Contracts and Infrastructure (`#61`, `#62`)

**Implemented** (some as shared, cross-student chunks; student-3's own additions confirmed with the group lead first)
- Shared MCP server (`ai-services/mcp-server/`) and RAG server (`ai-services/rag-server/`) scaffolding, host-native (not Compose services), per the Release 1 brief.
- `docker-compose.yml`/`.env.example` wiring for `MCP_SERVER_URL`/`RAG_SERVER_URL`/`host.docker.internal` across all backends.

### Stage 1 — Knowledge Base and MCP Tools (`KSS/r1-knowledge-and-tools`, PR `#62`)

**Implemented**
- `attractions.search`/`attractions.get_reviews` read-only MCP tools (category enum, `limit` ≤10, `extra="forbid"` unknown-field rejection — including a top-level wrapper gap found and fixed while preparing Stage 2).
- 8-doc RAG knowledge base under `ai-services/rag-server/knowledge/student-3/`.
- A real retrieval bug found and fixed while validating the knowledge base (no stopword stripping let irrelevant questions score too close to genuine matches).
- Agentic-loop record: `total_matches` field added to `attractions.search`, `changed` (hallucinated reviewer finding rejected).

**Done when:** both tools pass their own input-validation tests and return correctly-shaped, correctly-filtered results against the real database service.

### Stage 2 — Backend Integration (`KSS/r1-backend-mcp-rag`, PR `#79`)

**Implemented**
- `mcp_client.py` (streamable-HTTP MCP client) and `rag_client.py`, following `database_client.py`'s existing shape.
- `GET /api/mcp/tools`, `POST /api/mcp/invoke` (backend allow list), `POST /api/rag/ask` routes.
- Two real bugs found and fixed live: the Stage 1 top-level-field gap, and an `anyio` `ExceptionGroup` swallowing a tool's own validation error into a misleading "unavailable" result.
- Agentic-loop record: `RagResponseError.code` addition, `rejected` after review (correctly) caught bugs the reviewer's own stated finding had missed.

**Done when:** all three new routes work end to end against the real, live shared servers and the real student-3 database (verified, not just mocked).

### Stage 3 — Frontend Panels (`KSS/r1-frontend-panels`, PR `#80`)

**Implemented**
- "Attraction Tools (MCP)" panel (dynamic per-tool argument form) and "Ask the Destination Guide (RAG)" panel (confidence badge, citations, insufficient-context state), plus disabled/offline states for both.
- Verified live in a real browser (Playwright): a real MCP search result, a real Ollama-backed grounded RAG answer with citations, the insufficient-context state, both disabled states, both offline states, and no horizontal overflow at 375px.
- Agentic-loop record: `confidenceBadgeClass`, `kept` (reviewer's finding was hallucinated; code was already correct).

**Done when:** both panels are demonstrable through the browser against the integrated app, matching the existing HTMX/`escapeHtml` conventions.

### Stage 4 — Compose and CI (`KSS/r1-compose-ci`, PR `#86`)

**Implemented**
- `MCP_ENABLED`/`RAG_ENABLED` added to `student3-backend` in `docker-compose.yml`.
- `student-3.yml` extended: new `on.paths` triggers, `MCP_ENABLED=false`/`RAG_ENABLED=false` for the CI run, and three new smoke assertions for the disabled-body contract.
- `.env.example` documented.
- A loop attempt to add local Compose-config validation to `scripts/test/student-3.ps1` failed outright (reviewer hallucination, then a malformed format-correction retry) — implemented by hand and verified live against both a valid and a deliberately-broken `docker-compose.yml`.

**Done when:** `student-3.yml` passes end to end including the new disabled-body smoke assertions, verified via a full local run of the real recipe (build, db-init, up, smoke, down).

### Stage 5 — Agentic Loop Validation Modes (`KSS/r1-loop-validation-student3`, PR `#89`)

**Implemented**
- Extended the shared `ai-services/agentic-loop/ServiceValidation.cs` (ownership confirmed with the group lead first) so `validate-mcp`/`validate-rag` support `student-3` alongside the pre-existing `student-1`/`student-2`.
- Four loop attempts at the extension's own `IsValidStudent3Mcp` function all failed for host-environment reasons (implementer repetition once, then Ollama loading both loop models simultaneously three times) rather than a prompt problem — documented in full rather than hidden.
- Implemented by hand; captured the required live student-3 evidence (`attractions.search` restaurant filter, one answerable and one unanswerable RAG question) via `ServiceValidation.CaptureAsync` directly, bypassing the crashing CLI.

**Done when:** the shared validation modes correctly support student-3, and live evidence exists for all three required cases — met, with the answerable-RAG-question case additionally cross-referenced against its earlier Stage 3 success due to a host-timeout limitation (see `knownissues.md`).

### Stage 6 — Evidence, Report, and Cleanup (`KSS/r1-evidence-report-cleanup`, in progress)

**To produce**
- Full Release 1 rewrite of `requirements.md`, `architecture.md`, `featureplan.md` (this document), `riskplan.md`, `knownissues.md`.
- A green `student-3.yml` Actions run link.
- Draft report paragraphs and a showcase-video script (delivered in conversation, not committed files, per the handoff).
- My segment of the group showcase video and the Week 9 attendance checkpoint.

**Done when:** every checklist row in `knownissues.md` has an exact evidence location, and the group report/video are ready to submit.

## Working Rule

For each chunk:
1. Confirm the contract in `requirements.md` before changing behaviour.
2. Implement the smallest complete vertical slice (frontend → backend → database).
3. Run `pytest tests` from `student-3/`.
4. Manually verify against the real containers (`docker compose up -d --build student3-frontend`), not just mocked tests.
5. Update `prompt-log.md`/`review-record.md` with what AI assistance was used and how it was validated.
6. Integrate before starting the next chunk — never leave the frontend, backend, and database out of sync with each other.

## Local Setup Reference

```bash
docker compose up -d --build student3-frontend   # brings up the full slice + ollama dependency
# frontend:  http://localhost:5103
# backend:   http://localhost:5203
# database:  http://localhost:5303
cd student-3 && pip install -r backend/requirements.txt && python -m pytest tests
```
