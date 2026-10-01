# Travel Logistics & Advisory Service - Requirements

Student 5 (Alex Chen), Release 0 and Release 1. TL-FR-01..10 and TL-NFR-01..05
are Release 0; TL-FR-11..15 and TL-NFR-06..09 are Release 1 (MCP, RAG and
agentic-loop validation).

## Scope

```text
Browser -> student5-frontend (nginx) -> student5-backend (Flask) -> student5-database (Flask + SQLite)
                                             |-> ollama -> model tag from APPLICATION_MODEL
                                             |-> shared MCP server :5400/mcp  (logistics.* tools) -> student5-database
                                             \-> shared RAG server :5500/ask  (feature "student-5") -> ollama
```

The browser never calls the database service, Ollama, the MCP server or the RAG
server. The backend never opens a SQLite file, and the MCP tools read Student 5
data only through the database service's HTTP API.

## Functional requirements

| ID | Requirement | Implemented by | Acceptance criteria |
|---|---|---|---|
| TL-FR-01 | The traveller can choose from the recorded destinations. | `GET /ui/destinations/options` rendering into `<select id="destination-select">`; JSON equivalent `GET /api/destinations`. | The select loads on page load and lists every recorded destination (12 on a fresh database). The select is the single source of truth for "which destination" - the detail panels `hx-include` it rather than keeping their own copy. |
| TL-FR-02 | The traveller can read the recorded seasonal weather notes for the chosen destination. | `GET /ui/weather?destination_id=N` into `<div id="weather-panel">`; JSON `GET /api/weather-notes?destination_id=N`. | Changing the select re-fetches the panel. A destination with no notes renders a stated message rather than an empty box. |
| TL-FR-03 | The traveller can read the recorded entry/visa requirement and entry notes. | `GET /ui/visa?destination_id=N` into `<div id="visa-panel">`; JSON `GET /api/destinations/<id>`. | The panel shows `visa_requirement` verbatim from the stored row plus the stored notes. An unknown id renders the database service's own error text, not an invented one. |
| TL-FR-04 | The traveller can read the recorded transit options for the chosen destination. | `GET /ui/transit?destination_id=N` into `<div id="transit-panel">`; JSON `GET /api/transit-options?destination_id=N`. | Options render as a table of `type` and `details`. A destination with no options (Fiji, id 12 on a fresh database) says so. |
| TL-FR-05 | The traveller can generate an AI advisory grounded in the stored rows. This is the marked Frontend -> Backend/API -> Ollama -> LLM workflow. | `POST /ui/advisory` (form fields) into `<div id="advisory-panel">`, and `POST /api/advisory` (JSON); both call `advisory.generate_advisory`. | The prompt built by `advisory.build_prompt` contains the destination row, its weather notes and its transit options verbatim before the model is called. The JSON response carries the advisory text, the model tag actually used, and the destination row. `destination_id` is required and coerced to `int`; an unknown id forwards the database service's 404. |
| TL-FR-06 | The traveller can tell a slow generation from a hung one. | `formatElapsed(seconds)` in `frontend/index.html`, rendering into `<span id="advisory-elapsed">` inside the `role="status"` indicator. | Empty for the first 2 seconds, `Ns` from 2 seconds, `still working - Ns` past 45 seconds. The counter is `aria-hidden`, so the live region is announced once rather than once per second. Seen on screen at `17s` in `docs/evidence/ui-advisory-loading.png`; all three branches asserted in `docs/evidence/formatelapsed-assertions.txt`. |
| TL-FR-07 | An admin can add a destination. | `POST /ui/destinations` from the manage form; JSON `POST /api/destinations`. | `country` and `visa_requirement` are required, `notes` optional. A blank notes box is omitted entirely so the row stores `NULL`, not an empty string. The fragment route returns the refreshed table; the JSON route returns `201` and the created row. |
| TL-FR-08 | An admin can edit a destination in place. | `POST /ui/destinations/<id>` from the row's inline form; JSON `PUT /api/destinations/<id>`. | `PUT` is a partial merge - omitted columns keep their stored value. An emptied notes box is sent as JSON `null`, because the database rejects an empty string but accepts null for that one nullable column; without this, notes could be edited but never cleared. A rejected edit re-renders the table carrying the database service's own message. |
| TL-FR-09 | An admin can delete a destination, and its child rows go with it. | `POST /ui/destinations/<id>/delete` (behind `hx-confirm`); JSON `DELETE /api/destinations/<id>`. | The JSON route returns `204` with no body. Deleting a destination removes its `weather_notes` and `transit_options` rows through `ON DELETE CASCADE`, which works because every connection issues `PRAGMA foreign_keys = ON`. |
| TL-FR-10 | Weather notes and transit options are fully manageable over the JSON API. | `/api/weather-notes` and `/api/transit-options` - list with optional `?destination_id=` filter, create, and get/update/delete by id - on both the backend and the database service. | Creating or updating a child row with a `destination_id` that does not exist is rejected with `400` and a message naming the id. Shapes are identical on both services on purpose, so the frontend could be pointed at either. |
| TL-FR-11 | Release 1: three read-only Student 5 MCP tools on the shared MCP server. | `ai-services/mcp-server/tools/logistics.py`: `logistics.check_visa_requirement`, `logistics.get_weather`, `logistics.get_transit` (optional `type` filter), registered in `tools/__init__.py`. | Pydantic arguments with `extra="forbid"` and strict types; `destination_id` is a positive int; `type` is one of `metro`, `rail`, `bus`, `rideshare`, `ferry`, `airport-link`. Each tool only issues `GET`s to `STUDENT5_DATABASE_API_URL` with a 3s timeout, caps lists at 20 rows sorted by id (the transit `type` filter is applied before the cap), and returns `{"ok": false, "error": {"code", "message"}}` for `destination_not_found`, `dependency_timeout`, `dependency_unavailable` or `invalid_dependency_response`. Every visa result carries `official_source_reminder` naming Smartraveller. 34 tests in `tests/test_logistics_tools.py`. |
| TL-FR-12 | Release 1: the backend reaches the MCP tools for the frontend, behind an allow-list. | `GET /api/mcp/tools` and `POST /api/mcp/invoke` (`integrations.py`, `mcp_client.py`); `POST /ui/mcp` fragment. | `invoke` takes `{tool, arguments}`; only the three `logistics.*` tools are accepted (`400 unknown_tool` otherwise). Success is `200 {tool, result}`; a tool's own failure keeps the same body with `404` (`destination_not_found`), `504` (`dependency_timeout`) or `502`. Rejected arguments are `400 invalid_arguments`; an unreachable server is `502 mcp_unavailable`; the feature switched off is `503 mcp_disabled`. Calls are bounded at 5s. |
| TL-FR-13 | Release 1: the backend answers logistics questions from the curated Student 5 knowledge base, with citations. | 8 documents in `ai-services/rag-server/knowledge/student-5/`; `POST /api/rag/ask` (`rag_client.py`) posting `{"feature": "student-5", "question"}` to the shared RAG server; `POST /ui/rag` fragment. | Questions are 1-500 characters after trimming (`400 invalid_question`). Success is `200 {answer, citations, confidence}`; the client rejects a response whose citations lack `source`, `chunk_id`, `snippet` or `score`, or whose `insufficient` confidence disagrees with an empty citation list. An out-of-scope question returns the fixed sentence `Not enough information in the knowledge base to answer this.` with no citations, as a valid `200`. Failures are `502 rag_unavailable`, `504 rag_timeout` (30s client bound) and `503 rag_disabled`. |
| TL-FR-14 | Release 1: the traveller can use both integrations from the Student 5 page. | Collapsible "Live tools & knowledge base" section in `frontend/index.html`, rendered by `templates/mcp_result.html` and `rag_answer.html`. | The MCP form reuses the planner's destination select; the result names the tool used (provenance), and the visa result shows the official-source reminder. The RAG answer shows a confidence badge, numbered citations with source, chunk id, score and snippet, a caution line for low confidence, a distinct insufficient state, and a Smartraveller disclaimer as markup. Every failure renders as a readable notice at `200`, consistent with TL-NFR-03. |
| TL-FR-15 | Release 1: Student 5 is a supported fixture of the shared agentic-loop validation modes. | `--feature student-5` in `ai-services/agentic-loop/ServiceValidation.cs`; default backend `http://127.0.0.1:5205`; `--trip-id` rejected. | `validate-mcp` posts the fixed `logistics.check_visa_requirement` call for destination 1 and passes only if the result is `ok`, is for id 1, has a country and visa category, and keeps the Smartraveller reminder. `validate-rag` passes a grounded answer whose every citation id appears in the answer, or the exact insufficient sentence with no citations. 4 new loop tests. |

