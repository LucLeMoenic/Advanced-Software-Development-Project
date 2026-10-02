# Budget & Expense Tracker Context

## Ownership

- Owner: Liam Zelmanowski (Student 4)
- Release: Release 1, preserving Release 0 functionality
- Feature: Budget & Expense Tracker
- Supported route: `http://localhost:5100/budget/`

## Problem

Travellers need one independent place to define category limits, record actual
spending in supported currencies, and see whether each category is within,
approaching, or beyond its budget. The feature groups records by a locally owned
`journeyLabel`; it does not read an itinerary or another student's data.

## Approved Release 0 Solution

The browser loads a static HTML/CSS/JavaScript application through the shared
frontend. That application calls only the Student 4 ASP.NET Core backend. The
backend validates public requests, performs deterministic currency conversion
and dashboard calculations, and accesses persistence only through the Student 4
database HTTP API. The database API alone owns EF Core, SQLite migrations, the
`budget.db` file, constraints, and demonstration-data initialization.

Optional budget advice is requested through the backend from the existing
shared Ollama runtime. The model receives only an allow-listed deterministic
summary and cannot control money values, status, persistence, CRUD, or HTTP
outcomes. Complete model output is validated; one corrective retry is allowed,
after which deterministic fallback advice is returned.

## Design Validation

The design satisfies the Release 0 brief's individual frontend, backend,
database, CRUD, ten-record, AI-mode, containerisation, Compose, DevOps, unified
home, and documentation responsibilities.

Two repository-specific decisions require explicit treatment:

1. The project specification lists Python and Flask as the teaching stack, but
   Student 1 already establishes ASP.NET Core 8 as an integrated repository
   pattern. The approved Student 4 ASP.NET design preserves all required HTTP
   and container boundaries.
2. The brief describes a shared HTMX index, while the current integrated home
   is Vue. Student 4 will preserve the existing shared Vue home and bundle HTMX
   locally only in its independently served static frontend.

Neither point blocks implementation. MCP/RAG was excluded from Release 0 and is
implemented by Release 1 below. Release 2 multi-agent/cloud work remains out of scope.

## Fixed Boundaries

- `student4-frontend`: static application and nginx, host 5104/container 80.
- `student4-backend`: public API and orchestration, host 5204/container 8080.
- `student4-database`: data API and SQLite owner, host 5304/container 8080.
- Browser API requests use `/budget-api/`.
- Internal database requests use `http://student4-database:8080`.
- Model requests reach native Ollama through the configured host URL; Compose uses `host.docker.internal:11434`.
- No Student 4 service calls a Student 1, 2, 3, or 5 service.
- Money is represented as integer minor units at service and storage boundaries.
- Demonstration exchange rates are versioned configuration, never live data.

## Release 1 Direction

The Release 1 scope adds a read-only budget check through `budget.get_summary`
and separate Student 4-grounded guidance through shared native RAG. The browser
remains static HTML/JavaScript/HTMX; backend/database ownership, native
Ollama/MCP/RAG, and the shared loop remain in place. No schema changes,
cross-student calls, model-authored money values, or autonomous writes are in
scope.

**SOURCE AND EVIDENCE CHECKPOINT - 2026-10-02:** The implementation is recorded
at revision `c282a73` on branch `BCP/R1_Budget_Validation_CI`; the cancellation-
focus correction is committed and its final browser replay passed. Integration
with newer main changes is being resolved on `BCP/R1_Budget_RAG`; earlier CI
and runtime results do not certify the combined merge. The
live evidence is in
[`live-validation-2026-10-02.md`](evidence/release-1/live-validation-2026-10-02.md).
The real MCP journey check returned the same complete dashboard summary, and
read-only before/after lists and dashboard were byte-identical (12 budgets,
26 expenses). The integrated UI exercised MCP and RAG, including exact-source
citations, an insufficient-context response, temporary budget/expense CRUD and
cleanup; seeded records remained unchanged. Screenshots at 320/768/1280px show
no page-level overflow. Release 0 insights returned `source=ai` in the earlier
capture.

The Student 4 extractive RAG mode selects retrieved paragraph IDs and returns
their exact source text. Five answerable live cases were grounded and the Mars
negative case abstained; earlier freeform failures and prompt iterations remain
historical. Linux Actions run [36947214508](https://github.com/LucLeMoenic/Advanced-Software-Development-Project/actions/runs/36947214508)
passed at the implementation commit: 439 tests (frontend 19, backend 136,
database 12, loop 61, MCP 120, RAG 91), with 19 live-model RAG tests skipped;
all six AI/MCP/RAG mode flags were false in CI. This does not replace live
acceptance or establish group completion.

Fresh MCP and RAG loop records each have `contractPassed=true`, but both retain
`humanDecision=null`, `postTest=null`, and no finalisation. The post-loop
backend/frontend suites separately passed 136/136 and 19/19. Human loop
decisions, PR review/merge, and group report/video/attendance evidence remain
pending. Do not infer them from CI,
reviewer output, source quotations, or this status note. Compose uses
Student4-prefixed mode variables; `.env.example` enables them for an explicitly
started local demo.

## Development Workflow

Development uses Plan -> Act -> Observe -> Adapt. This is evidence for the
development process and is not exposed as a Budget Tracker runtime workflow.
The two required Student 4 validation-mode records exist; Liam still supplies
the explicit keep/change/reject decisions before either record is finalised.
Those human actions must not be inferred or pre-recorded.

## Evidence Policy

Documentation may record only observed command output or human-supplied
evidence. GitHub Actions success, screenshots, attendance, live Ollama output,
browser acceptance, showcase publication, commits, pushes, and approvals remain
pending until Liam or the relevant system produces them.