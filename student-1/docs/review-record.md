# Review Record

## 2026-09-01 - Student 2 Release 0 Readiness Review

**Scope:** Student 2 frontend, backend, database API, SQLite seed data, shared navigation, root Docker configuration, Student 2 CI, development-agent workflow evidence, planning artefacts, and Release 0 report/showcase requirements.

### Findings

| Severity | Finding | Status |
|---|---|---|
| Blocking | Student 2 initially had no individual requirements/backlog contribution, feature plan, risk plan, conceptual/ERD/logical/physical data designs, architecture diagrams, contribution log, screenshots, known-issues record, attendance evidence, or showcase-video evidence. | Planning/design documents, contribution-log structure, browser checklist, and known issues are now present. Shared-backlog linkage, screenshots, attendance, and showcase evidence remain open. |
| Blocking | No finalised shared agentic-loop execution record exists. The `agentTrace` returned by itinerary creation is application narration and is not evidence of the required two-model development Plan/Act/Observe/Adapt workflow. | Open |
| Blocking | The Student 2 workflow exists, but no successful GitHub Actions run or captured Compose execution evidence is stored. | Selective local commits now exist on `student-2/release-0-itinerary-planner`; push, PR, Actions, and clean Compose evidence remain open. |
| Required | Trip creation persisted the trip before all generated stops, and whole-itinerary regeneration deleted existing stops before replacement persistence succeeded. | Resolved with database-owned atomic create/replace operations and regression tests. |
| Required | AI validation accepted an incomplete stop array without enforcing two stops per day or complete day coverage. | Resolved with exact full-itinerary and single-stop regeneration contracts plus focused tests. |
| Required | Backend stop CRUD forwarded payloads without public-boundary validation, and frontend behavior had no automated tests. | Resolved for primary behavior with backend validation and two jsdom frontend tests; broader edge coverage remains useful. |
| Required | The frontend loaded HTMX from an external CDN despite having a local JavaScript implementation. | Resolved by removing HTMX and loading the local ES module directly. |
| Complete | Frontend, backend, and database services, health endpoints, Dockerfiles, root service wiring, shared `/itinerary/` route, shared theme alignment, SQLite ownership boundary, trip/stop CRUD, Ollama generation/fallback, and the versioned application prompt exist. Fresh-database tests assert 10 trips and 20 stops. | Implemented; broader evidence still required |

### Current Evidence

All seven manually started shared/Student 1/Student 2 containers are running locally, and port `5100` is bound to the shared frontend. This confirms current process state only; it is not a recorded clean Compose deployment because the local Docker installation lacks the Compose plugin. No new functional tests were run during this review at the user's request.

**Verdict:** Student 2's implementation and planning baseline are substantially complete, but it is not Release 0 submission-ready. Commit through the team's normal branch/PR process, capture a successful Student 2 Actions run and clean Compose execution, run and finalise the shared agentic workflow, and produce the remaining browser/report/showcase evidence.

## 2026-09-01 - AI Ranking Explanation Quality Review

**Scope:** Application ranking prompt, structured Ollama output schema, backend reason validation, and focused contract tests.

**Finding:** The previous example and 5-10 word limit encouraged the model to restate a single feature, such as "offers metro access," without explaining why that feature helps the traveller. The validator also accepted very short reasons and identical explanations for different accommodations.

**Resolution:** Reasons must now contain 8-18 words, explain the traveller benefit of one or two supplied facts, connect evidence to a stated preference when supported, and use a distinct fact or benefit for each candidate. The backend rejects reasons outside the word/character limits and rejects case-insensitive duplicates. The no-invention and untrusted-input rules remain unchanged.

**Status:** Focused ranking-client tests cover valid benefit-led reasons, prompt instructions, short and overlong output, exact duplicates, malformed output, and the existing ID/rank/security contract.

## 2026-09-01 - Accommodation Frontend Product Redesign Review

**Scope:** Accommodation application shell, trip search form, ranking selection, recommendation results, saved-search CRUD, loading/empty/error states, responsive behavior, keyboard flow, and component coverage.

**Findings:** The existing linear page made saved searches feel detached from the active task, compressed unrelated inputs into one dense grid, and exposed implementation language such as "programmatic" and "fallback" directly to travellers. The AI checkbox did not compare the two ranking choices clearly, the initial results area had no orientation state, and saved-search rows lost important destination context after rename. The redesign review also found weak budget accessible names, ineffective rank-one styling, silent history retries, non-focusing in-page links, and ambiguous rank semantics for screen readers.

**Resolution:** Reframed the page as a search-first product workspace with one bounded search surface and one results/history surface. Grouped stay, budget, and ranking fields semantically; replaced the checkbox with explicit Budget match and AI-assisted match radio choices; added a purposeful initial state; restored destination metadata; and made results, explanations, modes, actions, notices, and history states visually consistent. Follow-up corrections added full accessible budget names, live retry announcements, usable focus targets, explicit screen-reader rank text, stronger focus contrast, and clearer separation of destructive actions.

**Status:** The redesign preserves existing routes, API calls, payloads, validation, persistence, rename/delete behavior, focus movement, and backend ranking decisions. Automated frontend tests and the strict production build pass. Manual browser evidence at 320px, 768px, and 1280px remains open.

## 2026-09-01 - UI Simplification and Product Design Review

**Scope:** Shared feature entry page and the accommodation search, result, status, and history interfaces at desktop, tablet, and mobile widths.

**Findings:** The interface relied on oversized headings, repeated eyebrow labels, pill badges, rounded nested cards, shadows, a gradient feature card, and decorative rank/empty-state circles. These patterns gave primary, secondary, and tertiary information similar visual weight. The accommodation page also lacked an obvious path back to the shared feature list, while history cards required unnecessary lateral scanning.

**Resolution:** Reduced the heading scale and page width, removed shadows and gradients, retained one subtle boundary around the primary search task, and converted results and history to compact divider-led rows. Ranking modes and counts are now quiet metadata rather than pills, controls share a restrained radius, notices use a simple left rule, and the accommodation page includes a clear text link back to all features. The shared entry page now uses the same typography, spacing, row treatment, and interaction language.

## 2026-09-01 - GPU AI Timeout Regression Review

**Scope:** Shared Ollama setup job, NVIDIA Compose override, backend Ollama timeout, model lifecycle, and live AI recommendation behavior.

**Finding:** The consolidated `ollama-model-setup` job checked and downloaded model tags but no longer preloaded the application model. After an Ollama restart, `llama3.2:3b` still offloaded all 29 layers to the RTX 2000 Ada GPU, but initialization exceeded the backend's required 12-second timeout. Client cancellation then aborted the load, leaving no warm model for the next request and causing repeated fallback responses.

**Resolution:** The shared setup job now ensures `APPLICATION_MODEL` is installed and runs one bounded preload with a 30-minute keep-alive before dependent services start. The 12-second backend timeout, deterministic fallback, shared runtime, and GPU override remain unchanged.

## 2026-09-01 - Shared Entry Page Visual Review

**Scope:** Shared Vue landing component, global stylesheet, HTML title/description, navigation behavior, responsive layout, focus treatment, and consistency with the accommodation UI.

**Finding:** The entry page used unrelated hard-coded greys, a narrow plain list, and generic browser metadata, so it did not visually belong to the same integrated application as the accommodation feature.

