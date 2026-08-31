# Release 0 Full-Marks Evidence Checklist

This is an evidence index, not a confidence checklist. Mark an item complete only when integrated behaviour works and the evidence location is recorded.

Status values: `Not started`, `In progress`, `Blocked`, `Complete`.

## 1. Every Group Member's Individual Obligations

Each student must provide these for their assigned feature.

| Obligation | Full-marks evidence expected |
|---|---|
| Frontend microservice | Real containerised frontend, integrated from the unified home page and shared theme. |
| Backend/API microservice | Real containerised API mediating the frontend, database API, and one application LLM. |
| Database microservice | Real containerised API that alone owns its SQLite database. |
| CRUD | Create, Read, Update, and Delete demonstrated through browser, backend, database API, and persistence. |
| Populated data | At least 10 valid records in every submitted table, created repeatably. |
| Application AI | Frontend-triggered call visibly follows frontend -> backend/API -> Ollama -> one approved LLM. |
| Agentic loop | The integrated shared .NET service uses two distinct local Ollama models for implementation and review throughout development, with finalised pre/post evidence records. |
| CI/CD | Student's own `.github/workflows/student-x.yml` builds and validates all assigned services. |
| Testing | Pre/post testing evidence appropriate to the current release and assigned services. |
| Planning/design | Backlog requirements, feature plan, risk plan, conceptual model, ERD, logical and physical data designs, architecture diagrams. |
| AI-assisted development | Versioned prompts, selected context, implementer/reviewer outputs, human decisions, validation, and review record. |
| Repository contribution | Meaningful commits/PRs integrated into `main`, contribution log, and resolved integration issues. |
| Showcase | Student attends Week 6 and demonstrates their working feature in the integrated group video. |

If a feature is not integrated, the brief states that it receives 0 marks.

## 2. Group Obligations

| Obligation | Full-marks evidence expected |
|---|---|
| One integrated app | Five frontend/backend/database sets run together and are demonstrated from one machine. |
| Unified entry point | Shared containerised `index.html` links to all five features. |
| Shared visual system | Consistent CSS and UI across all features. |
| Application AI-mode | Ollama and approved model(s) support every frontend/backend feature. |
| Two-model agentic loop | Shared Compose service, distinct local implementation/review models, specialised prompts, records across development phases, terminal demonstration, and report evidence. |
| One Compose stack | Root Compose builds/runs all services with correct networking, volumes, configuration, models, and health. |
| Cross-feature data boundary | Other services access a database owner's data only through its API. |
| Five workflows | `student-1.yml` through `student-5.yml` build and validate assigned services. |
| Technical report | One PDF contains every required individual/group section and evidence item. |
| Video | Published, at most 10 minutes, all members participate, integrated software/AI/loop/CI/deployment shown, URL in report. |
| Attendance | All members attend Week 6; absence results in 0 for that member. |

## 3. Mitchell Feature Evidence Matrix

