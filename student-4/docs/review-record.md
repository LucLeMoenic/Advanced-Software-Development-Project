# Student 4 Review Record

## 2026-09-03 Repository and Design Review

Reviewer: GitHub Copilot, acting as an AI programming assistant for Liam
Zelmanowski.

### Scope Reviewed

- Release 0 project specification and assessment brief.
- Existing root Compose, environment, shared home, nginx, and visual system.
- Student 4 placeholders.
- Relevant Student 1 ASP.NET Core, EF Core, typed HTTP client, Ollama validation,
  integration-test, health-check, and Docker conventions.
- Relevant Student 2 static frontend, nginx, Vitest, CI smoke-test, and
  documentation conventions.

### Findings

| Severity | Finding | Resolution |
|---|---|---|
| Required | Student 4 has only placeholder Dockerfiles and a placeholder README; no functional frontend, backend, database API, tests, shared route, or CI validation exists. | Implement the complete approved Student 4 Release 0 slice. |
| Required | Root Compose exposes only `student4-frontend`; backend/database services, health dependencies, persistent storage, and model settings are absent. | Add the fixed three-service dependency chain and shared model dependency. |
| Required | The shared home links directly to diagnostic port 5104 and nginx has no `/budget/` or `/budget-api/` routes. | Replace the card and add supported same-origin routes. |
| Non-blocking | The specification's example stack is Flask, while the approved design uses ASP.NET Core 8. | Follow the repository's established Student 1 ASP.NET pattern while preserving the required architecture. |
| Non-blocking | The brief calls the shared index HTMX, while the repository's current shared home is Vue. | Preserve the integrated Vue home; use local HTMX only in Student 4. |

No existing Student 4 business implementation was available to review. No
passing behavior or human approval is claimed by this record.

## 2026-09-03 Implementation Self-Review

- Confirmed only the database project references EF Core/SQLite.
- Confirmed public expense input has no converted-value fields and unknown JSON
  members are rejected.
- Added database-side protection against changing a budget currency when
  conversion snapshots exist.
- Changed successful-delete focus restoration to a durable add command after a
  frontend test exposed focus loss during rerender.
- Confirmed database, backend, and frontend suites pass locally.
- Confirmed Student 4 and shared frontend package builds pass locally.
- Left Docker, browser, live-model, agentic-loop, GitHub Actions, and all
  human-only evidence pending rather than inferring results.

Liam's OBSERVE feedback and approval remain pending.

## 2026-09-03 Independent Review Resolution

A read-only code reviewer identified seed restart collisions, eager shared-nginx
upstreams in scoped CI, omitted request dates, stale frontend state,
period-aggregate row duplication, uncaught malformed dashboard data, non-atomic
journey currencies, and incomplete typed-client collection validation.

All substantiated findings were corrected and covered by focused tests. The
final independent review verdict was PASS with no blocking or high-severity
defects. Two proposed changes were intentionally not applied:

- Normal Compose still waits for completed model setup because the approved
  architecture explicitly requires that dependency. Automated CI starts the
  same backend image without Ollama and proves deterministic fallback.
- Public requests containing client-computed converted values are rejected,
  because the approved contract says those values are not authoritative; valid
  expense create/update requests omit them and are always recomputed.

Docker runtime, manual browser/accessibility, live Ollama, shared agentic-loop,
GitHub Actions, and Liam's review remain pending.

## 2026-09-03 Direct Integration Smoke

The real database and backend processes were started against a temporary SQLite
file. Health requests succeeded; startup produced 12 budgets and 24 expenses;
the Sydney dashboard returned AUD totals and six categories; a budget and
expense completed create/update/delete; 101 USD converted authoritatively to
155 AUD at rate snapshot 153846154; and unavailable Ollama returned
`source: fallback`.

This smoke exposed and led to correction of null-note response validation in
the typed database client. Its regression passes in the final backend suite.
Both processes and all temporary SQLite files were removed afterward. This is
local service evidence, not Docker, shared-nginx, browser, or live-model proof.

## 2026-09-03 Pull Request Packaging Review

The current uncommitted tree was reviewed for dependency order, buildability,
test ownership, shared integration risk, and GitHub Actions entry points. It is
packaged as three stacked local branches: data foundation, service API, and app
integration. Exact per-commit file lists, short messages, validation commands,
branch transitions, PR bases, and merge order are recorded in `pr-plan.md`.

