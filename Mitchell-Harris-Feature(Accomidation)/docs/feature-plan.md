# AI Accommodation Recommender Feature Plan

## 1. Goal and Delivery Rule

Deliver a clean Release 0 accommodation recommender in which a traveller submits criteria, receives explainable AI-ranked results from a seeded catalogue, and manages persisted search history.

The implementation is complete only inside the integrated team application. Each phase below must end with working software, automated checks, and captured evidence. Do not start optional or later-release work while a Release 0 exit gate is incomplete.

## 2. Fixed Architecture

```text
Shared home page
        |
        v
Vue 3 + TypeScript frontend container
        |
        v
ASP.NET Core backend/API container ------> Shared Ollama -> one application model
        |
        v
ASP.NET Core database API container
        |
        v
EF Core -> SQLite volume

Development agentic-loop runner
        |                         |
        v                         v
local Ollama implementer model    local Ollama reviewer model
```

Rules:

- Retain Vue 3/TypeScript and ASP.NET Core, which the tutor has confirmed are permitted technology choices.
- The frontend calls only the backend.
- The backend calls only the database API and Ollama.
- Only the database service opens SQLite.
- The application calls exactly one configured accommodation-ranking model.
- The shared .NET agentic-loop service calls two distinct locally hosted Ollama model tags: implementer for Plan/Act and reviewer for Observe.
- The loop is part of the integrated Compose application under `ai-services/agentic-loop`, not a feature-local script.
- Use synchronous HTTP. The stated classroom/demo scale does not justify queues, caches, gateways, service meshes, or extra stores.
- Use the seeded database catalogue in Release 0. Do not add Amadeus or another live provider before the required flow is complete and evidenced.

## 3. Phase Overview

| Phase | Feature slice | Depends on | Exit result |
|---:|---|---|---|
| 0 | Resolve team contracts | None | Ports, routes, model, theme, paths, and ownership are recorded. |
| 1 | Shared two-model loop foundation | 0 | The integrated .NET loop service runs through Compose and produces a finalised record. |
| 2 | Scaffold and health | 1 | All three real feature services build, start, and report health. |
| 3 | Database catalogue | 2 | Seeded accommodation CRUD works through the database API. |
| 4 | Search-history CRUD | 3 | Search records support create/read/rename/delete with snapshots. |
| 5 | Backend API without AI | 4 | End-to-end search and history work with deterministic ranking. |
| 6 | Ollama recommendation | 5 | Valid AI ranking and tested fallback both work. |
| 7 | Traveller frontend | 6 | Search, results, errors, and all history CRUD work in Vue. |
| 8 | Agentic-loop evidence hardening | 7 | Records prove the loop was used across implementation surfaces. |
| 9 | Shared integration | 8 | Feature and shared loop run in the unified Compose application. |
| 10 | CI and quality gates | 9 | Student workflow validates tests and three feature container builds. |
| 11 | Report and showcase | 10 | Every required evidence item is captured and traceable. |

## 4. Detailed Phases

### Phase 0 - Resolve Shared Contracts

**Work**

- Confirm Mitchell's student number and whether this folder will be renamed to the required `student-x/` structure.
- Agree the frontend route, host ports, Compose service names, shared CSS location, and navigation label.
- Agree three configured model roles while minimising unique downloads: one application ranking role plus distinct implementer and reviewer roles. The application role may reuse one of the two installed model tags, but the implementer and reviewer tags must differ.
- Record hardware constraints and select exact approved Ollama tags that run acceptably on the demonstration machine.
- Agree environment-variable names and who owns changes to shared Compose, home page, CSS, and workflow files.
- Create a requirements-to-backlog mapping in the team's sprint backlog.

**Deliverables**

- Updated `context.md` with confirmed values and no stale technology claims.
- Assigned backlog items for FR, NFR, tests, diagrams, integration, and evidence.

**Exit gate**

- No unresolved contract can force service URLs, route paths, model configuration, or folder structure to be rewritten later.

### Phase 1 - Shared Two-Model Loop Foundation

**Team work**