| Criterion | Required Mitchell evidence | Status | Evidence location |
|---|---|---|---|
| 1. Project Setup | Standard folder; three services; populated tables; Dockerfiles; shared route/theme; model config; workflow; Compose entries. | In progress | Standard folder, service projects, Dockerfiles, workflow, Compose entries, and 10 tracked Search records implemented; Accommodation records and shared route/theme integration remain |
| 2. Service Implementation | Healthy Vue frontend, ASP.NET backend, and ASP.NET/EF Core database API containers communicating over HTTP. | In progress | Database catalogue and search-history APIs are implemented under `database/` through scoped repositories; 19/19 database tests pass; frontend-facing search and recommendation HTTP behaviour remains |
| 3. AI-Mode Integration | Browser-triggered call through backend to exactly one configured application model, backend-owned ranking prompt, output validation, and visible result. | Not started | Pending |
| 4. Agentic AI Workflow | Integrated .NET loop service, implementer Plan/Act, distinct reviewer Observe, bounded Adapt, pre/post evidence, human decision, exact local model tags, and records throughout development. | In progress | `ai-services/agentic-loop/` and Compose wiring exist; real model records pending |
| 5. Prompt/Context Management | Implementer/reviewer prompts, prompt log, context, review record, allow-listed context, model outputs, and human decisions. | In progress | `ai-services/agentic-loop/prompts/`, `docs/context.md`, `docs/prompt-log.md`, `docs/review-record.md` |
| 6. DevOps/GitHub Actions | Passing assigned workflow runs frontend/.NET/runner checks and builds three images. | In progress | `.github/workflows/student-1.yml` now defines frontend build, .NET tests, Compose validation, and three-image builds; passing GitHub Actions URL remains pending |
| 7. Docker Compose | One stack with service DNS, health, shared Ollama/model setup, and SQLite persistence. | In progress | `docker-compose.yml` contains all three accommodation services, health ordering, service DNS configuration, and a bind mount for tracked `database/storage/accommodation.db`; full integrated stack evidence remains |
| 8. Working Software | Browser search create, history read/rename/delete, persisted restart, AI success and fallback. | In progress | Database API create/list/get/rename/delete and immutable snapshot persistence are implemented and tested; backend and browser layers remain |
| 9. Technical Report | Required diagrams, test/CI/Compose evidence, screenshots, logs, limitations, commits, contributions, attendance. | Not started | Pending |
| 10. Demonstration | Mitchell's rehearsed segment and final published group video URL. | Not started | Pending |

## 4. Design and Quality Artefacts

| Artefact | Status | Evidence location |
|---|---|---|
| Functional/non-functional requirements in sprint backlog | In progress | `docs/requirements.md`; team backlog link pending |
| Feature plan | Complete for planning | `docs/feature-plan.md` |
| Risk plan | Complete for planning | `docs/risk-plan.md` |
| Conceptual data model and ERD | Not started | Pending |
| Logical schema | In progress | `docs/requirements.md`; diagram pending |
| Physical SQLite design/migration | Not started | Pending |
| Individual/integrated/Compose/DevOps diagrams | Not started | Pending |
| Application one-model request-flow diagram | Not started | Pending |
| Two-model Plan -> Act -> Observe -> Adapt diagram | Not started | Pending |

## 5. Demonstration Scenarios

| Scenario | Status | Evidence location |
|---|---|---|
| Valid search produces one-model AI-ranked results | Not started | Pending |
| Invalid search has field errors and no side effects | Not started | Pending |
| No candidates skips the application model | Not started | Pending |
| Model timeout/malformed output produces deterministic fallback | Not started | Pending |
| History reopen does not rerun ranking | Not started | Pending |
| Rename/delete work from Vue | Not started | Pending |
| Restart preserves history | Not started | Pending |
| Keyboard and 320/768/1280px checks pass | Not started | Pending |
| Every table has at least 10 records | Not started | Pending |
| Two distinct local models complete implement-review-adapt cycle | Not started | Pending |
| Reviewer requests a correction and the final record shows the decision/validation | Not started | Pending |
| Finalised records cover database, backend, frontend, AI, Compose, and CI work | Not started | Pending |
| Full Compose app starts from documented setup | Not started | Pending |
| Assigned CI catches failure and has a passing run | Not started | Pending |

## 6. Report and Submission Evidence

| Item | Status | Evidence location |
|---|---|---|
| Project overview, approved feature allocation, Agile plan/backlog | Not started | Pending group artefacts |
| Repository structure and implementation summary | Not started | Pending report |
| Local testing, Actions, and Compose execution | Not started | Pending output/URLs/screenshots |
| Integrated application screenshots | Not started | Pending |
| Prompt log and two-model workflow record | In progress | Prompt artefacts exist; execution record pending |
| Known issues and limitations | In progress | `docs/context.md`; final report section pending |
| Commit/contribution logs and attendance checkpoints | In progress | Git history; remaining evidence pending |
| Published showcase video URL | Not started | Pending |

## 7. Final Gate

1. Replace every `Pending` evidence location with a committed path or stable URL.
2. Verify each `Complete` item on integrated `main`, not only a feature branch.
3. Cross-check report headings against the Release 0 submission list.
4. Confirm the app uses one LLM through its backend and the development loop record identifies two distinct local model tags.
5. Confirm all members appear and demonstrate their integrated feature in the video and attend Week 6.
