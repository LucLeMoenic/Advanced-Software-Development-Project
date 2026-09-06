# Travel Logistics & Advisory Service - Feature Plan

Student 5 (Alex Chen), Release 0. This records the build **as executed**, in the
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
| 1 | Database microservice: schema, seed, CRUD API, tests, healthy container | TL-FR-10, TL-NFR-01, TL-NFR-05 | **Complete** | 3 tables; 12/14/14 seeded rows; 26 pytest tests; container port 8080 mapped to host 5305. Commit `167b2f6`, PR #25. |
| 2 | Agentic-loop tooling fix (shared service) | Supports TL-NFR-05 | **Complete** | Added `.py`/`.sql` to the loop's accepted context extensions and raised token limits so larger source files fit. Commit `4543fae`, PR #26. Later `319f13b` fixed the `[OBSERVE]` heading regex. |
| 3 | Backend/API microservice: JSON CRUD passthrough over HTTP | TL-FR-10, TL-NFR-01, TL-NFR-02, TL-NFR-03 | **Complete** | `db_client.py` (returns status codes, raises only on transport failure), `relay()` as the single response chokepoint, `api` blueprint. Commit `5df2930`, PR #34. |
| 4 | AI advisory endpoint + HTMX fragment endpoints | TL-FR-02..05, TL-FR-07..09 | **Complete** | `ollama_client.py`, `advisory.py` (grounded prompt), `ui.py` + 7 Jinja templates. Suite grew to 68 tests. Commit `b6fb921`, PR #36. |
| 5 | Frontend microservice: static HTMX page behind nginx | TL-FR-01..09, TL-NFR-03 | **Complete** | Single page, no build step; HTMX 1.9.12 pinned with Subresource Integrity; nginx proxies `/ui/` and `/api/` so the backend needs no CORS. Commit `9ec2aa1`, PR #37. |
| 6 | Docker Compose integration + shared home page entry | TL-NFR-04, TL-NFR-05 | **Complete** | `student5-frontend` 5105, `student5-backend` 5205, `student5-database` 5305, all with healthchecks and dependency ordering behind `ollama-model-setup`. Commits `fa948af`, `9adae81`, PR #39. |
| 7 | CI workflow `.github/workflows/student-5.yml` | TL-NFR-05 | **Complete in source; run evidence outstanding** | Two separate pytest steps, `docker compose config --quiet`, three image builds. Commits `fc00e4a`, `9e894c9`, PR #40. **TODO: attach CI run screenshot or URL** from the Actions tab, workflow "Student 5 CI". |
| 8 | UX/UI uplift onto Student 2's design system | TL-FR-01..06 | **Complete** | Page restyled to the shared app shell - header, collapsible trip composer, sidebar+main planner grid, tucked-away admin section - so the five feature frontends read as one product. Commits `6058327`, `546c2a4`, PR #42; naming fix `3286e20`, PR #44. |
| 9 | Agentic-loop deliverable: `formatElapsed` elapsed-time readout | TL-FR-06 | **Complete** | Built through the shared Plan/Act/Observe/Adapt loop with a custom reviewer prompt. Commit `6dd3fd2`, PR #50. Record `20260906T053024Z-ad4b32c67df446e8af9e1fca8cc22044.json`. |
| 10 | Agentic-loop evidence captured | Criterion 4 and 5 | **Complete** | Three terminal screenshots, the finalised record JSON, and three supporting text captures, all in `docs/evidence/`. Commit `cdf8942`. |
| 11 | Release 0 documentation pack | All | **Complete** | This folder. |
| 12 | Browser evidence for the report | TL-FR-01..09 | **Outstanding** | **TODO: attach application screenshots** - `http://localhost:5105/` after `docker compose up --build student5-frontend student5-backend student5-database ollama ollama-model-setup`. |

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

MCP tools (`get_weather`, `check_visa_requirement`) are Release 1 work; nothing
in this release depends on them. Authentication, live visa/weather feeds, RAG
and multi-agent application behaviour are also out of scope.
