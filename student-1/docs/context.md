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
       -> shared Ollama -> one configured accommodation-ranking model

Shared .NET agentic-loop service in Docker Compose
  -> shared local Ollama implementer model
  -> shared local Ollama reviewer model
  -> human validation and apply/reject decision
```

Boundary rules:

- The frontend calls only the backend/API.
- The backend validates input, retrieves candidates, calls the one application model, validates output, applies fallback, and persists through the database API.
- Only the database service opens SQLite.
- Services communicate synchronously over HTTP using Compose DNS names.
- Configuration and secrets come from environment variables.
- The shared agentic-loop service receives only allow-listed context, never writes/commits/pushes automatically, and records model tags, prompt versions, outputs, pre/post validation, and human decisions.
- A live hotel provider is not required to prove Release 0. Complete the seeded catalogue path before considering Amadeus.

## Application Request Flow

1. Vue submits validated-looking criteria to the backend; the backend performs authoritative validation.
2. The backend requests eligible active accommodations from the database API.
3. The backend sends those candidates to exactly one configured ranking model through Ollama.
4. The backend validates the complete response or applies deterministic fallback.
5. The backend persists an immutable search-result snapshot through the database API.
6. Vue renders results and history actions.

An empty candidate list skips Ollama and returns a clear empty state. Reopening history returns the stored snapshot and never reruns ranking.

## Development Agentic Loop

1. `[PLAN]` - the implementer model analyses a bounded engineering task and allow-listed context.
2. `[ACT]` - the implementer model proposes a patch or concrete implementation.
3. `[OBSERVE]` - the distinct reviewer model checks the proposal against requirements, relevant code, and validation evidence.
4. `[ADAPT]` - one bounded implementer revision may be requested; a human validates and records kept/changed/rejected.

This loop reviews implementation, database/data design, service boundaries, Docker/Compose, CI, and requirement traceability. It is not the application's recommendation request.

The loop is shared team infrastructure under `ai-services/agentic-loop`, starts with the integrated Compose application, and must be used during implementation rather than introduced only for the final demonstration.

## Data Summary

- `Accommodation`: seeded candidate with name, destination, description, nightly price, capacity, amenities, optional URLs, active flag, and timestamps.
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
- Root Compose defines the three services, service-DNS configuration, dependency health ordering, confirmed ports, and a named SQLite volume.
- `student-1.yml` installs/builds the frontend, tests both .NET services, validates Compose, and builds all three feature images without requiring live Ollama.
- Local frontend build and four focused .NET endpoint tests pass; Compose configuration validates.
- Mitchell reports that the three containers build, start, and pass their runtime health checks.
- Chunk 2 catalogue code now includes an EF Core migration, POCO entity plus separate `IEntityTypeConfiguration`, validated create/list/filter/get/replace/delete endpoints, case-insensitive duplicate protection, exact integer-cent price storage, JSON amenities constraints, and isolated integration tests.
- The database container starts healthy with an empty catalogue, and temporary runtime CRUD validation leaves the catalogue empty.
- Automatic seed data is intentionally excluded by Mitchell's decision. FR-16 and the required minimum 10-record evidence remain open until Mitchell creates the records manually through the functional application.
- The shared .NET agentic-loop scaffold, focused tests, prompts, and Compose wiring now exist.
- Real two-model Ollama execution records remain to be produced.
- Manual catalogue data, search history, backend orchestration, application-model ranking, the complete traveller interface, shared navigation, diagrams, and final execution evidence remain to be implemented.

The current services prove the Chunk 1 boundaries and runtime health only; they do not yet implement accommodation search or recommendation behaviour.

## Immediate Next Gate

Create the manual catalogue records after the application entry flow exists; continue with Chunk 3 while tracking FR-16 as incomplete.