**Resolution:** Applied the accommodation interface's colour tokens, typography scale, panel/card treatment, spacing, focus colour, responsive width, and reduced-motion behavior. Existing destinations remain unchanged and unknown team features retain neutral labels rather than invented names.

## 2026-09-01 - Shared Ollama Topology Review

**Scope:** Root Compose Ollama runtime, model initialisation, Student 1 backend, agentic loop, GPU override, and shared configuration documentation.

**Finding:** Runtime traffic already used one `ollama` service, but separate `ollama-application-model` and `ollama-agentic-models` setup containers made the topology look application-owned and would encourage each feature to add another setup service.

**Resolution:** Replaced both with one neutral `ollama-model-setup` job driven by the shared `OLLAMA_MODELS` list. The job exits after ensuring models exist; the only long-running model server is `ollama`, and all consumers use Compose DNS `http://ollama:11434`.

## 2026-09-01 - AI-Only Preferences Review

**Scope:** Search-form preference visibility, request payload behavior, focused component coverage, and privacy requirements.

**Finding:** The preferences field remained visible for programmatic searches even though deterministic ranking does not use it. This was misleading and could persist text that had no effect.

**Resolution:** Preferences now render only after AI is selected. Programmatic submissions always send an empty preference value, including when AI is unticked after text was entered. Frontend tests cover hidden, revealed, re-hidden, and request-payload behavior.

## 2026-09-01 - Opt-in AI Ranking Review

**Scope:** Backend ranking selection, database ranking-mode persistence, Vue AI control and labels, responsive layout, migration, and focused automated tests.

**Goal:** Make AI recommendation explicitly opt-in without removing useful default ranking or mislabelling programmatic results as AI fallback.

### Findings

| Severity | Finding | Resolution |
|---|---|---|
| Required | Existing requests always reached Ollama, so users could not choose the faster deterministic path. | Added nullable backend input with explicit-true semantics and an unchecked frontend control. |
| Required | The database constraint represented only `ai` and `fallback`, which would misclassify intentional non-AI ranking. | Added `programmatic` across validation, EF configuration, migration, API types, and UI labels. |
| Required | The first frontend history label used a nested ternary and the checkbox's nine-column span could create implicit columns at tablet width. | Replaced the ternary with a label helper and made the checkbox span the responsive grid width. |
| Required | Existing UI tests could render mocked AI/fallback responses without proving the corresponding opt-in request. | Added request-body assertions for `useAi: false` and `useAi: true`, programmatic rendering coverage, and explicit opt-in before fallback coverage. |

### Status

**Implementation verdict:** The opt-in behavior is complete across code, migration, and the integrated runtime. Backend tests pass 67/67, database tests pass 20/20, frontend tests pass 8/8, the frontend production build passes, and EF reports no pending model changes. Rebuilt live requests returned `programmatic` with no notice by default and `ai` with six sentence-form reasons after opt-in. Browser screenshots remain required for final demonstration evidence.

## 2026-08-31 - Chunk 7 Shared Integration and CI Review

**Scope:** Shared Vue entry page, shared nginx boundary, root Compose, `student-1.yml`, root setup instructions, and current Chunk 6 worktree changes.

**Goal:** Complete Chunk 7 on the current branch without overwriting the still-running Chunk 6 frontend work.

### Findings

| Severity | Finding | Resolution |
|---|---|---|
| Required | The unified Vue page was still boilerplate and had no Accommodation Recommender link or `/accommodation` route. | Added the named feature entry and a shared nginx reverse-proxy route to the healthy Student 1 frontend. |
| Required | The shared frontend had no health check or dependency ordering for the proxied feature. | Added `/health`, Compose health configuration, and a healthy Student 1 frontend dependency. |
| Required | Student 1 CI built the frontend but did not run its component tests or explicit .NET restores. | Added frontend tests, explicit restores, `--no-restore` test execution, and shared integration image validation. |
| Required | Root instructions described template infrastructure and omitted exact integrated model, test, health, persistence, and stop commands. | Replaced the stale setup section with commands matching the implemented Compose stack. |
| Constraint | Chunk 6 had uncommitted changes in the Student 1 frontend and tracked database. | Left those files untouched and limited Chunk 7 edits to independent integration surfaces and required records. |

### Status

**Implementation verdict:** Chunk 7 code and documentation are complete. Local builds, tests, Compose validation, integrated route/assets/API checks, service health, and SQLite restart persistence pass. Manual browser demonstration and GitHub Actions run evidence remain pending.

## 2026-08-31 - Release 0 Documentation and AI Infrastructure Audit

**Scope:** `Project_Specifications.md`, Release 0 brief, accommodation feature docs, feature README, three Dockerfiles, root Compose, unified home page, and `student-1.yml`.

**Goal:** Determine each member's full-mark obligations and make Mitchell's requirements, implementation sequence, AI architecture, and evidence plan specific and testable.

### Findings

| Severity | Finding | Resolution |
|---|---|---|
| Blocking | The docs originally conflated the application's recommendation flow with the required Plan -> Act -> Observe -> Adapt development loop. | Separated the one-model application request from a two-model local development loop with implementer and reviewer roles. |
| Blocking | Existing backend/database Dockerfiles do not implement the documented ASP.NET Core services; the database container only sleeps. | Documented as incomplete and made replacement a Phase 1 exit gate. No false completion claim remains. |
| Blocking | `student-1.yml` echoes a placeholder rather than building or validating assigned services. | Added explicit CI requirements and evidence gate; implementation remains open. |
| Required | Requirements were subjective (`reasonable time`, `degrade gracefully`) and lacked IDs, boundaries, statuses, schemas, and tests. | Replaced with measurable FR/NFR/EV requirements, API contracts, data constraints, timeouts, fallback, and traceability. |
| Required | The plan listed components but lacked dependency gates, test cases, evidence, and shared-contract decisions. | Replaced with vertical phases, dependencies, tests, evidence, and exit gates. |
| Required | The development prompt library named files that did not exist and did not enforce independent review. | Added versioned implementer and reviewer prompts with untrusted-context rules and structured outputs. |
| Required | The first rewrite incorrectly placed the application ranking prompt in the development-lifecycle prompt library. | Removed it. The ranking prompt is product functionality and will live under `backend/Prompts/` with backend contract tests. |
| Required | Current shared Compose/home-page paths point to template `student-1/`, while the feature folder has a misspelled non-standard name. | Added a Phase 0 team decision and a critical integration risk; no unilateral rename was made. |
| Required | Amadeus added credentials, rate limits, and demo dependency without being required to prove Release 0. | Seeded catalogue is now the mandatory first path; provider integration is deferred until all required gates pass. |
| Required | Evidence checklist used unchecked claims rather than status plus evidence locations. | Rebuilt it as individual/group obligations and criterion/scenario evidence matrices. |

### Design Chunk Assessment

| Chunk | Goal alignment | Complexity result |
|---|---|---|
| Vue frontend, ASP.NET orchestration API, ASP.NET database API | Direct: required three-service student feature using the team's permitted stack. | Proportionate because separate services are assessment constraints. |
| EF Core/SQLite ownership behind HTTP | Direct: required database microservice and cross-service boundary. | Proportionate; direct backend SQLite access would violate the brief. |
| One application ranking model | Direct: functional accommodation recommendation and clarified AI path. | Proportionate. |
| Two-model local development loop | Direct: clarified agentic-loop assessment requirement. | Proportionate only with one shared Ollama runtime and bounded runner. |
| Seeded catalogue | Direct: candidates plus 10-record requirement. | Simpler and safer than a live provider for Release 0. |
| Amadeus | Partial: useful real-world data but not required for the core recommender or rubric. | Deferred as over-scoped until mandatory integration/evidence is complete. |
| Search result snapshots | Direct: reliable history despite catalogue changes. | Proportionate at classroom scale; avoids a third relation/table. |

