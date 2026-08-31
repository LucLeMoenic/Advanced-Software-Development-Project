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

Chunks 1, 3, 4, and the implementation portions of Chunks 5 and 6 are complete. The Vue frontend, ASP.NET backend, and ASP.NET/EF Core SQLite database API have production Dockerfiles, health endpoints, focused tests, root Compose wiring, and Student 1 CI build coverage. The database API implements accommodation catalogue CRUD/filtering plus persisted search-history CRUD; the backend validates searches, ranks through one configured Ollama model with deterministic fallback, and persists immutable snapshots.

The componentised traveller frontend provides search, result states, fallback notices, and history reopen/rename/delete through the backend API. Its 7 component tests and production build pass. Live application-model execution, manual 320/768/1280px browser checks, shared navigation, required accommodation records, and real local agentic-loop records remain open evidence work.

## Documentation Order

1. [`docs/context.md`](docs/context.md) - compact architecture and current-state handoff.
2. [`docs/requirements.md`](docs/requirements.md) - normative, testable Release 0 requirements.
3. [`docs/sprint-backlog.md`](docs/sprint-backlog.md) - requirement-linked implementation work, ownership, status, and exit evidence.
4. [`docs/feature-plan.md`](docs/feature-plan.md) - dependency-ordered implementation phases and gates.
5. [`docs/risk-plan.md`](docs/risk-plan.md) - scored risks, triggers, mitigations, and contingencies.
6. [`docs/release-0-full-marks-checklist.md`](docs/release-0-full-marks-checklist.md) - individual/group obligations and evidence index.
7. [`docs/frontend-browser-checklist.md`](docs/frontend-browser-checklist.md) - repeatable manual Chunk 6 browser and viewport validation.
8. [`docs/prompt-log.md`](docs/prompt-log.md) and [`docs/review-record.md`](docs/review-record.md) - AI contribution and review evidence.
9. [`../ai-services/agentic-loop/prompts/`](../ai-services/agentic-loop/prompts/) - authoritative shared implementer and reviewer prompts used by the runtime.

## Release 0 Scope Guard

Complete the local catalogue path first. The database starts empty by human decision, and Mitchell will create the required records manually through the functional application. Live booking/payments, authentication, MCP, RAG, multi-agent servers, and cloud deployment are not Release 0 work.

Phase 0 contracts are confirmed in `docs/context.md` and `docs/sprint-backlog.md`.