## Non-functional requirements

| ID | Requirement | How it is verified |
|---|---|---|
| TL-NFR-01 | Only `student5-database` opens a SQLite file. The backend reaches all data over HTTP through `db_client.py`, and no service touches another student's database. | `grep -rn "sqlite3" student-5/backend` returns nothing. The 68-test backend suite runs entirely against mocked HTTP using `responses`, which is only possible because there is no file access to stub (`docs/evidence/pytest-backend.txt`). |
| TL-NFR-02 | Every outbound call is bounded, and the bound differs by dependency. | `db_client.DEFAULT_TIMEOUT_SECONDS = 5.0`; `ollama_client.DEFAULT_TIMEOUT_SECONDS = 120.0`; nginx `proxy_read_timeout 180s` on `/ui/` and `/api/`. A slow generation is still an answer; a dead database must not hang a backend worker. |
| TL-NFR-03 | Every failure is visible to the reader and attributable to one dependency. | JSON API returns `503 {"error": "database service unavailable"}` and `503 {"error": "ai service unavailable"}` as distinct bodies. Fragment routes render a readable notice at `200`, because HTMX does not swap a non-2xx response and a silent no-swap is the worst possible feedback. A failure the backend never received - its container down, nginx answering 502 - is caught by the `htmx:responseError` listener in `index.html`, which replaces the stale placeholder with the same `.fragment-message` markup the backend uses. Covered by tests in `backend/tests/test_advisory.py` and `backend/tests/test_ui_fragments.py`. |
| TL-NFR-04 | All environment-specific values come from environment variables. No model tag or service URL is a literal in calling code, and nothing secret is committed. | `DATABASE_API_URL`, `OLLAMA_URL` and `APPLICATION_MODEL` (backend) and `DATABASE_PATH`, `PORT` (database) are read once in each `create_app`. `OllamaClient` is constructed with the configured tag, so no request-building code names a model. `docker compose config --quiet` resolves every value. |
| TL-NFR-05 | The feature is verifiable by repeatable commands and re-verified on every push. | `.github/workflows/student-5.yml` installs both requirement sets, runs the database suite (26 tests) and the backend suite (68 tests) as separate steps, runs `docker compose config --quiet`, then builds all three images - with no live model required. Step-by-step description in `testing-evidence.md`; local captures of the same commands in `docs/evidence/pytest-database.txt`, `pytest-backend.txt` and `compose-build.txt`. Restarting the database container against the existing bind mount does not duplicate rows, because `init_db` runs the seed only when `destinations` is empty. |
| TL-NFR-06 | Release 1: MCP and RAG are off unless explicitly enabled, and fail closed. | `MCP_ENABLED` / `RAG_ENABLED` default to false in `app.py` and in Compose; `scripts/deploy/start-release1.ps1` turns them on. Disabled routes answer `503 mcp_disabled` / `503 rag_disabled` without opening a connection. The CI smoke step asserts all four 503 bodies (`docs/evidence/release-1/ci-smoke-local.txt`). |
| TL-NFR-07 | Release 1: MCP tools are read-only and bounded, and cannot reach another student's data. | `logistics.py` has no write verbs, a 3s timeout, a 20-row cap, and reads only `STUDENT5_DATABASE_API_URL`. The backend's allow-list stops the frontend reaching any other student's tool through Student 5's API. Covered in `tests/test_logistics_tools.py` and `backend/tests/test_integrations.py`. |
| TL-NFR-08 | Release 1: generated knowledge-base answers are grounded and attributable. | The RAG server's contract (citations, confidence, fixed insufficient sentence) is re-validated by `rag_client.py`, not trusted. The knowledge base is curated, sourced to Smartraveller and official authorities in `official-sources.md`, and states that it is general guidance. `tests/test_student5_retrieval.py` (17 tests) pins which chunk answers each benchmark question and that out-of-scope questions are insufficient. |
| TL-NFR-09 | Release 1: every Student 5 integration is re-verified on every push. | `scripts/test/student-5.ps1` now also runs `test_logistics_tools.py` and `test_student5_retrieval.py`; `student-5.yml` triggers on those files and the Student 5 knowledge folder, starts the three containers, and runs a smoke test over `:5205` and the `:5105` proxy. Local run of the script: 26 + 125 + 34 + 17 passed. |

