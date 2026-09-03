# Budget & Expense Tracker Context

## Ownership

- Owner: Liam Zelmanowski (Student 4)
- Release: Release 0
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

Neither point blocks implementation. Release 1 MCP/RAG and Release 2
multi-agent/cloud capabilities remain intentionally out of scope.

## Fixed Boundaries

- `student4-frontend`: static application and nginx, host 5104/container 80.
- `student4-backend`: public API and orchestration, host 5204/container 8080.
- `student4-database`: data API and SQLite owner, host 5304/container 8080.
- Browser API requests use `/budget-api/`.
- Internal database requests use `http://student4-database:8080`.
- Internal model requests use `http://ollama:11434`.
- No Student 4 service calls a Student 1, 2, 3, or 5 service.
- Money is represented as integer minor units at service and storage boundaries.
- Demonstration exchange rates are versioned configuration, never live data.

## Development Workflow

Development uses Plan -> Act -> Observe -> Adapt. This is evidence for the
development process and is not exposed as a Budget Tracker runtime workflow.
Liam supplies observations and the final keep/change/reject decision; those
human actions must not be inferred or pre-recorded.

## Evidence Policy

Documentation may record only observed command output or human-supplied
evidence. GitHub Actions success, screenshots, attendance, live Ollama output,
browser acceptance, showcase publication, commits, pushes, and approvals remain
pending until Liam or the relevant system produces them.