# Contribution Log - Student 5

Alex Chen, feature **Travel Logistics & Advisory Service**, Releases 0-2.

Derived from `git log --all --author="alexanderschen08@gmail.com"` across my
`AC/*` branches and `main`. 25 commits between 1 and 6 September 2026, of which
15 are work commits and 10 are the squash/merge commits that landed them on
`main` via pull request. Both are listed, because the merge commit is what makes
the PR number traceable.

## Work delivered, by commit

| Date | Commit | Landed as | What it delivered |
|---|---|---|---|
| 2026-09-01 | `167b2f6` | PR #25 (`c9a3ae3`) | **Database microservice, complete.** `schema.sql` with three tables and cascade deletes; `seed.sql` with 12 destinations, 14 weather notes and 14 transit options; `app.py` with the application factory, generic CRUD handlers shared by all three resources, validation (required fields, non-empty strings, `destination_id` existence checks), partial-merge `PUT`, and `PRAGMA foreign_keys = ON` per connection; 26 pytest tests each against its own `tmp_path` database; Dockerfile with a `urllib`-based healthcheck. 9 files, ~860 lines. |
| 2026-09-01 | `4543fae` | PR #26 (`46bdc8e`) | **Shared agentic-loop tooling fix.** Added `.py` and `.sql` to the loop's accepted `--context` extensions and raised the token limits so larger source files fit in a run. A group-infrastructure change, not a Student 5 one - without it no Python service in the repo could be used as loop context. |
| 2026-09-03 | `319f13b` | (on `AC/agenticloop-work-01-country-filter`) | **`[OBSERVE]` heading regex fix** in the agentic loop's reviewer-output parser - made while investigating why the country-filter run (attempt (a) in `prompt-log.md`) recorded no `[OBSERVE]` header. |
| 2026-09-03 | `5df2930` | PR #34 (`617443d`) | **Backend/API microservice, first half.** `db_client.py` - the only route from the backend to data, returning `DatabaseResponse(status, payload)` rather than raising on 4xx, and raising `DatabaseUnavailable` only on transport failure; `relay()` as the single response chokepoint; the `api` blueprint mirroring the database service's shapes across all three resources; the initial test suite. 6 files, ~680 lines. |
| 2026-09-03 | `b6fb921` | PR #36 (`0d7805b`) | **AI advisory endpoint and HTMX fragment endpoints.** `ollama_client.py` (non-streaming `/api/generate`, 120s timeout, every failure collapsing to `OllamaUnavailable`); `advisory.py` with the four `describe_*` grounding helpers, `build_prompt`, and both the JSON and shared generation paths; `ui.py` plus seven Jinja fragment templates; `parse_destination_id` coercion at the untrusted boundary. Suite grown to 68 tests, all offline. Includes the notes-clearing fix found against a live database - an emptied notes box now sends JSON `null` rather than `""`, because the database accepts null but rejects an empty string. 16 files, ~1837 lines. |
| 2026-09-03 | `9ec2aa1` | PR #37 (`73362b8`) | **Frontend microservice.** Single-page `index.html` with no build step; HTMX 1.9.12 pinned and locked with Subresource Integrity; the destination `<select>` as the single source of truth with the panels `hx-include`ing it; the `htmx:responseError` listener that replaces stale placeholders when the backend itself is unreachable; `nginx.conf` proxying `/ui/` and `/api/` same-origin with `resolver 127.0.0.11` and 180s read timeouts; `style.css`; Dockerfile. 4 files, ~901 lines. |
| 2026-09-04 | `fa948af` | PR #39 (`f514400`) | **Docker Compose integration and the shared home page entry.** All three Student 5 services added to root `docker-compose.yml` on 5105/5205/5305 with healthchecks, dependency ordering behind `student5-database` and `ollama-model-setup`, environment-driven configuration, and the database bind mount. |
| 2026-09-04 | `9adae81` | PR #39 (`f514400`) | Removed duplicated shared home page content. |
| 2026-09-04 | `fc00e4a` | PR #40 (`8351004`) | **CI workflow `.github/workflows/student-5.yml`.** Path-filtered triggers; pip caching against both requirements files; the two pytest suites as **separate** steps (they collide if combined); `docker compose config --quiet`; build of all three images. No live model required. |
| 2026-09-04 | `9e894c9` | PR #40 (`8351004`) | **CI regression fix.** Removed the `/shared/style.css` link and the nginx/Dockerfile plumbing behind it - the file was not present in the Student 5 image and broke the page under CI. Student 5 now ships its own stylesheet. 5 files, 41 deletions. |
| 2026-09-04 | `6058327` | PR #42 (`6215c8c`) | **UX/UI uplift, first pass.** Page restructured onto Student 2's app shell so the five feature frontends read as one product: header, collapsible trip composer, sidebar+main planner grid, admin section tucked into a `<details>`. ~995 lines added. |
| 2026-09-04 | `546c2a4` | PR #42 (`6215c8c`) | **UX/UI uplift, second pass.** Print sheet (`@media print` plus the print-only dateline), accessible naming preserved across HTMX swaps - the advisory heading moved outside the swap target so the section keeps its accessible name after the first generation - and the `hx-indicator` / `hx-disabled-elt` overrides on the destination select that stop it inheriting the advisory form's pair. |
| 2026-09-04 | `3286e20` | PR #44 (`7acd2e4`) | Aligned the shared home page label with the feature's own product name. |
| 2026-09-06 | `6dd3fd2` | PR #50 (`dbbb3e6`) | **`formatElapsed` elapsed-time readout, built through the agentic loop.** The function itself, its timer wiring (`htmx:beforeRequest` / `htmx:afterRequest` with the `isAdvisoryRequest` guard, so the page-load options fetch cannot start a timer nothing stops), and my custom reviewer prompt `docs/prompt-library/reviewer-llama32-v2.md`. Produced through a full Plan -> Act -> Observe -> Adapt cycle with a recorded human decision; record `20260906T053024Z-ad4b32c67df446e8af9e1fca8cc22044.json`. 3 files, 143 lines. |
| 2026-09-06 | `cdf8942` | (on `AC/complete-documentation`) | **Agentic-loop evidence captured.** Three terminal screenshots, the finalised record JSON, and three supporting text captures, into `student-5/docs/evidence/`. 7 files. |
| 2026-09-06 | `a0f5ae0` | (on `AC/complete-documentation`) | **Release 0 documentation pack.** Context, requirements, feature plan, risk plan, sprint backlog, data design, architecture, prompt log, review record, prompt engineering, testing evidence, known issues and contribution log, plus the README rewrite; and the pytest, build and `compose ps` captures into `docs/evidence/`. 18 files, 1669 insertions. |
| 2026-09-06 | `5adfd3f` | (on `AC/complete-documentation`) | **Evidence index reconciled and the three required diagrams added.** Every pytest / Compose TODO replaced by a reference to the committed capture with its result line quoted; Mermaid diagrams for the Compose architecture, the DevOps pipeline and the Plan/Act/Observe/Adapt workflow in `architecture.md`; the `student-5.yml` step-by-step description in `testing-evidence.md`. 5 files, 281 insertions. |
| 2026-09-06 | (working tree) | (on `AC/complete-documentation`) | **Final evidence capture and documentation close-out.** The green CI run (`ci-run-green.png`) and four application screenshots (`ui-filled-panels.png`, `ui-advisory-output.png`, `ui-advisory-loading.png`, `ui-manage-table.png`) into `docs/evidence/`; the last two TODOs replaced across `testing-evidence.md`, `requirements.md`, `feature-plan.md` and `sprint-backlog.md`; evidence-completeness mapping added. No documentation item is outstanding. |