### Human Correction During Review

The first revision incorrectly treated the listed Python/Flask/HTMX technologies as mandatory. Mitchell supplied tutor guidance confirming technology choice is open and clarifying the one-model application versus two-model agentic-loop requirements. The rejected revision was not retained; the docs now preserve Vue/ASP.NET Core and define two distinct local Ollama roles.

Mitchell also identified that the application ranking prompt had been mixed into the development lifecycle. That review was correct: the file was removed from `docs/prompt-library/`, and the plan now places it with backend product source and tests.

### Status

**Documentation verdict:** substantially improved, but implementation is not started. The current repository must not be described as working infrastructure until placeholder containers, Compose, CI, application code, loop runner, tests, and evidence are completed.

## 2026-08-31 - Downloaded Project Specification Full-Marks Audit

**Source reviewed:** `C:\Users\Mitchell.Harris\Downloads\ASD_2026_Project_Specifications.md`.

**Important limitation:** the downloaded file defines responsibilities, architecture, and submission requirements but does not contain the numerical 10-criterion marking table. Numerical readiness must therefore be cross-checked against the Release 0 brief in the repository.

### Verdict

**Request changes.** The plan is capable of becoming a full-mark plan, but it is not yet full-mark safe. The current repository is not remotely submission-ready because almost every executable/evidence criterion remains a placeholder or is absent.

### Critical Issues (Blocking)

| Finding | Evidence | Required correction |
|---|---|---|
| The agentic loop is designed mainly as a separate terminal development runner, but Section 4.3 says it shall be implemented by the integrated team application. | Downloaded specification Section 4.3; `feature-plan.md` Phase 7; `requirements.md` FR-21 to FR-26. | Make the two-model loop a shared team service/component under `ai-services/`, include it in the shared Compose application, and expose a terminal demonstration command through that integrated service. Keep personal prompts/records, but do not present a feature-local script as the whole team loop. |
| The agentic loop is scheduled too late to satisfy "throughout the project." | Downloaded specification Sections 4.3 and 4.4; `feature-plan.md` places it after the complete frontend in Phase 7. | Move shared loop setup to Phase 0/1 and use it during database, backend, frontend, Docker, and CI work. Phase 7 may harden/demo it, not introduce it. |
| No working AI infrastructure exists. | `ai-services/README.md` and `scripts/README.md` are placeholders; no runner/config/records; root Compose contains only a bare Ollama image. | Implement model setup, role validation, shared loop service/runner, Compose wiring, fake-model tests, and at least one genuine two-model correction record. |
| No working feature infrastructure exists. | Flask-template backend Dockerfile expects missing `app.py`; database Dockerfile sleeps; frontend has no Vue build; `student-1.yml` echoes text; root Compose targets missing `student-1/frontend`. | Replace placeholders with runnable services, tests, health checks, shared integration, and CI before claiming any implementation marks. |
| Repository structure remains non-standard and misspelled. | Current folder `Mitchell-Harris-Feature(Accomidation)` versus required designated `student-x/` structure. | Resolve the final folder/student mapping with the team before implementation paths multiply. |
| The written specification lists Python/Flask/HTMX while the plan uses Vue/ASP.NET Core. Tutor permission may make this valid, but no evidence path is recorded. | Downloaded specification Section 5.3 versus `requirements.md:11` and `feature-plan.md:34`. | Preserve written tutor approval (email, Canvas post, Teams message, or dated decision record) and cite it in the report. Without evidence, this is an avoidable assessment dispute. |

### Required Changes

| Finding | Required correction |
|---|---|
| Pre-testing and post-testing evidence is named but not operationally defined. | For every AI-assisted change, record a baseline/pre-test, implementer output, reviewer findings, adapted change, post-test, and human decision. Add this sequence to each phase and loop record schema. |
| `feature-plan.md` makes 10 Search records conditional even though every database table must contain at least 10 records. | Remove "if"; seed and verify at least 10 Accommodation and 10 Search records in the submitted database. |
| The plan treats the shared team loop as mainly Mitchell-owned. | Separate team deliverables (shared service, Compose, common prompts/protocol) from Mitchell's individual contribution and evidence. |
| Exact application, implementer, and reviewer model tags are unresolved. | Select approved tags early, prove both distinct loop roles locally, record hardware and timings, and document whether the application reuses one loop model. |
| Conceptual, ERD, logical, physical, individual architecture, integrated architecture, Compose, DevOps, and workflow diagrams are all pending. | Create and version them before report assembly; link each from the evidence checklist. |
| The feature has database-API accommodation CRUD but browser CRUD is demonstrated only through Search history. | State explicitly in the report that Search is the assessed CRUD resource and demonstrate all four operations end-to-end. If the tutor expects catalogue CRUD in the frontend, add a minimal admin catalogue view only after confirmation. |
| The downloaded specification requires the shared loop to be progressively extended across releases. | Define Release 0 extension points/documented boundaries without implementing Release 1 MCP/RAG or Release 2 multi-agent features now. |

### Strengths

- Application AI is correctly separated from development AI: one backend-mediated ranking model versus two distinct implementation/review roles.
- Application output validation, deterministic fallback, prompt-injection handling, data ownership, and service boundaries are strong.
- Requirements have measurable IDs and acceptance criteria rather than subjective wording.
- Seeded catalogue first is the correct Release 0 scope; Amadeus would add risk without satisfying a missing criterion.
- The evidence checklist accurately exposes missing work instead of falsely marking planning as implementation.

### Readiness Estimate

| Area | Design readiness | Implemented evidence |
|---|---|---|
| Requirements and feature planning | Strong, after the loop corrections above | Documentation only |
| Application AI design | Strong | None |
| Two-model agentic-loop design | Partial; wrong ownership/location/sequence | Prompts only |
| Microservices and CRUD | Strong plan | None |
| Docker Compose and service integration | Planned | Placeholder |
| CI/CD | Planned | Echo-only placeholder |
| Testing and pre/post evidence | Partial | None |
| Report/showcase evidence | Well indexed | Mostly none |

**Practical Release 0 readiness:** approximately 1-2 marks out of 20 as an implemented submission today. This is not a quality judgment on the rewritten plan; marks require working integrated software and evidence, not intentions.

## 2026-08-31 - Full-Marks Audit Corrections Applied

The following review findings were addressed without changing the selected Vue 3/TypeScript and ASP.NET Core feature stack:

