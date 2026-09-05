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
| Application AI | Explicitly opted-in frontend call visibly follows frontend -> backend/API -> Ollama -> one approved LLM; default ranking remains programmatic. |
| Testing | Pre/post testing evidence appropriate to the current release and assigned services. |
| Planning/design | Backlog requirements, feature plan, risk plan, conceptual model, ERD, logical and physical data designs, architecture diagrams. |
| AI-assisted development | Prompt logs, human decisions, validation, and review records. |
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
| One Compose stack | Root Compose builds/runs all services with correct networking, volumes, configuration, models, and health. |
| Cross-feature data boundary | Other services access a database owner's data only through its API. |
| Technical report | One PDF contains every required individual/group section and evidence item. |
| Video | Published, at most 10 minutes, all members participate, integrated software, AI, and deployment shown, URL in report. |
| Attendance | All members attend Week 6; absence results in 0 for that member. |

## 3. Mitchell Feature Evidence Matrix

| Criterion | Required Mitchell evidence | Status | Evidence location |
|---|---|---|---|
| 1. Project Setup | Standard folder; three services; populated tables; Dockerfiles; shared route/theme; model config; Compose entries. | In progress | Standard folder, service projects, Dockerfiles, Compose entries, shared route/theme integration, 10 international Search records, and 50 active Accommodation records are implemented; every trip has exactly five eligible catalogue rows and final evidence capture remains |
| 2. Service Implementation | Healthy Vue frontend, ASP.NET backend, and ASP.NET/EF Core database API containers communicating over HTTP. | In progress | All three services and API layers are implemented; database tests pass 20/20, backend tests pass 67/67 including programmatic/AI selection and corrected live provider/ranking contracts, frontend tests pass 8/8, and the frontend production build passes; final integrated evidence remains |
| 3. AI-Mode Integration | Explicitly opted-in browser call through backend to exactly one configured application model, backend-owned ranking prompt, output validation, and visible result. | In progress | Frontend defaults to `programmatic`, sends `useAi` through `/api/searches`, and renders programmatic/AI/fallback results; backend ranking prompt/client/validation tests pass; repeated opted-in live requests through the frontend proxy return validated `ai` rankings within the model timeout; browser screenshot evidence remains |
| 5. Prompt/Context Management | Application prompt, prompt log, context, review record, model outputs, and human decisions. | In progress | `backend/Prompts/accommodation-ranking-v1.txt`, `docs/context.md`, `docs/prompt-log.md`, `docs/review-record.md` |
| 7. Docker Compose | One stack with service DNS, health, shared Ollama/model setup, and SQLite persistence. | In progress | `docker-compose.yml` contains all three accommodation services, health ordering, service DNS configuration, and a bind mount for tracked `database/storage/accommodation.db`; full integrated stack evidence remains |
| 8. Working Software | Browser search create, history read/rename/delete, persisted restart, default programmatic ranking, opted-in AI success, and fallback. | In progress | Vue search/results/history CRUD, default programmatic ranking, explicit AI opt-in, a live LiteAPI sandbox import, 10 international synthetic trips, 50 active accommodations, database persistence, and repeated live Ollama `ai` rankings through the frontend proxy are implemented; manual browser CRUD, restart recapture, forced-fallback capture, and screenshots remain |
| 9. Technical Report | Required diagrams, test/Compose evidence, screenshots, logs, limitations, commits, contributions, attendance. | Not started | Pending |
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
| Individual/integrated/Compose diagrams | Not started | Pending |
| Application one-model request-flow diagram | Not started | Pending |

## 5. Demonstration Scenarios

| Scenario | Status | Evidence location |
|---|---|---|
| Valid search produces programmatic results by default | In progress | Frontend request/rendering and backend Ollama-bypass behavior are covered by automated tests; integrated browser evidence pending |
| Opted-in search produces one-model AI-ranked results | In progress | Frontend opt-in request/rendering is covered by `frontend/src/App.test.ts`; backend model contract is covered by backend tests; live model/browser evidence pending |
| Invalid search has field errors and no side effects | In progress | `frontend/src/App.test.ts` and backend validation tests pass; integrated screenshot pending |
| No candidates skips the application model | In progress | Frontend empty state and backend no-candidate behavior are tested; integrated screenshot pending |
| Model timeout/malformed output produces deterministic fallback | In progress | Frontend fallback notice and backend failure paths are tested; forced-fallback browser evidence pending |
| History reopen does not rerun ranking | In progress | `frontend/src/App.test.ts` verifies GET reopen rather than POST; integrated browser evidence pending |
| Rename/delete work from Vue | In progress | `frontend/src/App.test.ts` covers rename synchronization, confirmation, deletion, and focus; integrated browser evidence pending |
| Restart preserves history | Not started | Pending |
| Keyboard and 320/768/1280px checks pass | In progress | Focus/live-region component tests pass; repeatable manual checks are in `docs/frontend-browser-checklist.md`; viewport execution/screenshots pending |
| Every table has at least 10 records | Not started | Pending |
| Full Compose app starts from documented setup | Not started | Pending |

## 6. Report and Submission Evidence

| Item | Status | Evidence location |
|---|---|---|
| Project overview, approved feature allocation, Agile plan/backlog | Not started | Pending group artefacts |
| Repository structure and implementation summary | Not started | Pending report |
| Local testing and Compose execution | Not started | Pending output/screenshots |
| Integrated application screenshots | Not started | Pending |
| Prompt log and review record | In progress | `docs/prompt-log.md` and `docs/review-record.md` |
| Known issues and limitations | In progress | `docs/context.md`; final report section pending |
| Commit/contribution logs and attendance checkpoints | In progress | Git history; remaining evidence pending |
| Published showcase video URL | Not started | Pending |

## 7. Final Gate

1. Replace every `Pending` evidence location with a committed path or stable URL.
2. Verify each `Complete` item on integrated `main`, not only a feature branch.
3. Cross-check report headings against the Release 0 submission list.
4. Confirm the app uses one LLM through its backend.
5. Confirm all members appear and demonstrate their integrated feature in the video and attend Week 6.