## Release 1

Written with GitHub Copilot CLI under my direction and reviewed by me (see
`prompt-log.md` and `review-record.md`). The assistant prepared each change in the
working tree only; I committed, pushed and opened every pull request myself, one
per step, each squash-merged into `main`.

| PR | Branch | Commit (Conventional) | What it delivers |
|---|---|---|---|
| #97 | `AC/mcp-logistics-tools` | `feat(mcp): add Student 5 logistics tools` | `logistics.check_visa_requirement`, `logistics.get_weather`, `logistics.get_transit`; registration; 34 tests |
| #98 | `AC/rag-knowledge-base` | `feat(rag): add Student 5 knowledge base` | 8 curated documents; 17 retrieval tests |
| #99 | `AC/backend-ui-integration` | `feat(student-5): integrate MCP and RAG through backend and UI` | MCP/RAG clients, `/api/mcp/*`, `/api/rag/ask`, `/ui/mcp`, `/ui/rag`, the "Live tools & knowledge base" section, Compose flags; backend suite 68 -> 125 |
| #101 | `AC/ci-mcp-rag-smoke-test` | `ci(student-5): run MCP and RAG suites and smoke-test the stack` | `student-5.ps1` runs the new suites; `student-5.yml` path filters, start, smoke test and stop steps |
| #100 | `AC/agentic-loop-validation` | `feat(agentic-loop): add student-5 MCP and RAG validation fixtures` | `--feature student-5` for `validate-mcp` / `validate-rag`; 4 tests; the two validation records |
| #102 | `AC/docs-and-evidence` | `docs(student-5): add Release 1 docs and evidence` | Release 1 docs and `evidence/release-1/` |
| (this PR) | `AC/ci-green-evidence` | `docs(student-5): record green Release 1 CI run` | Records Student 5 CI run #140 on `main` as Release 1 CI evidence |

