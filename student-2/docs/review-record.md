# Student 2 Review Record

## 2026-09-29 - Pending Change Review and Corrections

Reviewed the local pending changes, not a published PR or its remote CI results.
Scope included the overview producer/backend/UI contract, regression tests,
dependency lockfile, database test portability, optional smoke runner and docs.

### Findings Addressed

- Malformed forecast dates could fail the whole overview: `9999-12-31` followed
	by another date raised `OverflowError` during consecutive-date construction,
	escaping the weather-unavailable fallback. Reproduced with an in-memory
	provider response. Moved the stale-date rejection before date arithmetic;
	three tool-level regressions verify the summary survives upper-bound,
	lower-bound and invalid date responses.
- Removed this session's two Student 2 entries from the Student 1 prompt log,
	following the user's scope clarification. Verified that file now exactly
	matches HEAD; existing Student 1 entries were preserved.

### Verification and Limits

Fresh results: MCP 89, backend 49, database 5, frontend 16 and RAG 62 tests pass
(221 total); 19 live-model tests skip. Production Vite build, Compose config and
editor diagnostics pass. In-memory reproduction of the smoke runner's current
JSON collection filtering selected only its fixture, not the seed record.

No further defect was identified in the inspected paths, but this is not a
guarantee of a defect-free release. The container-to-native networking blocker
remains explicitly deferred. Remote CI, real model results and the data-mutating
smoke/restart path were not verified. The new weather module and supplied Release 1
brief remain untracked and must not be omitted when preparing the change set.
No saved trips, firewall settings or VM networking were changed; no commit,
push or merge was performed.

## 2026-09-29 - Limited Pre-Push Check

Scope: pending Student 2 overview work, test-runner safety/readiness, generated
artifacts and handoff documentation. This is not a full release or security review.

- Integration blocker remains: container-to-native MCP calls time out. The user
	explicitly deferred it; no firewall or VM networking changes were made.
- Generated Vite output and local Playwright artifacts are now ignored, not deleted.
- Database tests use temporary directories and pass on Windows; the runbook's
	obsolete temporary-file failure warning was corrected.
- MCP 86, backend 49, database 5 and frontend 16 tests passed; production build
	and PowerShell syntax checks passed. These do not establish live integration.
- The smoke runner was inspected but not executed against saved trips. CI currently
	uses its default unit-test path and separate basic container smoke commands;
	the expanded `-Smoke` CRUD/restart path still lacks fresh end-to-end evidence.

Human review, remote CI and integrated acceptance remain outstanding. No commit,
push or merge was performed. Networking follow-up is intentionally out of scope.

## 2026-09-27 - Release 1 Defect-Fix Follow-Up

The original six findings below are retained. Their current status:

| Finding | Resolution and evidence |
|---|---|
| 1: Integrated native-service success | Blocked at the VM-to-Windows boundary. Podman's default route matches the private Windows listener, but a direct VM RAG health request times out. Native calls succeed. No Ollama executable on PATH or model listener was found. Requires administrator network investigation and native model setup; no privileged changes attempted. |
| 2: Loop command/context | Fixed. Repository-root discovery handles dotnet run --project; README uses bounded itinerary source. Two new tests preserve context caps. Both actual CLI modes now reach the unavailable Ollama connection after loading context/prompts. No live-model record claimed. |
| 3: Extra MCP arguments | Fixed for the itinerary tool's generated argument model and discovery schema. Regression asserts no database call; native protocol discovery rejects the extra key and still accepts a valid persisted-trip request. Configuration uses pinned MCP 2.2.0 registration internals: retain schema/execution regressions on SDK upgrades. |
| 4: Buffered limits | Fixed in both Python RAG clients with incremental reads. Each oversized-stream regression consumes 16384 bytes of a 102400-byte response, rejects it and closes the stream; the 16000-byte body limit and outer deadlines remain. |
| 5: Grounding evaluation | Partially addressed. Nine real Student 2/3 supported/adversarial cases verify retrieval candidates; opt-in live tests emit answer/source/rubric evidence and require abstention on unsupported questions. Live generation, human entailment checks and independent held-out evaluation remain open. High-scoring unanswerable budget questions demonstrate why thresholds remain provisional. |
| 6: Malformed database JSON | Fixed. The actual requests JSONDecodeError now maps to invalid_dependency_response, covered by regression. |

