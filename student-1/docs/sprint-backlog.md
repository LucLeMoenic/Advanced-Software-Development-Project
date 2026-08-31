# Accommodation Recommender Sprint Backlog

Update status and evidence as work progresses. A backlog item is done only when its listed requirements and exit evidence are satisfied in the integrated application.

| ID | Phase | Backlog item | Requirement and evidence IDs | Definition of done | Owner | Status |
|---|---:|---|---|---|---|---|
| ACC-00 | 0 | Finalise integration contracts | FR-18 to FR-20, NFR-11 | Standard folder, route, service names, ports, theme, model tags, and shared-file ownership are recorded. | Mitchell + team | Done |
| ACC-01 | 1 | Complete shared agentic-loop evidence | FR-21 to FR-27, NFR-13 to NFR-14, EV-05 to EV-06 | Shared service passes tests and Compose health; one genuine finalised two-model record demonstrates a reviewer-requested correction and human decision. | Mitchell + AI owner | In progress |
| ACC-02 | 2 | Scaffold three healthy feature services | FR-19 to FR-20, NFR-09 to NFR-11 | Vue frontend, ASP.NET backend, and ASP.NET database API build, run in containers, and expose appropriate health behaviour. | Mitchell | Done |
| ACC-03 | 3 | Implement accommodation catalogue | FR-04, FR-15 to FR-17, NFR-06, NFR-09 to NFR-10, EV-02 | Database API owns SQLite and supports catalogue CRUD/filtering. Mitchell will manually create the required 10 records after the application flow exists; automatic seeding was declined. | Mitchell | In progress |
| ACC-04 | 4 | Implement persisted search history | FR-11 to FR-14, FR-17, NFR-07, EV-02 | Search history supports create, list, reopen, rename, and delete with immutable result snapshots and at least 10 records. | Mitchell | Not started |
| ACC-05 | 5 | Implement deterministic backend workflow | FR-01 to FR-05, FR-09 to FR-14, FR-20, NFR-02 to NFR-03, NFR-08 to NFR-09, EV-01, EV-03 | Backend validates requests, retrieves candidates through the database API, ranks deterministically, persists results, and handles dependency failures. | Mitchell | Not started |
| ACC-06 | 6 | Integrate application Ollama ranking | FR-06 to FR-10, NFR-01 to NFR-03, NFR-06, NFR-08, EV-01, EV-03 | One configured application model ranks candidates; complete output validation and deterministic fallback are proven. | Mitchell | Not started |
| ACC-07 | 7 | Build the traveller interface | FR-01, FR-03, FR-05, FR-10, FR-12 to FR-14, FR-18, FR-20, NFR-04 to NFR-05, NFR-07, EV-04, EV-09 | Browser supports search, results, fallback notice, reopen, rename, delete, keyboard use, focus handling, and required viewport widths. | Mitchell | Not started |
| ACC-08 | 8 | Audit development-workflow evidence | FR-27, EV-05 to EV-06, EV-11 | Records and logs cover database, backend, frontend, AI, Compose, CI, pre/post validation, and human decisions. | Mitchell | Not started |
| ACC-09 | 9 | Integrate with shared application | FR-18 to FR-20, NFR-10 to NFR-11, EV-07, EV-09 to EV-10 | Unified page opens the feature; one Compose stack runs all services using service DNS and preserves SQLite data across restart. | Mitchell + integration owner | Not started |
| ACC-10 | 10 | Complete Student 1 CI | NFR-12, EV-08 | Student 1 workflow tests/builds the frontend, backend, database, and assigned containers without requiring live Ollama. | Mitchell | Not started |
| ACC-11 | 11 | Assemble report and showcase evidence | EV-01 to EV-11 | Required diagrams, test/CI/Compose evidence, screenshots, workflow logs, contributions, limitations, and video URL have exact evidence locations. | Mitchell + team | Not started |

## Confirmed Integration Values

| Contract | Value |
|---|---|
| Final feature folder | `student-1/` |
| Shared route | `/accommodation` |
| Navigation label | `Accommodation Recommender` |
| Compose services | `student1-frontend`, `student1-backend`, `student1-database` |
| Host ports | Frontend `5101`, backend `5201`, database `5301` |
| Container ports | Frontend `80`; backend and database `8080` |
| Theme | Reuse shared CSS variables and design tokens |
| Application model | `llama3.2:3b` |
| Implementer model | `qwen2.5-coder:7b` |
| Reviewer model | `llama3.2:3b` |
| Shared-file ownership | Mitchell may update root Compose, shared navigation/theme, and `student-1.yml` for this feature |