The CI-equivalent `npm run validation` command passed and the Student 4
PowerShell scripts parsed with zero errors. Docker remained unavailable locally
at the time, so GitHub Actions container evidence remained required before PR 3
approval. No commit or push was performed by Copilot.

## 2026-09-04 Release 0 Startup, Compose, CI, and Evidence Review

Reviewer: GitHub Copilot, acting as an AI programming assistant for Liam
Zelmanowski.

### Scope Reviewed

- ASD 2026 project specification and Release 0 brief.
- Root README, `.env.example`, `docker-compose.yml`, and `docker-compose.gpu.yml`.
- Student 4 README, context, requirements, checklist, known issues, prompt log,
  and review record.
- Student 4 source-validation and then-current container lifecycle scripts.
- Student 4 GitHub Actions workflow.
- Student 4 frontend/backend/database source boundaries relevant to startup,
  testing, and AI use.
- Student 1 and Student 2 README, workflow, checklist, and shared-route patterns.

### Findings

| Severity | Finding | Evidence | Required adaptation |
|---|---|---|---|
| Required evidence | Student 4 is implemented in the shared root Compose file and uses the shared Ollama DNS, but the then-current Student 4 convenience startup command was scoped to Student 4 plus the shared frontend. That is not full integrated-app evidence. | `docker-compose.yml` defines `student4-frontend`, `student4-backend`, `student4-database`, `ollama`, and `ollama-model-setup`; `scripts/start-app.ps1` is the full no-service-argument startup path. | Capture final Release 0 evidence from `docker compose up -d --build --wait` or `./scripts/start-app.ps1`, then record health, `docker compose ps`, and the shared page route. |
| Required evidence | Student 4 has strict Ollama request/validation/fallback code, but live successful model output is still not durable evidence. | `student-4/docs/release-0-checklist.md` and `student-4/docs/known-issues.md` still mark live Ollama success as pending; source review shows fallback tests and shared runtime configuration. | Run a real `Generate budget advice` request with `STUDENT4_MODEL` available and save `source: ai` or `source: ai_retry`; keep the forced-unavailable `fallback` evidence separately. |
| Required evidence | The GitHub Actions workflow is present and stronger than a pure build workflow, but no remote successful run has been recorded. | `.github/workflows/student-4.yml` runs source validation, Docker validation, and cleanup; checklist placeholders still show the Actions run URL as pending. | Push through Liam's branch/PR process and capture the successful `student-4.yml` Actions URL or screenshot. |
| Required evidence | The assessed shared development loop has not been finalised for Student 4. This Copilot review is an OBSERVE/ADAPT support activity, but it does not replace the required terminal-runnable two-model loop record. | Root Compose defines `agentic-loop` with distinct `IMPLEMENTER_MODEL` and `REVIEWER_MODEL`; Student 4 checklist and known issues still mark the loop/human decision pending. | Run the shared agentic-loop service with Student 4 context, finalise the record with Liam's keep/change/reject decision, and cite the record in the report. |
| Medium | The then-current Student 4 container smoke used `--no-deps` and expected fallback advice, so it tried to prove container health and forced-fallback behavior in one step. It did not prove live shared Ollama success or full team startup. | The smoke built the shared frontend and three Student 4 images, started them with `--no-deps`, checked 12/24 records, then asserted `/api/insights` returned `fallback`. | Superseded by the later script-alignment adaptation: keep container checks in CI, but use the shared root Compose file directly and keep live-AI and forced-fallback evidence as separate explicit checks. |
| Medium | The then-current container smoke was not reliably Ollama-independent on a developer machine where the shared `ollama` service was already running. The backend could still resolve and call that container even when started with `--no-deps`, which made the fallback-only assertion environment-sensitive. | The 2026-09-04 run built the four targeted images and reported Student 4/shared containers healthy, but exited with `The Ollama-independent smoke test did not return fallback advice.` `docker compose ps` then showed `advanced-software-development-project-ollama-1` up and healthy. | Superseded by the later script-alignment adaptation. |
| Medium team integration | The shared home uses same-origin routes for Students 1, 2, and 4, but Student 3 and 5 cards still point directly at diagnostic localhost ports and shared nginx has no matching proxied routes. This is a group-level integration risk, not a Student 4 defect. | `shared/vue-frontend/src/App.vue` uses `/accommodation/`, `/itinerary/`, `/budget/`, but `http://localhost:5103` and `http://localhost:5105` for Students 3 and 5; shared nginx only proxies accommodation, itinerary, and budget routes. | Ask Students 3 and 5 to add shared routes before final group evidence, or explicitly document that their links are diagnostic until owned fixes land. |
| Low clarification | Student 4 is not adding a separate model runtime and currently defaults to the shared Llama model. The repository has more than two model tags because the shared development loop needs distinct implementer/reviewer models and Student 3 has its own Qwen tag. | `.env.example` lists `OLLAMA_MODELS`, `IMPLEMENTER_MODEL`, `REVIEWER_MODEL`, `APPLICATION_MODEL`, `STUDENT4_MODEL`, and `STUDENT3_MODEL`; `STUDENT4_MODEL` defaults to `llama3.2:3b`. | No Student 4 code change required. Keep `STUDENT4_MODEL` equal to `APPLICATION_MODEL` unless there is a feature-specific reason to diverge. |

