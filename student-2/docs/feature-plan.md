# Itinerary Planner Feature Plan

## Goal

Deliver a containerised itinerary planner that generates and safely revises persisted day-by-day trips through the integrated team application.

## Fixed Contracts

| Contract | Value |
|---|---|
| Shared route | `/itinerary/` |
| Shared entry point | `http://localhost:5100` |
| Services | `student2-frontend`, `student2-backend`, `student2-database` |
| Diagnostic host ports | `5102`, `5202`, `5302` |
| Backend/database container port | `8080` |
| Application model | `${APPLICATION_MODEL:-llama3.2:3b}` |
| Ollama URL | `http://ollama:11434` |
| Database | SQLite owned only by the database API |

## Implementation Status

| Phase | Completion gate | Status |
|---|---|---|
| 1. Service foundation | Three real Docker images and health endpoints exist. | Complete |
| 2. Database and seed data | CRUD, constraints, cascade delete, 10 trips, and at least 10 stops exist. | Complete |
| 3. Backend orchestration | Validation, database API client, AI generation, fallback, and CRUD proxy exist. | Complete |
| 4. Safe persistence | Create and whole-trip regeneration use database-owned atomic operations. | Complete |
| 5. Traveller frontend | Input, day view, saved trips, edit/regenerate/add/remove controls, and shared styling exist. | Complete |
| 6. Focused automated tests | Frontend, backend, and database suites cover primary behavior and safety regressions. | Complete; broader edge coverage remains useful |
| 7. Shared integration and CI | Home route, Compose services, and Student 2 workflow exist. | Complete locally, including service startup and HTTP smoke checks; remote Actions evidence pending |
| 8. Agentic workflow | Shared two-model loop has a finalised Student 2 record. | Not started |
| 9. Report evidence | Diagrams, screenshots, execution records, contributions, limitations, and video references are assembled. | In progress |

## Next Gates

1. Run the shared agentic loop against the Student 2 reliability or architecture changes and finalise the record after human review.
2. Review and commit the latest fixes on the Student 2 feature branch, then open a pull request.
3. Capture a successful GitHub Actions run.
4. Capture a clean-checkout integrated Compose startup for durable report evidence.
5. Complete the browser checklist and collect screenshots.
6. Add report references, attendance evidence, and the published group showcase URL.