## Data requirements

Three tables, all owned by `student5-database`. Full detail in `data-design.md`.

| Table | Columns | Rows on a fresh database |
|---|---|---:|
| `destinations` | `id`, `country`, `visa_requirement`, `notes` (nullable) | 12 |
| `weather_notes` | `id`, `destination_id` -> `destinations.id` cascade, `season`, `notes` | 14 |
| `transit_options` | `id`, `destination_id` -> `destinations.id` cascade, `type`, `details` | 14 |

Seed data is illustrative sample data for the assignment. Real visa and border
rules change frequently and must be checked against Smartraveller before travel.
The advisory fragment carries that disclaimer as markup, independently of
whether the model chooses to write it.

## Evidence required

- Both pytest suites, run separately - captured in
  `docs/evidence/pytest-database.txt` (`26 passed in 0.84s`) and
  `docs/evidence/pytest-backend.txt` (`68 passed in 0.54s`). Commands in
  `testing-evidence.md`.
- A successful `student-5.yml` run - captured in `docs/evidence/ci-run-green.png`:
  workflow "Student 5 CI", run `AC/complete-documentation #92`, job
  `logistics-services` `succeeded now in 24s` with every step green, including
  both pytest steps, `Validate Docker Compose config` and
  `Build integrated Student 5 containers`.
