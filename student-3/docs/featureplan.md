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

### Chunk 5 — Report and Demonstration Evidence (in progress)

**To produce**
- This documentation set (`requirements.md`, `feature-plan.md`, `risk-plan.md`, `architecture.md`, `review-record.md`, `contribution-log.md`, `known-issues.md`).
- A finalised agentic-loop record under `docs/agentic-loop-records/` for a real piece of student-3 work (see `known-issues.md`).
- Screenshots: browse/filter, create/edit/delete in the browser, review submission, AI success, AI fallback, `student-3.yml` green run, `docker compose up` output.
- My segment of the group showcase video.

**Done when:** every checklist row in `known-issues.md`/the technical report has an exact evidence location, and my segment of the group video shows CRUD, the AI loop, and the integrated feature.

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
