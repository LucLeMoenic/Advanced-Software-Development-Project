# AI Accommodation Recommender Risk Plan

## 1. Method

Review this register at the start and end of each feature-plan phase and before shared Compose, CI, model, schema, or public API changes.

- Probability (P): 1 rare, 2 unlikely, 3 possible, 4 likely, 5 almost certain.
- Impact (I): 1 negligible, 2 minor, 3 moderate, 4 major, 5 release/marks threatening.
- Score: `P x I`. Treat 15-25 as critical, 8-12 as high, 4-6 as medium, and 1-3 as low.
- Owner is accountable for action, not necessarily the only implementer.

## 2. Risk Register

| ID | Risk and consequence | P | I | Score | Prevention / mitigation | Trigger and contingency | Owner | Evidence / review point |
|---|---|---:|---:|---:|---|---|---|---|
| R-01 | Feature remains outside the integrated app, causing zero for non-integrated work. | 4 | 5 | 20 | Confirm standard folder, shared route, ports, Compose names, theme, and shared-file ownership in Phase 0; integrate incrementally. | If the unified page cannot open the working feature, stop feature expansion and pair with the integration owner. | Mitchell + integration owner | Unified-page URL and full Compose evidence. |
| R-02 | Placeholder Dockerfiles or echo-only CI are mistaken for completed infrastructure. | 4 | 4 | 16 | Phase gates reject placeholders; build each real image and make CI execute tests. | Any `sleep infinity`, missing entry point, or echo-only build step blocks completion. | Mitchell | Docker build logs and workflow run. |
| R-03 | The chosen Vue/ASP.NET stack is not consistently implemented across docs, containers, and CI. | 3 | 4 | 12 | Record the tutor clarification; use Vue/TypeScript and ASP.NET Core consistently; remove Flask templates. | Conflicting runtime/dependency in a changed file blocks merge. | Mitchell | Dependency, Dockerfile, and documentation review. |
| R-04 | The application calls more than one ranking model or bypasses its backend API, violating the clarified application AI flow. | 3 | 5 | 15 | One `APPLICATION_MODEL` setting exists only in backend configuration; frontend has no Ollama URL. | Network/source review finds another model or direct browser call: block integration and remove it. | Mitchell | Browser network capture and backend configuration. |
| R-05 | The agentic loop uses one model for both roles, so review is not independent. | 3 | 5 | 15 | Require distinct `IMPLEMENTER_MODEL` and `REVIEWER_MODEL` values and fail fast when equal. | Equal model tags or missing role evidence makes the run invalid and must be repeated. | Mitchell | Terminal output and saved loop record. |
| R-06 | Required local models exceed demonstration-machine RAM/VRAM/disk or respond too slowly. | 4 | 4 | 16 | Benchmark approved quantised model tags early; minimise unique tags by allowing the app to reuse one loop model; document pull/setup. | If either call exceeds the agreed timeout, select smaller approved tags and rerun evidence before implementation depends on them. | Mitchell + demo host | Model list, hardware note, timing record. |
| R-07 | Application Ollama output is malformed/partial, breaking the demo or corrupting results. | 4 | 4 | 16 | Validate complete output and implement deterministic fallback before AI integration. | Timeout, invalid JSON/schema/IDs/ranks invokes fallback and visible notice. | Mitchell | Failure tests and forced-fallback demo. |
| R-08 | Model follows malicious instructions embedded in preferences, catalogue data, repository files, or proposed code. | 3 | 4 | 12 | Delimit untrusted data, state it is data, restrict output, allow-list context, and validate model output. | Unexpected instructions/unknown IDs/out-of-scope proposal is rejected; no automatic write occurs. | Mitchell | Injection tests for app and loop prompts. |
| R-09 | Agentic runner leaks secrets or sends excessive/unrelated code to models. | 3 | 5 | 15 | Reject `.env`, credential, binary, outside-repository, and oversized inputs; use explicit file allow-lists; redact records. | Suspected secret: stop, rotate/revoke, remove from current changes, notify team, and follow repository history-remediation policy. | Secret owner + Mitchell | Context-filter tests and record review. |
| R-10 | Agentic loop applies unsafe changes, loops indefinitely, or falsely claims validation. | 3 | 5 | 15 | No automatic write/commit/push; bound calls/iterations; include real validation output; human records apply/reject. | Timeout, malformed output, failed validation, or iteration limit returns non-zero and requires human resolution. | Mitchell | Fake-model tests and one rejected-run record. |
| R-11 | Backend directly accesses SQLite, destroying the database-service boundary. | 3 | 5 | 15 | Keep EF Core/SQLite packages and connection string only in database project; backend receives only data API URL. | Static/dependency review finds SQLite access in backend: block merge and use HTTP client. | Mitchell | Architecture review and project references. |
| R-12 | Partial failure persists incomplete or invalid search history. | 3 | 4 | 12 | Validate ranking before one search create; store immutable snapshot in one database transaction. | Persistence failure returns explicit error and never claims save success. | Mitchell | Transaction and dependency-failure tests. |
| R-13 | Tables have fewer than the required 10 records. | 3 | 5 | 15 | Idempotently seed every submitted table and assert minimum counts in tests/CI. | Count below 10 blocks CI/demo readiness. | Mitchell | Seed test and database count. |
| R-14 | CRUD exists only in API tooling rather than through the frontend. | 3 | 5 | 15 | Implement create/read/rename/delete history through Vue and both API layers. | Missing browser action blocks frontend completion; curl/Postman is not a substitute. | Mitchell | Browser CRUD recording and tests. |
| R-15 | Shared Compose changes collide with team services or use `localhost`. | 4 | 4 | 16 | Agree names/ports; use service DNS; review the full stack. | Collision/unhealthy dependency requires correcting Mitchell's conflicting change with the integration owner. | Mitchell + team | `docker compose config` and integrated startup. |
| R-16 | Search history changes after catalogue edits/deletes. | 3 | 3 | 9 | Persist immutable result snapshots rather than live joins on reopen. | History mutation after catalogue CRUD blocks data phase. | Mitchell | Snapshot regression test. |
| R-17 | Accessibility/responsive behaviour is deferred until the demo. | 3 | 3 | 9 | Include labels, focus, keyboard, live status, alt text, and 320/768/1280px checks in the frontend gate. | Blocked keyboard flow or horizontal page scroll blocks completion. | Mitchell | Browser checklist/screenshots. |
| R-18 | Folder spelling/standard-structure mismatch breaks scripts, CI, or assessment navigation. | 4 | 4 | 16 | Resolve `Accomidation` spelling and required `student-x/` placement before code paths multiply; quote paths until migration. | If rename is delayed, centralise paths and record the limitation. | Mitchell + team | Phase 0 decision and CI/Compose config. |
| R-19 | Amadeus scope consumes time or creates rate-limit/credential failures without improving required marks. | 3 | 4 | 12 | Complete and evidence the seeded catalogue first; require traceability and a tested fallback before adding a provider. | Provider work is deferred whenever a mandatory gate is incomplete. | Mitchell | Scope review in every planning change. |
| R-20 | Prompt/development logs become unverifiable claims or academic-integrity risk. | 3 | 4 | 12 | Record task, models, prompt versions, outputs, human decision, validation, and commit/PR/evidence link. | Incomplete record cannot be cited in the report until corrected. | Mitchell | Weekly evidence audit. |
| R-21 | Demo/report evidence is collected too late or misses individual participation. | 3 | 5 | 15 | Capture evidence at each phase; maintain paths in the checklist; rehearse Mitchell's segment. | Missing path in Phase 11 blocks done; rerun/reshoot before submission. | Mitchell + report/video owners | Weekly checklist review and rehearsal. |
| R-22 | The agentic loop is added only for the demonstration instead of being used throughout development. | 3 | 5 | 15 | Establish the shared service in Phase 1 and require finalised pre/post records in every meaningful later phase. | Missing phase records block the loop evidence gate even if the final demo works. | Team AI owner + Mitchell | Record audit in Phase 8. |
| R-23 | The Vue/ASP.NET technology approval cannot be proven against the written Python/Flask/HTMX specification. | 3 | 5 | 15 | Preserve the tutor's written clarification or obtain a dated confirmation and cite it in planning/report evidence. | If no durable evidence exists, ask for written confirmation before final report claims. | Mitchell | Approval artefact path in Phase 0. |

## 3. Active Actions

| Priority | Action | Due phase | Status |
|---:|---|---:|---|
| 1 | Confirm folder, route, ports, service names, theme, model tags, and shared-file ownership. | 0 | Complete |
| 2 | Replace the three placeholder accommodation Dockerfiles and extend Student 1 CI to build and test the real services. | 2 / 10 | Open |
| 3 | Implement idempotent seed data and 10-record assertions. | 3 / 4 | Open |
| 4 | Implement deterministic application fallback before connecting Ollama. | 5 | Open |
| 5 | Run the bounded two-model service with distinct installed models and finalise a genuine correction record. | 1 | Open |
| 6 | Integrate from the shared page and full Compose stack before report work. | 9 | Open |

## 4. Accepted Constraints

- Local Ollama latency depends on demonstration hardware; exact tags and timings must accompany evidence.
- Model recommendations/reviews are advisory. Application validators and human review own correctness.
- Release 0 is classroom-scale, so synchronous HTTP, one SQLite store, and one shared Ollama runtime are proportionate.

## 5. Review Rule

When a risk changes score, mitigation, owner, or status, record the date and reason in `review-record.md` and update this file in the same change.
