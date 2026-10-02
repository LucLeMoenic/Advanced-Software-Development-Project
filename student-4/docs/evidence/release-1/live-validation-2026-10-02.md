# Student 4 Release 1 Live Validation

Date: 2026-10-02. This is runtime evidence, not release acceptance or a human loop decision. The browser 404s below are a historical snapshot from before the frontend route correction; their recorded request URLs and responses are retained as provenance. Current verification is recorded separately in `rag-guidance-live-2026-10-02.json`.

## Environment and Offline Test

- Rebuilt only `student4-backend` with `docker compose build student4-backend`.
- Recreated only that service with `docker compose up -d --no-deps --wait student4-backend`, with `STUDENT4_AI_ENABLED=true`, `STUDENT4_MCP_ENABLED=true`, and `STUDENT4_RAG_ENABLED=true`. It reported healthy and published `localhost:5204` -> container port 8080.
- `GET http://localhost:5204/api/capabilities` returned `aiEnabled=true`, `mcpEnabled=true`, and `ragEnabled=true`.
- `dotnet test student-4/backend/tests/Backend.Tests.csproj --configuration Release --no-restore`: 136 passed, 0 failed, 0 skipped.
- Native MCP and RAG were not restarted or rebound. The supplied host PIDs were MCP 65928 and RAG 52792. No `LOCAL_AI_HOST` override was set by this validation. Both live loop calls below succeeded through the backend's configured host gateway.
- Existing database rows were not seeded, changed, or deleted.

## Live MCP and Persistence

`POST http://localhost:5100/budget-api/budget-check` with `{"journeyLabel":"Sydney Weekender"}` returned HTTP 200 and `tool=budget.get_summary`, `result.ok=true`. The result matched the dashboard JSON semantically across every field and category. Values included AUD planned 785000 minor units, actual 231083, remaining 553917, and 29.44% used.

Before/after read-only list checks found 12 budgets and 26 expenses. The dashboard, complete budget-list JSON, and complete expense-list JSON were byte-identical before and after the MCP check. Invalid `{}` returned HTTP 400 (`invalid_request`); a missing journey returned HTTP 404 (`journey_not_found`).

Live loop record: `docs/agentic-loop-records/20261001T235709Z-1887f0244aa54a0ab2335e3b24062e69.json`. It records status 200 and `contractPassed=true`, with implementer `qwen2.5-coder:7b`, reviewer `llama3.2:3b`, shared prompt versions `shared-implementer-v1` and `shared-reviewer-v1`. It remains pending human finalisation. The reviewer returned ACCEPT but made unsupported suggestions that `status` and `percentageUsed` were absent from the contract; `ai-services/mcp-server/tools/budget.py` explicitly validates both fields. Treat that reviewer text as a model miss, not a source defect.

## Live RAG and Insights

The original live positive RAG loop request to `POST http://127.0.0.1:5204/api/budget-guidance` for “What does the 80% category budget warning mean?” returned HTTP 200 with `contractPassed=true`, `confidence=low`, and citation `category-budgets#2` (`Category budgets and spending statuses`, score 0.2729). Record: `docs/agentic-loop-records/20261001T235806Z-03533a8d644b4ba79a09ed8415cd954c.json`, using the same distinct model tags and shared prompt versions. It remains pending human finalisation and is preserved as historical evidence. Fresh post-clarification live answers and their grounding assessments are in [rag-guidance-live-2026-10-02.json](rag-guidance-live-2026-10-02.json).

**Grounding defect observed:** the generated answer says that spending at 80% or more indicates the category is "overspent." Its cited source says 80% through exactly 100% is `warning`, and only strictly above 100% is `overspent`. Structural/citation validation passed but did not establish claim entailment. The reviewer returned ACCEPT and vaguely suggested citations were incorrect; the citation ID/source membership is correct, while the answer's claim is not. This output must not be presented as a correct grounded answer.

A separate live backend request for "Tell me about Mars." returned HTTP 200 with the exact insufficient-context answer, empty citations, and `confidence=insufficient`. This proves backend abstention only; the browser UI request failed before reaching RAG.

The existing insights endpoint was exercised once through `POST http://localhost:5100/budget-api/insights` using the existing Sydney journey. It returned HTTP 200 with `source=ai`; no fallback was used. No insight request writes data.

## Historical Pre-Fix Browser Evidence

