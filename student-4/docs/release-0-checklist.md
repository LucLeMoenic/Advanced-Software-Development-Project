# Student 4 Release 0 Checklist

Status date: 2026-09-03

## Produced Locally

- [x] Three real service implementations and production Dockerfiles exist.
- [x] Database API owns EF Core, SQLite, migrations, constraints, and seeding.
- [x] Backend accesses persistence only through a typed HTTP client.
- [x] Public budget and expense CRUD endpoints are implemented.
- [x] Fixed-rate conversion is authoritative and snapshots are persisted.
- [x] Dashboard totals and status thresholds are deterministic.
- [x] Strict Ollama response validation, one retry, and fallback are implemented.
- [x] Frontend CRUD, conversion preview, advice, loading/error/empty states, and confirmations are implemented.
- [x] Shared Vue card, `/budget/`, and `/budget-api/` integration are implemented.
- [x] Root Compose contains frontend/backend/database health dependencies and storage.
- [x] Student 4 GitHub Actions workflow contains test/build/smoke/count/fallback/teardown stages.
- [x] Database tests pass: 12/12.
- [x] Backend tests pass: 31/31.
- [x] Frontend tests pass: 10/10.
- [x] Student 4 frontend package build passes with locally bundled HTMX.
- [x] Shared Vue production build passes after card integration.
- [x] Direct database/backend HTTP smoke passes health, 12/24 seed counts,
  six-category dashboard, budget and expense CRUD, authoritative conversion,
  and unavailable-Ollama fallback.
- [x] Required Student 4 design, risk, architecture, evidence, and operational documents exist.

## Pending Environmental or Human Evidence

- [ ] `docker compose config --quiet` passes. Local attempt blocked because `docker` was not available on `PATH`.
- [ ] All four required images build in Docker.
- [ ] Three Student 4 containers report healthy and the shared route responds.
- [ ] Containerised database API confirms exactly 12 budgets and 24 expenses.
- [ ] Browser CRUD and responsive checklist is completed by Liam.
- [ ] Live Ollama returns a valid `ai` or `ai_retry` response.
- [ ] Forced-unavailable Ollama returns `fallback` in the Compose stack. Direct-service fallback is verified.
- [ ] Shared two-model development loop runs with distinct configured models and real before/after tests.
- [ ] Liam supplies the loop keep/change/reject decision.
- [ ] Student 4 GitHub Actions run passes after push.
- [ ] Screenshots and report evidence are captured.
- [ ] Liam records commits, PR/review, attendance, and contribution confirmation.
- [ ] The team publishes the showcase video and records its URL.

## Human Evidence Placeholders

- GitHub Actions run URL: `[pending]`
- Pull request URL: `[pending]`
- Commit range: `[pending]`
- Browser screenshot folder/link: `[pending]`
- Agentic-loop record: `[pending]`
- Liam Adapt decision: `[pending]`
- Attendance checkpoint: `[pending]`
- Showcase video URL: `[pending]`