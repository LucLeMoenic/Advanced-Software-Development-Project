# Feature Context - Travel Logistics & Advisory Service

Student 5 (Alex Chen). Read this page first, then `requirements.md`,
`architecture.md` and `known-issues.md` before changing anything.

## Goal

A traveller picks a destination and immediately sees what is *recorded* about
it: seasonal weather notes, the entry/visa requirement, and transit options.
They can then ask for an AI advisory that turns those stored rows into a short
packing-and-documents brief written for their month of travel and interests.
An admin section on the same page maintains the destination list.

The feature is only complete when all three of its services run together in the
group's Docker Compose stack. Standalone services do not satisfy the brief.

## Scope

Release 0 only. Everything below is implemented and integrated.

| Release 0 in scope | Not in this release |
|---|---|
| Three containerised services, Compose-integrated | MCP tools (`get_weather`, `check_visa_requirement`) - Release 1 |
| JSON CRUD over HTTP, HTMX fragment UI, AI-Mode advisory | Authentication, multi-user data, cloud deployment |
| Seeded sample data, CI on every push | Live visa/weather feeds; RAG; multi-agent behaviour |

## Fixed contracts

| Contract | Value |
|---|---|
| Feature folder | `student-5/` |
| Compose services | `student5-frontend`, `student5-backend`, `student5-database` |
| Host ports | frontend `5105`, backend `5205`, database `5305` |
| Container ports | frontend `80`; backend and database `8080` |
| Frontend | nginx + static HTML + HTMX 1.9.12 (pinned, SRI-locked) |
| Backend | Python 3.11, Flask |
| Database | Python 3.11, Flask, SQLite (stdlib `sqlite3`) |
| SQLite file | `/data/logistics.db`, bind-mounted from `student-5/database/storage` |
| Application model | env `APPLICATION_MODEL` (Compose default `llama3.2:3b`) |
| Development implementer / reviewer models | `qwen2.5-coder:7b` / `llama3.2:3b` |
| CI workflow | `.github/workflows/student-5.yml` |
| Design system | Student 2's visual language, reimplemented in `frontend/style.css` |

## Shape of the stack

```text
Browser
  -> student5-frontend  (nginx :5105) - static page, proxies /ui/ and /api/
  -> student5-backend   (Flask :5205) - JSON passthrough, HTMX fragments, advisory
       -> student5-database (Flask + SQLite :5305) - the only SQLite owner
       -> ollama (:11434) -> model tag from APPLICATION_MODEL
```

The rule that shapes the whole design: **no service opens another service's
SQLite file.** The backend has no `sqlite3` import at all; every read and write
travels over HTTP through `backend/db_client.py`.

## The three code boundaries worth knowing

1. **`db_client.py` returns status codes, it does not raise on 4xx.** A 404 is a
   real answer worth forwarding. Only a transport failure raises
   `DatabaseUnavailable`, which becomes `503 {"error": "database service unavailable"}`.
2. **`ollama_client.py` does the opposite.** Every failure - refused connection,
   timeout, non-200, unparseable body - collapses into `OllamaUnavailable`, which
   becomes `503 {"error": "ai service unavailable"}`. There is no partial
   advisory to hand back, and the two 503 bodies differ so an operator can tell
   which dependency broke.
3. **`/ui/` fragments answer 200 even on failure.** HTMX will not swap a non-2xx
   response, so a 404 or 503 there would leave a stale "Loading..." on screen.
   The fragment routes render the problem *as content*; the JSON API keeps the
   honest status codes.

## Where things live

| Path | Contents |
|---|---|
| `database/app.py` | Application factory, generic CRUD handlers, all routes |
| `database/schema.sql`, `seed.sql` | Three tables; 12 / 14 / 14 seeded rows |
| `backend/app.py` | Factory, `relay()`, the `api` JSON passthrough blueprint |
| `backend/db_client.py` | The only code that speaks to the database service |
| `backend/ollama_client.py` | The only code that speaks to Ollama |
| `backend/advisory.py` | Grounding + prompt assembly + both advisory endpoints |
| `backend/ui.py`, `backend/templates/` | Server-rendered HTMX fragments |
| `frontend/index.html`, `style.css`, `nginx.conf` | The page, its CSS, the edge |
| `docs/evidence/` | Agentic-loop artefacts - see `testing-evidence.md` |
| `docs/prompt-library/` | `reviewer-llama32-v2.md`, my custom reviewer prompt |

## Running it

```bash
docker compose up --build student5-frontend student5-backend student5-database
```

Then open `http://localhost:5105/`. The advisory button additionally needs
`ollama` and `ollama-model-setup` running.

## Gotcha before you run the tests

The two pytest suites **must be run separately**. Both services have a module
named `app`, so a single combined invocation collides on import. See
`testing-evidence.md` for the exact commands.