In the pre-fix browser run, the integrated page was opened at `http://localhost:5100/budget/`. Selecting Sydney and clicking **Check this journey** issued `POST /budget-api/api/budget-check` and returned HTTP 404. Submitting the guidance question, including keyboard Enter with “Tell me about Mars.”, issued `POST /budget-api/api/budget-guidance` and returned HTTP 404. Both requests contained an extra `/api` segment because `student-4/frontend/app.js` passed `/api/budget-check` and `/api/budget-guidance` to a helper that already prefixes `/budget-api`; the shared gateway rewrite in `shared/vue-frontend/nginx.conf` adds the backend `/api/` prefix. The corrected browser routes are `/budget-api/budget-check` and `/budget-api/budget-guidance`.

This was a confirmed frontend-to-gateway path mismatch and explains the recorded 404s. The browser could not then display the successful MCP response, expand citations, or show the Mars insufficient-context response. Playwright captured the two 404s and matching console errors. The frontend paths and mocks have since been corrected and covered by tests against the actual shared nginx rewrite; an integrated browser replay remains pending.

Full-page screenshots of the live page state:

- `screenshots/budget-live-320.png`
- `screenshots/budget-live-768.png`
- `screenshots/budget-live-1280.png`

At all three viewport widths, `document.documentElement.scrollWidth` equalled `clientWidth` (320, 768, and 1280 respectively). Visual inspection found no horizontal overflow or clipped text; category/expense tables stack at 320px. The screenshots preserve the visible browser API error state.

## Historical Scope and Remaining Gates

- At the time of the original capture, no source, Git, authentication, database, or native-service configuration was changed. No test/mock response was used for live evidence.
- The integrated dashboard and the existing AI insights path worked. Backend MCP round-trip and database non-mutation worked. Live RAG returned a structurally valid but materially inaccurate claim; Mars abstention worked at the backend.
- The pre-fix browser MCP and RAG flows, citation expansion, and browser-rendered abstention failed because of the doubled `/api` route. The source correction is now made; browser replay, citation expansion, and browser-rendered abstention still need verification.
- The reviewer suggestions and findings are not a human decision. Both records have `humanDecision=null`, no post-test, and no finalisation.
- GitHub Actions, CRUD create/update/delete browser flows, and Release 1 human acceptance were not run or claimed.

## Final Live Verification

