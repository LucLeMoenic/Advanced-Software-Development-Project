# AI Accommodation Recommender

Mitchell Harris's Release 0 feature for the integrated Agentic AI application.

## Intended User Flow

A traveller enters destination, dates, guest count, nightly budget, and preferences. The backend retrieves eligible records through the database API; for an uncached destination it can first import validated LiteAPI sandbox rates through that API. It then asks one configured Ollama model to rank candidates, validates the output, persists a search snapshot, and returns explainable results. The traveller can reopen, rename, and delete history.

## Architecture

```text
Vue 3 + TypeScript frontend
  -> ASP.NET Core backend/API
       -> ASP.NET Core database API -> EF Core -> SQLite
       -> LiteAPI sandbox -> validated catalogue imports
       -> shared Ollama -> one application ranking model
```

Only the database service may open SQLite. The frontend may call only the backend. One Ollama runtime can host the required model tags.

## Current Status

Chunks 1, 3, 4, and the implementation portions of Chunks 5 and 6 are complete. The Vue frontend, ASP.NET backend, and ASP.NET/EF Core SQLite database API have production Dockerfiles, health endpoints, focused tests, and root Compose wiring. The database API implements accommodation catalogue CRUD/filtering plus persisted search-history CRUD; the backend validates searches, ranks through one configured Ollama model with deterministic fallback, and persists immutable snapshots.

The componentised traveller frontend provides search, result states, provider-import and fallback notices, and history reopen/rename/delete through the backend API. The backend imports an uncached destination from LiteAPI, validates the live v3 rates response, stores accommodations only through the database API, re-queries eligible candidates, ranks them with Ollama, and persists the result. Its backend and frontend tests and production build pass. The tracked SQLite database contains 10 synthetic trips across Tokyo, Paris, New York, Rome, Barcelona, Singapore, Vancouver, Cape Town, Reykjavik, and Dubai, with exactly five eligible accommodations and five tailored ranking reasons per trip. These snapshots demonstrate the interface but do not replace live Ollama evidence. The unified page opens the feature at `/accommodation/`; manual 320/768/1280px browser checks remain open evidence work.

## Documentation Order

1. [`docs/context.md`](docs/context.md) - compact architecture and current-state handoff.
2. [`docs/architecture.md`](docs/architecture.md) - current HLD for the accommodation feature and shared Ollama topology.
3. [`docs/requirements.md`](docs/requirements.md) - normative, testable Release 0 requirements.
4. [`docs/sprint-backlog.md`](docs/sprint-backlog.md) - requirement-linked implementation work, ownership, status, and exit evidence.
5. [`docs/feature-plan.md`](docs/feature-plan.md) - dependency-ordered implementation phases and gates.
6. [`docs/risk-plan.md`](docs/risk-plan.md) - scored risks, triggers, mitigations, and contingencies.
7. [`docs/release-0-full-marks-checklist.md`](docs/release-0-full-marks-checklist.md) - individual/group obligations and evidence index.
8. [`docs/frontend-browser-checklist.md`](docs/frontend-browser-checklist.md) - repeatable manual Chunk 6 browser and viewport validation.
9. [`docs/prompt-log.md`](docs/prompt-log.md) and [`docs/review-record.md`](docs/review-record.md) - AI contribution and review evidence.

## Release 0 Scope Guard

LiteAPI imports are demonstration catalogue data, not guaranteed live quotes. Live booking/payments, authentication, production provider availability, MCP, RAG, multi-agent servers, and cloud deployment are not Release 0 work.

Phase 0 contracts are confirmed in `docs/context.md` and `docs/sprint-backlog.md`.
