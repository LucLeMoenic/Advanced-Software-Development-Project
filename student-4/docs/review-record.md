# Student 4 Review Record

## 2026-09-03 Repository and Design Review

Reviewer: GitHub Copilot, acting as an AI programming assistant for Liam
Zelmanowski.

### Scope Reviewed

- Release 0 project specification and assessment brief.
- Existing root Compose, environment, shared home, nginx, and visual system.
- Student 4 placeholders.
- Relevant Student 1 ASP.NET Core, EF Core, typed HTTP client, Ollama validation,
  integration-test, health-check, and Docker conventions.
- Relevant Student 2 static frontend, nginx, Vitest, CI smoke-test, and
  documentation conventions.

### Findings

| Severity | Finding | Resolution |
|---|---|---|
| Required | Student 4 has only placeholder Dockerfiles and a placeholder README; no functional frontend, backend, database API, tests, shared route, or CI validation exists. | Implement the complete approved Student 4 Release 0 slice. |
| Required | Root Compose exposes only `student4-frontend`; backend/database services, health dependencies, persistent storage, and model settings are absent. | Add the fixed three-service dependency chain and shared model dependency. |
| Required | The shared home links directly to diagnostic port 5104 and nginx has no `/budget/` or `/budget-api/` routes. | Replace the card and add supported same-origin routes. |
| Non-blocking | The specification's example stack is Flask, while the approved design uses ASP.NET Core 8. | Follow the repository's established Student 1 ASP.NET pattern while preserving the required architecture. |
| Non-blocking | The brief calls the shared index HTMX, while the repository's current shared home is Vue. | Preserve the integrated Vue home; use local HTMX only in Student 4. |

No existing Student 4 business implementation was available to review. No
passing behavior or human approval is claimed by this record.

## 2026-09-03 Implementation Self-Review

- Confirmed only the database project references EF Core/SQLite.
- Confirmed public expense input has no converted-value fields and unknown JSON
  members are rejected.
- Added database-side protection against changing a budget currency when
  conversion snapshots exist.
- Changed successful-delete focus restoration to a durable add command after a
  frontend test exposed focus loss during rerender.
- Confirmed database, backend, and frontend suites pass locally.
- Confirmed Student 4 and shared frontend package builds pass locally.
- Left Docker, browser, live-model, agentic-loop, GitHub Actions, and all
  human-only evidence pending rather than inferring results.

Liam's OBSERVE feedback and approval remain pending.

## 2026-09-03 Independent Review Resolution

A read-only code reviewer identified seed restart collisions, eager shared-nginx
upstreams in scoped CI, omitted request dates, stale frontend state,
period-aggregate row duplication, uncaught malformed dashboard data, non-atomic
journey currencies, and incomplete typed-client collection validation.

All substantiated findings were corrected and covered by focused tests. The
final independent review verdict was PASS with no blocking or high-severity
defects. Two proposed changes were intentionally not applied:

- Normal Compose still waits for completed model setup because the approved
  architecture explicitly requires that dependency. Automated CI starts the
  same backend image without Ollama and proves deterministic fallback.
- Public requests containing client-computed converted values are rejected,
  because the approved contract says those values are not authoritative; valid
  expense create/update requests omit them and are always recomputed.

Docker runtime, manual browser/accessibility, live Ollama, shared agentic-loop,
GitHub Actions, and Liam's review remain pending.

## 2026-09-03 Direct Integration Smoke

The real database and backend processes were started against a temporary SQLite
file. Health requests succeeded; startup produced 12 budgets and 24 expenses;
the Sydney dashboard returned AUD totals and six categories; a budget and
expense completed create/update/delete; 101 USD converted authoritatively to
155 AUD at rate snapshot 153846154; and unavailable Ollama returned
`source: fallback`.

This smoke exposed and led to correction of null-note response validation in
the typed database client. Its regression passes in the final backend suite.
Both processes and all temporary SQLite files were removed afterward. This is
local service evidence, not Docker, shared-nginx, browser, or live-model proof.

## 2026-09-03 Pull Request Packaging Review

The current uncommitted tree was reviewed for dependency order, buildability,
test ownership, shared integration risk, and GitHub Actions entry points. It is
packaged as three stacked local branches: data foundation, service API, and app
integration. Exact per-commit file lists, short messages, validation commands,
branch transitions, PR bases, and merge order are recorded in `pr-plan.md`.

The CI-equivalent `npm run validation` command passed and all four Student 4
PowerShell scripts parsed with zero errors. Docker remains unavailable locally,
so `npm run docker-validation` and GitHub Actions container evidence remain
required before PR 3 approval. No commit or push was performed by Copilot.