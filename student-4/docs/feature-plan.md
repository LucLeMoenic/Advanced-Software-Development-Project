# Budget & Expense Tracker Feature Plan

## High-Level Design

Implement three independently containerised Student 4 services behind the
existing shared frontend. The static frontend presents complete budget and
expense CRUD. The backend owns public validation, deterministic conversion and
aggregation, and optional AI advice. The database API owns EF Core, SQLite,
migrations, constraints, and idempotent sample data.

## Delivery Stages

### Stage 0: Plan

- Validate scope against the Release 0 brief and current repository.
- Define testable functional, non-functional, and evidence requirements.
- Define service/data/Compose/DevOps architecture and risk controls.

Exit: no unresolved architecture blocker; documents reflect approved scope.

### Stage 1: Database API

- Create ASP.NET Core 8 database service, entities, EF configurations, initial
  migration, repositories, validation, stable errors, filters, and health.
- Add 12 budgets and 24 expenses through idempotent initialization.
- Add temporary-SQLite integration tests for migrations, CRUD, filtering,
  conflicts, foreign keys, cascade delete, exact integer storage, and seeds.

Exit: database tests pass and both tables contain at least ten rows.

### Stage 2: Backend API

- Add typed database client and stable dependency-error mapping.
- Add public budget/expense CRUD, journey list, currencies, conversion preview,
  and deterministic dashboard endpoints.
- Add fixed-rate provider configuration and unit/integration tests.

Exit: backend CRUD, conversion, aggregation, status, validation, and dependency
tests pass without EF Core or SQLite references.

### Stage 3: Application AI

- Add versioned prompt and typed Ollama client.
- Send an allow-listed dashboard summary as untrusted data.
- Require complete strict JSON, reject unknown fields/categories, retry once,
  and return deterministic fallback advice for every model failure.

Exit: valid, retry, malformed, partial, wrapped, unknown, extra-field, timeout,
connection, HTTP, and no-data tests pass without a live LLM.

### Stage 4: Frontend

- Build the working dashboard as the first screen using semantic HTML,
  feature CSS, vanilla JavaScript, and locally bundled HTMX.
- Implement budget/expense CRUD, conversion preview, notices, insights,
  accessible dialogs, status/error/empty/loading states, and safe rendering.
- Add separate Release 1 MCP budget-check and grounded-guidance controls, gated
  by `/api/capabilities`, with exact safe-integer money display and stale-request
  protection.
- Add Vitest/jsdom coverage and a deterministic packaging validation.

Exit: frontend tests and packaging pass; browser checklist is prepared.

### Stage 5: Integration and CI

- Add production Dockerfiles, nginx proxying, root Compose services, persistent
  storage, health/dependency ordering, shared route/card, and model setting.
- Replace Student 4 CI with frontend/.NET tests plus direct shared-Compose
  validation, image builds, model-independent health/API smoke tests, count
  assertions, and unconditional teardown. Do not add a Student 4-only Compose or
  container lifecycle path.

Exit: local config, builds, health, seeded API, and supported route checks pass,
or any environmental blocker is recorded precisely.

### Stage 6: Evidence Reconciliation

- Reconcile README, checklists, contribution log, known issues, prompt log, and
  review record with observed results only.
- When configured models are available, use the shared two-model loop for one
  bounded genuine change and leave final Adapt to Liam.

Exit: ACT report distinguishes produced evidence from human-only pending work.

## Development Method

Each substantive edit is followed by the narrowest relevant check. A failed
check is repaired in the same slice and rerun before implementation expands.
Liam performs all commits, pushes, PRs, approvals, attendance records, browser
acceptance, and showcase publication.

## Release 1 Delivery

Retain the current static HTML/JavaScript/HTMX frontend and deterministic budget
backend. Add a read-only `budget.get_summary` MCP tool whose fixed callback reads
the existing dashboard endpoint, and separate grounded budgeting guidance using
shared native RAG with `feature: student-4`, validated citations, and explicit
insufficient-context abstention. Keep Ollama advice distinct, preserve database
ownership, and make no schema changes or cross-student calls.

1. **Mode controls and capabilities - implemented:** strict lowercase mode flags
  with AI on and MCP/RAG off by default; `GET /api/capabilities`; disabled AI
  advice uses existing fallback with no Ollama call. Backend tests pass 68/68.
2. **MCP budget check - implemented, offline-tested:** registered read-only
  `budget.get_summary` with a fixed dashboard callback and added `POST
  /api/budget-check`. Strict bounded request parsing, response validation,
  stable failures, cancellation, the browser safe-integer boundary, and an
  in-process official SDK call are covered. Student 4 backend tests pass 106/106;
  shared MCP tests pass 120/120. Live native/container connectivity, callback
  re-entry, and database non-mutation evidence remain pending.
3. **Student 4 RAG guidance - implemented, offline-tested, direct live selection
  checked:** added three source-grounded knowledge documents and `POST
  /api/budget-guidance`. The shared native RAG model now selects one to three
  retrieved paragraph IDs only for Student 4; the service returns their exact
  full source text with citations. Strict parsing, feature isolation, selection
  validation, exact abstention, size limits and timeout/error mapping have
  focused tests. The final direct `llama3.2:3b` set grounded all five answerable
  questions and abstained on Mars. The Student 4 backend route, browser flow,
  loop, CI and release acceptance remain open.
4. **Static UI - implemented, offline-tested:** added compact MCP budget-check
  and separate RAG-guidance panels without replacing the existing frontend or
  combining guidance with private financial data. Capabilities fail closed for
  new controls only; safe money formatting, request invalidation, response states,
  and text-only citation rendering have Vitest coverage. Browser/live acceptance
  and responsive viewport evidence remain pending.
5. **Integration and evidence - planned:** validate native connectivity, mode-off
  behavior, live MCP/RAG paths, accessibility, and the affected release gates.

Steps 1-3 have offline evidence; direct live RAG selection is now observed as
recorded above. Static UI acceptance, integrated MCP/RAG validation, loop/CI and
release evidence remain pending; no human review or release sign-off is recorded
here.