Fresh suites: backend 35, MCP 26, RAG 31, loop 38: **130 passed**, with nine live
RAG cases explicitly skipped. Updated native services were restarted; the backend
image rebuilt and became healthy. Native MCP protocol and no-context RAG checks
pass. No saved data was mutated, no model output was fabricated, and no commit/push
was made. See the [runbook](release-1-runbook.md) for remaining machine setup and
genuine acceptance gates. Release 1 is still not acceptance-ready.

## 2026-09-27 - Release 1 Implementation Against Documentation

**Verdict:** Substantial implementation alignment, but not Release 1 acceptance-ready. This review compares current code with the [implementation design](release-1-design.md), [runbook](release-1-runbook.md), [feature requirements](requirements.md), and [Release 1 brief](../../docs/Project_Specifications/Release_1_brief.md). It does not assign marks or certify other students' features. No runtime code was changed.

### Verified Findings

1. **Blocking acceptance: neither new interaction succeeds through the integrated backend.** Fresh read-only POSTs to `http://localhost:5100/itinerary-api/trips/10/mcp-summary` and `/itinerary-advice` both returned HTTP 504 with `dependency_timeout`. The latter used the documented budget question. The brief requires successful frontend/backend MCP and generated, cited RAG demonstrations; native-only SDK success and an insufficient-context response do not satisfy those gates. The runbook acknowledges the connectivity/model setup problem accurately. Resolve private host routing and native model setup, then capture both success paths and live loop evidence.