- Maintain the shared .NET service at `ai-services/agentic-loop`.
- Keep the service in the root Compose application with the shared Ollama runtime.
- Configure distinct `IMPLEMENTER_MODEL` and `REVIEWER_MODEL` tags.
- Verify and benchmark both approved models already installed on the demonstration machine. Model installation remains an explicit user/team action and is never performed automatically by the project scripts.
- Keep shared implementer/reviewer prompts versioned under the service.
- Keep model calls bounded, context allow-listed, and source writes/commits/pushes human-controlled.

**Mitchell's work and evidence**

- Contribute accommodation-specific requirements/context to a bounded loop run.
- Run a real pre-test or baseline before the proposed change.
- Record implementer Plan/Act output and reviewer Observe findings.
- Apply, change, or reject the proposal manually.
- Run the post-test and finalise the record with the human decision.

**Tests**

- .NET unit tests for distinct roles, context traversal, secret files, UTF-8 input, and reviewer verdict parsing.
- Docker build and health endpoint.
- Fake/stub model integration in CI; real local Ollama execution for demonstration evidence.

**Exit gate**

- `docker compose up -d ollama agentic-loop` starts the shared services.
- A finalised JSON record identifies two distinct model tags, pre/post evidence, review findings, adaptation, and human decision.
- The loop is available before feature implementation begins and is used throughout later phases.

## Lifecycle Evidence Required in Phases 2-10

For every meaningful AI-assisted code, infrastructure, test, or design change:

1. Run and record the relevant pre-test or baseline.
2. Invoke the shared agentic-loop service with only the required context files.
3. Review the implementer proposal and independent reviewer findings.
4. Apply, modify, or reject the proposal manually.
5. Run and record the post-test.
6. Finalise the JSON record and link it from `prompt-log.md` or `review-record.md`.

Documentation-only wording changes do not require artificial test commands; record the source comparison or consistency check used instead.

### Phase 2 - Replace Placeholders with Runnable Services

**Work**

- Frontend: scaffold Vue 3 with TypeScript strict mode, Vite, a minimal route/page, nginx production serving, and the shared stylesheet.
- Backend: scaffold an ASP.NET Core Web API with nullable reference types, OpenAPI in development, typed configuration validation, and `/health`.
- Database: scaffold a separate ASP.NET Core Web API with EF Core SQLite, migration support, connectivity-aware `/health`, and no database package in the backend project.
- Replace floating base-image tags with team-approved pinned versions.
- Add `.dockerignore` files and run containers as non-root where the selected image supports it without unnecessary complexity.

**Tests**

- Frontend production build and type-check.
- Startup/health tests for both ASP.NET Core services.
- Health endpoint tests.
- Docker build for each service.

**Evidence**

- Terminal output for local service health and three successful image builds.

**Exit gate**

- No placeholder `sleep infinity`, echo-only command, missing entry point, or runtime package installation without a requirements file remains.

### Phase 3 - Accommodation Catalogue and Seed Data

**Work**

- Implement the `Accommodation` schema exactly as defined in `requirements.md`.
- Add parameterised database access, constraints, timestamps, and the candidate filter.
- Implement database API create, list/filter, get, replace, and delete endpoints.
- Add an idempotent seed command with at least 10 realistic records.
- Ensure every submitted database table has at least 10 demo records.

**Tests**

- CRUD success and not-found cases.
- Validation boundaries and malformed JSON.
- Destination, price, capacity, and active filtering.
- Seed idempotency and minimum record count.
- SQL-injection-shaped input remains data and does not alter the schema.

**Evidence**

- Test output and a database API response showing 10 or more records.

**Exit gate**

- Catalogue CRUD and filtering pass through HTTP; no backend or frontend code accesses the SQLite file.

### Phase 4 - Search-History CRUD

**Work**

- Implement the `Search` schema and immutable ranked-result snapshot.
- Implement database API create, list, get, rename, and delete endpoints.
- Order history newest first and validate title length.
- Seed at least 10 representative Search records. Every submitted table must contain at least 10 records.

**Tests**

- Create/read/list/rename/delete happy paths.
- Invalid title, invalid snapshot, missing record, repeated delete, and timestamp behaviour.
- Old snapshots remain readable after catalogue records change or are deleted.

**Evidence**

- API-level CRUD transcript and passing integration tests.

**Exit gate**

- The data service alone owns persistence rules and all user-facing CRUD has a database endpoint.

