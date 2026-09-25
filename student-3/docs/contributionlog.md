# Student 3 Contribution Log

Do not claim a commit, pull request, review, attendance event, or demonstration until its durable evidence exists.

| Date | Contribution | Files/scope | Validation or review evidence | Commit/PR |
|---|---|---|---|---|
| 2026-09-01 | Built attraction CRUD core: SQLite schema, seed data (12 attractions, 14 reviews), database API, and the backend proxy API. | `student-3/database/`, `student-3/backend/app.py`, `student-3/backend/database_client.py` | Database + backend tests passing at commit time | `8525cae` (PR #17) |
| 2026-09-01 | Removed a dangling placeholder AI form left over from before the real recommend integration. | `student-3/frontend/` | Manual verification | `1d8f0b0` (PR #23) |
| 2026-09-01 | Implemented the `/api/recommend` Plan → Act → Observe → Adapt loop against Ollama/Qwen, with closed-context prompting, an on-topic usability check, a narrower-prompt retry, and a deterministic fallback. | `student-3/backend/recommend.py` | `test_recommend.py` (mocked Ollama) plus live verification against a real `qwen2.5:3b` container | `0d11095` (PR #24) |
| 2026-09-03 | Finished attraction card rendering (browse/filter read view) and hardened `student-3.yml`: pytest stage, Compose config validation, image builds, db-init run, service startup with health waits, and a live smoke test asserting all three `/health` endpoints and ≥10 seeded attractions. | `student-3/frontend/`, `.github/workflows/student-3.yml` | CI workflow run (see Human Evidence To Add) | `7e8578d` (PR #35) |
| 2026-09-03 | Closed the frontend CRUD gap: added create/edit/delete UI for attractions and a review-submission form, plus an inline `json-body` htmx extension fixing a discovered request-encoding bug against the JSON-only backend endpoints. | `student-3/frontend/app.js`, `index.html`, `style.css` | `pytest tests` 29/29 pass (unmodified); manual curl round-trip against live containers (create/update/review/delete, plus both validation-error paths) | `517a92a` (PR #38, open as of this log) |
| 2026-09-06 | Used the shared two-model agentic loop (implementer `qwen2.5:3b`, reviewer `llama3.2:3b`) to implement `formatElapsed(seconds)` for the "Get Recommendation" wait indicator. Rejected both hallucinated reviewer REQUIRED findings and fixed the implementer's arithmetic bug in the human Adapt phase; finalised the record as `changed`. | `student-3/frontend/index.html`, `docs/agentic-loop-records/20260906T104055Z-f52cc6be69164e07b0502a263671ee67.json`, `student-3/docs/prompt-log.md` | `node -e` post-test, 6/6 assertions pass (0, 1, 2, 14, 45, 52); phase-by-phase analysis in `reviewrecord.md` 2026-09-25 | `eb40659` (PR #55) |
| 2026-09-25 | Release 1 Stage 1: added Student 3's `attractions.search`/`attractions.get_reviews` read-only MCP tools (category enum, limit ≤10, unknown-field rejection via `extra="forbid"`) on the shared MCP server, and an 8-doc RAG knowledge base under `ai-services/rag-server/knowledge/student-3/`. Fixed a real retrieval bug found while validating it (no stopword stripping let irrelevant questions score ~0.25, too close to genuine 0.27-0.40 matches). Used the shared agentic loop (first live run of `reviewer-student3-v1.md`) to add a `total_matches` field to `attractions.search`; rejected a hallucinated BLOCKING finding and finalised the record as `changed`. | `ai-services/mcp-server/tools/attractions.py`, `ai-services/mcp-server/tests/`, `ai-services/rag-server/knowledge/student-3/`, `ai-services/rag-server/retrieval.py`, `ai-services/rag-server/tests/`, `docs/agentic-loop-records/20260925T085024Z-68a0be4d595440b99e2275569c55786f.json` | `pytest tests` — 16/16 passing (`ai-services/mcp-server`), 4/4 passing (`ai-services/rag-server`); phase-by-phase analysis in `reviewrecord.md` 2026-09-25 (Stage 1 entry) | pending (branch `KSS/r1-knowledge-and-tools`, not yet committed) |

Branch: `KSS/Documentation` (PR #38 — CRUD UI change; despite the branch name, documentation was added in a separate pass, see below).

## Documentation Added

| Date | Contribution | Files | Commit/PR |
|---|---|---|---|
| 2026-09-04 | Added `requirements.md`, `featureplan.md`, `riskplan.md`, `architecture.md`, `reviewrecord.md`, `contributionlog.md` (this file), and `knownissues.md`. Same commit also confirmed and fixed the `currentCategory` filter-preservation bug (`riskplan.md` R-06) via a real Playwright browser pass against the integrated app, with evidence screenshots. | `student-3/docs/`, `student-3/frontend/app.js`, `student-3/frontend/index.html` | `python -m pytest tests` 29/29 pass, unchanged; browser verification evidence in `student-3/docs/evidence/` | This commit (see `git log` on `KSS/Documentation`, immediately after `517a92a`) |

## Human Evidence To Add

- Pull request #38 merge decision and reviewer sign-off.
- Successful `student-3.yml` GitHub Actions run URL/screenshot for the PR #38 branch.
- Manual browser verification of the PR #38 UI (see `review-record.md` and `known-issues.md`).
- Terminal screenshots of the agentic-loop `run` and `finalise` invocations (the finalised record itself is logged above under PR #55).
- Week 6 attendance checkpoint.
- Group showcase video URL and my (Khushi's) segment timestamp.
