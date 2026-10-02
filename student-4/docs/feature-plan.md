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

Status checked 2026-10-02 at revision `3e8be05` on branch
`BCP/R1_Budget_Validation_CI`. The cancellation-focus fix remains uncommitted,
but its final browser replay passed. Detailed live results and
limitations are in the [Release 1 runbook](release-1-runbook.md) and
[live-validation record](evidence/release-1/live-validation-2026-10-02.md).

1. **Modes/capabilities - implemented and tested:** strict flags and
  `GET /api/capabilities`; disabled advice preserves fallback behavior.
2. **MCP budget check - integrated and verified:** the UI-to-backend-to-native
  MCP callback returned HTTP 200 and matched every dashboard field/category.
  Before/after dashboard, budgets and expenses were byte-identical (12/26).
3. **Student 4 RAG - integrated and verified:** five answerable live gateway
  questions returned exact cited source paragraphs; the unsupported Mars query
  abstained in the UI. Earlier freeform failures remain preserved as history.
4. **Static UI - integrated and verified:** real budget/expense create, read,
  update and confirmed delete flows were exercised and cleaned up; canceling
  delete dialogs preserved records and focus. Screenshots at 320/768/1280px
  showed no horizontal overflow. After guidance cancellation, the final browser
  replay confirmed the visible cancelled status, request abort (`net::ERR_ABORTED`),
  and focus restoration to `guidance-question`. The frontend image was rebuilt
  and its container reported healthy.
5. **CI - passed:** Linux Actions run [36947214508](https://github.com/LucLeMoenic/Advanced-Software-Development-Project/actions/runs/36947214508)
  passed at the implementation commit with 439 tests; 19 live RAG tests were
  skipped and all six AI/MCP/RAG flags were false. Windows local `All` remains
  subject to its symlink privilege limitation.
6. **Shared validation loop - records produced, not finalised:** fresh MCP/RAG
  records both passed their runtime contracts and post-loop backend/frontend
  suites passed 136/136 and 19/19. Both records have null human decisions and
  post-tests; Liam's decisions and finalisation remain pending.
7. **Release evidence - partial:** Student 4 implementation criteria 2-7 have
  substantial implementation/runtime/CI evidence. All-five-feature integration,
  final group PDF/video links, attendance, Q&A and release sign-off are not
  established. The five PRs (#104-#108) remain open/unmerged pending human review.

Two independent functional/rubric reviews found no current Student 4 functional
blocker. No grade, group-wide completion, PR approval, or human loop decision is implied.