| Finding | Resolution |
|---|---|
| Loop was a late feature-local script. | Added a shared .NET 8 service under `ai-services/agentic-loop`, wired it into root Compose, and moved establishment to Phase 1. |
| Loop was not used throughout development. | Added mandatory pre-test -> Plan/Act -> Observe -> Adapt -> post-test -> finalise evidence for Phases 2-10. |
| No executable two-model infrastructure. | Added Ollama client, distinct-role enforcement, one bounded revision, independent re-review, health endpoint, JSON records, verification script, prompts, and tests. |
| Context/secrets could be exposed. | Added repository-bound allow-listed file loading, secret/binary/path traversal rejection, and size limits. |
| Human decision/testing was not enforceable. | Run records remain pending until a separate human finalisation command supplies decision and post-test evidence. |
| Ten Search records were conditional. | Made at least 10 records mandatory for every submitted table. |
| Team versus individual loop ownership was unclear. | Marked service/Compose/protocol as shared team infrastructure and Mitchell's prompts/records as individual contribution evidence. |
| Tutor technology deviation lacked an evidence action. | Added a Phase 0 requirement and risk to preserve durable written approval. |

The first implementation attempt used Python. Mitchell rejected that technology; it was removed and replaced with .NET 8 before completion.

Automatic Ollama model pulls were also removed at Mitchell's request. `scripts/verify-agentic-models.ps1` now checks existing local tags and fails without downloading anything.

**Remaining blocking work:** real local model execution records, accommodation feature services, populated databases, full feature Compose integration, feature CI jobs, diagrams, report evidence, and showcase evidence.

## 2026-08-31 - Main DevOps Merge Review

Reviewed the conflicting `docker-compose.yml` and Student 1 workflow changes from `BCP/Clean_Up_Design` and `origin/main`.

| Finding | Resolution |
|---|---|
| Both branches independently replaced the placeholder Compose file, producing duplicate Ollama ports, volumes, and conflicting volume names. | Kept `main`'s shared and Student 2-5 frontend services, retained the branch's Ollama health check and agentic-loop service, and reduced Ollama to one port mapping and one `ollama-data` volume. |
| `main` added only a scaffold-presence check for Student 1, while the branch added executable .NET tests and container/Compose checks. | Retained the stronger executable checks and added `student-1/**` to the path triggers for the planned standard-folder migration. |

**Verdict:** conflicts resolved without dropping either branch's compatible infrastructure. The merge remains uncommitted for human review and commit.

## 2026-08-31 - Runtime Prompt Duplication Review

| Finding | Resolution |
|---|---|
| The shared runtime and accommodation feature folder contained different copies of both implementer and reviewer prompts. Their versions, headings, and validation placement had already drifted. | Kept `ai-services/agentic-loop/prompts/implementer.md` and `reviewer.md` as the only runtime sources and deleted the feature copies. |
| Evidence documentation linked to the duplicate prompt library instead of the files actually loaded and hashed by the runner. | Updated the feature README, context, checklist, prompt-library index, and repository instructions to reference the shared runtime paths. |

**Verdict:** resolved. One authoritative prompt now exists for each runtime model role.

## 2026-08-31 - Post-Merge PR Cleanliness Audit

**Verdict:** required corrections applied. The loop is substantial but its retained parts trace to the Release 0 agentic workflow, safety, reproducibility, or evidence requirements.

| Finding | Resolution |
|---|---|
| Any non-empty implementer response and minimally labelled reviewer verdict could be recorded as valid Plan/Act/Observe evidence. | Added structural validation for one ordered, non-empty Plan and Act plus ordered reviewer findings, validation gaps, scope check, and evidence fields for non-accept verdicts. |
| Allowed text files could contain credentials even though only sensitive filenames were rejected. | Added conservative checks for private-key headers, recognised token formats, and credential assignments before context reaches Ollama. |
| Records stored prompt hashes but not the human-readable versions required by NFR-14. | Added implementer and reviewer prompt versions to schema version 2 while retaining finalisation support for schema version 1 records. |
| The main web project could include `tests/**` content during local publish, producing recursive generated output. | Excluded test content and `None` items from the main project. |
| The checklist incorrectly described Student 1 CI as echo-only, and shared-loop CI ownership was implicit. | Corrected the evidence status and recorded temporary ownership pending a root shared workflow. |
| Reviewer headings outside `[OBSERVE]`, contradictory ACCEPT findings, model aliases, and sensitive symbolic-link targets could bypass validation. | Bounded reviewer parsing to the Observe section, rejected ACCEPT with blocking/required findings, normalised model tags before comparison/use/recording, and revalidated resolved link targets. |

No additional service, model, dependency, abstraction, or speculative Release 1 capability was added.

## 2026-08-31 - Feature Plan Chunking Review

**Goal:** provide a direct build sequence for the accommodation recommender without repeating the requirements, risk register, evidence checklist, or agentic-loop implementation details.

| Chunk | Goal alignment | Complexity result |
|---|---|---|
| Contracts and boundaries | Directly prevents incompatible paths, ports, service calls, and model usage. | Kept as one compact table and boundary list. |
| Runnable services | Required foundation for all feature behaviour. | Reduced to scaffold, health, images, and Compose. |
| Catalogue and history | Required persistence and CRUD functionality. | Kept as two chunks because they have different schemas and acceptance tests. |
| Deterministic backend and AI ranking | Required search flow and safe model integration. | Kept separate so basic integration works before Ollama failure modes are introduced. |
| Traveller frontend | Required browser functionality, CRUD, accessibility, and responsive behaviour. | Proportionate to the marking criteria. |
| Shared integration and CI | Required for non-zero integration and DevOps marks. | Combined into one final software-delivery chunk. |
| Report and demonstration | Required submission evidence. | Reduced to one evidence chunk. |
| Agentic-loop setup | Required demonstration setup but not application functionality. | Moved to the end instead of interrupting every implementation phase. |

**Verdict:** the revised plan is implementation-focused and contains no speculative Release 1 or Release 2 work.

## 2026-08-31 - Chunk 1 Scaffold and Health Review

**Review type:** Copilot-simulated review. The local Ollama implementer and reviewer models were not run for this review.

**Scope:** `student-1/frontend`, `student-1/backend`, `student-1/database`, root Compose, Student 1 CI, and active path/documentation references.

| Severity | Finding | Decision and resolution |
|---|---|---|
| Required | The initial Vue build imported a stylesheet path that did not exist outside the Vite project. | Removed the invalid cross-project import and kept the frontend self-contained; the production build then passed. Shared theme integration remains a later frontend/integration task. |
| Required | SQLite test cleanup initially failed because pooled connections retained the temporary database file. | Added explicit SQLite pool clearing after the test host is disposed; both database endpoint tests then passed. |
| Required | Main ASP.NET projects could recursively compile source files placed under their `tests` folders. | Excluded `tests/**` from each main project's default items while retaining project references from the test projects. |
| Required | Compose needed explicit runtime dependency ordering and persistent database ownership. | Added frontend -> backend -> database/Ollama health dependencies, service-DNS URLs, the confirmed ports, and the `student1-sqlite-data` volume. |
| Required | Active instructions and examples still referenced the old misspelled folder after migration. | Updated active repository instructions, CI triggers, runner example, context, plan, backlog, README, checklist, and risk controls to `student-1/`; historical review evidence remains unchanged. |

**Validation:** Vue type-check/production build passed; backend endpoint tests passed 2/2; database endpoint tests passed 2/2; Compose configuration validated. Mitchell separately reported that all three images build, the containers start, and their health checks pass.

**Verdict:** Chunk 1 is complete. The implementation establishes healthy, containerised service boundaries only; it correctly does not claim catalogue CRUD, search history, recommendation AI, or the finished traveller interface.

## 2026-08-31 - Current Implementation Planning Review

