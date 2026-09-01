# Student 3 — Local Experience & Attraction Recommender

Release 0 microservice slice: browse/filter local attractions, leave reviews, and get an
AI-Mode recommendation (Ollama + Qwen) grounded in the seeded attraction catalogue. Full
RAG-grounding against a curated destination knowledge base is Release 1 scope.

## Layout

- `frontend/` — static HTML/CSS + HTMX. `index.html` browses/filters attractions and hosts
  the "ask the AI" interest form. Served by nginx, which reverse-proxies `/api/` to
  `student3-backend` (see `nginx.conf`) so the page can call same-origin `/api/...` paths.
- `backend/` — Flask API. Owns the public `/api/*` contract used by the frontend, and the
  `/api/recommend` Plan → Act → Observe → Adapt loop (`recommend.py`). Talks to the database
  service over HTTP via `database_client.py` — it never touches the SQLite file directly.
- `database/` — Flask API that owns `attractions.db` and the `attractions`/`reviews` schema
  (`schema.sql`). Exposes CRUD at `/api/data/*`. `init_db.py` creates the schema; `seed.py`
  inserts sample rows (idempotent - skips if already seeded).
- `tests/` — pytest suite covering both services' CRUD and `/api/recommend`, all offline
  (the database tests use a temp SQLite file per test; the recommend tests mock Ollama).
- `docs/prompt-log.md` — running log of AI-assisted design decisions, especially the
  `/api/recommend` prompt shape.

## Local development (without Docker)

```bash
# terminal 1 - database service
cd student-3/database
pip install -r requirements.txt
python init_db.py && python seed.py
python app.py            # listens on :8080

# terminal 2 - backend service
cd student-3/backend
pip install -r requirements.txt
set DATABASE_API_URL=http://localhost:8080
set OLLAMA_URL=http://localhost:11434
python app.py             # listens on :8080 too - use a different port locally if running both at once

# terminal 3 - frontend
cd student-3/frontend
python -m http.server 5103   # nginx/reverse-proxy isn't available outside Docker, so
                              # point index.html's fetch calls at the backend's real port
                              # if you're not going through docker-compose
```

Running both `backend` and `database` locally at once needs two different ports (both
default to 8080) — set `PORT`-style overrides or just run one at a time depending on what
you're testing.

## Tests

```bash
cd student-3
pip install -r backend/requirements.txt
pytest tests
```

## Docker Compose

Wired into the root `docker-compose.yml`: `student3-db-init` (one-shot schema+seed) →
`student3-database` → `student3-backend` (also depends on the shared `ollama-model-setup`,
which pulls `qwen2.5:3b` via `OLLAMA_MODELS`) → `student3-frontend`. From the repo root:

```bash
docker compose up -d student3-frontend
```

brings up this whole slice plus its `ollama` dependency.
