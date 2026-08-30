# Feature Plan

## Scope

Build the AI Accommodation Recommender feature as a three-service system: `frontend`, `backend`, and `db`, with supporting docs, Docker, and CI evidence.

This plan follows the Release 0 build order and is written so each step can be completed, reviewed, and evidenced independently.

## Build Order

1. Create the documentation and prompt-management files.
2. Scaffold the three services.
3. Add Dockerfiles and Compose integration.
4. Implement the database service.
5. Wire the backend to the database.
6. Add Amadeus sourcing.
7. Add Ollama ranking and orchestration.
8. Build the Vue frontend.
9. Integrate into the shared workspace.
10. Add CI/CD.
11. Prepare the report and demo evidence.

## Step Details

### 1. Documentation and Prompt Management

Deliverables:
- `context.md`
- `requirements.md`
- `feature-plan.md`
- `risk-plan.md`
- `prompt-log.md`
- `review-record.md`
- `prompt-library/`

Done when:
- The docs describe the integrated Release 0 feature, not just the standalone feature idea.
- Future AI chats can use the docs as a handoff without needing the full HLD every time.

### 2. Scaffold the Three Services

Deliverables:
- Empty `frontend`, `backend`, and `db` projects.
- Each service builds and runs with a placeholder health endpoint or scaffold output.

Done when:
- The three projects exist in the feature folder and can be started independently.
- The service boundaries match the high-level design.

### 3. Dockerfiles and Compose Integration

Deliverables:
- Dockerfile for each service.
- Updates to the shared `docker-compose.yml`.

Done when:
- The feature services build in Docker.
- The Compose file wires the services together with the expected environment variables and volume.

### 4. Database Service

Deliverables:
- `Chat` and `Accommodation` entities.
- EF Core `AppDbContext`.
- Migration and CRUD controllers.

Done when:
- The database service enforces the required relationship, cascade delete, and unique rank constraint.
- All backend-facing CRUD endpoints work.

### 5. Backend Wiring

Deliverables:
- `DataApiClient`.
- Backend chat controller.
- Stub search endpoint.

Done when:
- The backend can create, read, update, and delete through the data service.
- A simple end-to-end search path works before AI and external sourcing are added.

### 6. Amadeus Sourcing

Deliverables:
- `AmadeusAccommodationSourceService`.
- External API configuration.
- Failure and empty-result handling.

Done when:
- Real accommodation candidates are sourced and persisted through the backend pipeline.
- External API failures degrade gracefully instead of crashing the feature.

### 7. Ollama Ranking and Orchestration

Deliverables:
- `OllamaRankingService`.
- Ranking validation and fallback logic.
- `SearchOrchestrator` with `[PLAN]/[ACT]/[OBSERVE]/[ADAPT]` logging.

Done when:
- A search can source candidates, rank them, persist them, and return ranked results.
- Malformed model output falls back to a safe ranking strategy.

### 8. Frontend

Deliverables:
- Typed API client.
- Search, loading, results, and history components.
- Rename and delete interactions in the history panel.

Done when:
- The user can search, view ranked results, revisit history, rename a search, and delete a search from the UI.

### 9. Shared Workspace Integration

Deliverables:
- Shared `index.html` integration.
- Theme alignment with the group frontends.

Done when:
- The feature works inside the shared app instead of only in isolation.

### 10. CI/CD

Deliverables:
- Student-specific GitHub Actions workflow.
- Build and validation steps for the assigned services.

Done when:
- The workflow runs only for this feature folder and captures the build/validation evidence needed for the report.

### 11. Report and Demo Evidence

Deliverables:
- Docker Compose evidence.
- GitHub Actions evidence.
- Prompt log and review record evidence.
- Commit history and known-issues notes.

Done when:
- The report can be assembled directly from the written evidence.
- The demo can show the full integrated flow without extra explanation.

## Target Dates

- Documentation setup: start of feature work.
- Service scaffolding: after docs.
- Core feature implementation: after scaffolding and Docker.
- Frontend and integration: after backend and database are stable.
- CI/report/demo: after the feature is working end to end.

## Dependency Notes

- Do not start later steps until the earlier step is stable enough to support them.
- Keep each step small enough to review in isolation.
- Re-check the Release 0 brief whenever the implementation affects marks, evidence, or integration expectations.
