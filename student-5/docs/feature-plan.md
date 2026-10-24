# Travel Logistics & Advisory Service - Feature Plan

Student 5 (Alex Chen), Releases 0-2. This records the build **as executed**, in the
order it happened, with the status of each deliverable. Requirement IDs refer to
`requirements.md`.

## Goal

A traveller picks a destination and sees the recorded weather notes, entry
requirement and transit options, then asks for an AI advisory grounded in those
same rows. An admin section maintains the destination list. All three services
run together in the group Compose stack.

## Sequencing rule used

Each chunk had to build, pass its own tests and start in a container before the
next one began. The order was bottom-up - database, then backend, then frontend,
then integration - so that every layer was written against a dependency that
already worked rather than against a stub.

## Deliverables and status

| # | Deliverable | Requirements | Status | Evidence / notes |
|---|---|---|---|---|
| 1 | Database microservice: schema, seed, CRUD API, tests, healthy container | TL-FR-10, TL-NFR-01, TL-NFR-05 | **Complete** | 3 tables; 12/14/14 seeded rows; 26 pytest tests (`docs/evidence/pytest-database.txt`, `26 passed in 0.84s`); container port 8080 mapped to host 5305. Commit `167b2f6`, PR #25. |
| 2 | Agentic-loop tooling fix (shared service) | Supports TL-NFR-05 | **Complete** | Added `.py`/`.sql` to the loop's accepted context extensions and raised token limits so larger source files fit. Commit `4543fae`, PR #26. Later `319f13b` fixed the `[OBSERVE]` heading regex. |
| 3 | Backend/API microservice: JSON CRUD passthrough over HTTP | TL-FR-10, TL-NFR-01, TL-NFR-02, TL-NFR-03 | **Complete** | `db_client.py` (returns status codes, raises only on transport failure), `relay()` as the single response chokepoint, `api` blueprint. Commit `5df2930`, PR #34. |
| 4 | AI advisory endpoint + HTMX fragment endpoints | TL-FR-02..05, TL-FR-07..09 | **Complete** | `ollama_client.py`, `advisory.py` (grounded prompt), `ui.py` + 7 Jinja templates. Suite grew to 68 tests (`docs/evidence/pytest-backend.txt`, `68 passed in 0.54s`). Commit `b6fb921`, PR #36. |
| 5 | Frontend microservice: static HTMX page behind nginx | TL-FR-01..09, TL-NFR-03 | **Complete** | Single page, no build step; HTMX 1.9.12 pinned with Subresource Integrity; nginx proxies `/ui/` and `/api/` so the backend needs no CORS. Commit `9ec2aa1`, PR #37. |
| 6 | Docker Compose integration + shared home page entry | TL-NFR-04, TL-NFR-05 | **Complete** | `student5-frontend` 5105, `student5-backend` 5205, `student5-database` 5305, all with healthchecks and dependency ordering behind `ollama-model-setup`. All three verified healthy together in `docs/evidence/compose-ps.txt`; images build in `docs/evidence/compose-build.txt`. Diagram in `architecture.md`. Commits `fa948af`, `9adae81`, PR #39. |
| 7 | CI workflow `.github/workflows/student-5.yml` | TL-NFR-05 | **Complete** | Two separate pytest steps, `docker compose config --quiet`, three image builds; step-by-step description and pipeline diagram in `testing-evidence.md` and `architecture.md`. Green run captured in `docs/evidence/ci-run-green.png` - run `AC/complete-documentation #92`, `logistics-services` succeeded in 24s, every step ticked. Local captures of the same steps in `pytest-database.txt`, `pytest-backend.txt` and `compose-build.txt`. Commits `fc00e4a`, `9e894c9`, PR #40. |
| 8 | UX/UI uplift onto Student 2's design system | TL-FR-01..06 | **Complete** | Page restyled to the shared app shell - header, collapsible trip composer, sidebar+main planner grid, tucked-away admin section - so the five feature frontends read as one product. Commits `6058327`, `546c2a4`, PR #42; naming fix `3286e20`, PR #44. |
| 9 | Agentic-loop deliverable: `formatElapsed` elapsed-time readout | TL-FR-06 | **Complete** | Built through the shared Plan/Act/Observe/Adapt loop with a custom reviewer prompt. Commit `6dd3fd2`, PR #50. Record `20260906T053024Z-ad4b32c67df446e8af9e1fca8cc22044.json`. |
| 10 | Agentic-loop evidence captured | Criterion 4 and 5 | **Complete** | Three terminal screenshots, the finalised record JSON, and three supporting text captures, all in `docs/evidence/`. Commit `cdf8942`. Workflow diagram in `architecture.md`. |
| 11 | Release 0 documentation pack | All | **Complete** | This folder, including the Compose, DevOps-pipeline and agentic-workflow diagrams in `architecture.md` and the `student-5.yml` step description in `testing-evidence.md`. |
| 12 | Test and stack evidence captured | TL-NFR-05 | **Complete** | `pytest-database.txt` (26 passed), `pytest-backend.txt` (68 passed), `compose-build.txt` (all three images `Built`), `compose-ps.txt` (all three services `healthy`), all in `docs/evidence/`. |
| 13 | Browser evidence for the report | TL-FR-01..09 | **Complete** | Four screenshots of the running stack at `http://localhost:5105/`, in `docs/evidence/`: `ui-filled-panels.png` (populated weather, visa and transit panels), `ui-advisory-output.png` (a generated advisory with the `llama3.2:3b` tag in its footer), `ui-advisory-loading.png` (the elapsed readout at `17s` mid-generation) and `ui-manage-table.png` (the admin table with the created row id 13 and its inline edit/delete controls). |