**Scope:** Current Student 1 frontend, backend, database API, Dockerfiles, root Compose, Student 1 CI, feature requirements, feature plan, sprint backlog, and risk plan.

| Finding | Planning decision |
|---|---|
| The three feature containers, health checks, service-DNS configuration, ports, and SQLite volume now exist. | Preserve the current deployment shape; do not add another service, gateway, queue, cache, or data store. |
| Accommodation catalogue code and an initial EF Core migration are present as uncommitted work, but the existing database tests cover only root and health endpoints. | Finish catalogue contract tests and verify migration/seed behaviour before starting search history. |
| The backend still exposes only root and health endpoints. | Implement deterministic search orchestration and database HTTP clients before adding Ollama, so dependency and persistence behaviour can be proven without model variability. |
| The frontend remains a readiness page and the shared frontend has no accommodation entry point. | Build the traveller workflow after the backend contract is stable, then add the shared navigation link as the final integration step. |
| Student 1 CI already expects frontend build, both .NET test projects, Compose validation, and all three image builds. | Extend existing test projects and keep CI independent of live Ollama; no separate CI architecture is needed. |

**Verdict:** Continue with the existing feature-plan sequence. The minimum complete design remains three Student 1 services plus the already-shared Ollama runtime; current work should proceed catalogue -> history -> deterministic backend -> Ollama -> frontend -> shared integration.

## 2026-08-31 - Conditional Ollama Model Setup Decision

The earlier manual-only model installation decision was superseded by Mitchell's explicit instruction to let Compose pull a model when it is missing, without downloading it again when already installed.

| Finding | Resolution |
|---|---|
| Starting only the traveller application should not force installation of the larger development implementer model. | Added a dedicated `ollama-application-model` setup service used by the backend. |
| Starting the agentic loop requires both distinct development model tags. | Added a separate `ollama-agentic-models` setup service used by `agentic-loop`. |
| Repeated startup must not redownload existing models. | Each setup service runs `ollama show` before `ollama pull` and uses the persistent `ollama-data` volume through the shared Ollama server. |

**Verdict:** The conditional setup is scoped to required configured tags, preserves existing model data, and adds no new runtime application component.

### Follow-up Reliability Review

The setup-service pattern is proportionate for a local classroom deployment, but the initial agentic-model loop did not explicitly stop after a failed pull. Both setup scripts now use `set -eu`, so a missing variable or failed model download prevents the dependent backend or agentic-loop service from starting.

## 2026-08-31 - Post-Setup Parallel Work Review

**Goal:** identify work after Chunk 1 that can proceed concurrently without textual merge conflicts while preserving the feature plan's dependency order.

| Work area | Parallel decision |
|---|---|
| Chunk 2 catalogue and Chunk 3 search history | Do not run as independent branches. Both modify the database project, `AccommodationDbContext`, migrations/model snapshot, startup registration, seeding, and database tests. |
| Chunk 4 deterministic backend and Chunk 5 AI ranking | Do not run as independent branches. Chunk 5 depends on Chunk 4's DTOs, orchestration, persistence, ranking interface, endpoint wiring, and tests. |
| Database implementation and frontend preparation | Safe only after the API payloads are frozen and ownership is restricted to `student-1/database/**` versus `student-1/frontend/**`. The frontend lane may build typed clients, components, styling, and component tests against fixtures, but final end-to-end wiring waits for the backend contract. |
| Database implementation and backend preparation | Safe only with strict ownership of `student-1/database/**` versus `student-1/backend/**` and a frozen database API contract. The backend lane may create DTOs, clients, deterministic ranking, and fake-client tests; integration validation waits for the database endpoints. |
| Application implementation and report diagrams/evidence templates | Safe when the evidence lane creates separate new files and does not edit shared logs, the backlog, README, Compose, workflows, or source files. Claims of completion and screenshots must wait for real validation. |
| Chunk 7 shared integration | Keep as one exclusive lane after application behaviour stabilises because it owns shared navigation, root Compose, CI, and setup documentation. |

**Verdict:** no complete numbered chunks after Chunk 1 are guaranteed conflict-free when developed in parallel. Guaranteed conflict avoidance requires explicit directory/file ownership; the strongest useful split is database, backend, frontend, and new evidence-file lanes, with dependent integration performed sequentially.

## 2026-08-31 - Chunk 2 Catalogue Review

**Review type:** Copilot-simulated review using a parallel reviewer subagent. The local Ollama implementer and reviewer models were not run.

**Scope:** Accommodation EF model/configuration/migrations, database API CRUD and filters, integration tests, Docker runtime, and FR-04/FR-15 to FR-17 traceability.

| Severity | Finding | Decision and resolution |
|---|---|---|
| Blocking | SQLite's default EF decimal mapping stored prices as text, causing valid values to fail numeric database constraints. | Replaced the mapping with exact integer-cent storage while keeping decimal API values; regenerated the migration and reran the complete suite. |
| Blocking | Plain-text amenities had no database JSON invariant, so malformed manually inserted data could break response mapping. | Added a SQLite `json_valid`/array check constraint in a follow-up generated migration and added a direct constraint test. |
| Required | The initial `DbContext` contained every table, column, conversion, index, and constraint mapping inline and did not match Mitchell's expected EF structure. | Compared representative WiseTech Academy code and moved mapping into `Configurations/AccommodationConfiguration.cs`; the context now only exposes the `DbSet` and applies the configuration. |
| Required | The requirements call for repeatable seed data and at least 10 records, but Mitchell explicitly declined automatic seeding. | Removed the seeder. The catalogue intentionally starts empty, and FR-16/EV-02 minimum-record evidence remains blocked until Mitchell manually creates at least 10 records through the functional application. |
| Required | Candidate queries must exclude inactive records. | The database API supports explicit `active=true`; the future backend integration must always supply it for candidate retrieval. Catalogue administration may still list inactive records deliberately. |

**Validation:** 12/12 tests pass, including CRUD, validation, case-insensitive conflicts, inclusive filters, not-found responses, SQL-injection-shaped data, price/capacity constraints, malformed amenities JSON, health, and empty startup. The Docker image builds, the existing volume advances through both migrations, the container reports healthy, and runtime create/delete leaves the catalogue empty.

**Verdict:** the Chunk 2 catalogue code is functional and follows the requested WiseTech EF configuration pattern. Chunk 2 cannot be marked fully complete against the original requirements until at least 10 records exist; that gap is an explicit human decision rather than an implementation claim.

## 2026-08-31 - EF Repository Refactor Review

**Review type:** Copilot-simulated review. The local Ollama implementer and reviewer models were not run.

**Scope:** Database context naming and registration, accommodation repository boundary, endpoint EF dependencies, migration metadata, database constraint tests, and the existing catalogue HTTP contract.