### Comparison With Student 1 and Student 2

- Student 4 follows the same integrated-shared-route pattern as Student 1 and
  Student 2: shared page -> feature frontend -> feature backend -> feature
  database API, with Ollama accessed only through the backend.
- Student 4's workflow is closer to Student 2 than Student 1: it runs local
  suites, validates Compose/builds containers, and performs an
  Ollama-independent smoke. Student 1 currently builds containers and tests the
  shared agentic-loop project, but does not start its slice in CI.
- Student 1 and Student 2 also still record evidence gaps for live model/report
  artefacts, GitHub Actions capture, browser screenshots, and finalised
  agentic-loop records. Student 4 is not uniquely behind there, but its Docker
  runtime evidence still needs a successful current run.

### Decision

No runtime code change was made in this review. The immediate adaptation is to
preserve the current shared-resource design, stop treating the scoped Student 4
startup as full Release 0 evidence, and collect the missing full Compose, live
Ollama, Actions, browser, and shared-loop artefacts before the final report.

### Validation During Review

`npm --prefix student-4/frontend run validation` was attempted during this
review. The run confirmed frontend tests 10/10, backend tests 31/31, and
database tests 12/12 before the terminal stopped making visible progress after
the database phase and was terminated. The shared Vue production build was then
run directly and passed. Treat the wrapper command itself as not completed, but
the individual source checks as current passing evidence.

`docker compose config --quiet` passed with Docker 29.7.2 and Docker Compose
v5.5.0. The previous container smoke built `shared-frontend`,
`student4-frontend`, `student4-backend`, and `student4-database`, and the
scoped containers reported healthy. The command then failed at the expected
fallback assertion because the shared `ollama` container was already running
and healthy in the Compose project.

After the failed smoke cleaned up the scoped containers,
the scoped services were restored. Health checks for shared frontend, Student 4
frontend, backend, and database returned 200; `/budget/` served the
application; the containerised database returned 12 budgets and 24 expenses;
and a live `/api/insights` request for `Sydney Weekender` returned `source: ai`.

## 2026-09-04 Student 4 Startup Script Alignment

Liam observed that Student 4-specific start/stop/container validation scripts
conflicted with the Release 0 expectation that the team application runs through
one shared Compose file. The repository comparison showed Student 2 has no such
scripts; Student 1 has only a convenience startup helper, while its workflow
uses direct Compose build commands.

Adaptation applied:

- Removed Student 4-only start, stop, and container-validation scripts.
- Removed the matching `start`, `stop`, and container-validation npm aliases.
- Kept Student 4 source validation aliases for local and CI test/build use.
- Changed Student 4 GitHub Actions to run Docker Compose config/build/start,
  health, seed-count, dashboard, route, and teardown steps directly.
- Updated Student 4 README, requirements, feature plan, PR plan, and the root
  scripts index to direct runtime startup through `./scripts/start-app.ps1` or
  root `docker compose` commands.

This adaptation touched only Student 4-owned files and shared/root integration
files already used by Student 4. Other students' implementation files were not
modified.

Validation after the adaptation: edited-file diagnostics passed, no stale
Student 4 lifecycle-command references remained, the retained source validation
completed successfully, and `docker compose config --quiet` passed.