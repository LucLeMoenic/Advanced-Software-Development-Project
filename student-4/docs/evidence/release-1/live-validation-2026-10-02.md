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