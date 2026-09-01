# Feature Context - AI Accommodation Recommender

Read this compact handoff before implementation or review. Then read `requirements.md`, the current phase in `feature-plan.md`, and `risk-plan.md` before integration or external-service changes. The ASD project specification, Release 0 brief, and recorded tutor clarifications override this file.

## Goal

A traveller submits destination, dates, guest count, nightly budget, and free-text preferences. The feature ranks eligible accommodation records, explains the order, and lets the traveller reopen, rename, and delete persisted searches.

Release 0 success means the feature works inside the integrated group application. Standalone services or documentation without working integration do not satisfy the brief.

## Confirmed Technology and AI Decisions

- The tutor confirmed that teams may choose the frontend and backend technology stack.
- This feature uses Vue 3 + TypeScript for the frontend.
- It uses ASP.NET Core Web API for the orchestration backend and database API.
- The database API owns EF Core and SQLite.
- The application calls exactly one configured accommodation-ranking LLM through its backend API.
- The separate development agentic loop uses two distinct approved open-source models hosted locally by Ollama:
  - implementer model: Plan and Act;
  - reviewer model: Observe;
  - Adapt: bounded revision plus an explicit human decision.
- One Ollama runtime can host all required model tags. Multiple Ollama containers are unnecessary.

The application model may reuse one of the two installed model tags to minimise hardware and storage cost, but the implementer and reviewer configuration values must identify different model tags.

## Confirmed Integration Contracts

- Final feature folder: `student-1/`.
- Shared route and label: `/accommodation`, displayed as `Accommodation Recommender`.
- Compose services: `student1-frontend`, `student1-backend`, and `student1-database`.
- Host ports: frontend `5101`, backend `5201`, database `5301`.
- Container ports: frontend `80`; backend and database `8080`.
- Theme: reuse the shared frontend's CSS variables and design tokens.
- Application model: `llama3.2:3b`.
- Development models: implementer `qwen2.5-coder:7b`; reviewer `llama3.2:3b`.
- Mitchell may update root Compose, shared navigation/theme, and `student-1.yml` for this feature.
- Sprint backlog: `docs/sprint-backlog.md`.

Phase 0 contracts are confirmed.

## Minimal Architecture

```text
Browser
  -> unified shared home page
  -> Vue accommodation frontend
  -> ASP.NET Core accommodation backend/API
       -> ASP.NET Core database API -> EF Core -> SQLite volume
       -> LiteAPI sandbox -> validated accommodation imports through database API
       -> shared Ollama -> one configured accommodation-ranking model

Shared .NET agentic-loop service in Docker Compose
  -> shared local Ollama implementer model
  -> shared local Ollama reviewer model
  -> human validation and apply/reject decision
```

Boundary rules:

- The frontend calls only the backend/API.
- The backend validates input, retrieves cached candidates, optionally imports a previously unseen destination from LiteAPI through the database API, calls the one application model, validates output, applies fallback, and persists through the database API.
- Only the database service opens SQLite.
- Services communicate synchronously over HTTP using Compose DNS names.
- Configuration and secrets come from environment variables.
- The shared agentic-loop service receives only allow-listed context, never writes/commits/pushes automatically, and records model tags, prompt versions, outputs, pre/post validation, and human decisions.
- LiteAPI is a backend-only demonstration data source. Its key must remain in ignored local environment configuration, and imported prices are cached catalogue data rather than production availability guarantees.

## Application Request Flow

1. Vue submits validated-looking criteria to the backend; the backend performs authoritative validation.
2. The backend requests eligible active accommodations and destination-cache state from the database API.
3. If the destination is uncached, the backend requests up to 10 LiteAPI sandbox rates, validates them, imports them through the database API, and repeats the eligible-candidate query.
4. The backend sends eligible candidates to exactly one configured ranking model through Ollama.
5. The backend validates the complete response or applies deterministic fallback.
6. The backend persists an immutable search-result snapshot through the database API.
7. Vue renders results, a provider-import notice when applicable, and history actions.