Date: 2026-10-02. Verified on branch `BCP/R1_Budget_Validation_CI`, commit `3e8be05`, PR [#108](https://github.com/LucLeMoenic/Advanced-Software-Development-Project/pull/108). This section supersedes only the pending browser/CRUD/backend-route statements above; the pre-fix 404s, earlier grounding failures, and reviewer observations remain historical evidence. No source, Git, authentication, service configuration, or seeded data was changed.

### Integrated MCP and Dashboard

- At `http://localhost:5100/budget/`, clicking **Check this journey** issued a real `POST /budget-api/budget-check`, body containing only `journeyLabel`, and returned HTTP 200. The UI displayed `budget.get_summary` and the validated summary.
- Europe Escape matched the dashboard: EUR 3,750.00 planned, EUR 4,126.85 actual, EUR -376.85 remaining, 110.05%; all six categories and their warning/overspent statuses rendered.
- Sydney Weekender matched the dashboard: AUD 7,850.00 planned, AUD 2,310.83 actual, AUD 5,539.17 remaining, 29.44%; all six categories rendered. Changing journeys after success cleared the previous MCP result.
- The MCP callback is read-only. No database API or SQLite endpoint was called directly by the browser.

### Integrated RAG

- The UI question “What does the 80% category budget warning mean?” returned HTTP 200, medium retrieval confidence, and the exact `category-budgets#2` source paragraph. Its citation disclosure expanded with the source name, chunk ID, and snippet. The answer displays the full source paragraph; the separately displayed citation snippet is capped by the existing response contract.
- Keyboard path: Tab from the question field to **Ask guidance**, then Enter submitted “What visa do I need to visit Mars?” through the UI. The real backend returned HTTP 200 with the fixed insufficient-context answer, `confidence=insufficient`, and no citations.
- Five sequential requests to the same-origin `/budget-api/budget-guidance` gateway all returned HTTP 200 and exact source text with the expected source and chunk ID: direct threshold (medium), threshold paraphrase (low), conversion paraphrase (medium), direct conversion (low), and exact-limit boundary (low). No mocked/intercepted response or direct RAG URL was used.
- Busy/cancel state was observed on a real request: `aria-busy=true`, submit disabled, Cancel visible. Cancellation aborted the browser request and cleared the result. Focus then fell to `body`, not a useful control; this is a verified accessibility gap and remains unmodified under the no-source-change constraint.

### Temporary UI CRUD and Preservation

- Created the unique journey `Live Validation 20261002-0046` and budget ID 16 through the UI (HTTP 201), read it in the selector/dashboard, and updated its limit from EUR 250.00 to EUR 300.00 (HTTP 200).
- Created expense ID 32 through the UI: USD 12.34 previewed and persisted as EUR 11.39, with the authoritative rate/date snapshot. Updated it to USD 13.57 and EUR 12.53 (HTTP 200), and read the updated ledger row.
- Cancelled each delete dialog first: no DELETE was sent, the row remained, and focus returned to its delete button. Confirmed expense deletion returned HTTP 204 and removed its row; confirmed budget deletion returned HTTP 204 and removed the temporary journey. The expense was deleted before the budget, so budget-delete cascade behavior was not separately exercised.
- After cleanup, the only journeys were Europe Escape and Sydney Weekender. Each displayed 6 budgets and 13 expenses (12 budgets/26 expenses total); original summaries and seeded ledger rows were present. This matches the pre-test UI baseline and retained historical read-only 12/26 evidence.

### Responsive and Runtime Evidence

- Full-page screenshots, with the live MCP summary and grounded threshold guidance visible: [320 px](screenshots/budget-final-320.png), [768 px](screenshots/budget-final-768.png), [1280 px](screenshots/budget-final-1280.png).
- At all three widths `document.documentElement.scrollWidth` equalled `clientWidth`; visual inspection found no page-level horizontal scrolling, overlapping content, or clipped visible text. Tables stack into labelled records at 320 px; longer values wrap within their cells at 768 px.
- No new browser console errors were reported during the corrected-route run. Historical pre-fix 404 messages remain in the earlier all-history console capture; current requests used the corrected gateway paths.
- Backend post-test after both loops: `dotnet test student-4/backend/tests/Backend.Tests.csproj --configuration Release --no-restore --logger 'console;verbosity=minimal'` passed 136/136. Frontend post-test: `npm test --prefix student-4/frontend` passed 19/19. These were run after the live loop commands and are external post-test evidence, not values written into the loop records.
- Fresh pending loop records: [MCP](../../../../docs/agentic-loop-records/20261002T005739Z-59967194280a408087431012d86206f2.json) and [RAG](../../../../docs/agentic-loop-records/20261002T005841Z-f35f9215b3b44708b1349c215b4a9077.json). Both record HTTP 200 and `contractPassed=true`, use `qwen2.5-coder:7b` / `llama3.2:3b`, and retain `humanDecision=null`, `postTest=null`, and no finalisation. Reviewer suggestions remain model output, not a human decision.

GitHub Actions, full Student 4 `All` suite, budget-delete cascade with a linked row, and human loop/release decisions were not run or claimed. Existing untracked `.vscode/` and `ai-services/venv-mcp/` directories were observed in status and not modified.

### Cancellation Focus Replay

Date: 2026-10-02. The deployed frontend was rebuilt with `docker compose build student4-frontend` (succeeded) and recreated with `docker compose up -d --no-deps --wait student4-frontend` (healthy after 11.3 seconds). No dependency services were recreated. The already-running backend's `GET http://localhost:5204/api/capabilities` reported `aiEnabled=true`, `mcpEnabled=true`, and `ragEnabled=true`.

- Reused the existing Playwright browser and reloaded `http://localhost:5100/budget/`; no test server or mock response was used.
- Submitted the real guidance question “What does the 80% category budget warning mean?” through the page form. Before cancellation, the actual request was busy (`aria-busy=true`), Cancel was visible, and submit was disabled. Clicking Cancel immediately during that busy state produced the visible status `Guidance request cancelled.`, cleared the result, and restored focus to element ID `guidance-question`.
- The browser network log recorded the real `POST http://localhost:5100/budget-api/budget-guidance` as `FAILED net::ERR_ABORTED`, confirming the browser request was aborted.
- The deterministic dashboard remained rendered with four summary cards; the category budget list retained six rows, 12 enabled row-action buttons, and an enabled Add budget button; the expense ledger retained 13 rows, 26 enabled row-action buttons, and an enabled Add expense button. No CRUD action was taken.
- Only the Student 4 frontend image/service was rebuilt/recreated. No source, Git, authentication, backend service, configuration, or seeded data changes were made. This browser-level abort does not claim server-side processing cancellation.