# Review Record

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
