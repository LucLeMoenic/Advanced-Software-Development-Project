# Budget & Expense Tracker Requirements

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
| NFR-10 | Scope | Release 0 adds no authentication, cloud, MCP, RAG, multi-agent, payment/bank, live-rate, or cross-feature integration. |

## Evidence Requirements

| ID | Evidence | Source |
|---|---|---|
| EV-01 | Frontend behavior suite result | `npm test --prefix student-4/frontend` |
| EV-02 | Frontend packaging result | `npm run build --prefix student-4/frontend` |
| EV-03 | Backend test result | `dotnet test student-4/backend/tests/Backend.Tests.csproj` |
| EV-04 | Database test result and seed counts | `dotnet test student-4/database/tests/Database.Tests.csproj` and database API counts |
| EV-05 | Compose configuration and image build | `docker compose config --quiet` and targeted `docker compose build` |
| EV-06 | Integrated health and HTTP boundary | Health URLs plus backend/data API requests after Compose startup |
| EV-07 | Browser CRUD, conversion, status, and responsive checks | Liam-completed frontend browser checklist and screenshots |
| EV-08 | AI success and forced fallback | Captured responses from live Ollama and unavailable/invalid-model scenarios |
| EV-09 | GitHub Actions execution | Repository Actions run URL and screenshot supplied after push |
| EV-10 | Development agentic loop | Shared runner record with real tests and Liam's explicit keep/change/reject decision |
| EV-11 | Collaboration and publication | Commit/PR log, attendance checkpoint, and showcase URL supplied by Liam |

## Traceability

| Requirement group | Implementation stage | Verification |
|---|---|---|
| FR-04, FR-05, FR-10, FR-11, FR-16 | Stage 1: database API | Database integration tests; EV-04 |
| FR-01-FR-09, FR-16 | Stage 2: backend orchestration | Backend client/endpoint/calculator tests; EV-03 |
| FR-12-FR-15 | Stage 3: Ollama insights | Strict-output, retry, failure, and fallback tests; EV-03 and EV-08 |
| FR-01, FR-02, FR-07-FR-09, NFR-01-NFR-03 | Stage 4: frontend | Vitest/jsdom; EV-01, EV-02, EV-07 |
| FR-17, FR-18, NFR-07-NFR-09 | Stage 5: integration and CI | Compose config/build/smoke; EV-05, EV-06, EV-09 |
| NFR-10, EV-10, EV-11 | Stage 6: evidence reconciliation | Document review and human-supplied records |

All implementation and tests are initially pending. A requirement becomes
verified only when its listed evidence is actually produced.