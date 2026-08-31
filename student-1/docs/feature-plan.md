# AI Accommodation Recommender Feature Plan

## Goal

Build an integrated accommodation recommender where a traveller:

1. submits destination, dates, guests, budget, and preferences;
2. receives explainable accommodation rankings from one backend-controlled Ollama model;
3. still receives deterministic results when Ollama fails;
4. can reopen, rename, and delete saved searches.

The feature is complete only when its Vue frontend, ASP.NET backend, ASP.NET database API, SQLite data, Ollama integration, shared navigation, Docker Compose configuration, and Student 1 CI work together.

Detailed contracts are in `requirements.md`. Work status and requirement mapping are in `sprint-backlog.md`.

## Fixed Implementation Contracts

| Contract | Value |
|---|---|
| Final folder | `student-1/` |
| Shared route | `/accommodation` |
| Navigation label | `Accommodation Recommender` |
| Frontend service / host port | `student1-frontend` / `5101` |
| Backend service / host port | `student1-backend` / `5201` |
| Database service / host port | `student1-database` / `5301` |
| Internal ports | Frontend `80`; backend and database `8080` |
| Frontend | Vue 3, TypeScript, Vite |
| Backend | ASP.NET Core Web API |
| Database API | ASP.NET Core, EF Core, SQLite |
| Application model | `llama3.2:3b` |
| Development implementer model | `qwen2.5-coder:7b` |
| Development reviewer model | `llama3.2:3b` |
| Theme | Shared CSS variables and design tokens |

Boundary rules:

- The frontend calls only the backend.
- The backend calls the database API and Ollama.
- Only the database API opens SQLite.
- The application uses one ranking model per request.
- History stores an immutable ranked-result snapshot.
- All services use Compose DNS names internally.
- Secrets and environment-specific values come from environment variables.

## Implementation Sequence

Complete each chunk before starting the next. Do not add Amadeus, authentication, cloud deployment, MCP, RAG, queues, caches, or additional services during Release 0.

### Chunk 1 - Standard Folder and Runnable Services

**Implement**

- Keep the feature in the standard `student-1/` folder.
- Replace the three placeholder Dockerfiles.
- Scaffold the Vue 3 and TypeScript frontend.
- Scaffold the ASP.NET Core backend.
- Scaffold the separate ASP.NET Core database API with EF Core SQLite.
- Add environment-driven service URLs and `/health` endpoints.
- Add all three services to root Compose using the confirmed names and ports.

**Test**

- Frontend type-check and production build.
- Backend and database unit/startup tests.
- All three Docker image builds.
- Compose configuration and health endpoints.

**Done when**

- `docker compose up --build` starts all three feature containers.
- Each container reports healthy.
- No placeholder command, missing entry point, or Flask template remains.

### Chunk 2 - Accommodation Catalogue

**Implement**

- Create the `Accommodation` EF Core model and migration.
- Enforce the field constraints from `requirements.md`.
- Implement database API create, list/filter, get, replace, and delete endpoints.
- Filter by destination, price, capacity, and active status.
- Keep the catalogue empty by default; populate the tracked demonstration database explicitly through the HTTP API rather than startup seed code.

**Test**

- CRUD success, validation, duplicate/constraint, and not-found cases.
- Candidate filtering boundaries.
- Empty-database migration and manual-record persistence.
- SQL-injection-shaped values remain data and do not modify the schema.

**Done when**

- Catalogue CRUD and filtering work through HTTP.
- The tracked demonstration database contains at least 10 valid accommodation records created through the HTTP API.
- No frontend or backend code accesses SQLite directly.

FR-16's minimum 10-record count is complete. Automatic runtime seed data remains intentionally excluded by human decision.

### Chunk 3 - Search History

**Implement**

- Create the `Search` EF Core model and migration.
- Store validated criteria, title, ranking mode, timestamps, and immutable ranked-result JSON.
- Implement database API create, newest-first list, get, rename, and delete endpoints.
- Seed at least 10 representative searches.

**Test**

- Create, list, get, rename, and delete.
- Invalid title, malformed snapshot, missing record, and repeated deletion.
- Stored searches remain readable after catalogue records change or are deleted.
- Seed idempotency and minimum record count.

**Done when**

- All search-history operations work through the database API.
- Both submitted tables contain at least 10 records.

### Chunk 4 - Backend Search Without AI

**Implement**

- Add explicit request, candidate, result, history, and error DTOs.
- Validate and normalise every search field at the backend boundary.
- Retrieve cached candidates only through the database API.
- If the destination has no cached records, request at most 10 LiteAPI sandbox rates, validate and import them through the database API, then repeat candidate filtering.
- Implement deterministic ranking by budget-midpoint distance, nightly price, then accommodation ID.
- Persist completed searches through the database API.
- Expose frontend-facing search and history CRUD endpoints.
- Add database-client timeouts and explicit dependency error handling.

**Test**

- Every validation boundary in FR-02.
- Invalid input causes no database or Ollama call.
- Candidate-filter request construction.
- LiteAPI request/response validation, import, cache hit, empty response, and dependency failures using test doubles.
- Empty-candidate response.
- Deterministic ordering.
- Database timeout and malformed response.
- Search creation and history CRUD through a fake database API.

**Done when**

- Search, results, persistence, reopen, rename, and delete work end to end without Ollama.
- Empty results and database, provider, and Ollama dependency failures return the required response shapes.

### Chunk 5 - Application AI Ranking