| Severity | Finding | Decision and resolution |
|---|---|---|
| Required | Catalogue endpoints directly queried `AccommodationDbContext`, which left HTTP behavior coupled to EF Core and did not match the selected full WiseTech Academy pattern. | Added a scoped `IAccommodationRepository`/`AccommodationRepository`; all catalogue queries, tracking choices, duplicate checks, adds, removals, and saves now pass through it. |
| Required | The context name was feature-specific even though it is the database service's shared unit of work and will also own search history. | Renamed it to `DatabaseContext` and updated DI, health checks, startup migration application, tests, migration designers, and the model snapshot metadata. |
| Required | Copying WiseTech Academy's broad generic repository and SQL Server conventions would add unrelated operations and provider assumptions. | Kept only the catalogue methods used by current endpoints and retained SQLite-specific filtering and constraints. |
| Required | A repository refactor could accidentally alter CRUD, filtering, duplicate, migration, or constraint behavior. | Reused the existing integration suite against fresh temporary SQLite files; all 12 tests pass without changing the public API contract or schema. |
| Note | The optional `dotnet-ef` CLI is not installed, so `has-pending-model-changes` could not run. | Did not install a new tool for this refactor. Fresh-database startup in the integration suite still applies both checked-in migrations successfully, and the compiled migration metadata references `DatabaseContext`. |

**Evidence:** `database/Repositories/IAccommodationRepository.cs`, `database/Repositories/AccommodationRepository.cs`, `database/Data/DatabaseContext.cs`, `database/Api/AccommodationEndpoints.cs`, `database/Program.cs`, migration designer/snapshot metadata, and `dotnet test student-1\database\tests\Database.Tests.csproj --no-restore` with 12/12 passing.

**Verdict:** accepted. The database API now follows the selected context/configuration/repository pattern while preserving the existing SQLite schema and catalogue API behavior. FR-16 remains open because the catalogue still intentionally lacks the required manually created records.

## 2026-08-31 - Chunk 3 Search History Review

**Review type:** Copilot-simulated review. The local Ollama implementer and reviewer models were not run.

**Scope:** Search entity/configuration/migration, repository and endpoint boundaries, create/list/get/rename/delete behavior, immutable snapshots, database constraints, one-time data population, Compose persistence, and FR-11 to FR-14/FR-17 traceability.

| Severity | Finding | Decision and resolution |
|---|---|---|
| Blocking | A committed SQLite file would be hidden by the existing named `/data` volume, so pushing the populated file would not make it available in a clean Compose checkout. | Replaced the Student 1 named volume with a bind mount of `student-1/database/storage`; the tracked database is now the file opened at `/data/accommodation.db`. |
| Required | The initial implementation included startup seed code, which would recreate sample records and mix fixture generation with normal runtime behavior. | Removed the seeder and its startup call. Populated 10 representative Search rows once through the real HTTP endpoint and checkpointed the database into one self-contained tracked file. |
| Required | Search records require protection beyond API validation because the SQLite file may also be populated manually. | Added database checks for date order, guests, cent-based price range/order, ranking mode, text lengths, and a valid JSON-array snapshot. |
| Required | History summaries must be newest first and reopening must not rerun or depend on live Accommodation rows. | Added descending creation/ID ordering and a regression test that creates a snapshot, deletes its accommodation, and reopens the unchanged stored result. |
| Required | Search input includes malformed JSON, missing dates, past check-in, invalid price order, invalid ranking modes, and non-array snapshots. | Added boundary validation with stable error envelopes and integration coverage proving invalid requests do not persist. |

**Evidence:** `database/Data/Search.cs`, `database/Data/Configurations/SearchConfiguration.cs`, migration `20260831093522_AddSearchHistory`, `database/Repositories/SearchRepository.cs`, `database/Api/SearchEndpoints.cs`, `database/tests/SearchHistoryTests.cs`, tracked `database/storage/accommodation.db`, and the Student 1 database bind mount in root Compose.

**Validation:** 19/19 database tests pass; `dotnet-ef migrations has-pending-model-changes` reports no model changes; `docker compose config --quiet` passes; the rebuilt database image starts healthy and its HTTP history endpoint returns all 10 records from the bind-mounted tracked database; the stopped database has no WAL/SHM sidecars.

**Verdict:** accepted. Chunk 3 is complete at the database-service boundary. Backend and frontend history endpoints remain correctly deferred to later chunks, and FR-16 remains open until at least 10 Accommodation records are created.

## 2026-08-31 - Academy EF Pattern Alignment Review

**Review type:** Copilot-simulated review. The local Ollama implementer and reviewer models were not run.

**Scope:** All handwritten Student 1 EF context, entities, configurations, repositories, startup registration, and tests, compared with representative WiseTech Academy database patterns. Generated migrations and snapshots were inspected but not treated as handwritten architecture.

| Severity | Finding | Decision and resolution |
|---|---|---|
| Required | `AccommodationConfiguration` and `SearchConfiguration` were separate files but still placed table, key, properties, constraints, and indexes in one direct `IEntityTypeConfiguration.Configure` method. This did not implement the Academy base-configuration pattern previously agreed with Mitchell. | Added `BaseEntityTypeConfiguration<TEntity>` and converted both configurations to the ordered table, primary-key, properties, indexes, and foreign-key lifecycle. |
| Required | The context used a primary constructor and expression-bodied sets rather than the explicit Academy context shape. | Changed `DatabaseContext` to an explicit options constructor and initialized `DbSet` properties while retaining explicit configuration application in `OnModelCreating`. Academy's `virtual` modifier was deliberately omitted because this project does not use lazy-loading proxies or context-property overrides. |
| Noted | The Academy base class discovers `Schema.TableName` with reflection. Copying that mechanism would hide a required value behind runtime reflection and nullable casts. | Preserved the nested `Schema.TableName` convention but required each configuration to expose it through a compile-time checked override. |
| Noted | This project needs SQLite table check constraints that the sampled Academy base class does not model. | Added one virtual table-configuration hook so constraints remain grouped separately without bypassing the base lifecycle. |
| Accepted | Accommodation and Search repositories already isolate endpoints from EF queries and persistence, and startup is the only runtime location that directly applies migrations. | No repository or startup restructuring was required. |

**Validation:** all 19 database tests pass; EF reports no pending model changes; no concrete entity configuration implements `IEntityTypeConfiguration` directly; migration and snapshot files remain generated artifacts.

**Verdict:** accepted after correction. The handwritten EF layer now consistently follows the agreed Academy context/configuration/repository structure without copying its reflection weakness or SQL Server-specific details.

## 2026-08-31 - Chunk 4 Deterministic Backend Review

**Review type:** Copilot-simulated adversarial review. The local Ollama implementer and reviewer models were not run.

**Scope:** Backend DTOs, search validation, deterministic ranking, database HTTP client, persistence, history CRUD, dependency failures, tests, tracked SQLite compatibility, and FR-01 to FR-05/FR-09 to FR-14 traceability.

| Severity | Finding | Decision and resolution |
|---|---|---|
| Blocking | Well-formed but semantically invalid database JSON could deserialize into null/default CLR values and then cause a `500` or leak invalid public DTOs. | Added nullable wire DTOs and explicit semantic validation before mapping candidates, history summaries, stored searches, and result snapshots. Invalid payloads now produce `502 dependency_response_error`. |
| Blocking | The database client treated every dependency `404` as a missing history record, so route/version errors on candidate list, history list, or persistence could escape as `500`. | Limited record-not-found translation to ID-based get/rename/delete calls. Collection and create `404` responses are now unusable dependency responses and map to `502`. |
| Required | Non-JSON request content types could bypass the stable validation envelope. | Added a JSON content-type boundary check and a focused test proving no database call occurs. |
| Required | Failure logs did not identify whether candidate retrieval or persistence failed. | Added structured stage, outcome, duration, candidate count, ranking mode, failure category, and correlation ID fields without logging preferences. |
| Required | The first result DTO copied catalogue-only description, amenity, and URL fields that were absent from the 10 existing persisted snapshots. | Reduced the result contract to the FR-10 display fields: identity, name, destination, nightly price, capacity, rank, and reason. All tracked history now reopens without rewriting SQLite data. |
| Required | Initial tests did not prove the final accommodation-ID tie-break, semantic payload failures, wrong content type, collection `404`, or repeated deletion. | Expanded the focused backend suite to 29 tests covering those cases in addition to all FR-02 invalid boundaries, empty results, persistence, history CRUD, timeout, malformed JSON, and error shapes. |

