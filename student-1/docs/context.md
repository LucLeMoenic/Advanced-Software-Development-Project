# Feature Context - AI Accommodation Recommender

Read this compact handoff before implementation or review. Then read `requirements.md`, the current phase in `feature-plan.md`, and `risk-plan.md` before integration or external-service changes. The ASD project specification, Release 0 brief, and recorded tutor clarifications override this file.

## Goal

A traveller submits destination, dates, guest count, and nightly budget. The feature ranks eligible accommodation records, optionally accepts free-text preferences for AI-selected ranking, explains the order, and lets the traveller reopen, rename, and delete persisted searches.

Release 0 success means the feature works inside the integrated group application. Standalone services or documentation without working integration do not satisfy the brief.

## Confirmed Technology and AI Decisions

- The tutor confirmed that teams may choose the frontend and backend technology stack.
- This feature uses Vue 3 + TypeScript for the frontend.
- It uses ASP.NET Core Web API for the orchestration backend and database API.
- The database API owns EF Core and SQLite.
- Programmatic ranking is the application default. The traveller may opt in per search to one configured accommodation-ranking LLM through the backend API.
- One shared Ollama runtime hosts the model tags required by team microservices. Consumers select a model tag but do not own an Ollama runtime.

## Confirmed Integration Contracts

- Final feature folder: `student-1/`.
- Shared route and label: `/accommodation`, displayed as `Accommodation Recommender`.
- Compose services: `student1-frontend`, `student1-backend`, and `student1-database`.
- Host ports: frontend `5101`, backend `5201`, database `5301`.
- Container ports: frontend `80`; backend and database `8080`.
- Theme: reuse the shared frontend's CSS variables and design tokens.
- Application model: `llama3.2:3b`.
- Mitchell may update root Compose and shared navigation/theme for this feature.
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

```

Boundary rules:

- The frontend calls only the backend/API.
- The backend validates input, retrieves cached candidates, optionally imports a previously unseen destination from LiteAPI through the database API, ranks deterministically, calls the one application model only when requested, validates AI output, applies fallback after AI failure, and persists through the database API.
- Only the database service opens SQLite.
- Services communicate synchronously over HTTP using Compose DNS names.
- Configuration and secrets come from environment variables.
- LiteAPI is a backend-only demonstration data source. Its key must remain in ignored local environment configuration, and imported prices are cached catalogue data rather than production availability guarantees.

## Application Request Flow

1. Vue submits validated-looking criteria to the backend; the backend performs authoritative validation.
2. The backend requests eligible active accommodations and destination-cache state from the database API.
3. If the destination is uncached, the backend requests up to 10 LiteAPI sandbox rates, validates them, imports them through the database API, and repeats the eligible-candidate query.
4. The backend uses deterministic programmatic ranking unless the traveller explicitly selected AI ranking.
5. For opted-in searches, the backend sends eligible candidates to exactly one configured ranking model through Ollama, then validates the complete response or applies deterministic fallback.
6. The backend persists an immutable search-result snapshot through the database API.
7. Vue renders results, a provider-import notice when applicable, and history actions.

An empty candidate list skips Ollama and returns a clear empty state. Reopening history returns the stored snapshot and never reruns ranking.

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
- Never claim validation without an evidence path.
- Keep prompts free of secrets, credentials, personal data, and unrelated repository content.
- Human review remains mandatory; the student owns every submitted artefact.

## Current State

As of 2026-08-31:

- Requirements and phases now distinguish the one-model application path from the two-model local development loop.
- Chunk 1 is complete: the feature is in `student-1/` with Vue 3/TypeScript, ASP.NET Core backend, and ASP.NET Core/EF Core SQLite database API projects.
- All three services have production Dockerfiles and health checks.
- Root Compose defines the three services, service-DNS configuration, dependency health ordering, confirmed ports, and a repository-backed SQLite bind mount.
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
- Chunk 5 application ranking now defaults to deterministic `programmatic` ranking and calls one configured Ollama model only after explicit traveller opt-in. The model path retains its 12-second timeout, versioned backend prompt, complete ID/rank/reason validation, trusted display-field restoration, and deterministic fallback with a visible notice.
- The backend suite passes 67/67 tests, including programmatic Ollama bypass and database-response mapping, valid AI ranking, malformed/Markdown output, unknown/missing/duplicate/extra IDs, invalid ranks/reasons, sentence-format and word-count constraints, prompt-injection-shaped data, timeout, connection, HTTP, incomplete-response failures, and the live LiteAPI response contract.
- Chunk 6 traveller frontend now provides the labelled search form with unchecked AI opt-in and an AI-only preferences field, client/backend field feedback, duplicate-submit prevention, loading/empty/programmatic/AI/fallback/dependency states, ranked cards, and newest-first history reopen/rename/confirmed-delete behavior.
- `App.vue` coordinates three focused components for search input, history CRUD, and results. Live announcements, focus movement, visible focus, text-only interpolation, responsive breakpoints, and long-text containment are implemented.
- The frontend suite passes 8/8 component tests and the strict TypeScript/Vite production build passes. Manual 320/768/1280px execution and browser screenshots remain open.
- Chunk 7 shared integration is implemented: the unified Vue page links to `/accommodation/`, shared nginx proxies the feature and backend API without asset collisions, and Compose health/dependency ordering passes.
- The unified entry page now uses the same blue/neutral tokens, typography, bordered panels, rounded feature cards, visible focus treatment, and responsive behavior as the accommodation interface.
- Local integrated validation confirms the shared page, accommodation route/assets, API proxy, five health checks, and preservation of 12 search records across a database-container restart.
- Live application-model execution is now confirmed: after removing the local WSL CPU cap, replacing generic Ollama JSON mode with an exact ranking-array schema, and compacting the unchanged allow-listed ranking input, cold Sydney and Tokyo searches returned five `ai`-ranked results through the frontend proxy within the 12-second model timeout. Ranking reasons now use distinct 8-18 word sentences that explain why supplied accommodation facts benefit the traveller rather than merely restating an amenity.
- Opt-in runtime behavior is confirmed through the rebuilt frontend proxy: an unchecked-equivalent Sydney request returned six `programmatic` results with no notice, while the same request with `useAi: true` returned six `ai` results with sentence-form reasons and no fallback notice.
- On compatible Windows/NVIDIA machines, `scripts/start-student1.ps1` automatically includes `docker-compose.gpu.yml`; the current RTX 2000 Ada runtime offloads all model layers and reduced the previously failing Sydney search to 2.5 seconds. The main Compose file remains CPU-compatible.
- Root Compose now has one long-running `ollama` service and one short-lived shared `ollama-model-setup` job. The setup job installs missing shared tags and preloads `APPLICATION_MODEL` for 30 minutes so the backend's 12-second request timeout is not consumed by a cold model load. Student 1 uses `http://ollama:11434`; future team AI consumers use the same service and add required tags to `OLLAMA_MODELS`.
- Diagrams and manual frontend viewport checks remain to be produced.

The browser and backend implementations now cover the traveller search and history workflow. Integrated runtime and manual viewport evidence are still required before the frontend chunk is complete.

## Immediate Next Gate

Run the Chunk 6 browser checklist against the populated Compose application and capture ranking, history, and responsive screenshots. Preserve one forced-fallback example alongside the confirmed live AI success.