## Decisions taken during the build, and why

| Decision | Alternative rejected | Reason |
|---|---|---|
| Backend forwards the database service's status codes verbatim | Re-validate in the backend | Two sources of truth for the same rule drift. The database owns validation; the backend owns transport failure only. |
| Ollama failures collapse into one exception | Forward Ollama's status like the database's | A 500 from a generation endpoint gives the traveller nothing actionable, and there is no partial advisory to relay. |
| The two 503 bodies differ | One generic 503 | An operator reading a log or a response can tell which container died without opening either. |
| `/ui/` fragments answer 200 even on failure | Honest status codes everywhere | HTMX does not swap a non-2xx, so an honest 503 would leave a stale "Loading..." on screen. The JSON API keeps the honest codes; the fragments optimise for the reader seeing what happened. |
| Writes go through `/ui/` endpoints, not `hx-put` at `/api/` | Point HTMX at the JSON API | A JSON body cannot be swapped into the page, and the visible table would drift from stored state. Each `/ui/` write performs the change and re-renders from a fresh read. |
| The advisory prompt pastes stored rows in verbatim | Let the model recall visa rules | An invented visa rule is the most dangerous output this domain can produce. Grounding makes a wrong rule a *data* bug, which is fixable, rather than a model bug, which is not. |
| Server-rendered HTMX fragments rather than a JS framework | Vue/React SPA | No build step, and it keeps the rendering decisions next to the data access in Python where the tests already are. |
| HTMX pinned to 1.9.12 with SRI | Floating CDN version | The browser refuses the file if the CDN ever serves different bytes under that URL. |

## Deliberately out of scope for Release 0

MCP tools (`get_weather`, `check_visa_requirement`) were Release 1 work; nothing
in Release 0 depends on them. Authentication, live visa/weather feeds, RAG
and multi-agent application behaviour were also out of scope.

## Release 1 - MCP, RAG and agentic validation

Delivered as one pull request per step (see `contribution-log.md`). Same sequencing rule, bottom-up: the
shared tool and knowledge base first, then the backend clients, then the UI,
then CI and the loop fixtures.

