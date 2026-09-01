# Student 2 Release 0 Checklist

Reassessed against the Release 0 brief and project specification on 2026-09-01.

## Status Key

- **Complete:** implementation or documentation exists and has local validation.
- **Evidence pending:** implementation exists, but assessment proof has not been captured.
- **Blocked:** the current environment cannot complete the item.
- **Human action:** requires the student/team rather than Copilot.

## Overall Status

| Area | Status | Current evidence |
|---|---|---|
| Feature implementation | Complete | Frontend, backend, database API, SQLite, CRUD, AI generation/fallback, atomic persistence, Dockerfiles, health endpoints, and shared routing exist. |
| Automated validation | Complete | Frontend 2/2, backend 6/6, and database 3/3 tests pass; all three Student 2 production images build. |
| Planning and design | Complete | Requirements, feature plan, risk plan, conceptual model, ERD, logical/physical design, and architecture diagrams exist under `student-2/docs/`. |
| Integrated execution proof | Evidence pending / blocked | Seven services run through a manual Docker network, but clean Compose evidence is blocked because Compose v2 is unavailable locally. |
| AI execution proof | Evidence pending | Source integration exists; a live frontend-triggered Ollama success and forced fallback still need capture. |
| Development agentic loop | Not evidenced | No finalised Student 2 two-model Plan/Act/Observe/Adapt record exists. |
| GitHub/CI evidence | Human action | Five selective local commits exist on the Student 2 branch; push, PR, and successful Actions evidence remain pending. |
| Report and showcase | In progress | Documentation structure exists; screenshots, execution evidence, attendance, and video remain. |

## Marking Criteria

| No. | Criterion | Current status | Done | Still required |
|---:|---|---|---|---|
| 1 | Project setup | Evidence pending | Standard folders; shared `/itinerary/` route and theme; Dockerfiles; root service definitions; Student 2 workflow; shared Ollama configuration; 10 trips and 20 stops on fresh initialization; selective local commit history. | Push/PR, clean Compose capture, and report evidence. |
| 2 | Service implementation | Evidence pending | Independently containerised frontend, backend, and database API; health endpoints; HTTP boundaries; production images build. | Capture the integrated services healthy through the official Compose command. |
| 3 | AI-Mode integration | Evidence pending | Backend calls shared Ollama with one configured approved model; versioned prompt, strict output validation, deterministic fallback, and visible generation mode exist. | Capture a genuine AI result initiated from the integrated frontend and identify the exact model tag. |
| 4 | Agentic AI workflow | Not evidenced | Shared runner and prompts exist at team level. | Run Student 2 work through distinct implementer/reviewer models, demonstrate Plan/Act/Observe/Adapt in the terminal, human-review it, and finalise the record. |
| 5 | Prompt engineering and context | In progress | Application prompt, untrusted-data instructions, output constraints, prompt log, review record, and architecture boundaries exist. | Add the genuine loop record and explain selected context, model roles, validation, and human decision in the report. |
| 6 | DevOps and GitHub Actions | Evidence pending | `student-2.yml` installs Node/Python dependencies, runs all three suites, validates Compose, and builds shared/Student 2 images. Five local proof commits exist. | Push the branch with approval, open a pull request, and capture a successful Actions run URL or screenshot. |
| 7 | Docker Compose integration | Blocked locally | Root Compose defines Student 2 services, health ordering, shared frontend route, database storage, and one shared Ollama runtime. | Repair/install Compose v2, run clean `docker compose up --build`, and capture configuration, health, and routing evidence. |
| 8 | Working software and CRUD | Evidence pending | Browser controls and backend/database endpoints implement create/read/update/delete for trips/stops plus add/remove/edit/regenerate actions. Atomic writes prevent partial itinerary replacement. | Complete and capture the integrated browser CRUD sequence and database restart persistence. |
| 9 | Technical report | In progress | Requirements, planning, risk, data design, architecture, prompt/review records, contribution log, known issues, and evidence checklists exist. | Add test output, Actions/Compose evidence, screenshots, commit/PR references, attendance checkpoint, and final limitations. |
| 10 | Project demonstration | Not started | Feature has a demonstrable browser workflow. | Rehearse Student 2 segment; show integrated CRUD, live AI, fallback, agentic loop, CI, and deployment; attend Week 6; publish and link the group video. |

## Software Checklist

