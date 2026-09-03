# Student 3 Contribution Log

Do not claim a commit, pull request, review, attendance event, or demonstration until its durable evidence exists.

| Date | Contribution | Files/scope | Validation or review evidence | Commit/PR |
|---|---|---|---|---|
| 2026-09-01 | Built attraction CRUD core: SQLite schema, seed data (12 attractions, 14 reviews), database API, and the backend proxy API. | `student-3/database/`, `student-3/backend/app.py`, `student-3/backend/database_client.py` | Database + backend tests passing at commit time | `8525cae` (PR #17) |
| 2026-09-01 | Removed a dangling placeholder AI form left over from before the real recommend integration. | `student-3/frontend/` | Manual verification | `1d8f0b0` (PR #23) |
| 2026-09-01 | Implemented the `/api/recommend` Plan → Act → Observe → Adapt loop against Ollama/Qwen, with closed-context prompting, an on-topic usability check, a narrower-prompt retry, and a deterministic fallback. | `student-3/backend/recommend.py` | `test_recommend.py` (mocked Ollama) plus live verification against a real `qwen2.5:3b` container | `0d11095` (PR #24) |
| 2026-09-03 | Finished attraction card rendering (browse/filter read view) and hardened `student-3.yml`: pytest stage, Compose config validation, image builds, db-init run, service startup with health waits, and a live smoke test asserting all three `/health` endpoints and ≥10 seeded attractions. | `student-3/frontend/`, `.github/workflows/student-3.yml` | CI workflow run (see Human Evidence To Add) | `7e8578d` (PR #35) |
| 2026-09-03 | Closed the frontend CRUD gap: added create/edit/delete UI for attractions and a review-submission form, plus an inline `json-body` htmx extension fixing a discovered request-encoding bug against the JSON-only backend endpoints. | `student-3/frontend/app.js`, `index.html`, `style.css` | `pytest tests` 29/29 pass (unmodified); manual curl round-trip against live containers (create/update/review/delete, plus both validation-error paths) | `517a92a` (PR #38, open as of this log) |

Branch: `KSS/Documentation` (PR #38 — CRUD UI change; despite the branch name, documentation was added in a separate pass, see below).

## Documentation Added

| Date | Contribution | Files | Commit/PR |
|---|---|---|---|
| 2026-09-04 | Added `requirements.md`, `featureplan.md`, `riskplan.md`, `architecture.md`, `reviewrecord.md`, `contributionlog.md` (this file), and `knownissues.md`. Same commit also confirmed and fixed the `currentCategory` filter-preservation bug (`riskplan.md` R-06) via a real Playwright browser pass against the integrated app, with evidence screenshots. | `student-3/docs/`, `student-3/frontend/app.js`, `student-3/frontend/index.html` | `python -m pytest tests` 29/29 pass, unchanged; browser verification evidence in `student-3/docs/evidence/` | This commit (see `git log` on `KSS/Documentation`, immediately after `517a92a`) |

## Human Evidence To Add

- Pull request #38 merge decision and reviewer sign-off.
- Successful `student-3.yml` GitHub Actions run URL/screenshot for the PR #38 branch.
- Manual browser verification of the PR #38 UI (see `review-record.md` and `known-issues.md`).
- A finalised shared agentic-loop record referencing real student-3 work.
- Week 6 attendance checkpoint.
- Group showcase video URL and my (Khushi's) segment timestamp.