**Persistence decision:** the tracked `student-1/database/storage/accommodation.db` remains the source of the 10 representative records and is bind-mounted by Compose. No startup seed code was added. SQLite `-wal` and `-shm` runtime sidecars are ignored while the primary database remains tracked.

**Evidence:** backend tests pass 29/29; database regressions pass 19/19; Docker rebuild succeeds; all 10 persisted searches list and reopen through the rebuilt backend; Compose configuration and diff checks pass.

**Verdict:** accepted after corrections. Chunk 4 is complete without Ollama: valid searches rank and persist deterministically, empty searches persist with an empty snapshot, history CRUD is exposed through the backend, dependency failures use stable `502`/`503` envelopes, and persisted SQLite data survives service rebuilds.

## 2026-08-31 - Chunk 5 Application AI Ranking Review

**Review type:** Copilot adversarial diff review. The local Ollama implementer and reviewer models were not run.

**Scope:** Application ranking prompt, Ollama HTTP client/configuration, request allow-list, output validation, trusted candidate mapping, search fallback/persistence, response notice, logging, and FR-06 to FR-10/NFR-01 to NFR-03/NFR-06/NFR-08 traceability.

| Severity | Finding | Decision and resolution |
|---|---|---|
| Accepted | The model receives validated criteria and only ranking-relevant eligible candidate fields. Preferences and descriptions are explicitly labelled untrusted, and model output cannot replace trusted names, destinations, prices, or capacities. | Kept the bounded prompt/input contract and map accepted IDs/ranks/reasons back onto validated database candidates. |
| Accepted | Whole-response validation rejects Markdown, malformed JSON, unknown/missing/duplicate/extra IDs, non-contiguous or duplicate ranks, empty/oversized/untrimmed reasons, and unexpected output properties. | Kept one rejection path that invokes deterministic fallback before persistence. |
| Required | The initial tests did not exercise non-success Ollama HTTP status, `done: false`/empty generation responses, or endpoint fallback for an unavailable ranking client. | Added focused client and endpoint tests for all three paths and asserted structured failure categories plus persisted fallback mode/notice. |
| Accepted | Empty candidate searches skip Ollama, while timeout, connection, HTTP, and invalid-response failures retain valid candidates and persist deterministic results. | Kept empty-result behavior separate from AI failure notices and preserved the existing deterministic ordering contract. |

**Evidence:** `backend/Prompts/accommodation-ranking-v1.txt`, `backend/Clients/OllamaRankingClient.cs`, `backend/Api/SearchEndpoints.cs`, `backend/tests/OllamaRankingClientTests.cs`, and `backend/tests/SearchEndpointsTests.cs`.

**Validation:** all 46 backend tests pass and `git diff --check` reports no whitespace errors.

**Verdict:** implementation accepted. Live Ollama execution remains open evidence work; this review used deterministic test doubles and must not be cited as a genuine model run.

## 2026-08-31 - Chunk 6 Traveller Frontend Review

**Review type:** Copilot-simulated review. The local Ollama implementer and reviewer models were not run.

**Scope:** `frontend/src/App.vue`, the typed frontend API boundary, search/history/results components, responsive styling, component tests, and FR-01/FR-03/FR-05/FR-10/FR-12 to FR-14/FR-20/NFR-04 to NFR-07 traceability.

| Severity | Finding | Decision and resolution |
|---|---|---|
| Required | The first component split allowed the initial history request to overwrite a search completed while history was still loading. | Reconciled loaded and newly added summaries by ID and newest-first creation time; added a test that resolves the initial list after search creation. |
| Required | Renaming a search updated history but left the currently displayed results heading stale. | Added a typed rename event to the coordinator and update the displayed snapshot when IDs match; the test now reopens, renames, and checks the result heading. |
| Required | Entering, validating, saving, cancelling, and deleting history actions did not consistently move or restore keyboard focus. | Added focus movement into the rename input, local validation announcement/focus, restoration to Rename after save/cancel, and movement to the next action or history heading after deletion. |
| Required | Valid long unbroken user/model text could overflow cards at the required 320px width. | Added minimum-width containment and `overflow-wrap: anywhere` to history and result text containers. |
| Required | Initial tests did not cover the history race, rename synchronization, focus movement, or rename live announcements. | Expanded the suite from five to seven tests and added active-element and live-region assertions. Manual viewport execution remains an explicit evidence item because jsdom does not calculate layout. |
| Accepted | `App.vue` now coordinates only global search state, errors, live status, and cross-component synchronization. | Kept `SearchForm`, `SearchHistory`, and `SearchResults` as the three component boundaries; no additional store, router, or UI dependency was introduced. |
| Accepted | Browser data is rendered only through Vue interpolation and all network calls use relative backend `/api/searches` routes. | Kept the text-only rendering and frontend-to-backend boundary; no `v-html`, database URL, or Ollama URL exists in frontend source. |

**Validation:** `npm --prefix student-1/frontend test` passes 7/7 tests; `npm --prefix student-1/frontend run build` passes strict TypeScript checking and the Vite production build; `git diff --check` passes.

**Verdict:** implementation accepted after corrections. Manual keyboard walkthrough, 320/768/1280px layout execution, integrated API execution, and screenshots remain pending and are not claimed by this simulated review.

## 2026-08-31 - LiteAPI Import and Ranking Review

**Review type:** Copilot-simulated code review plus verification against the official LiteAPI v3 `/hotels/rates` OpenAPI documentation. No real LiteAPI credential or sandbox request was used.

**Scope:** LiteAPI request/response contract, backend-only credential handling, destination cache decision, database-API import boundary, search orchestration, Ollama hand-off, frontend notice, Compose configuration, and deterministic tests.

| Severity | Finding | Decision and resolution |
|---|---|---|
| Blocking | The initial client modelled `offerRetailRate` as one object, but the official response defines an array. A conforming sandbox response would fail deserialization. | Changed the wire contract to a price array, accept one usable AUD offer price, and updated the provider fixtures to match the official schema. |
| Required | `cityName` was sent without the country code LiteAPI requires for that search method. | Replaced it with the documented `aiSearch` location method so the existing free-text destination contract remains valid without inventing a country field. |
| Required | Response validation allowed up to 100 entries even though this integration requests and promises at most 10. | Enforced a maximum of 10 rate results and 10 hotel metadata records at the provider boundary. |
| Required | Empty responses, duplicate hotel metadata, missing/multiple offer prices, rate limits, missing credentials, and import/cache orchestration needed explicit coverage. | Expanded the provider and endpoint suites; all 61 backend tests pass with deterministic HTTP/database/Ollama doubles. |
| Accepted limitation | LiteAPI total-stay rates are converted to nightly catalogue prices and cached independently of dates. This can become stale for later date combinations. | Kept this intentionally for the non-production university demonstration requested by Mitchell and documented that imported data is not a live price guarantee. |
| Accepted limitation | Imports are individual database API creates rather than one atomic provider batch. | Kept the existing CRUD API boundary to avoid an unrequested database protocol expansion. A mid-batch failure returns an explicit dependency error; production-grade transactional import remains out of Release 0 scope. |
| Security action | A sandbox credential was disclosed in conversation. | The value was not used, logged, copied into commands, or stored in repository files. It must be revoked and replaced before real runtime validation; only the replacement belongs in ignored local `.env`. |

