# Budget & Expense Tracker Requirements

**Current checkpoint - 2026-10-23:** Release 2 is implemented in the uncommitted
workspace. R0/R1 tables below retain their historical release scope and evidence;
current R2 acceptance IDs follow at the end. Use the
[runbook](release-2-runbook.md) and
[dated evidence](evidence/release-2/validation-2026-10-23.md) for current limits.

## Functional Requirements

| ID | Requirement | Acceptance criterion |
|---|---|---|
| FR-01 | The browser shall manage category budgets through the Student 4 backend. | Create, list, read, update, and confirmed delete work through `/budget-api/budgets`; deleting a budget cascades its expenses. |
| FR-02 | The browser shall manage expenses through the Student 4 backend. | Create, list, read, update, and confirmed delete work through `/budget-api/expenses`. |
| FR-03 | Budgets shall be grouped by locally owned journey labels. | `/api/journeys` returns distinct labels and no external itinerary identifier is stored or requested. |
| FR-04 | Budget input shall enforce category, date, positive amount, currency, uniqueness, and one-currency-per-journey rules. | Invalid input returns 400; duplicate periods or mixed journey currencies return 409 without persistence. |
| FR-05 | Expense input shall enforce description, amount, supported currency, notes length, and in-period spent date. | Invalid input returns 400 without persistence. |
| FR-06 | The backend shall perform authoritative deterministic currency conversion. | Preview and save use configured decimal rates; save/update ignore client conversion fields, round once to minor units, and persist the rate snapshot and date. |
| FR-07 | The dashboard shall calculate journey and category totals. | Planned, actual, remaining, percentage, and base currency equal deterministic sums of persisted minor units. |
| FR-08 | The dashboard shall classify category spending deterministically. | Under 80% is `within_budget`, 80%-100% is `warning`, and over 100% is `overspent`. |
| FR-09 | The application shall display original and converted expense values. | Ledger rows include original currency/amount, converted currency/amount, rate, and rate date. |
| FR-10 | The database API shall own SQLite persistence. | Only the database project references EF Core SQLite or opens `budget.db`; backend persistence is HTTP-only. |
| FR-11 | The database shall contain idempotent representative data. | Re-running initialization creates no duplicates and leaves at least 12 budgets and 24 expenses. |
| FR-12 | The backend shall generate optional budget advice through shared Ollama. | A usable journey causes one strict-JSON model request; valid output returns `source: ai`. |
| FR-13 | Invalid model output shall receive one bounded corrective retry. | A first invalid complete response triggers exactly one narrower request; valid retry returns `source: ai_retry`. |
| FR-14 | AI failure shall preserve useful deterministic advice. | Timeout, connection, HTTP, malformed, wrapped, partial, extra-field, unknown-category, or twice-invalid output returns `source: fallback`. |
| FR-15 | Model output shall never mutate or authoritatively calculate data. | Insight requests perform no write calls; all monetary values/statuses originate from backend calculations. |
| FR-16 | The backend and database APIs shall return stable errors. | Errors use `{error:{code,message,fields,correlationId}}` with appropriate 400, 404, 409, 502, or 503 status. |
| FR-17 | The unified application shall expose Student 4 through same-origin routes. | `/budget` redirects to `/budget/`; `/budget/` serves the app; `/budget-api/` reaches the backend. |
| FR-18 | All three Student 4 services shall be independently containerised and healthy. | Ports 5104, 5204, and 5304 expose healthy services with the configured dependency order. |

## Non-Functional Requirements

| ID | Area | Acceptance criterion |
|---|---|---|
| NFR-01 | Accessibility | Forms have semantic labels, focus is visible, status is announced, dialogs are keyboard operable, and destructive operations require confirmation. |
| NFR-02 | Security | User/model text is rendered with text APIs; no unsafe user interpolation into `innerHTML`; prompts identify supplied labels as untrusted data. |
| NFR-03 | Responsiveness | No horizontal page scrolling at 320px, 768px, or 1280px browser widths. |
| NFR-04 | Reliability | Dashboard and CRUD remain available when Ollama is unavailable; dependency errors are bounded and mapped. |
| NFR-05 | Determinism | Money uses integer minor units and decimal-safe configured rates; model output does not affect totals or state. |
| NFR-06 | Maintainability | Explicit public DTOs, typed HTTP clients, replaceable exchange-rate provider, migrations, and focused tests are used. |
| NFR-07 | Isolation | Student 4 code contains no runtime calls to `student1-*`, `student2-*`, `student3-*`, or `student5-*`. |
| NFR-08 | Configuration | Dependency URLs, timeouts, model, rates, rate date, ports, and connection string are environment/configuration driven. |
| NFR-09 | CI | Student 4 CI tests all three services, validates the shared Compose file, builds the shared frontend plus Student 4 images, runs model-independent health/data/route smoke checks, and always tears down. |
| NFR-10 | Release 0 scope | Release 0 adds no authentication, cloud, MCP, RAG, multi-agent, payment/bank, live-rate, or cross-feature integration. Release 1 scope is defined separately below. |