**Implement**

- Add `backend/Prompts/accommodation-ranking-v1.txt`.
- Send only validated criteria and eligible candidate fields to Ollama.
- Treat preferences and candidate descriptions as untrusted data.
- Request JSON-only ranking output.
- Validate exact candidate IDs, unique contiguous ranks, and reason lengths.
- Use the deterministic ranker on timeout, connection failure, or invalid output.
- Return a visible fallback notice and persist the ranking mode.

**Test**

- Valid ranking response.
- Malformed or Markdown-wrapped JSON.
- Unknown, missing, duplicated, and extra candidate IDs.
- Invalid ranks and reasons.
- Ollama timeout and connection failure.
- Prompt-injection text in preferences and candidate descriptions.

**Done when**

- A healthy model produces validated rankings.
- Every invalid or unavailable model response produces deterministic fallback results without corrupting history.

### Chunk 6 - Traveller Frontend

**Implement**

- Build the labelled search form and client-side feedback.
- Display loading, validation, empty, AI-ranked, fallback, and dependency-error states.
- Render ranked accommodation cards.
- Build newest-first search history with reopen, rename, and confirmed delete.
- Reuse shared CSS variables and design tokens.
- Support keyboard operation, visible focus, live status updates, and 320px, 768px, and 1280px widths.
- Render all user and model text through Vue interpolation; do not use `v-html`.

**Test**

- Valid and invalid submission.
- Duplicate-submit prevention.
- Empty, AI, fallback, and error states.
- Reopen without reranking.
- Rename and delete.
- Keyboard flow, focus movement, status announcements, and required viewport widths.

**Done when**

- The complete feature can be demonstrated through the browser without direct API tools.

### Chunk 7 - Shared Integration and CI

**Implement**

- Add the accommodation link to the shared home page.
- Complete root Compose health, dependencies, service DNS, environment variables, and the SQLite volume.
- Extend `student-1.yml` to restore dependencies, run all frontend/.NET tests, and build all three feature images.
- Keep CI independent of live Ollama by using deterministic fakes.
- Update root setup instructions with exact build, start, seed, model, test, health, and stop commands.

**Test**

- Start from a clean checkout and configuration.
- Open the feature through the shared page.
- Demonstrate AI success, forced fallback, reopen, rename, and delete.
- Restart Compose and confirm search history persists.
- Confirm CI fails for a broken test and succeeds after correction.

**Done when**

- The integrated group application runs through one Compose file.
- Student 1 CI validates the complete assigned feature.
- The feature is reachable from the unified entry page.

### Chunk 8 - Report and Demonstration Evidence

**Produce**

- Individual service architecture diagram.
- Integrated Release 0 architecture diagram.
- Docker Compose and DevOps pipeline diagrams.
- Plan -> Act -> Observe -> Adapt diagram.
- Conceptual, ERD, logical, and physical data designs.
- Local test, CI, Compose, AI success/fallback, CRUD, accessibility, and responsive evidence.
- Prompt/context assets, review records, commit history, contribution log, known issues, and attendance evidence.
- Mitchell's video segment showing the shared entry page, search, recommendation explanation, reopen, rename, and delete.

**Done when**

- Every checklist row has an exact evidence location.
- The group video includes the working feature, deployment, CI/CD, AI-mode, and the shared agentic-loop execution.

## Working Rule

For each chunk:

1. Select its requirement IDs from `sprint-backlog.md`.
2. Implement the smallest complete vertical behaviour.
3. Run the targeted tests.
4. Review correctness, failure handling, security, accessibility, and service boundaries.
5. Update evidence only with real files and results.
6. Integrate before starting the next chunk.

## Local Agentic-Loop Setup and Demonstration

The .NET agentic-loop code is implemented. Complete this setup before the final report and video evidence.

1. Compose checks the configured model tags and pulls only models missing from the persistent Ollama volume.
2. Copy `.env.example` to `.env` and confirm:

   ```text
   IMPLEMENTER_MODEL=qwen2.5-coder:7b
   REVIEWER_MODEL=llama3.2:3b
   APPLICATION_MODEL=llama3.2:3b
   ```

3. Start the services. The one-shot model setup containers complete before their dependent application services start:

   ```powershell
   docker compose build agentic-loop
   docker compose up -d ollama agentic-loop
   ```

4. Run a real pre-test, then execute one bounded task:

   ```powershell
   docker compose exec agentic-loop dotnet /app/AgenticLoop.dll run `
     --task "Implement one bounded accommodation change" `
     --context "student-1/docs/requirements.md" `
     --context "student-1/path/to/relevant/source-file" `
     --pre-test-command "<actual command>" `
     --pre-test-result "<actual result>"
   ```

5. Show the same terminal printing implementer Plan/Act, reviewer Observe, and any bounded Adapt revision.
6. Manually keep, change, or reject the proposal and run the post-test.
7. Finalise the generated record:

   ```powershell
   docker compose exec agentic-loop dotnet /app/AgenticLoop.dll finalise `
     --record "/workspace/docs/agentic-loop-records/<record>.json" `
     --decision changed `
     --notes "<what was kept, changed, or rejected>" `
     --post-test-command "<actual command>" `
     --post-test-result "<actual result>"
   ```

8. Include the terminal execution in the group video and reference the prompts, review record, and genuine result in the technical report.

This setup is demonstration evidence. It does not block writing the Phase 2 application code, but it must be completed before submission.