2. **High: documented loop execution cannot reach validation.** The [MCP example](../../ai-services/agentic-loop/README.md#L65), run from the repository root with explicit distinct model tags, failed with `Context file does not exist: student-2/docs/release-1-design.md`. [Workspace resolution](../../ai-services/agentic-loop/AgenticLoopApplication.cs#L156) relies on the process working directory, which does not resolve that path in this `dotnet run --project` invocation. Repeating with `--workspace` set to the repository root failed with `Context file exceeds 16000 bytes`. The [per-file cap](../../ai-services/agentic-loop/AgenticLoopApplication.cs#L364) therefore also rejects the example's chosen document. Use an explicit supported workspace and bounded context fixtures; test the documented CLI commands, not only loop internals. Do not remove the safety cap simply to fit this document.

3. **Medium: the MCP top-level input boundary is not strict.** The [registered tool](../../ai-services/mcp-server/tools/itinerary.py#L56) forbids extra keys inside `params`, but not at the SDK argument-envelope level. An in-process call through the installed official MCP server with `{"params":{"trip_id":12},"url":"http://unexpected"}` succeeded and made one mocked database read. The design specifically requires this SDK-dependent case to be checked; [current tests](../../ai-services/mcp-server/tests/test_itinerary_tools.py#L47) cover only nested extras. Reject unknown top-level keys before the tool executes and add protocol coverage. The extra URL was ignored, not followed: this is not evidence of URL injection, and the browser backend currently sends only fixed arguments.

4. **Medium: response-size checks are post-buffer checks, not memory bounds.** [RAG generation](../../ai-services/rag-server/generation.py#L81) awaits a fully buffered HTTP response before checking 16000 bytes; the [backend RAG adapter](../backend/ai_clients.py#L142) uses the same pattern. A synthetic HTTP stream supplied 102400 bytes and all were consumed before generation raised its controlled 502. This does not meet the design's bounded-upstream-output intent, although the runbook/shared README disclose the limitation. Enforce the byte limit while reading and test early stream closure; retain the outer time deadlines.

5. **Medium acceptance gap: calibration and grounding validation are incomplete.** The design requires labelled evaluation across available feature corpora, irrelevant keyword overlap, adversarial questions, and held-out claim-to-source checks. The [retrieval fixture test](../../ai-services/rag-server/tests/test_retrieval.py#L79) evaluates only Student 2's twelve questions; the four irrelevant examples do not exercise misleading itinerary-keyword overlap. Existing Student 3 fixture tests are not a calibration of the real shared corpus. [Generation tests](../../ai-services/rag-server/tests/test_query.py#L21) use test doubles and validate structure/references, not actual model entailment. Treat confidence thresholds as provisional and do not equate valid citation IDs with supported claims.

6. **Low: malformed database JSON receives the wrong public error category.** A mocked database HTTP 200 whose JSON parser raised `requests.exceptions.JSONDecodeError` produced `dependency_unavailable` from the itinerary tool. That exception is caught by [RequestException](../../ai-services/mcp-server/tools/itinerary.py#L67) before the invalid-data branch. The backend consequently maps it to 503 rather than the design's `invalid_dependency_response`/502. Separate JSON decoding errors from network failures and add a regression for an actual requests JSON-decoding exception.

### Design Coverage

| Slice | Assessment |
|---|---|
| Configuration and adapters | Largely aligned: strict flags, capabilities without probes, disabled zero-call tests, fixed tool/feature routes, response validation and controlled dependency errors. Size limiting and one error mapping need correction. |
| MCP vertical slice | Read-only database ownership, privacy filtering, inclusive day coverage and decimal allocation implemented. Live container path, top-level argument rejection, discovery/handshake/cleanup coverage remain open. |
| RAG foundation and advice | Six feature documents, feature isolation, filtered retrieval, constrained generation, citation assembly and abstention implemented. Live generation, cross-feature calibration and adversarial/semantic grounding checks remain open. |
| Frontend | Summary/advice controls, safe text rendering, disabled/busy/error states and deletion-race coverage implemented. Prior viewport results are documented; keyboard/focus and broader navigation races were not independently browser-tested in this review. |
| Host deployment and CI | Native-only AI topology and Student 2 CI disable flags are present; gateway integration was previously verified. Current live AI requests fail. A successful remote workflow for the final commit is not evidenced here. |
| Assessment validation | Separate native loop modes exist but documented invocation fails. Genuine model outputs, human finalisation, full group behavior, contribution commits and report/showcase evidence remain pending. |

### Verification and Scope

Fresh suites: backend 34/34, MCP 24/24, RAG 21/21, frontend 9/9, shared loop 36/36: **124 passed**. The five database tests were not rerun; their prior Linux pass and Windows temporary-file limitation remain historical evidence. Python probes used the explicit portable Python 3.11.9 runtime, not a claimed editor-selected interpreter.

Additional checks: two real gateway HTTP outcomes; two expected CLI failure reproductions; installed-SDK extra-argument and malformed-JSON probes; a synthetic oversized HTTP stream. These probes did not mutate saved trips or invoke a model. Remote GitHub Actions, live model quality, all other features and firewall configuration were not independently validated. Review entries are the only repository edits for this request.

## 2026-09-01 - Release 0 Readiness Review

**Scope:** Student 2 frontend, backend, database API, SQLite seed data, shared navigation, root Docker configuration, Student 2 CI, development-agent workflow evidence, planning artefacts, and Release 0 report/showcase requirements.

### Findings

| Severity | Finding | Status |
|---|---|---|
| Blocking | Student 2 initially had no individual requirements/backlog contribution, feature plan, risk plan, conceptual/ERD/logical/physical data designs, architecture diagrams, contribution log, screenshots, known-issues record, attendance evidence, or showcase-video evidence. | Planning/design documents, contribution-log structure, browser checklist, and known issues are now present. Shared-backlog linkage, screenshots, attendance, and showcase evidence remain open. |
| Blocking | No finalised shared agentic-loop execution record exists. The `agentTrace` returned by itinerary creation is application narration and is not evidence of the required two-model development Plan/Act/Observe/Adapt workflow. | Open |
| Blocking | The Student 2 workflow exists, but no successful GitHub Actions run or captured Compose execution evidence is stored. | Selective local commits now exist on `LLM/release-0-itinerary-planner`; push, PR, Actions, and clean Compose evidence remain open. |
| Required | Trip creation persisted the trip before all generated stops, and whole-itinerary regeneration deleted existing stops before replacement persistence succeeded. | Resolved with database-owned atomic create/replace operations and regression tests. |
| Required | AI validation accepted an incomplete stop array without enforcing two stops per day or complete day coverage. | Resolved with exact full-itinerary and single-stop regeneration contracts plus focused tests. |
| Required | Backend stop CRUD forwarded payloads without public-boundary validation, and frontend behavior had no automated tests. | Resolved for primary behavior with backend validation and two jsdom frontend tests; broader edge coverage remains useful. |
| Required | The frontend loaded HTMX from an external CDN despite having a local JavaScript implementation. | Resolved by removing HTMX and loading the local ES module directly. |
| Required | The backend and database accept a stop day from 1-31 without checking it against the parent trip. A two-day trip can therefore persist a day-31 stop through the normal add/edit endpoints. | Open |
| Required | Updating a trip can shorten its date range without checking existing stops, leaving persisted stops outside the revised trip duration. | Open |
| Required | The backend and database expose trip update endpoints, but the frontend has no trip-edit control or request path. The Release 0 checklist's claim that trip CRUD is implemented through the frontend is therefore inaccurate. | Open |
| Required | Updating a stop to reference a missing trip can raise an uncaught SQLite foreign-key exception and return HTTP 500 instead of a controlled validation/not-found response. | Open |
| Required | Automated coverage is too narrow to support the checklist's broad completion claim. The two frontend tests cover only list/create; focused tests do not cover frontend update/delete/regeneration, trip shortening, parent-relative stop days, stop-update foreign keys, or explicit cascade-delete assertions. | Open |
| Complete | Frontend, backend, and database services, health endpoints, Dockerfiles, root service wiring, shared `/itinerary/` route, shared theme alignment, SQLite ownership boundary, Ollama generation/fallback, and the versioned application prompt exist. Fresh-database tests assert 10 trips and 20 stops. Stop CRUD and backend/database trip CRUD exist, but frontend trip update remains incomplete. | Implemented with open defects and broader evidence still required |

### Source-Only Follow-Up Review

At the user's request, this follow-up reviewed documentation and source code only. No commands, tests, builds, containers, or live services were run. The findings above are grounded in the checked-in handlers, frontend event wiring, and test cases; runtime claims from earlier records were not independently revalidated.

The release checklist and known-issues record also conflict: the checklist says push and successful Actions evidence are pending, while known issues says the branch is pushed and the latest Student 2 Actions run failed during backend test collection. Reconcile both documents against the actual remote run before using either as report evidence.

### Current Evidence

All seven manually started shared/Student 1/Student 2 containers are running locally, and port `5100` is bound to the shared frontend. This confirms current process state only; it is not a recorded clean Compose deployment because the local Docker installation lacks the Compose plugin. No new functional tests were run during this review at the user's request.

**Verdict:** Student 2 is not Release 0 submission-ready. In addition to the existing CI, Compose, agentic-loop, browser, and report evidence gaps, frontend trip update and parent-relative stop/date integrity must be fixed and covered by focused tests before the implementation can accurately claim complete CRUD.

## 2026-09-02 - Release 0 Criteria Reassessment

**Scope:** Current Student 2 implementation and checked-in evidence assessed against all ten Release 0 marking criteria.

### Findings

| Severity | Criterion | Finding |
|---|---|---|
| Blocking | 4, 5 | No finalised Student 2 Plan/Act/Observe/Adapt runner record exists. The itinerary response's `agentTrace` is application narration and does not demonstrate the assessed two-model development workflow or human decision. |
| Blocking | 6, 9 | No successful `student-2.yml` run URL or screenshot is recorded. The checklist says push/PR are pending while `known-issues.md` says the branch was pushed and CI failed, so the evidence records must be reconciled against GitHub. |
| Blocking | 7, 9 | No clean shared `docker compose up --build` execution, service-health capture, routing capture, or persistence-after-restart evidence is recorded. Manually started containers do not prove the required Compose workflow. |
| Blocking | 9, 10 | Integrated screenshots, attendance checkpoint, published showcase URL, and Student 2 demonstration timestamp are absent. These cannot receive implementation credit without durable report/showcase evidence. |
| Required | 8 | Full trip CRUD is not available through the frontend: trips can be created, opened, and deleted, but there is no trip-edit control or `PUT /trips/{id}` browser path. |
| Required | 8 | Normal stop create/update validates day only against 1-31, not the parent trip duration. A short trip can therefore contain an out-of-range stop. |
| Required | 8 | Updating a trip can shorten its date range without rejecting or reconciling existing stops that then fall outside the trip. |
| Required | 8 | Updating a stop to a nonexistent `tripId` can raise an uncaught SQLite foreign-key error and return HTTP 500 rather than a controlled 400/404 response. |
| Required | 2, 8 | Automated coverage does not exercise frontend trip update, stop update/delete/regeneration, whole-trip regeneration, parent-relative stop dates, trip shortening, failed foreign-key updates, or an explicit cascade-delete assertion. |
| Evidence gap | 3 | Ollama integration, strict model-output validation, and deterministic fallback exist in source, but no genuine frontend-triggered AI success or forced-fallback capture identifies the exact approved model tag in use. |
| Evidence gap | 1, 9 | Requirements are documented locally but are not yet linked from the shared sprint backlog/report plan. GitHub commit/PR evidence and the report-facing repository/integration evidence remain incomplete. |

### Criterion Assessment

| No. | Criterion | Current assessment |
|---:|---|---|
| 1 | Project setup | Partially evidenced: structure, routing, seed data, Dockerfiles, workflow, and shared Ollama wiring exist; remote and integrated execution evidence is incomplete. |
| 2 | Service implementation | Implemented in source with health endpoints and HTTP service boundaries; operational integrated execution is not yet evidenced. |
| 3 | AI-Mode integration | Implemented in source with an approved default model and fallback; live integrated proof is pending. |
| 4 | Agentic AI workflow | Not evidenced for Student 2. |
| 5 | Prompt engineering and context | Application prompt and AI activity records exist; the genuine loop record, model roles, selected context, validation, and human decision evidence are incomplete. |
| 6 | DevOps and GitHub Actions | Workflow is implemented; successful remote execution evidence is missing. |
| 7 | Docker Compose integration | Student 2 services are wired into the shared file; successful clean Compose execution evidence is missing. |
| 8 | Working software | Partial: create/read/delete trips and stop CRUD/regeneration exist, but frontend trip update and data-integrity handling are incomplete. |
| 9 | Technical report | In progress; substantial execution, screenshot, commit/PR, attendance, and showcase evidence remains. |
| 10 | Project demonstration | Not evidenced. |

**Verdict:** Not Release 0 submission-ready. Fix the four Criterion 8 implementation defects first, then capture the agentic-loop, CI, Compose, browser, report, attendance, and showcase evidence needed to turn source-level claims into assessable proof.

### Validation Note

Independent execution on 2026-09-02 was blocked by the available shell environment: Python was not on `PATH`, frontend test dependencies were not installed (`vitest` unavailable), and the installed Docker Compose command rejected `config --quiet`. The source-level defects and missing evidence above were therefore not reclassified as runtime-tested findings. VS Code reported no diagnostics in the Student 2 workflow or root Compose file.

### Feature-Fix Resolution

The four Criterion 8 implementation defects from this reassessment were resolved on 2026-09-02:

- The frontend now edits persisted trip details through `PUT /api/trips/{id}` and reloads the complete saved itinerary.
- Backend and database APIs reject stop days outside the parent trip duration; the stop dialog mirrors the current duration.
- Trip updates reject date ranges that would exclude existing stops, preserving the prior trip and stops.
- Stop updates targeting a missing trip return a controlled `404` without modifying the existing stop.
- Focused coverage now includes frontend trip update, stop edit/regeneration/removal, whole-itinerary regeneration, parent-relative stop days, trip shortening, missing-parent updates, and cascade deletion.

Validation used disposable language-runtime containers because the host shell lacked Python/Vitest: database 5/5, backend 8/8, and frontend 4/4 tests pass. Criteria 4-7 and 9-10 evidence gaps remain open and are not resolved by these feature changes.

## 2026-09-02 - Post-Implementation Release 0 Review

**Scope:** Fresh review of Student 2 source, automated tests, current Compose runtime, shared integration, CI, and checked-in assessment evidence against the ten Release 0 criteria. This section supersedes earlier current-status claims but preserves them as historical review context.

### Verified Findings

| Severity | Criterion | Finding |
|---|---|---|
| Blocking evidence | 4, 5 | No finalised Student 2 two-model Plan/Act/Observe/Adapt record exists under `docs/agentic-loop-records/`. The application `agentTrace` is not development-loop evidence. |
| Blocking evidence | 6, 9, 10 | No successful Student 2 Actions URL, technical report artifact, integrated screenshot set, attendance checkpoint, published showcase URL, or Student 2 video timestamp is checked in. |
| High integration risk | 1, 7 | Student 2 is integrated and healthy, but the group Compose application still lacks complete backend/database sets for Students 4 and 5. The required integrated five-feature application is therefore not evidenced as complete. |
| High compliance risk | 1 | The Release 0 brief explicitly requests a shared HTMX index, while the shared entry point is Vue. Student 2's README also still describes its frontend as HTMX although its implementation is plain HTML/CSS/JavaScript. Confirm tutor acceptance or align implementation and documentation. |
| Required fix | 8 | Stop update accepts a client-supplied `tripId` and the database updates `trip_id`, allowing an existing stop to be moved to another valid trip. The requirement describes stop updates as day/activity/notes changes, so ownership should be derived from the stored stop and remain immutable. |
| Required fix | 8 | The stop form submits `sortOrder: 99` for both create and edit. Editing an existing stop therefore silently moves it to the end instead of preserving its stored order. |
| Required fix | 2, 8 | API failures open the custom error dialog but do not replace stale live-region text such as “Planning your itinerary...” or “Regenerating the itinerary...”, producing contradictory status feedback. |
| Test gap | 2, 3, 7 | CI validates isolated mocked suites, Compose syntax, and image builds, but does not start the stack or smoke-test shared proxy, backend/database HTTP boundaries, persistence, or controlled Ollama success/fallback behavior. |
| Documentation risk | 6, 7, 9 | `release-0-checklist.md`, `known-issues.md`, `contribution-log.md`, and earlier review sections contain stale or conflicting branch, Compose, test-count, push, and CI claims. Reconcile them before report use. |

### Criterion Assessment

| No. | Criterion | Repository and runtime support |
|---:|---|---|
| 1 | Project setup | Partial: Student 2 structure, seeded data, workflow, shared route, and model configuration exist; shared HTMX compliance and complete five-feature integration remain unresolved. |
| 2 | Service implementation | Supported for Student 2 locally: frontend, backend, and database services are healthy and integrated; error-state consistency and CI integration coverage remain open. |
| 3 | AI-Mode integration | Partial: approved-model Ollama invocation, strict output validation, and fallback exist in source; genuine frontend-triggered AI success evidence is absent. |
| 4 | Agentic AI workflow | Unsupported by evidence: shared runner assets exist but no finalised Student 2 execution record exists. |
| 5 | Prompt engineering and context | Partial: versioned application prompt and AI logs exist; assessed two-model context, review, adaptation, and human-decision record is absent. |
| 6 | DevOps and GitHub Actions | Partial: the workflow runs all isolated suites, validates Compose, and builds images; no successful remote run is recorded and no runtime smoke test exists. |
| 7 | Docker Compose integration | Partial: the live Student 2 path is healthy through shared Compose routing, but complete group integration and durable evidence are incomplete. |
| 8 | Working software | Substantially implemented: browser/backend/database CRUD and generation workflows run, with stop ownership, ordering, and stale-error-state defects still requiring correction. |
| 9 | Technical report | Partial: extensive feature documentation exists, but the report and required CI, AI, browser, attendance, and execution evidence are incomplete. |
| 10 | Project demonstration | Unsupported by evidence: no published video, attendance record, or Student 2 timestamp is present. |

### Validation Evidence

- Frontend Vitest: 6/6 passed in Node 22.
- Backend pytest: 8/8 passed in Python 3.11.
- Database pytest: 5/5 passed in Python 3.11.
- `docker compose config --quiet`: passed.
- `shared-frontend`, `student2-frontend`, `student2-backend`, `student2-database`, and `ollama`: running and healthy.
- Shared home, `/itinerary/`, and `/itinerary-api/trips`: HTTP 200.
- Current persisted development data: 11 trips and 11 stops; fresh initialization source creates 10 trips and 20 stops.

**Verdict:** Student 2 is functionally substantial and locally integrated, but not yet Release 0 submission-ready. Fix the three implementation defects, add an integrated CI smoke test, reconcile stale documentation, and capture the missing AI, agentic-loop, Actions, report, attendance, and showcase evidence.

## 2026-09-02 - Required Fix Resolution

**Scope:** Resolution of the implementation, CI, and documentation findings from the post-implementation review.

| Previous finding | Resolution | Evidence |
|---|---|---|
| Client-controlled stop ownership | Resolved. Backend and database update handlers derive `tripId` from the stored stop and never update `trip_id`. | Backend ownership regression passes; database forged-`tripId` regression passes. |
| Stop edits overwrite ordering | Resolved. The frontend preserves stored `sortOrder`, and both APIs derive it from the stored stop rather than trusting an update payload; new stops receive the next order within their selected day. | Frontend request-payload and API forged-order regressions pass. |
| API errors leave stale progress text | Resolved. Opening an error dialog clears the live status region first. | Frontend failed-planning regression passes. |
| CI has no runtime integration check | Resolved in workflow. CI starts the three Student 2 services without Ollama dependencies, waits for health, and verifies backend-to-database retrieval of at least 10 trips. | Exact Compose startup and smoke commands pass locally with 11 trips. Remote Actions evidence remains pending. |
| Current documents conflict | Resolved for current-status documents. Historical review entries remain unchanged as dated evidence. | README, checklist, feature/risk plans, known issues, contribution log, and prompt log use the current branch and validation state. |

Validation after the fixes: frontend 6/6, backend 10/10, database 5/5; Compose configuration valid; Student 2 frontend, backend, and database healthy; backend trip retrieval returned 11 records. A genuine shared-route request produced trip 14 in `ai` mode with two stops on each day; the preceding invalid model shape produced trip 13 in deterministic `fallback` mode with complete coverage.

**Current verdict:** The identified Student 2 implementation defects and local AI execution requirement are resolved. Remaining blockers are evidence or team-owned work: a finalised human-controlled two-model loop record, a successful remote Actions run, clean-checkout/browser/report evidence, complete Student 4/5 service integration, and retained tutor acceptance of the shared Vue frontend.