## Pull requests

| PR | Branch | Merge commit | Scope |
|---|---|---|---|
| #25 | `AC/student5-release-0` | `c9a3ae3` | Database microservice |
| #26 | `AC/agentic-loop-ext-fix` | `46bdc8e` | Agentic-loop context-extension and token-limit fix |
| #34 | `AC/backend-api` | `617443d` | Backend CRUD passthrough and database client |
| #36 | `AC/ai-advisory-endpoint` | `0d7805b` | Advisory endpoint and HTMX fragments |
| #37 | `AC/frontend-HTMX-microservice` | `73362b8` | Frontend microservice |
| #39 | `AC/docker-integration-and-shared-home-page` | `f514400` | Compose integration, shared home entry |
| #40 | `AC/ci-workflow-implementation` | `8351004` | CI workflow and the shared-stylesheet regression fix |
| #42 | `AC/UX-UI-uplift` | `6215c8c` | Design-system uplift |
| #44 | `AC/shared-home-page-tweak` | `7acd2e4` | Naming alignment |
| #50 | `AC/agenticloop-work-elapsed-timer` | `dbbb3e6` | Agentic-loop deliverable and reviewer prompt |
| #97 | `AC/mcp-logistics-tools` | `1105410` | Release 1: Student 5 MCP logistics tools |
| #98 | `AC/rag-knowledge-base` | `2a15c02` | Release 1: Student 5 RAG knowledge base |
| #99 | `AC/backend-ui-integration` | `1083525` | Release 1: backend and UI integration of MCP and RAG |
| #101 | `AC/ci-mcp-rag-smoke-test` | `7dd74d5` | Release 1: test script and CI smoke test |
| #100 | `AC/agentic-loop-validation` | `12008ea` | Release 1: agentic-loop `student-5` validation fixtures |
| #102 | `AC/docs-and-evidence` | `49e5489` | Release 1: docs and evidence |

## Summary by area

| Area | Contribution |
|---|---|
| Database service | Schema, seed, full CRUD API, validation, cascade deletes, idempotent seeding, 26 tests, container |
| Backend service | HTTP database client, JSON passthrough, Ollama client, grounded advisory workflow, HTMX fragment blueprint with 7 templates, 68 tests |
| Frontend service | Single-page HTMX application, nginx edge with same-origin proxying, own stylesheet, print sheet, client-side failure handling |
| Integration | Three Compose services with healthchecks and dependency ordering; shared home page entry |
| CI | `student-5.yml` - two test suites, Compose validation, three image builds; green run captured (`ci-run-green.png`). Release 1: MCP/RAG suites, container start and smoke test |
| Release 1 integration | Three MCP tools, eight-document RAG knowledge base, backend MCP/RAG routes and UI section, `student-5` agentic-loop validation fixture |
| Group infrastructure | Agentic-loop context-extension fix, token-limit increase, `[OBSERVE]` regex fix |
| AI workflow evidence | One completed and finalised Plan/Act/Observe/Adapt record, custom reviewer prompt, six artefacts covering the run |
| Documentation | This `docs/` folder - 13 documents, three architecture diagrams, and 17 indexed evidence artefacts with nothing outstanding |

## Note on the record

Three agentic-loop attempts before the successful one produced no artefacts and
therefore no commits; they are documented in `prompt-log.md` from the working
session rather than from the repository history.

## Release 2

Repository: https://github.com/LucLeMoenic/Advanced-Software-Development-Project. Derived
from `git log origin/main..origin/AC/student5-r2-<topic>` for each chunk branch and the
squash-merge commits on `main`: 19 work commits between 21 and 23 October 2026 (author
`alexanderschen08@gmail.com`), landed as 6 pull requests merged by me (GitHub `chalex08`).
Code and documents were written with an AI coding assistant under my direction. I
reviewed every change, made every human decision in the evidence, and committed, pushed
and merged every pull request myself (see `prompt-log.md` and `review-record.md`).

### Work completed

