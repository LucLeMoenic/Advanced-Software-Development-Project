# AI Accommodation Recommender

Mitchell Harris's Release 0 feature for the integrated Agentic AI application.

## Intended User Flow

A traveller enters destination, dates, guest count, nightly budget, and preferences. The backend retrieves eligible records through the database API, asks one configured Ollama model to rank them, validates the output, persists a search snapshot, and returns explainable results. The traveller can reopen, rename, and delete history.

## Architecture

```text
Vue 3 + TypeScript frontend
  -> ASP.NET Core backend/API
       -> ASP.NET Core database API -> EF Core -> SQLite
       -> shared Ollama -> one application ranking model

Terminal development loop
  -> local Ollama implementer model (Plan/Act)
  -> different local Ollama reviewer model (Observe)
  -> human-controlled Adapt decision
```

Only the database service may open SQLite. The frontend may call only the backend. One Ollama runtime can host the required model tags.

## Current Status

Planning and AI-assistance documentation are established. A shared .NET two-model agentic-loop service, focused tests, prompts, and root Compose wiring now exist. Real local model execution records are still required.

The three accommodation feature Dockerfiles remain templates/placeholders, and no runnable accommodation application or real feature CI validation exists yet.

Do not use the current containers as implementation evidence:

- `backend/Dockerfile` is a Flask template that conflicts with the selected ASP.NET Core design and expects a missing `app.py`.
- `database/Dockerfile` only sleeps and does not expose a database API.
- `frontend/Dockerfile` has no Vue build stage or implemented application.
- Root `docker-compose.yml`, shared navigation, and `student-1.yml` still target repository templates.

## Documentation Order

1. [`docs/context.md`](docs/context.md) - compact architecture and current-state handoff.
2. [`docs/requirements.md`](docs/requirements.md) - normative, testable Release 0 requirements.
3. [`docs/feature-plan.md`](docs/feature-plan.md) - dependency-ordered implementation phases and gates.
4. [`docs/risk-plan.md`](docs/risk-plan.md) - scored risks, triggers, mitigations, and contingencies.
5. [`docs/release-0-full-marks-checklist.md`](docs/release-0-full-marks-checklist.md) - individual/group obligations and evidence index.
6. [`docs/prompt-log.md`](docs/prompt-log.md) and [`docs/review-record.md`](docs/review-record.md) - AI contribution and review evidence.
7. [`docs/prompt-library/`](docs/prompt-library/) - reusable development-loop prompts only. Application prompts belong in backend source.

## Release 0 Scope Guard

Complete the seeded local catalogue path first. Live booking/payments, authentication, MCP, RAG, multi-agent servers, and cloud deployment are not Release 0 work.

Implementation must not begin until Phase 0 contracts in `docs/feature-plan.md` are confirmed with the team.
