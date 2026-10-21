# Student 5 Release 2 Plan

Student 5 (Alex Chen), Travel Logistics & Advisory. Follow the
[Release 2 brief](../../docs/Project_Specifications/Release_2_brief.md) and
[project specifications](../../docs/Project_Specifications/Project_Specifications.md).
Release 0/1 functionality is retained; only the integrated group application is
assessed, so every Student 5 change must work inside the shared stack.

## Scope

Student 5's own frontend, backend/API and database microservices, plus the
Student 5 slice of shared artefacts (`docker-compose.yml` environment block, the
cloud smoke check and agentic-loop evidence). Other students' gaps are flagged to
their owners, not changed.

## What already exists and is reused

| Requirement | Existing shared work | Student 5 change |
| --- | --- | --- |
| Planner -> Worker -> Reviewer -> Human Review via terminal and UI | Native Multi-Agent Server, `ai-services/multi-agent-server/` (PR #112), CLI, hash-chained audit log | Backend client and routes, HTMX review panel, compose flags. No new agent runtime. |
| Agentic-loop review modes | `review-multi-agent`, `review-testing`, `review-cloud` in `ai-services/agentic-loop/` | Run each on Student 5 evidence and `finalise` with a human decision. |
| Pre-commit security scans | `.pre-commit-config.yaml`: Ruff `S` rules, detect-secrets, pip-audit, already covering `student-5/` | Run on a real commit, resolve or document findings, retire the Student 5 pip-audit exception. |
| Two endpoint tests in `student-5.yml` | Student 1/3 `test_endpoints_cicd.py` + `scripts/test/junit_summary.py` pattern | Create-destination and update-destination HTTP tests with JUnit artefact. |
| Cloud deployment with AI services off | `cloud-deployment.yml`, `scripts/deploy/prepare_cloud.py` (sets all four flags `false`), `smoke_cloud.py` | Honour `AI_ENABLED`; add a Student 5 CRUD check to the cloud smoke test. |

## New requirements

| ID | Requirement |
| --- | --- |
| TL-FR-16 | A traveller can request a **trip readiness review** for one destination. The backend sends that destination's weather notes, entry requirement and transit options as evidence to the shared Multi-Agent Server, and the UI shows the Planner plan, Worker checklist and Reviewer risks. |
| TL-FR-17 | The traveller records a human decision (approve, correct, partial acceptance, reject) on a completed review. Decisions are stored only in the shared workflow audit log; no Student 5 database row changes. |
| TL-FR-18 | `AI_ENABLED=false` disables the advisory: `POST /api/advisory` and the advisory UI return a clear "AI disabled" response without calling Ollama. |
| TL-NFR-10 | Multi-Agent, MCP and RAG are off unless explicitly enabled; AI-Mode is on unless `AI_ENABLED=false`. When any of the four is off, its endpoints return 503 within 1 s and make no network call. |
| TL-NFR-11 | `student-5.yml` runs the two endpoint tests on every push with all four AI flags `false`, and publishes JUnit results. |

## Delivery sequence

Each chunk is one focused branch (`AC/student5-r2-<topic>`), committed only after
its tests pass, with results recorded in `prompt-log.md`.

1. **AI-off guard (TL-FR-18).** Add `AI_ENABLED` to `app.py` config and short-circuit
   the advisory route and UI fragment, as already done for MCP/RAG. Tests for both
   states. Required before cloud acceptance.
2. **Multi-Agent integration (TL-FR-16/17, TL-NFR-10).** `backend/multi_agent.py`
   (modelled on Student 2's Flask client): build bounded evidence from the database
   API, with distinctive per-record titles so the server's subject checks pass;
   routes to create, poll and decide; `MULTI_AGENT_ENABLED` / `MULTI_AGENT_SERVER_URL`
   in the `student5-backend` compose block (default `false`). HTMX "Trip readiness
   review" panel with polling and the four decision buttons. Mocked-HTTP tests.
3. **Endpoint CI tests (TL-NFR-11).** `backend/tests/test_endpoints_cicd.py` covering
   `POST /api/destinations` and `PUT /api/destinations/<id>` (valid, invalid and
   not-found cases, database API mocked). New `student-5.yml` step with all four
   flags `false`, `--junitxml`, `junit_summary.py` and `upload-artifact`.
4. **Pre-commit evidence.** Bump `student-5/database` pytest to >= 9.0.3 and remove
   its pip-audit exception; run the hooks during a real commit; save outputs under
   `docs/evidence/release-2/precommit/`.
5. **Cloud coverage.** Student 5 create -> read -> update -> delete destination check
   (plus advisory 503) in `scripts/deploy/smoke_cloud.py`, with a test, following
   Student 1's PR #125.
6. **Local deployment and reviews.** Run Ollama, MCP, RAG and the Multi-Agent Server
   natively in separate terminals with the Compose stack; capture logs; complete one
   readiness review from the Student 5 page with a real human decision; copy the
   workflow and audit records into `docs/evidence/release-2/multi-agent-server/`; run
   the three loop review modes and `finalise` each.
7. **Documentation.** Endpoint-testing, multi-agent and pre-commit reports under
   `docs/evidence/release-2/`; update `contribution-log.md`, `review-record.md`,
   `known-issues.md`, `requirements.md`, `architecture.md` (Release 2 design flow)
   and `feature-plan.md`.

## Acceptance gates

Local tests do not certify release acceptance. Each of these must be shown with
real output, not mocks:

- Pushed `student-5.yml` run green with the endpoint-test artefact.
- A completed Planner -> Worker -> Reviewer -> Human Review workflow from the
  Student 5 UI and from the terminal, with audit verification (`GET /audit/verify`).
- Pre-commit hooks executed during an actual commit.
- A `cloud-deployment.yml` run that includes the Student 5 smoke check, with the
  Student 5 page reachable on the deployed URL.

## Open items and dependencies

- **Cloud environment:** status of the VM, GitHub `production` secrets and public URL
  is unconfirmed. Ask the cloud workflow owner for access status and a run link;
  Student 5 does not provision resources.
- **Cloud gate:** `cloud-deployment.yml` requires every student workflow to be green
  for the same commit; Student 4 has no Release 2 endpoint step yet (owner to confirm).
- **Known Release 1 defect (Student 1, flagged only):** RAG source titles render as
  mojibake in Student 1's backend (`Tokyo â€” Where to Stay`); the RAG server output
  is correct UTF-8.

## Discrepancies between authoritative documents

The Release 2 brief is followed where it conflicts with the general specification:

| Topic | Project specification | Release 2 brief (followed) |
| --- | --- | --- |
| Due date | 18 October 2026 | 25 October 2026, 11:59 PM AEST |
| Cloud AI-Mode | Enabled with Ollama | Disabled by default; enabling is bonus B1 |
| Pre-commit testing | pytest validation | Ruff security rules, detect-secrets, pip-audit |
| Post-commit testing | AI-assisted unit testing | Tests for two backend endpoint functions |
| AI services | Containerised in Compose | Non-containerised native services |