- [x] Frontend input form covers traveller, destination, dates, budget, and interests.
- [x] Day-by-day itinerary view exists.
- [x] Add, edit, regenerate, and remove stop controls exist.
- [x] Whole-itinerary regeneration exists.
- [x] Trip and stop CRUD pass through frontend -> backend -> database API.
- [x] Only the database service opens SQLite.
- [x] Trip deletion cascades to stops.
- [x] Trip creation and whole-itinerary replacement are transactional.
- [x] AI output requires exact fields, valid days, and complete day coverage.
- [x] Full generation requires exactly two stops per day.
- [x] Single-stop regeneration requires exactly one stop on the target day.
- [x] Invalid/unavailable model output uses deterministic fallback.
- [x] Application prompt treats traveller and existing-stop data as untrusted.
- [x] Frontend has no external CDN/runtime dependency.
- [x] Shared home page links to `/itinerary/`.
- [x] Student 2 uses the shared visual system.
- [x] Fresh database initialization creates 10 trips and 20 stops.
- [x] Frontend tests pass 2/2.
- [x] Backend tests pass 6/6.
- [x] Database tests pass 3/3.
- [x] Frontend, backend, and database production images build.
- [ ] Broaden failure-path coverage beyond the focused Release 0 regression suite.

## Planning and Documentation Checklist

- [x] Functional and non-functional requirements.
- [x] Individual feature plan.
- [x] Risk management plan.
- [x] Conceptual data model.
- [x] Entity relationship diagram.
- [x] Logical data design.
- [x] Physical data design.
- [x] Individual service architecture diagram.
- [x] AI request-flow diagram.
- [x] Docker Compose architecture diagram.
- [x] DevOps pipeline diagram.
- [x] Agentic workflow diagram.
- [x] Prompt log entry.
- [x] AI review record.
- [x] Contribution-log structure.
- [x] Known issues and limitations.
- [x] Browser evidence checklist.
- [ ] Copy the Student 2 requirements into or link them from the shared sprint backlog/report plan.

## Evidence Checklist

- [ ] Save combined frontend/backend/database test output in the report evidence location.
- [ ] Capture a successful `student-2.yml` GitHub Actions run.
- [ ] Capture clean Docker Compose configuration and startup.
- [ ] Capture frontend, backend, database, shared frontend, and Ollama health.
- [ ] Capture the shared home page opening `/itinerary/`.
- [ ] Capture a genuine frontend -> backend -> Ollama -> LLM success.
- [ ] Capture a forced AI fallback without losing the itinerary.
- [ ] Capture create/read/update/delete through the browser.
- [ ] Capture atomic whole-itinerary regeneration.
- [ ] Restart services and capture persisted trips/stops.
- [ ] Complete keyboard-only operation checks.
- [ ] Capture 320px, 768px, and 1280px layouts without horizontal scrolling.
- [ ] Save integrated application screenshots.
- [ ] Finalise a shared agentic-loop record with distinct models and a human decision.

## Human and Team Actions

- [x] Create or switch to the agreed Student 2 feature branch.
- [x] Review and selectively isolate Student 2 changes from unrelated worktree changes.
- [x] Create meaningful local commits in database, backend, frontend, integration, and documentation chunks.
- [ ] Push and open a pull request.
- [x] Record local commit hashes in `contribution-log.md`.
- [ ] Record the pull-request URL and reviewer decision in `contribution-log.md`.
- [ ] Record the successful Actions URL.
- [ ] Add Student 2 evidence to the group technical report.
- [ ] Record the Week 6 attendance checkpoint.
- [ ] Rehearse and record the Student 2 showcase segment.
- [ ] Add the published group video URL and Student 2 timestamp.

## Critical Path

1. Repair Docker Compose v2 and capture one clean integrated run.
2. Run and finalise the genuine two-model development agentic loop.
3. Complete the browser checklist, including AI success, fallback, CRUD, restart, keyboard, and responsive captures.
4. Push the reviewed local branch, open the Student 2 pull request, and retain the successful Actions run.
5. Assemble report evidence and complete attendance/video actions.

## Important Distinction

The `agentTrace` displayed after itinerary creation explains the application's internal orchestration. It does not satisfy the assessed development agentic-loop requirement. Only a genuine terminal run with distinct implementer and reviewer models, followed by human validation and a finalised shared-runner record, counts as that evidence.