- `docker compose build` output - captured in `docs/evidence/compose-build.txt`,
  ending in `Image ...-student5-database Built`, `... -student5-backend Built`
  and `... -student5-frontend Built`. `docker compose config --quiet` produces no
  output on success by design; it runs as its own step in the CI workflow.
- All three services healthy in the integrated stack - captured in
  `docs/evidence/compose-ps.txt`, which shows `student5-database`,
  `student5-backend` and `student5-frontend` each `Up About an hour (healthy)`
  on host ports 5305, 5205 and 5105.
- Browser screenshots of the detail panels, a generated advisory, and the manage
  table - captured at `http://localhost:5105/` in `docs/evidence/`:
  `ui-filled-panels.png` (TL-FR-01..04: weather, visa and transit panels
  populated for Indonesia), `ui-advisory-output.png` (TL-FR-05: a Japan advisory
  with the footer `Generated by llama3.2:3b`), `ui-advisory-loading.png`
  (TL-FR-06: `17s` on the elapsed readout mid-generation) and
  `ui-manage-table.png` (TL-FR-07..09: the created row id 13 `Testlandia` with
  the inline edit and delete controls).
- A genuine finalised Plan/Act/Observe/Adapt record - held in
  `docs/evidence/agentic-loop-run-final-record.json` with the three terminal
  screenshots beside it, described in `prompt-log.md` and `review-record.md`.

## Release 1 evidence

All under `docs/evidence/release-1/`, indexed in `testing-evidence.md`.

- Test suites: `pytest-database.txt` (26 passed), `pytest-backend.txt`
  (125 passed), `pytest-mcp-server.txt` (135 passed, 34 of them Student 5),
  `pytest-rag-server.txt` (94 passed, 28 skipped; 17 Student 5) and
  `dotnet-agentic-loop-tests.txt` (73 passed).
- TL-FR-11/12: live MCP calls through `:5205` - `mcp-tools.json`,
  `mcp-visa-japan.json`, `mcp-weather-japan.json`,
  `mcp-transit-japan-metro.json`, and the failure contracts
  `mcp-destination-not-found.json` (404), `mcp-unknown-tool.json` (400) and
  `mcp-invalid-arguments.json` (400).
- TL-FR-13: live RAG calls - `rag-evisa.json` (grounded, cited),
  `rag-smartraveller.json`, `rag-insufficient.json`,
  `rag-invalid-question.json` (400), `rag-cold-start-timeout.json` (504), and
  `proxy-rag-travel-insurance.json` through the nginx edge on `:5105`.
- TL-FR-14: `screenshots/assist-desktop-transit-and-rag.png`,
  `assist-desktop-visa-and-insufficient.png`, `page-desktop-assist-open.png`,
  `assist-mobile-375.png`; rendered fragments `ui-mcp-fragment.html` and
  `ui-rag-fragment.html`.
- TL-FR-15: `loop/validate-mcp-terminal.txt` and `loop/validate-rag-terminal.txt`,
  with records `20261001T114821Z-cafe2142e4624e52807d4b54c983d954.json` and
  `20261001T114858Z-e3385d8dc6f1499db6c99f34beee5180.json` in
  `docs/agentic-loop-records/`.
- TL-NFR-06/09: `ci-smoke-local.txt` (the CI smoke step passes with both flags
  off and correctly fails with them on) and `compose-ps.txt` (all three
  services healthy with MCP and RAG enabled).