| # | Deliverable | Requirements | Status | Evidence / notes |
|---|---|---|---|---|
| R1-1 | Three `logistics.*` MCP tools on the shared server | TL-FR-11, TL-NFR-07 | **Complete** | `ai-services/mcp-server/tools/logistics.py` + 34 tests (`release-1/pytest-mcp-server.txt`). Read-only `GET`s to the Student 5 database service only. |
| R1-2 | Student 5 RAG knowledge base | TL-FR-13, TL-NFR-08 | **Complete** | 8 curated documents in `ai-services/rag-server/knowledge/student-5/`; 17 retrieval tests (`release-1/pytest-rag-server.txt`). |
| R1-3 | Backend MCP and RAG clients and routes | TL-FR-12, TL-FR-13, TL-NFR-06 | **Complete** | `mcp_client.py`, `rag_client.py`, `integrations.py`; feature flags default off; 57 new backend tests (125 total). Live captures in `release-1/mcp-*.json` and `rag-*.json`. |
| R1-4 | Frontend "Live tools & knowledge base" section | TL-FR-14 | **Complete** | `/ui/mcp` and `/ui/rag` fragments; desktop and 375px screenshots in `release-1/screenshots/`. |
| R1-5 | Compose flags, test script and CI smoke test | TL-NFR-06, TL-NFR-09 | **Complete** | `MCP_ENABLED`/`RAG_ENABLED` on `student5-backend`; `student-5.yml` starts the services and asserts the fail-closed 503s. Smoke step verified locally (`release-1/ci-smoke-local.txt`); green on GitHub: Student 5 CI run #140 on `main` at `49e5489` (https://github.com/LucLeMoenic/Advanced-Software-Development-Project/actions/runs/36872202961); screenshot `release-1/ci-run-green.png`. |
| R1-6 | `--feature student-5` in agentic-loop `validate-mcp` / `validate-rag` | TL-FR-15 | **Complete** | `ServiceValidation.cs` + 4 tests (73 total). Both modes run live; records finalised by Alex: (e) `kept`, (f) `kept`. |
| R1-7 | Release 1 docs and evidence | All | **Complete** | This folder and `docs/evidence/release-1/`. |

| Decision | Alternative rejected | Reason |
|---|---|---|
| MCP tools read the Student 5 database over HTTP | Open `travel.db` from the MCP server | Keeps TL-NFR-01: one owner for the data, and the tool gets the same validation and 404s as every other caller. |
| The backend allow-lists the three `logistics.*` tools | Proxy any tool name | Student 5's public API must not become a route into other students' tools. |
| The RAG client re-validates the server's response | Trust the shared server | A response with a citation the answer never uses, or an "insufficient" answer with citations, is a contract breach the UI should not render as authoritative. |
| MCP and RAG default to disabled; CI asserts the disabled path | Enable both in CI | CI has no model and no shared servers. Asserting the fail-closed 503s still proves the routes, Compose wiring and the `:5105` proxy without flaky dependencies. |
| The Smartraveller reminder is part of the tool result and the RAG markup | Rely on the model | Same reason as Release 0's advisory disclaimer: it must appear whatever the model writes. |

## Release 2 - Multi-Agent, testing and deployment

Delivered from [`release-2-plan.md`](release-2-plan.md), one branch and one pull request
per chunk, each squash-merged into `main` by me. Commit hashes are the work commits on
each branch; the merge commit is what lands on `main`. Evidence paths are relative to
`student-5/docs/`.

| # | Deliverable | Requirements | Status | Branch, commits, PR (merge) | Evidence |
|---|---|---|---|---|---|
| R2-1 | AI-off guard: `AI_ENABLED` switches the advisory off with `503 ai_disabled` and no network call | TL-FR-18 | **Complete** | `AC/student5-r2-ai-off-guard`: `e0dae03`, `a2ee74b`; PR #129 (`59e5ce4`). The PR is titled "multi-agent integration", but it holds the AI-off guard and the Release 2 plan. | `prompt-log.md` and `review-record.md` (Release 2, Chunk 1); 5 new backend tests |
| R2-2 | Trip readiness review on the shared Multi-Agent Server: backend client and routes, HTMX panel with polling and the four decisions, Compose flags | TL-FR-16, TL-FR-17, TL-NFR-10 | **Complete** | `AC/student5-r2-multi-agent`: `de8de91`, `ffbc847`, `77f2a82`, `da2edfe`; PR #132 (`7798bc8`) | `backend/tests/test_readiness.py`; `prompt-log.md` (Chunk 2) |
| R2-3 | Post-commit endpoint tests for `POST` and `PUT /api/destinations` in `student-5.yml`, with JUnit results and a live container check | TL-NFR-11 | **Complete** | `AC/student5-r2-endpoint-ci`: `83a578b`, `01fee2f`, `afb34bb`; PR #133 (`e523738`) | `evidence/release-2/endpoint-testing-report.md`, `endpoint-tests/` (runs 39697590918 and 39698558980 green) |
| R2-4 | Pre-commit security evidence: hooks run on a real commit; pytest `>=9.0.3`; Student 5 pip-audit exception removed | Brief criterion 3 | **Complete** | `AC/student5-r2-precommit`: `f77c09b`, `3c42f93`, `de85886`; PR #135 (`df5ec56`) | `evidence/release-2/precommit-security-report.md`, `precommit/01`-`04` |
| R2-5 | Student 5 cloud smoke check: four AI-off bodies, then destination create, read, update, delete and `404` | TL-NFR-10, brief criterion 7 | **Complete**; cloud baseline run owned by the cloud workflow owner | `AC/student5-r2-cloud-smoke`: `87597cb`, `2d66767`; PR #137 (`7aadf5a`) | `evidence/release-2/cloud-deployment-report.md`; 18 offline tests at merge (19 on `main` after PR #143); cloud run 39741981906 |
| R2-6 | Local deployment with the native Multi-Agent Server; five workflows from UI and terminal with human decisions; three agentic-loop report reviews finalised | Brief criteria 1, 2, 8 | **Complete** | `AC/student5-r2-evidence`: `949bb13`, `06ea17e`, `40a083b`, `05de520`, `d660a8a`; PR #145 (`e146338`) | `evidence/release-2/local-deployment-report.md`, `multi-agent-server-report.md`, `loop/README.md` |
| R2-7 | Release 2 documentation and report sections | All | **Complete** | `AC/student5-r2-docs`: `a0afec6`, `80180f9`, `1732bd3`, `a550afb`, `48a52de`; PR #151 (`07eb996`) | `architecture.md` (Release 2), `release-2-report-sections.md`, `evidence/release-2/cloud/11-protected-ai-run-39893640923-excerpt.txt` |