### Phase 5 - Backend API with Deterministic Ranking

**Work**

- Implement the frontend-facing search and history endpoints.
- Validate and normalise all input at the backend boundary.
- Create explicit request, response, candidate, and ranked-result DTOs; do not pass EF entities or unstructured JSON objects across service boundaries.
- Add database API client timeouts and explicit mapping for validation, not-found, conflict, and dependency errors.
- Implement the FR-09 deterministic ranker first.
- Persist completed searches through the database API.

**Tests**

- Full validation boundary matrix from FR-02.
- Candidate filtering request construction.
- Empty candidate result.
- Database timeout/malformed response.
- Search create and history CRUD through a fake database API.

**Evidence**

- End-to-end HTTP demonstration using the deterministic ranker.

**Exit gate**

- A complete search and CRUD path works before Ollama is introduced, so AI failures cannot hide basic integration defects.

### Phase 6 - Ollama Ranking and Safe Fallback

**Work**

- Add the versioned application ranking prompt at `backend/Prompts/accommodation-ranking-v1.txt`, load it from the backend, and cover its contract with backend tests. Do not place application prompts in the development-loop prompt library.
- Add an Ollama client with the configured model, JSON response mode where supported, and a 12-second timeout.
- Treat criteria and candidate text as untrusted prompt data.
- Validate JSON, exact ID membership, unique contiguous ranks, and reason length.
- On timeout, connection failure, or invalid output, use the deterministic ranker and return a visible fallback notice.
- Never invent accommodation fields from model output.

**Tests**

- Valid response.
- Markdown-wrapped or malformed JSON.
- Unknown, omitted, duplicated, and extra candidate IDs.
- Duplicate, missing, negative, and out-of-range ranks.
- Oversized/missing reasons.
- Timeout and connection error.
- Prompt-injection text inside preferences or accommodation descriptions.

**Evidence**

- One successful local Ollama ranking and one forced fallback, with secrets and full preferences absent from logs.

**Exit gate**

- AI improves ordering when healthy but cannot make the feature unavailable or corrupt persisted history.

### Phase 7 - Vue Traveller Experience

**Work**

- Build typed Vue components for the labelled search form, loading state, validation summary, empty state, results, fallback notice, and history panel.
- Add history reopen, rename, delete confirmation, and post-action focus management.
- Render untrusted values through Vue text interpolation; do not use `v-html` for user or model content.
- Reuse the shared CSS theme and add only feature-specific layout rules that the shared theme does not provide.
- Make the page keyboard-operable and responsive at 320px, 768px, and 1280px.

**Tests**

- Submit valid and invalid searches.
- Loading controls prevent duplicate submission.
- Render AI and fallback results.
- Reopen without reranking.
- Rename and delete.
- Keyboard navigation, focus, live status announcements, image alt behaviour, and target viewport widths.

**Evidence**

- Screenshots or short recordings covering each visible state and CRUD action.

**Exit gate**

- The complete feature can be demonstrated through the browser without direct API tooling.

### Phase 8 - Agentic-Loop Evidence Hardening

**Work**

- Audit the finalised records produced during Phases 2-7.
- Ensure records cover database/data design, backend implementation, frontend implementation, model integration, Docker/Compose, and requirement traceability.
- Confirm each record contains actual pre/post evidence rather than model claims.
- Run one end-to-end demonstration in which the reviewer requests a correction and the implementer produces one bounded revision.
- Verify the shared service is still part of the integrated Compose application and uses the selected distinct local model tags.

**Tests**

- Re-run the shared .NET unit tests and Docker build.
- Exercise unavailable-model, equal-model, malformed-review, and Ollama-timeout paths.
- Confirm pending records cannot be presented as final evidence.

**Evidence**

- Finalised records from multiple implementation phases.
- Terminal capture showing both exact local model tags, reviewer-requested correction, adaptation, human decision, and post-test.

**Exit gate**

- The assessor can prove that the integrated loop was used throughout development, not added at the end for demonstration.

### Phase 9 - Shared Repository and Compose Integration

**Work**