**Validation:** backend tests pass 61/61; frontend tests pass 7/7; strict TypeScript/Vite build passes; Compose configuration and `git diff --check` pass.

**Verdict:** implementation accepted for deterministic integration. A real LiteAPI sandbox request, SQLite import, Ollama ranking, browser result, and second-search cache hit remain pending and must not be claimed until a replacement key is configured.

## 2026-08-31 - LiteAPI End-to-End Flow Understanding Review

**Scope:** Current frontend search submission, backend validation and orchestration, LiteAPI import, database catalogue access, Ollama ranking, result persistence, and frontend rendering.

| Severity | Finding | Status |
|---|---|---|
| Accepted | The implemented happy path matches the intended frontend -> backend -> catalogue/LiteAPI -> Ollama -> search snapshot flow. Search criteria are validated before dependency calls, provider data is validated before database import, model output is validated before use, and the saved snapshot includes ranking order and reasons. | Implemented with deterministic tests; live provider/model execution remains pending. |
| Required | The import decision currently uses the eligible-candidate query result. Therefore a destination with cached records that are outside the requested budget or guest capacity is treated as uncached and triggers LiteAPI, contrary to FR-04a's rule that existing destination data skips the provider. | Open. Add a destination-cache-state query or equivalent database API contract, test cached-but-ineligible searches, and call LiteAPI only when the destination itself is absent. |
| Accepted limitation | Imported total-stay prices are converted to nightly catalogue prices and persist beyond the requested dates. | Intentionally retained for Release 0 demonstration data; not a live availability or price guarantee. |
| Evidence gap | The repository proves the flow with fakes but not with a replacement LiteAPI key, live SQLite import, live Ollama ranking, browser rendering, and a second request demonstrating the cache hit. | Open. |

**Verdict:** The core integration is substantially implemented and connected. Correct the cache-state decision before claiming exact FR-04a compliance, then collect the live end-to-end evidence.

## 2026-08-31 - Live LiteAPI Contract Correction

**Scope:** The browser-reported `accommodation_provider_response_error`, correlated backend request, live sandbox response structure, provider request options, `LiteApiClient`, and its contract tests.

| Severity | Finding | Resolution |
|---|---|---|
| Blocking | The live rate response omitted `hotels` because the request did not set `includeHotelData`. The client requires that metadata to create catalogue records, so every otherwise successful provider response was rejected. | Added `includeHotelData: true` to the rate request. |
| Blocking | The live sandbox returns each room type's `offerRetailRate` as one money object, while the implemented DTO expected an array. | Corrected the DTO and mapping to consume the observed object shape and updated provider fixtures. |
| Required | The live response included one rate without corresponding hotel metadata alongside eight usable results. The client rejected the entire response instead of discarding only the incomplete entry. | Missing metadata entries are now skipped; structurally invalid IDs and batches with no usable imports remain rejected. |
| Correction | The earlier simulated review incorrectly concluded that the provider contract required an `offerRetailRate` array. | Superseded that conclusion with evidence from the live sandbox response. |

**Verdict:** The cause of the live `502` is corrected in source. Rebuild the backend image and repeat the browser search to confirm provider import, Ollama ranking, persistence, and cache behavior.

## 2026-09-01 - Live Ollama Fallback Investigation

**Scope:** Browser fallback state, backend and Ollama runtime logs, Docker/WSL resources, Ollama request format, ranking output validation, and live frontend-proxy execution.

| Severity | Finding | Resolution |
|---|---|---|
| Blocking | WSL limited Docker to two processors and 4 GB, so Ollama used one inference thread and the backend cancelled real ranking requests at the required 12-second timeout. | Retained an 8 GB WSL memory limit and removed the processor cap, allowing Docker to use the host's 22 logical processors while the application retains its specified 12-second timeout. |
| Blocking | The client sent `"format": "json"`. Live `llama3.2:3b` responses were JSON objects containing repeated `accommodationId`, `rank`, and `reason` keys rather than the required array, so strict validation correctly selected fallback. | Replaced generic JSON mode with an exact JSON schema requiring an array with the current candidate count, allowed candidate IDs, rank bounds, reason bounds, required fields, and no additional properties. The existing whole-response validator remains authoritative. |
| Blocking | After the schema correction, a changed destination still timed out because the prompt repeated verbose candidate field names and duplicated trust instructions. Exact repeated prompts benefited from Ollama's cache, masking the cold-prompt failure. | Kept every allow-listed input field but serialised candidate values under one shared field header and shortened the equivalent prompt contract. Cold Sydney and Tokyo prompts now complete within the existing timeout. |
| Required | The initial performance-oriented prompt requested 1-4 word reasons, producing generic fragments such as `Best price` and comma-separated lists rather than useful explanations. | Required one specific 5-10 word sentence containing a supplied price, amenity, capacity, or location detail. The JSON schema and backend validator enforce sentence casing, final punctuation, length, and the 10-word maximum. |
| Required | The host had an NVIDIA RTX 2000 Ada GPU with 8 GB VRAM, but the Compose Ollama service requested no GPU device and therefore ran entirely on CPU. | Added a small optional GPU Compose override. The Student 1 startup script selects it only when both `nvidia-smi` and Docker's NVIDIA runtime are available, preserving the main CPU-only Compose path. |
| Accepted | Deterministic fallback prevented request failure and invalid history while the AI path was unavailable or malformed. | Kept fallback behavior unchanged. |

**Validation:** all 65 backend tests pass. Ollama reports CUDA execution with all 29 model layers offloaded and `size_vram` of about 2.55 GB. Retrying the previously failing Sydney request through `http://localhost:5101/api/searches` returned five specific sentence-form reasons with `rankingMode: ai`, no notice, and 2.5 second completion. Database, backend, frontend, and Ollama services remained healthy.

**Verdict:** fixed. The live frontend-triggered path now reaches the configured Ollama model, accepts a schema-conforming ranking, persists it as `ai`, and returns it without the fallback notice.

## 2026-09-01 - Integrated Startup GPU Opt-In Review

**Scope:** `scripts/start-app.ps1`, the optional GPU Compose override, CPU portability, NVIDIA runtime detection, and startup documentation.

| Severity | Finding | Resolution |
|---|---|---|
| Required | The integrated startup script always used the CPU-only main Compose file, so users could not explicitly enable the existing Ollama GPU override. | Added `-Gpu`, validated NVIDIA GPU and Docker runtime availability before startup, and reused the same selected Compose files for `up` and `ps`. |
| Accepted | GPU mode must remain optional because other team machines and CI may not expose NVIDIA devices. | CPU remains the default; the main Compose file and CI behavior are unchanged. |

**Verdict:** accepted. `scripts/start-app.ps1 -Gpu` enables Ollama GPU acceleration explicitly, while `scripts/start-app.ps1` remains portable CPU mode.