### Acceptance gates from the plan

| Gate | Status | Evidence |
|---|---|---|
| Pushed `student-5.yml` run green with the endpoint-test artefact | **Met** | Run 39698558980 on `main` at `e523738`: `13 passed`, `12/12 checks passed`, artifact `student-5-endpoint-test-results` (`endpoint-tests/07`-`10`) |
| Planner -> Worker -> Reviewer -> Human Review from the UI and from the terminal, with `GET /audit/verify` | **Met** | Thailand (browser, `partial`), Indonesia (UI, `correct`), Vietnam (terminal, `partial`); final verify `valid: true`, 50 entries (`multi-agent-server/transcripts/audit-verify-final.txt`) |
| Pre-commit hooks run during an actual commit | **Met** | `precommit/04-blocked-commit.txt` (a real commit rejected); the Chunk 4 commits ran all three hooks |
| A `cloud-deployment.yml` run that includes the Student 5 smoke check, with the page reachable on the deployed URL | **Met, with a caveat** | Run 39741981906 at `851bdd7`: `PASS: Student 5 cloud profile and CRUD checks.` (`cloud/03`); page and disabled notices in `cloud/04`-`07`. The shared runbook says this run came before the CI-gate fix, and no AI-off baseline run has succeeded since (see `known-issues.md`). |

### Changes to Student 5 files by other team members

`166a4a4` (PR #147, the cloud workflow owner) added an opt-in `CLOUD_AI_SLOW_MODE` to
`student-5/backend/app.py` (longer Ollama and RAG timeouts for the cloud AI mode) and
`backend/tests/test_cloud_deadlines.py` (2 tests). It does not turn any AI flag on.
The backend suite is therefore 201 tests on `main`, not the 199 recorded in Chunks 3-6.

`851bdd7` (PR #143, the cloud workflow owner) gave `check_student5` an `enabled`
parameter, so the AI-off bodies are skipped for components the protected AI mode turns
on, and added 1 test to `scripts/test/test_cloud_smoke_student5.py` (19 tests, 18 at
PR #137). PR #130 (another team member) added the first, read-only Student 5 cloud
check, which PR #137 replaced. PRs #128 and #141 (other team members) each made a
one-line change to `student-5.yml` (a build retry wrapper and `workflow_dispatch`).

### Release 2 decisions

| Decision | Alternative rejected | Reason |
|---|---|---|
| The backend builds the Multi-Agent evidence from its own database reads | Let the Multi-Agent Server read Student 5 data | Keeps TL-NFR-01: one owner for the data, and the evidence a reviewer sees is exactly what the backend sent. |
| Human decisions live only on the shared server's audit log | A Student 5 table of decisions | The server already hash-chains them; a second copy could drift and would need its own migration. |
| AI-Mode defaults on; MCP, RAG and Multi-Agent default off | All four off by default | AI-Mode is the Release 0 core feature. Cloud and CI turn all four off explicitly. |
| The endpoint tests mock the database, and a separate live check hits the real containers | Only one of the two | The mocked tests prove the backend's own contract; the live check proves the real path. |
| The cloud check reads the `*_disabled` body, not just `503` | Accept any `503` | A down backend also answers `503` through the gateway. |
