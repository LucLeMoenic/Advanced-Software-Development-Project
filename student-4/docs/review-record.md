# Student 4 Review Record

## 2026-10-02 - Student 4 ADAPT Route and Live-Grounding Adjudication

**Scope:** Student 4 static UI route construction and frontend tests, the shared
nginx browser-prefix rewrite, Student 4 RAG corpus/retrieval IDs, the loop's
Student 4 citation allowlist, and actual post-refresh model answers. Backend
routes, shared generation prompt, confidence thresholds and loop records were
not changed.

| Finding | Adjudication | Resolution |
|---|---|---|
| Live UI calls returned 404 at `/budget-api/api/budget-check` and `/budget-api/api/budget-guidance`. | Confirmed root cause: `api()` already prefixes `/budget-api`, while shared nginx rewrites that browser prefix to backend `/api/`. The backend's `/api/budget-check` and `/api/budget-guidance` routes are correct. | Changed the two caller paths to `/budget-check` and `/budget-guidance`; corrected all corresponding mocks; existing tests now assert exact browser URLs, reject the doubled URLs, and read the real shared nginx location/rewrite. Updated the browser checklist. The old 404 is preserved as historical evidence; integrated browser replay is pending. |
| Reviewer claimed `budgeting-workflow#2` was a phantom and should be removed from the loop allowlist. | Rejected with source/runtime evidence. The configured `venv-rag` loaded six real chunks. `budgeting-workflow#1` is the first body paragraph; `budgeting-workflow#2` is the second body paragraph: “This knowledge base provides general tracker guidance and has no access to saved expenses or current journey totals...” | Kept the valid `ServiceValidation` allowlist entry. No extra brittle source-parsing consistency test was added; direct index output is recorded in the Student 1 prompt log. |
| The prior live answer claimed 80% or more was overspent; the 80%-100% band is warning. | Confirmed. `DashboardCalculator.Status` uses the unrounded ratio, with `>100` overspent, `>=80` warning, otherwise within budget. The historical loop record is retained unchanged and its reviewer ACCEPT does not establish entailment. | Updated only the compressed `category-budgets#2` paragraph and review date, explicitly stating exactly 80% and exactly 100% are warning, only strictly above 100% is overspent, decisions use the unrounded ratio, and display rounds to two decimals. No shared prompt or threshold change. |
| Did the source clarification make every live answer grounded? | No. Of four required real-model questions, the canonical threshold and held-out conversion paraphrase were grounded. A threshold paraphrase added the contradictory claim “80 percent or more” is warning; the broad conversion answer attached an expense-entry claim to `budgeting-workflow#2`, whose text does not support it. A separate exact-limit question was grounded. | Recorded exact questions, answers, citations, snippets, confidence and assessments in `docs/evidence/release-1/rag-guidance-live-2026-10-02.json`. Do not claim all four passed; bounded live evaluation stopped without changing the shared prompt or selecting substitute questions. |

**Validation:** frontend suite 19/19; Student 4 retrieval 17/17; full shared RAG
79 passed, 19 live-model tests skipped, one Starlette deprecation warning. Five
sequential real `llama3.2:3b` requests ran through the refreshed native RAG and
existing backend. The frontend Docker image build passed and the recreated
`student4-frontend` container reports healthy. Integrated browser replay,
citation expansion, and browser-rendered abstention remain pending.

## 2026-10-02 - Student 4 Shared Loop Fixtures and CI

**Scope:** `ServiceValidation`, validation CLI arguments, shared reviewer prompt
and parser, agentic-loop tests, `scripts/test/student-4.ps1`, Student 4 workflow,
and the Student 4 Release 1 runbook. No UI, database schema, or runtime service
was changed.

| Severity | Finding | Resolution |
|---|---|---|
| Required | Student 4 was rejected as an unsupported loop feature; its MCP path needs a journey label rather than a trip ID, and its HTTP RAG response uses `chunkId` rather than shared retrieval's internal `chunk_id`. | Added Student 4-specific route/body/default handling and exact MCP/RAG validators. MCP verifies the requested journey, result envelope, full totals/categories, supported currency/status boundaries and malformed/error cases. RAG requires known cited answered content with matching `chunkId`; insufficient context remains a failed positive gate. |
| Required | MCP/RAG loop commands did not exercise actual Student 4 CLI option rules. | Added parsing tests for mandatory `--journey-label`, ignored trip-ID rejection, feature-specific option rejection, 1-80 label bounds, fixed backend origin/question, and captured HTTP bodies. |
| Reliability | The reviewer prompt showed alternative verdict/severity values as literal template text and left required sections blank; headings with leading indentation were accepted. | Replaced the template with one complete standalone ACCEPT example, explicitly required column-one headings and one severity value, and tightened parser recognition without weakening the no-ACCEPT-with-required-finding guard. Added nested-heading and enum-echo regressions. |
| Environment | This Windows account cannot create symbolic links (`ERROR_PRIVILEGE_NOT_HELD`), so one existing loop security test cannot run locally. | Left the security test intact. Local loop validation excludes only that test; Linux CI retains it. |

**Validation:** Student 4 frontend 19/19 and production build passed; backend
135/135 (also with all generic and Student 4 AI/MCP/RAG flags false); database
12/12; shared Vue build passed; loop suite 60/60 excluding the Windows-only
symlink privilege case; shared MCP 120/120; shared RAG 79 passed and 19 live
model tests skipped; `docker compose config --quiet` exited 0 with all six mode
variables false. The complete `All` runner reaches the loop stage, then exits
non-zero on the symlink test in this Windows environment.

**Open limits:** no Docker build/start/stop, native MCP/RAG/Ollama process, real
Student 4 loop mode, database non-mutation check, browser, GitHub Actions run,
human source review, or release approval was performed. Offline fixtures do not
prove model grounding or live host-to-container connectivity.

## 2026-10-02 - Student 4 RAG HLD Verification

**Scope:** Current `POST /api/budget-guidance`, `RagClient`, Student 4 corpus and
retrieval tests, canonical shared grounding prompt, and HLD sections 4-6. UI,
live-model behavior, native/container connectivity, loop, CI, and release
acceptance were out of scope.

| Severity | Finding | Resolution |
|---|---|---|
| Required test coverage | Known/paraphrase, unsupported, and misleading-overlap retrieval cases existed, but Student 4 had no injection-shaped query case. | Added one offline retrieval regression combining an injection attempt with a supported threshold question; the relevant category-status chunk remains top-ranked. |
| Verified behavior | The route fixes `student-4`; the client streams a bounded response under a linked 30-second deadline; the API enforces the shared 8 KiB request bound; validation checks exact envelope/citation fields, supported ID/title pairs, markers, finite score/confidence consistency, and exact insufficient abstention. | Matches the inspected HLD contracts. The shared prompt treats question and context as untrusted data. Production code, shared prompt, and thresholds were not changed. |

**Validation:** Retrieval 17/17; focused backend RAG/client tests 29/29; full
Student 4 backend 135/135; shared RAG 79 passed and 19 live-model tests skipped;
`docker compose config --quiet` exited 0. One Starlette deprecation warning
appeared in the shared Python suite.

**Open limits:** Offline retrieval does not prove claim entailment or live-model
resistance to injected instructions. No model, service, container, UI, database,
CI, or human acceptance was exercised.

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