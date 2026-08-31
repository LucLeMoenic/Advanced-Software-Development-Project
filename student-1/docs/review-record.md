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