## Evidence Requirements

| ID | Evidence | Source |
|---|---|---|
| EV-01 | Frontend behavior suite result | `npm test --prefix student-4/frontend` |
| EV-02 | Frontend packaging result | `npm run build --prefix student-4/frontend` |
| EV-03 | Backend test result | `dotnet test student-4/backend/tests/Backend.Tests.csproj` |
| EV-04 | Database test result and seed counts | `dotnet test student-4/database/tests/Database.Tests.csproj` and database API counts |
| EV-05 | Compose configuration and image build | `docker compose config --quiet` and targeted `docker compose build` |
| EV-06 | Integrated health and HTTP boundary | Health URLs plus backend/data API requests after Compose startup |
| EV-07 | Browser CRUD, conversion, status, and responsive checks | [Integrated live evidence and screenshots](evidence/release-1/live-validation-2026-10-02.md) |
| EV-08 | AI success and forced fallback | Captured responses from live Ollama and unavailable/invalid-model scenarios |
| EV-09 | GitHub Actions execution | [Student 4 Actions run 36947214508](https://github.com/LucLeMoenic/Advanced-Software-Development-Project/actions/runs/36947214508); run passed, with 19 live-model RAG tests skipped |
| EV-10 | Development agentic loop | Fresh MCP/RAG records under `docs/agentic-loop-records/`; Liam's explicit keep/change/reject decisions remain pending |
| EV-11 | Collaboration and publication | Student 4 contribution log; PRs #104-#108 plus the final integration PR into main; attendance and showcase evidence remain human-supplied |

## Traceability

| Requirement group | Implementation stage | Verification |
|---|---|---|
| FR-04, FR-05, FR-10, FR-11, FR-16 | Stage 1: database API | Database integration tests; EV-04 |
| FR-01-FR-09, FR-16 | Stage 2: backend orchestration | Backend client/endpoint/calculator tests; EV-03 |
| FR-12-FR-15 | Stage 3: Ollama insights | Strict-output, retry, failure, and fallback tests; EV-03 and EV-08 |
| FR-01, FR-02, FR-07-FR-09, NFR-01-NFR-03 | Stage 4: frontend | Vitest/jsdom; EV-01, EV-02, EV-07 |
| FR-17, FR-18, NFR-07-NFR-09 | Stage 5: integration and CI | Compose config/build/smoke; EV-05, EV-06, EV-09 |
| NFR-10, EV-10, EV-11 | Stage 6: evidence reconciliation | Document review and human-supplied records |

Implementation status is source-verified, but each requirement's acceptance
status depends on its listed evidence. The latest integrated run, post-tests and
known limitations are recorded in the Release 1 runbook; CI, direct model checks,
browser checks and human sign-off are distinct evidence types.

## Release 1 Requirements

| ID | Requirement | Acceptance criterion | State |
|---|---|---|---|
| R1-01 | Runtime modes shall be explicit and strict. | `AI_ENABLED` accepts exactly lowercase `true` or `false` and defaults to true; `MCP_ENABLED` and `RAG_ENABLED` accept the same values and default to false; invalid values fail startup. | Implemented; backend tests pass. |
| R1-02 | The backend shall expose enabled capabilities. | `GET /api/capabilities` returns boolean `aiEnabled`, `mcpEnabled`, and `ragEnabled` values matching configuration. | Implemented; backend tests pass. |
| R1-03 | Disabled AI advice shall remain useful without contacting Ollama. | Advice returns the existing deterministic `fallback` contract with zero Ollama-client calls; enabled `ai`, `ai_retry`, and failure fallback behavior remains unchanged. | Implemented; backend tests pass. |
| R1-04 | Budget check shall read authoritative current totals through MCP. | Read-only `budget.get_summary` uses a fixed callback to the existing dashboard endpoint; no second money calculator, database access, or write operation is introduced. | Integrated UI/backend/native MCP call passed; all summary fields/categories matched the dashboard; before/after read-only data was byte-identical (12 budgets/26 expenses). |
| R1-05 | Budgeting guidance shall be grounded in Student 4 knowledge. | Shared native RAG receives `feature: student-4`; the local model selects one to three retrieved paragraph IDs only, and the server returns their exact source text with validated citations. Invalid selections fail as dependency errors; insufficient context explicitly abstains; guidance does not consume private spending records. | Integrated UI/backend/RAG passed five answerable gateway cases with exact source text/citations and one UI Mars abstention. Fresh loop contract passed; human finalisation remains pending. Earlier freeform failures are retained as historical evidence. |
| R1-06 | Release 1 shall preserve the application boundaries. | Retain the static Student 4 UI and native Ollama/MCP/RAG arrangement; make no database schema changes or cross-student runtime calls. | Integrated UI CRUD/MCP/RAG, responsive checks, and final cancellation-focus replay passed; the focus fix is committed in `c282a73`, whose CI passed. Fresh checks of the resolved merge with main are required separately. Group acceptance and human release sign-off remain open. |

Historical baseline status (superseded 2026-10-02): R1-01 through R1-05 had
offline evidence only, and R1-06 was partially implemented at that checkpoint.
R1-01 through R1-06 have implementation evidence; integrated live and CI evidence
is distinguished in the state column and runbook. Fresh loop records are not
finalised: Liam's human decisions are absent. No group-wide completion, grade, or
release sign-off is implied.

## Release 2 Acceptance

These IDs scope Student 4 behavior and evidence; they do not award marks or
replace the integrated-group requirements in the
[Release 2 brief](../../docs/Project_Specifications/Release_2_brief.md).

| ID | Acceptance criterion | Current evidence or remaining gate |
|---|---|---|
| R2-01 | Preview replaces all existing category-aggregate limits exactly once; positive safe-integer amounts and total; deterministic planned/actual/remaining/percentage/status before and after. Actuals and saved data remain unchanged. | 74 focused calculator tests, included in 322 backend tests; recorded live EUR 3750 -> 3850 planned, EUR 4126.85 actual unchanged. |
| R2-02 | `POST /api/what-if/preview` accepts `{journeyLabel,limits}` and returns `{original,proposed,snapshotHash}` without requiring AI. Reject zero, incomplete, duplicate, unsafe or malformed proposals. | Implemented and covered by backend/frontend tests; real gateway preview captured. |
| R2-03 | `POST /api/what-if/workflows` requires the same complete proposal plus `snapshotHash`; return 202 `{id,status,token,preview,workflow}`. Poll and decide via `/api/what-if/workflows/{id}` and `/decision`, with `X-WhatIf-Token`. | Real native Planner/Worker/Reviewer reached `awaiting_human_review`; no real human completion yet. |
| R2-04 | Require explicit `approve`, `correct`, `partial` or `reject`, actual human name of 1-60 characters and notes <=1000. Reject needs nonblank notes; partial selects existing item IDs; correction changes commentary, never financial numbers. | All four paths covered with fake dependencies. A genuine human decision/name/notes and history remain pending. Name is self-declared, not authentication. |
| R2-05 | Protect workflow/preview binding for two hours; ephemeral backend restart invalidates tokens. Reject invalid tokens with 403 and stale snapshots with 409. Bound requests, responses, deadlines and retry behavior; do not automatically duplicate start/decision POSTs. | Implemented and tested; runbook documents recovery, Stop polling and Retry status. |
| R2-06 | Strict `MULTI_AGENT_ENABLED` defaults false and is surfaced as `multiAgentEnabled` in capabilities. Compose maps `STUDENT4_MULTI_AGENT_ENABLED` (default false) and shared `MULTI_AGENT_SERVER_URL`. | Source-confirmed; local demo explicitly true. Disabled review is 503 while preview/core CRUD remain available. |
| R2-07 | Retain Student 4 R0/R1 behavior, native Ollama/MCP/RAG/shared loop, database ownership and existing shared Multi-Agent Server. Add no schema, runtime dependency, financial-write or cross-student data path. | Local Ollama/Multi-Agent exercised. MCP/RAG currently false; retained behavior is not fresh live acceptance. |
| R2-08 | Show before/after preview, native workflow stages/findings and explicit human-review controls; safe text rendering, validation, stop/retry and no page overflow at 1280/768/320px. | 79 frontend tests/build and real gateway preview captures. Awaiting-human browser evidence needs main-session confirmation. |
| R2-09 | Run local pre-commit security checks and report skipped scans accurately; retain no new runtime dependencies. | Installed hook: Ruff security/detect-secrets passed; pip-audit skipped (no changed requirements). .NET transitive vulnerability check reported none. |
| R2-10 | Assigned CI explicitly tests preview and workflow-start endpoint functions and uploads TRX results after publication. | Filter/upload implemented; local backend passed. No new post-push remote CI run yet. |
| R2-11 | Demonstrate the complete integrated local application and integrated cloud baseline with all four AI modes off, working frontend/backend/database/CRUD and preview. | Four-container local subset only; cloud tooling tests 35 Student 4/210 related passed. Full-group/live-cloud/workflow evidence remains pending. |
| R2-12 | Reuse `review-multi-agent`, `review-testing`, `review-cloud`; retain real outputs, validation logs and human Adapt finalisation after actual post-tests. | Runnable commands documented; no new mode records/finalisation claimed. Group report/video/Q&A and release sign-off remain separate gates. |