An empty candidate list skips Ollama and returns a clear empty state. Reopening history returns the stored snapshot and never reruns ranking.

## Development Agentic Loop

1. `[PLAN]` - the implementer model analyses a bounded engineering task and allow-listed context.
2. `[ACT]` - the implementer model proposes a patch or concrete implementation.
3. `[OBSERVE]` - the distinct reviewer model checks the proposal against requirements, relevant code, and validation evidence.
4. `[ADAPT]` - one bounded implementer revision may be requested; a human validates and records kept/changed/rejected.

This loop reviews implementation, database/data design, service boundaries, Docker/Compose, CI, and requirement traceability. It is not the application's recommendation request.

The loop is shared team infrastructure under `ai-services/agentic-loop`, starts with the integrated Compose application, and must be used during implementation rather than introduced only for the final demonstration.

## Data Summary

- `Accommodation`: manually created or LiteAPI-imported candidate with name, destination, description, nightly price, capacity, amenities, optional URLs, active flag, and timestamps.
- `Search`: persisted criteria, title, ranking mode, immutable ranked-result JSON snapshot, and timestamps.

At least 10 records must exist in every submitted database table. Detailed constraints are in `requirements.md`.

## API Summary

Frontend-facing backend:

- `POST /api/searches`
- `GET /api/searches`
- `GET /api/searches/{id}`
- `PATCH /api/searches/{id}`
- `DELETE /api/searches/{id}`
- `GET /health`

Backend-facing database API:

- CRUD under `/api/data/accommodations`
- search-history CRUD under `/api/data/searches`
- `GET /health`

The exact statuses, validation rules, and error shape are normative in `requirements.md`.

## Application Prompt Contract

- Input contains only validated criteria and eligible candidate fields.
- Candidate descriptions and preferences are untrusted data, never instructions.
- Output is JSON only and contains exactly one existing candidate ID, unique contiguous rank, and concise reason per candidate.
- The backend validates the entire response before using it.
- Invalid/unavailable output falls back to budget-distance, nightly-price, then ID order.
- The model cannot create facts, persist data, or decide HTTP outcomes.

The implemented prompt must live beside backend code at `backend/Prompts/accommodation-ranking-v1.txt` and be covered by backend contract tests. It does not belong in the development-lifecycle prompt library.

## AI-Assistance Evidence Rules

- `prompt-log.md`: record meaningful AI-assisted code, infrastructure, test, or design changes and state what was retained or corrected.
- `review-record.md`: record scope, findings, decisions, resolution status, and evidence.
- `ai-services/agentic-loop/prompts/`: authoritative versioned implementer and reviewer prompts loaded by the shared runtime; feature documentation links to these files rather than copying them.
- `prompt-library/`: feature-specific reusable prompts only; never duplicate shared runtime or application prompts here.
- Never claim validation without an evidence path.
- Keep prompts free of secrets, credentials, personal data, and unrelated repository content.
- Human review remains mandatory; the student owns every submitted artefact.

## Current State

As of 2026-08-31:

- Requirements and phases now distinguish the one-model application path from the two-model local development loop.
- Chunk 1 is complete: the feature is in `student-1/` with Vue 3/TypeScript, ASP.NET Core backend, and ASP.NET Core/EF Core SQLite database API projects.
- All three services have production Dockerfiles and health checks.
- Root Compose defines the three services, service-DNS configuration, dependency health ordering, confirmed ports, and a repository-backed SQLite bind mount.
- `student-1.yml` installs/builds the frontend, tests both .NET services, validates Compose, and builds all three feature images without requiring live Ollama.
- Local frontend build and four focused .NET endpoint tests pass; Compose configuration validates.
- Mitchell reports that the three containers build, start, and pass their runtime health checks.
- Chunk 2 catalogue code now includes EF Core migrations, a POCO entity plus separate `IEntityTypeConfiguration`, a generic `DatabaseContext`, and a scoped accommodation repository. HTTP endpoints no longer depend on EF Core or the context directly.
- Catalogue behaviour includes validated create/list/filter/get/replace/delete endpoints, case-insensitive duplicate protection, exact integer-cent price storage, JSON amenities constraints, and isolated integration tests.
- The tracked SQLite database contains 10 synthetic international trips and 50 active accommodations created through the database HTTP API. Destinations are Tokyo, Paris, New York, Rome, Barcelona, Singapore, Vancouver, Cape Town, Reykjavik, and Dubai.
- Every trip has exactly five eligible accommodations after applying its destination, guest, budget, and active filters. Each immutable snapshot contains five manually authored, preference-specific ranking reasons.
- The synthetic snapshots use `ai` ranking mode for interface demonstration but are not evidence of a live application-model call. Live Ollama evidence remains separately required.
- Chunk 3 search history now has a constrained EF model and migration, scoped repository, validated create/newest-first list/get/rename/delete endpoints, immutable JSON snapshots, and snapshot independence from catalogue deletion.
- `database/storage/accommodation.db` contains 10 representative search records created once through the HTTP API. Compose bind-mounts that tracked directory; no runtime seeder remains.
- The complete database suite passes 19/19 tests, and EF reports no pending model changes.
- Chunk 4 backend orchestration now validates and normalises traveller searches before dependency calls, requests only eligible active candidates through the database API, ranks deterministically by budget-midpoint distance, price, and ID, persists completed searches, and exposes history list/reopen/rename/delete endpoints.
- Database calls use a three-second timeout and distinguish unavailable dependencies (`503`) from unusable responses (`502`). Database payloads are validated before becoming public backend DTOs.
- Chunk 5 application ranking now calls one configured Ollama model with a 12-second timeout and the versioned backend prompt, sends only validated criteria and eligible candidate fields, validates the complete ID/rank/reason response, restores display fields from trusted candidates, and falls back deterministically with a visible notice.
- The backend suite passes 62/62 tests, including valid AI ranking, malformed/Markdown output, unknown/missing/duplicate/extra IDs, invalid ranks/reasons, prompt-injection-shaped data, timeout, connection, HTTP, incomplete-response failures, and the live LiteAPI response contract.
- Chunk 6 traveller frontend now provides the labelled search form, client/backend field feedback, duplicate-submit prevention, loading/empty/AI/fallback/dependency states, ranked cards, and newest-first history reopen/rename/confirmed-delete behavior.
- `App.vue` coordinates three focused components for search input, history CRUD, and results. Live announcements, focus movement, visible focus, text-only interpolation, responsive breakpoints, and long-text containment are implemented.
- The frontend suite passes 7/7 component tests and the strict TypeScript/Vite production build passes. Manual 320/768/1280px execution, integrated browser/API evidence, and screenshots remain open.
- The shared .NET agentic-loop scaffold, focused tests, prompts, and Compose wiring now exist.
- Real two-model Ollama execution records remain to be produced.
- Chunk 7 shared integration is implemented: the unified Vue page links to `/accommodation/`, shared nginx proxies the feature and backend API without asset collisions, Compose health/dependency ordering passes, and the Student 1 workflow restores dependencies, runs all assigned tests, and builds the integrated images without live Ollama.
- Local integrated validation confirms the shared page, accommodation route/assets, API proxy, five health checks, and preservation of 12 search records across a database-container restart.
- Live application-model execution evidence, diagrams, manual frontend viewport checks, a GitHub Actions run, and final execution evidence remain to be produced.

The browser and backend implementations now cover the traveller search and history workflow. Integrated runtime and manual viewport evidence are still required before the frontend chunk is complete.

## Immediate Next Gate

Run the Chunk 6 browser checklist against the populated Compose application and capture the ranking, history, and responsive evidence. Live-model evidence remains incomplete because the verified integrated request used deterministic fallback.