- Add the three services to the single root `docker-compose.yml`.
- Use service DNS names, environment variables, health checks, dependency health conditions where supported, and a named SQLite volume.
- Connect the backend and shared agentic-loop service to the team's single Ollama runtime; multiple model tags do not require multiple Ollama containers.
- Add the feature to `shared/index.html` and apply the shared theme.
- Update root setup instructions with exact prerequisites, all required model pulls, build, start, health, loop, test, and stop commands.

**Tests**

- Build and start from a clean checkout/configuration.
- Check all health endpoints and open the feature through the shared entry page.
- Run AI success, forced fallback, history reopen, rename, and delete.
- Stop/start the stack and confirm persisted history survives.

**Evidence**

- Compose service/health output, unified home-page screenshot, full-flow screenshots, and architecture diagram.

**Exit gate**

- The integrated feature works from the shared entry point. Standalone success does not satisfy this gate.

### Phase 10 - Student 1 CI and Quality Gates

**Work**

- Restrict path triggers to this feature and any shared files that can break it.
- Restore npm and NuGet dependencies from committed manifests/lock metadata.
- Run frontend type-check/build/tests and backend/database .NET tests with deterministic fakes.
- Run the agentic-loop runner's non-model unit/integration tests.
- Build all three Docker images.
- Do not require live Ollama, external credentials, or mutable third-party accommodation data.
- Remove every echo-only placeholder step.

**Evidence**

- Successful PR workflow URL/screenshot and a deliberate failing-run example or local equivalent proving failures block the job.

**Exit gate**

- The workflow fails for a broken test or image and succeeds for the reviewed feature.

### Phase 11 - Report and Showcase Package

**Work**

- Produce individual service, integrated architecture, Compose, DevOps, data-model, application-LLM flow, and two-model Plan -> Act -> Observe -> Adapt diagrams.
- Prepare conceptual, ERD, logical, and physical data designs.
- Capture local tests, Compose, GitHub Actions, screenshots, AI success/fallback, prompt assets, review record, commit log, contribution log, known issues, and attendance checkpoints.
- Rehearse Mitchell's section of the group video: enter from the unified page, create a search, explain AI output, reopen, rename, delete, show agentic logs, and show CI evidence.
- Confirm the published video is at most 10 minutes, includes every team member, and its URL is in the report.

**Exit gate**

- Every row in `release-0-full-marks-checklist.md` has an evidence location, not merely a tick.

## 5. Implementation Order Within Each Phase

Use the same small loop for each slice:

1. Select requirement IDs and write acceptance tests/checklist.
2. Implement the smallest vertical behaviour.
3. Run targeted validation.
4. Review against security, failure, accessibility, and boundary requirements.
5. Update prompt/review records when AI materially contributed.
6. Commit one coherent change with a meaningful message.
7. Integrate before starting the next dependency.

## 6. Change Control

A proposed addition enters Release 0 only if it traces to a requirement or marking criterion. Record the requirement ID in the pull request. If it does not trace, defer it.

Changes to public endpoints, table fields, service names, ports, model/tag, shared routes, or shared CSS are integration-contract changes and require team agreement before implementation.

## 7. Known Decisions and Open Contracts

### Decisions

- Local seeded catalogue instead of Amadeus for Release 0.
- Synchronous HTTP only.
- Two simple SQLite tables: accommodation catalogue and search history with result snapshots.
- Deterministic ranking fallback.
- User-facing CRUD is demonstrated through search history.
- One shared Ollama runtime can host all configured models.
- The application uses one ranking model; the development loop uses distinct implementer and reviewer model tags.

### Shared Team Ownership

- `ai-services/agentic-loop`, shared Ollama configuration, shared Compose wiring, and the common execution/record format are team infrastructure.
- Mitchell contributes accommodation-specific prompts/context, reviewed changes, finalised records, and report evidence.
- Mitchell's personal feature documentation must not claim sole ownership of the shared team loop.

### Must Be Confirmed in Phase 0

- Mitchell's assigned `student-x` number and final standard folder path.
- Compose service names and host ports.
- Unified home-page route and navigation label.
- Shared stylesheet contract.
- Exact application, implementer, and reviewer model tags; implementer and reviewer must differ.
- Whether the team requires one or both of Llama and Qwen for the demonstration.
- A durable evidence location for the tutor's approval of Vue and ASP.NET Core.
