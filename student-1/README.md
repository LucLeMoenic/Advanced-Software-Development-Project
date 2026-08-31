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

Chunk 1 is complete. The Vue frontend, ASP.NET backend, and ASP.NET/EF Core SQLite database API have production Dockerfiles, health endpoints, focused endpoint tests, root Compose wiring, and Student 1 CI coverage. The database API also implements the Chunk 2 accommodation catalogue with migrations, validated CRUD/filtering, and a scoped repository boundary modelled on WiseTech Academy's EF structure. Local frontend and .NET checks pass, Compose configuration validates, and Mitchell reports that all three containers build, start, and report healthy.

Search history, backend orchestration, application-model ranking, the complete traveller interface, shared navigation, and the required manually created catalogue records remain later work. Real local agentic-loop execution records are also still required.

## Documentation Order

1. [`docs/context.md`](docs/context.md) - compact architecture and current-state handoff.
2. [`docs/requirements.md`](docs/requirements.md) - normative, testable Release 0 requirements.
3. [`docs/sprint-backlog.md`](docs/sprint-backlog.md) - requirement-linked implementation work, ownership, status, and exit evidence.
4. [`docs/feature-plan.md`](docs/feature-plan.md) - dependency-ordered implementation phases and gates.
5. [`docs/risk-plan.md`](docs/risk-plan.md) - scored risks, triggers, mitigations, and contingencies.
6. [`docs/release-0-full-marks-checklist.md`](docs/release-0-full-marks-checklist.md) - individual/group obligations and evidence index.
7. [`docs/prompt-log.md`](docs/prompt-log.md) and [`docs/review-record.md`](docs/review-record.md) - AI contribution and review evidence.
8. [`../ai-services/agentic-loop/prompts/`](../ai-services/agentic-loop/prompts/) - authoritative shared implementer and reviewer prompts used by the runtime.

## Release 0 Scope Guard

Complete the local catalogue path first. The database starts empty by human decision, and Mitchell will create the required records manually through the functional application. Live booking/payments, authentication, MCP, RAG, multi-agent servers, and cloud deployment are not Release 0 work.

Phase 0 contracts are confirmed in `docs/context.md` and `docs/sprint-backlog.md`.