| Chunk | PR (merge commit) | Branch and work commits | What it delivered |
|---|---|---|---|
| 1 | [#129](https://github.com/LucLeMoenic/Advanced-Software-Development-Project/pull/129) (`59e5ce4`) | `AC/student5-r2-ai-off-guard`: `e0dae03`, `a2ee74b` | **AI-off guard (TL-FR-18).** `AI_ENABLED` in `app.py` and Compose; `OllamaDisabled`; advisory and fragment refuse before any network call; 5 tests; the Release 2 plan. The PR title says "multi-agent integration"; its content is the AI-off guard. `a2ee74b` removed a local `.env` backup committed by mistake in `e0dae03`, so it is not in the merged diff. |
| 2 | [#132](https://github.com/LucLeMoenic/Advanced-Software-Development-Project/pull/132) (`7798bc8`) | `AC/student5-r2-multi-agent`: `de8de91`, `ffbc847`, `77f2a82`, `da2edfe` | **Trip readiness review (TL-FR-16, TL-FR-17, TL-NFR-10).** `multi_agent_client.py`, `readiness.py`, two templates, the HTMX panel with polling and the four decisions, Compose flags; `test_readiness.py`. 15 files, 1815 insertions. |
| 3 | [#133](https://github.com/LucLeMoenic/Advanced-Software-Development-Project/pull/133) (`e523738`) | `AC/student5-r2-endpoint-ci`: `83a578b`, `01fee2f`, `afb34bb` | **Post-commit endpoint tests (TL-NFR-11).** `test_endpoints_cicd.py` (13), `live_endpoint_check.py` (12 checks), five new `student-5.yml` steps, endpoint testing report. |
| 4 | [#135](https://github.com/LucLeMoenic/Advanced-Software-Development-Project/pull/135) (`df5ec56`) | `AC/student5-r2-precommit`: `f77c09b`, `3c42f93`, `de85886` | **Pre-commit security evidence.** pytest `>=9.0.3,<10.0` in both services, Student 5 pip-audit exception removed, reasons on the `S608` suppressions, pre-commit report with a blocked commit. |
| 5 | [#137](https://github.com/LucLeMoenic/Advanced-Software-Development-Project/pull/137) (`7aadf5a`) | `AC/student5-r2-cloud-smoke`: `87597cb`, `2d66767` | **Cloud smoke coverage.** `check_student5` in the shared `smoke_cloud.py` (four AI-off bodies, then CRUD with cleanup in `finally`) and 18 offline tests; cloud deployment report. |
| 6 | [#145](https://github.com/LucLeMoenic/Advanced-Software-Development-Project/pull/145) (`e146338`) | `AC/student5-r2-evidence`: `949bb13`, `06ea17e`, `40a083b`, `05de520`, `d660a8a` | **Local, Multi-Agent and loop evidence.** Real CI and cloud runs recorded; multi-terminal local run; five workflows with my decisions and a 50-entry verified audit log; three agentic-loop report reviews finalised. |
| 7 | (this branch, not yet committed) | `AC/student5-r2-docs` | **Release 2 documentation.** Release 2 design, cloud boundary and DevOps diagrams; this record; `release-2-report-sections.md`; the protected-AI cloud run capture. |

### Release 2 responsibilities (brief, "Individual Responsibilities")

| Responsibility | What I did | Evidence |
|---|---|---|
| Assigned microservices | Kept all three Student 5 services working; added the readiness routes, client and panel | PRs #129, #132 |
| Release 1 integration | AI-Mode, MCP and RAG kept; shown live through the gateway | `local/03`, `local/04`, `local/05` |
| Multi-Agent integration | Backend and UI integration with the shared server; UI and terminal workflows decided by me | `multi-agent-server-report.md` |
| Agentic-loop reviews | Ran and finalised all three Release 2 modes on Student 5 evidence | `loop/README.md` |
| Pre-commit security testing | Ran the hooks on real commits; fixed one vulnerability; documented every accepted finding | `precommit-security-report.md` |
| Post-commit CI/CD testing and `student-5.yml` | Two endpoint functions tested on every push; green runs | `endpoint-testing-report.md` |
| Local deployment | Integrated stack with native AI services and the Multi-Agent Server | `local-deployment-report.md` |
| Cloud deployment | Student 5 smoke check in the group workflow; page and AI-off notices on the public URL | `cloud-deployment-report.md` |
| Repository contribution | 19 work commits in 6 PRs, each with a prompt-log and review-record entry | this section |

### Shared work owned by others that Student 5 depends on

`ai-services/multi-agent-server/`, `cloud-deployment.yml`, `prepare_cloud.py`,
`deploy-vm.sh`, the VM and `start-release1.ps1` belong to other team members. Student 5
changed only its own slice of shared files (`check_student5`, the `student5-backend`
Compose block, `student-5.yml`, the Student 5 entry in `pip-audit-accepted.json`, and
audited additions to `.secrets.baseline` plus three records in `docs/agentic-loop-records/`
in PR #145). Other team members changed Student 5 files in PRs #128, #141, #143 and
#147; they are listed in `feature-plan.md` ("Changes to Student 5 files by other team
members") and `known-issues.md`.
