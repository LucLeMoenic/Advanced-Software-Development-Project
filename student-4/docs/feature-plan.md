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
- Add Vitest/jsdom coverage and a deterministic packaging validation.

Exit: frontend tests and packaging pass; browser checklist is prepared.

### Stage 5: Integration and CI

- Add production Dockerfiles, nginx proxying, root Compose services, persistent
  storage, health/dependency ordering, shared route/card, and model setting.
- Replace Student 4 CI with frontend/.NET tests, Compose validation, image
  builds, Ollama-independent startup, health/API smoke tests, count assertions,
  and unconditional teardown.

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