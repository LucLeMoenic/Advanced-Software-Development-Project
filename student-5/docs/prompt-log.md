# Agentic Loop Prompt Log

Student 5 (Alex Chen), Release 0 and Release 1. Every attempt I made at a Plan/Act/Observe/
Adapt run through the shared development loop, in order, including the three
that failed, plus the Release 1 validation runs and AI-written code.

Only attempt (d) produced saved artefacts. Attempts (a) to (c) are recorded from
the working session; no evidence file is cited for them, because none was kept.

## All four attempts

| # | `--task` (abridged; full text of (d) is in the record JSON) | `--context` | Why one file was enough | Implementer | Reviewer | Reviewer prompt | Outcome |
|---|---|---|---|---|---|---|---|
| a | Add a country filter to the destinations list endpoint. | `student-5/database/app.py` | That module is the whole database service - schema constants, validation helpers, generic CRUD handlers and every route are in the one file. A list-filtering change touches `list_resource` and one route, both visible in it, so no second file could have changed the proposal. | `qwen2.5-coder:7b` | `llama3.2:3b` | shared `prompts/reviewer.md` (`shared-reviewer-v1`) | **Failed.** The reviewer produced no `[OBSERVE]` header at all, so `ParseVerdict` rejected the output and the run could not record a verdict. |
| b | Implement `formatElapsed(seconds)` for the advisory loading indicator. | `student-5/frontend/index.html` | The page is a single self-contained document - markup, CSS link, and the whole inline script including the function's callers and the timer that drives it. The function is pure and has no imports, so nothing outside that file constrains it. | `qwen2.5-coder:7b` | `llama3.2:3b` | shared `prompts/reviewer.md` (`shared-reviewer-v1`) | **Failed.** The reviewer echoed the shared prompt's own fill-in template - the pipe-separated `ACCEPT \| REVISE \| REJECT` and `BLOCKING \| REQUIRED \| SUGGESTION` menus - and left the required sections empty. `ParseVerdict` rejected it for an empty required section and an unresolvable verdict line. |
| c | Same `formatElapsed` task as (b). | `student-5/frontend/index.html` | As above. | `qwen2.5-coder:7b` | `codellama:7b` | shared `prompts/reviewer.md` (`shared-reviewer-v1`) | **Abandoned.** Switching the reviewer to a second 7B model put two 7B models in memory at once and Ollama OOM-killed the load: `llama-server process has terminated: signal: killed`. Abandoned on the spot rather than retried, because `codellama` is outside the unit's approved LLM list anyway - so even a successful run would not have been usable evidence. |
| d | Implement `formatElapsed(seconds)` at the `TODO(you)` marker: empty string for the first 2 seconds, `Ns` from 2 seconds, `still working - Ns` past 45 seconds; pure function, no DOM access, ES2020, no build step; plus a commented-out `node -e` assertion snippet covering 0, 1, 2, 14, 45, 52; with an explicit scope note forbidding changes to any other function, `hx-*` attribute, CSS or file, and forbidding proposals of performance testing, extra tooling or a test framework. | `student-5/frontend/index.html` | As above - one document holds the stub, its two callers, the interval that calls it, and the surrounding code style the task asks the proposal to match. | `qwen2.5-coder:7b` | `llama3.2:3b` | **`student-5/docs/prompt-library/reviewer-llama32-v2.md`** (`student5-reviewer-llama32-v2`) | **Succeeded.** Full `[PLAN]` -> `[ACT]` -> `[OBSERVE]` -> `[ADAPT]` -> second `[OBSERVE]`, record written, then finalised with a human decision. |

Attempts (a) to (c) left no record file, so there is no artefact to cite for
them. What the repository does still carry is the branch each was attempted on -
`AC/agenticloop-work-01-country-filter` for (a), and
`AC/agenticloop-work-elapsed-timer` for (b), (c) and (d) - and commit `319f13b`
on the first of those, an `[OBSERVE]` heading regex fix made while investigating
why attempt (a) produced no verdict.

## What changed between (b) and (d)

The task, the context file and both models were identical. The only difference
was `--reviewer-prompt`, pointing at my rewritten reviewer prompt instead of the
shared one. That is what turned a run the parser rejected into a run that
completed - see `prompt-engineering.md` for the defect in
`shared-reviewer-v1` and what v2 changed.

## Attempt (d) in detail

### Command as run

```bash
docker compose exec agentic-loop dotnet /app/AgenticLoop.dll run \
  --task "<full task text - see the record JSON>" \
  --context "/workspace/student-5/frontend/index.html" \
  --pre-test-command "Select-String -Path student-5/frontend/index.html -Pattern 'TODO\(you\)'" \
  --pre-test-result "formatElapsed stub present at the TODO(you) marker, returns empty string - no elapsed counter renders during generation" \
  --reviewer-prompt "/workspace/student-5/docs/prompt-library/reviewer-llama32-v2.md"
```

### Configuration recorded by the run

| Field | Value |
|---|---|
| Record | `20260906T053024Z-ad4b32c67df446e8af9e1fca8cc22044.json` |
| Created | 2026-09-06T05:30:24Z |
| Implementer model / prompt | `qwen2.5-coder:7b` / `shared-implementer-v1` |
| Reviewer model / prompt | `llama3.2:3b` / `student5-reviewer-llama32-v2` |
| Generation options | temperature 0, context 16384, max output 4096 |
| Ollama version | 0.33.3 |
| Context SHA-256 | `95A6AFCB...E017518` for `student-5/frontend/index.html` |
| Reviewer prompt SHA-256 | `956DD0F2...D1D2E5F38` |

### What happened, phase by phase

1. **`[PLAN]` / `[ACT]`** - the implementer restated the requirements, named the
   one file, listed two steps, and proposed the function plus the commented
   assertion snippet.
2. **First `[OBSERVE]`** - the reviewer returned `Verdict: ACCEPT` alongside a
   `Severity: REQUIRED` finding. `ParseVerdict` rejects that combination
   (a REQUIRED finding cannot coexist with ACCEPT), printed
   `Reviewer output was malformed; requesting one format correction`, and asked
   for one correction. The corrected review returned `Verdict: REVISE` with the
   same finding.
3. **`[ADAPT]`** - the implementer produced one bounded revision. It re-emitted
   the same function, which is the correct response to a finding that does not
   apply to it.
4. **Second `[OBSERVE]`** - the reviewer returned `REVISE` again with the same
   finding, and the run stopped for human finalisation:
   `Agentic-loop record awaiting human finalisation`.
5. **Human decision** - I verified by inspection that the proposed function
   contains no division, no list and no `count` variable, rejected the finding,
   applied the proposal, and finalised with `--decision changed` and seven
   passing `node -e` assertions.

The reviewer's finding is word-for-word Example 2 in
`reviewer-llama32-v2.md`. The full analysis is in `review-record.md`.

### Evidence for (d)

| File | Shows |
|---|---|
| `evidence/agentic-loop-run-part1.png` | The `run` command with all five flags, `[PLAN]`, `[ACT]`, the first malformed `[OBSERVE]`, and the format-correction retry |
| `evidence/agentic-loop-run-part2.png` | `[ADAPT]`, the second `[OBSERVE]`, and `Agentic-loop record awaiting human finalisation: /workspace/docs/agentic-loop-records/20260906T053024Z-ad4b32c67df446e8af9e1fca8cc22044.json` |
| `evidence/agentic-loop-finalise.png` | The `finalise` command with the decision, notes and post-test flags, and `Finalised agentic-loop record: ...` |
| `evidence/agentic-loop-run-final-record.json` | The finalised record, including `humanDecision`, `humanNotes`, `preTest` and `postTest` |
| `evidence/agentic-loop-models.txt` | The loop's health output confirming the two distinct model tags |
| `evidence/agentic-loop-records-index.txt` | The records directory listing, confirming the record file and its size |
| `evidence/formatelapsed-assertions.txt` | `all assertions passed` from the post-test run |

## Context management across the four attempts

Every attempt used exactly **one** `--context` file, chosen so the proposal
could not need a second. That is a deliberate control, not a shortcut: a 7B
implementer given several files starts proposing changes across all of them, and
the loop's record then covers a diff too large for one human decision.

The task text carried the same discipline. Attempt (d)'s task ends with an
explicit scope note - *do not change any other function, any `hx-*` attribute,
any CSS, or any other file, and do not propose performance testing, additional
tooling, or a test framework* - written after earlier attempts drifted toward
suggesting a test framework for a nine-line pure function. The reviewer's
`Scope check:` line then has something concrete to check against, and it
correctly reported that the change touched only the one function.

## Release 1

### AI-written code for Release 1

The Release 1 implementation was written by **GitHub Copilot CLI** (Claude
Opus 5.5) in one supervised session, working from the Release 1 brief, the
project specifications, this docs folder and the existing Student 1-3 Release 1
patterns. I directed scope, ran the stack, and reviewed the result (see
`review-record.md`, "Release 1").

| Area | Files written or changed by the assistant |
|---|---|
| MCP tools | `ai-services/mcp-server/tools/logistics.py`, `tools/__init__.py` (registration line), `tests/test_logistics_tools.py` |
| RAG knowledge | 8 documents in `ai-services/rag-server/knowledge/student-5/`, `tests/test_student5_retrieval.py` |
| Backend | `mcp_client.py`, `rag_client.py`, `integrations.py`, `ui.py`, `app.py`, `templates/mcp_result.html`, `templates/rag_answer.html`, `requirements.txt`, `Dockerfile`, `tests/conftest.py`, `tests/test_integrations.py` |
| Frontend | `index.html` (assist section), `style.css` (assist, citation and confidence styles; responsive rules) |
| Integration and CI | `docker-compose.yml` (`student5-backend` flags only), `.env.example` comment, `scripts/test/student-5.ps1`, `.github/workflows/student-5.yml` |
| Shared agentic loop | `ServiceValidation.cs` (`student-5` fixture), `AgenticLoopApplication.cs` (`--trip-id` rejection), `tests/AgenticLoopTests.cs`, `README.md` |
| Docs and evidence | This folder and `evidence/release-1/` |

The assistant made its changes in the working tree only. An earlier
single-branch push it made was withdrawn, and I then committed, pushed and
opened each of the seven Release 1 pull requests myself (see
`contribution-log.md`).

Tests run on the final working tree (on top of `main` at `5114071`), all passing:

| Suite | Result |
|---|---|
| `student-5/database` | 26 passed |
| `student-5/backend` | 125 passed (68 before Release 1) |
| `ai-services/mcp-server` | 135 passed, 34 of them Student 5 |
| `ai-services/rag-server` | 94 passed, 28 skipped (opt-in live evaluation), 17 of them Student 5 |
| `ai-services/agentic-loop/tests` | 73 passed (69 before Release 1) |
| `scripts/test/student-5.ps1` | 26 + 125 + 34 + 17 passed |
| CI smoke step, run locally | passes with flags off; fails with `AssertionError: 200` with flags on (`evidence/release-1/ci-smoke-local.txt`) |

Two things the assistant got wrong and corrected during the session: it first
passed the repository root as a positional argument to `start-release1.ps1`,
which bound to `-McpVenv` and created a virtual environment in the repo (cleaned
up; do not pass `.`); and the `/ui/mcp` transit filter field is `transit_type`,
not `type`, which it found when the first fragment capture ignored the filter.
An independent AI code review then found that `get_transit` filtered after the
20-row cap; that was fixed with a regression test before committing (see
`review-record.md`).

### Validation runs (e) and (f)

Both runs used the native loop against the live stack, with
`MCP_ENABLED=true RAG_ENABLED=true`, the same two models as (d), and my
`reviewer-llama32-v2.md` prompt. `--reviewer-prompt` needs an absolute path; a
relative path is resolved against the loop project directory.

| # | Mode | `--task` | `--context` | Pre-test | Reviewer outcome | Record |
|---|---|---|---|---|---|---|
| e | `validate-mcp --feature student-5` | Validate the captured `logistics.check_visa_requirement` result for destination 1 against the tool design: confirm it is read-only, bounded, scoped to the requested destination and carries the official-source reminder. Propose at most one small, bounded improvement to `logistics.py` if a real gap exists; otherwise state that no change is needed. | `ai-services/mcp-server/tools/logistics.py`, `student-5/backend/integrations.py` | `200`, `contractPassed: true` | First review malformed (echo of the prompt's worked example); after one format correction, `ACCEPT` with one SUGGESTION. No `[ADAPT]`. | `20261001T114821Z-cafe2142e4624e52807d4b54c983d954.json` |
| f | `validate-rag --feature student-5` | Validate the captured visa guidance answer against its cited knowledge chunks. List any sentence in the answer that is not supported by a cited snippet. Propose at most one small, bounded improvement to `visa-categories.md` if a real gap exists; otherwise state that no change is needed. | `ai-services/rag-server/knowledge/student-5/visa-categories.md` | `200`, `contractPassed: true`, question `What is the difference between visa on arrival and an eVisa?` | `ACCEPT` with one SUGGESTION. No `[ADAPT]`. | `20261001T114858Z-e3385d8dc6f1499db6c99f34beee5180.json` |

```powershell
dotnet run --project ai-services/agentic-loop -- validate-mcp --feature student-5 `
  --task '<task (e) above>' `
  --context ai-services/mcp-server/tools/logistics.py `
  --context student-5/backend/integrations.py `
  --reviewer-prompt "$PWD\student-5\docs\prompt-library\reviewer-llama32-v2.md"

dotnet run --project ai-services/agentic-loop -- validate-rag --feature student-5 `
  --task '<task (f) above>' `
  --context ai-services/rag-server/knowledge/student-5/visa-categories.md `
  --question 'What is the difference between visa on arrival and an eVisa?' `
  --reviewer-prompt "$PWD\student-5\docs\prompt-library\reviewer-llama32-v2.md"
```

In both runs the implementer concluded that no change was needed. Terminal
output is in `evidence/release-1/loop/`. I finalised both records myself
after reviewing them: (e) `kept`, (f) `kept` (see `review-record.md`).

## Release 2

Plan: [`release-2-plan.md`](release-2-plan.md). Code was written by an AI coding
assistant in supervised sessions; every change was reviewed, tested and committed
by me.

### Chunk 1 - AI-off guard (TL-FR-18), 21 October 2026

**Why:** the cloud baseline (`scripts/deploy/prepare_cloud.py`) sets
`AI_ENABLED=false` on every backend, but Student 5's backend never read it, so
`POST /api/advisory` would still have called Ollama and timed out in the cloud.

**Prompt (summary):** "Start Chunk 1": make AI-Mode switchable the same way MCP and
RAG already are, default on, and verify it in tests and the live container.

**AI-written change:**

- `ollama_client.py`: `OllamaDisabled` exception, `enabled` flag and
  `ensure_enabled()`, checked at the top of `generate()`.
- `advisory.py`: `generate_advisory()` calls `ensure_enabled()` *before* the
  database read, so a disabled advisory makes no network call at all.
- `app.py`: `AI_ENABLED` read through `env_flag(..., default=True)`. AI-Mode is the
  Release 0 core feature, unlike opt-in MCP/RAG. 503 handler returns
  `{"error": "ai_disabled", "message": "AI-Mode is disabled."}`, the same shape as
  the MCP/RAG disabled responses.
- `ui.py`: `OllamaDisabled` renders a "switched off for this deployment" notice.
- `docker-compose.yml`: `AI_ENABLED: ${AI_ENABLED:-true}` on `student5-backend`.
- Tests: `ai_off_client` fixture, plus 5 tests for env parsing, a 503 with no
  network call, a 400 still returned first for a bad body, CRUD with AI off, and
  the UI notice.

**Correction during the session:** the first CRUD-with-AI-off test mocked
`/destinations`; the database API path is `/api/destinations`. Found by reading
the existing fixtures before running, then fixed.

**Validation:**

| Check | Result |
| --- | --- |
| Backend pytest (repo `.venv`, Python 3.13) | `130 passed in 2.88s` |
| Full Student 5 suites (`student-5.ps1` equivalents) | database 26, backend 130, MCP logistics 34, RAG student-5 retrieval 17 passed |
| Independent AI code review | No findings; see `review-record.md` (Release 2 - Chunk 1) |
| Pre-commit hooks on the changed files | Ruff security rules Passed; detect-secrets Passed; pip-audit Skipped (no requirements changed) |
| Live container, `AI_ENABLED=false` | `POST /api/advisory` returns `503 {"error":"ai_disabled",...}` in 0.006 s; `/logistics/ui/advisory` through the shared gateway renders the notice; `GET /api/destinations` returns 200 |
| Live container, `AI_ENABLED=true` (restored) | Real grounded advisory from `llama3.2:3b`, HTTP 200 in 2.65 s |

### Chunk 2 - Multi-Agent integration (TL-FR-16, TL-FR-17, TL-NFR-10), 22 October 2026

**Why:** Release 2 marks the Planner -> Worker -> Reviewer -> Human Review workflow
through the frontend, and Student 5 had no route to the shared Multi-Agent Server
(`ai-services/multi-agent-server/`).

**Prompt (summary):** "Chunk 2 of my plan": integrate Student 5 with the shared
server, modelled on Student 2's Flask integration but without another agent system.
An opt-in client (`MULTI_AGENT_ENABLED`, default `false`); bounded evidence for one
destination with distinctive titles so the server's subject checks pass; create,
poll and decision routes that check the workflow is Student 5's and belongs to the
requested destination; an HTMX "Trip readiness review" panel that polls every 2 s
and ends in a four-way decision form; compose flags; mocked tests; one live review
through `http://localhost:5100/logistics/`, leaving the decision to me.

**AI-written change:**

- `multi_agent_client.py`: `MultiAgentDisabled`, `MultiAgentUnavailable` and
  `MultiAgentRefused` (status + code, for busy / not found / already decided /
  server decision rules). Workflow ids are checked against the server's own regex
  before any URL is built; every record is shape-checked before it is rendered;
  10 s bound per call.
- `readiness.py`: evidence built through the existing `load_context()` - one item
  for the entry requirement, one per weather note and transit option (max 6 each),
  "none recorded" items for empty lists, texts clipped to 400 characters, and the
  count of rows supplied stated first. `distinct_titles()` suffixes any title that
  contains or is contained in another, because the server's `checks.py` matches
  subjects by substring. The first evidence id, `destination-<id>`, binds the
  workflow to its destination. JSON routes: `POST
  /api/destinations/<id>/readiness-reviews`, `GET /api/readiness-reviews/<wid>`,
  `POST /api/readiness-reviews/<wid>/decision`. The server's decision rules are
  relayed rather than repeated, as with the database's validation.
- `ui.py` + `readiness_status.html` / `readiness_review.html`: a self-polling status
  block that answers `204` while the status is unchanged, so the panel's live region
  is not re-announced every 2 s; then the plan, the checklist (with the record each
  item cites), the Reviewer findings and the decision form (approve / correct per
  item / partial by checkbox / reject, plus `decided_by`). A refused decision
  re-renders with the reason and the typed values kept.
- `app.py`, `Dockerfile`, `docker-compose.yml` (`student5-backend` only),
  `frontend/index.html` and `style.css`, `requirements.md` (TL-FR-16, TL-FR-17,
  TL-NFR-10).
- Tests: `tests/test_readiness.py` (56), plus `MULTI_AGENT_ENABLED: False` pinned in
  the two existing conftest fixtures.

The code is split into `multi_agent_client.py` + `readiness.py` rather than the
plan's single `multi_agent.py`, to match Student 5's existing `*_client.py` +
blueprint split (`rag_client.py` / `integrations.py`).

**Corrections during the session:**

- The first template put the Reviewer before the Worker so the checklist could sit
  inside the form. It now follows pipeline order, with the form opened before the
  checklist.
- Ids in the fragment broke the "templates carry classes only" rule in `ui.py`;
  inputs are now wrapped in their labels and the loading indicator lives in
  `index.html`.
- Three of the first test assertions were wrong (a nested `**extra`, Flask decoding
  `%2F` before routing, and a heading-order check that matched the verdict badge).
- After the independent review: a missed poll now keeps polling instead of
  stranding a running review; a `400` on create is now a `502` (it means our
  evidence was refused, not the caller's request); textarea CRLF is folded to LF
  before the server's length limits apply.

**Validation:**

| Check | Result |
| --- | --- |
| Backend pytest (repo `.venv`, Python 3.13) | `186 passed` (130 before + 56 in `test_readiness.py`) |
| Full Student 5 suites | database 26, backend 186, MCP logistics 34, RAG student-5 retrieval 17 passed |
| Independent AI code review | 1 important, 1 minor, 2 nits; 3 fixed, 1 kept by design - see `review-record.md` (Release 2 - Chunk 2) |
| Pre-commit hooks on the changed files | Ruff security rules Passed; detect-secrets Passed; pip-audit Skipped (no requirements changed) |
| Native Multi-Agent Server | `scripts/deploy/start-multi-agent.ps1` (single worker, `127.0.0.1:5600`), reachable from the container via `host.docker.internal` |
| Live review through `:5100/ui/` (Japan) | `wf-20261021T230750Z-6cded4a6`: queued -> planning -> working -> reviewing -> awaiting_human_review in 28 s (Planner 14.5 s, Worker 5.2 s, Reviewer 7.5 s, `llama3.2:3b`). 5 evidence items, 5 checklist items each citing its own record; verdict `concerns` (one model warning), no blocking finding; unchanged polls returned `204` |
| Binding check, live | Poll and decision for destination 2 return `404 review_not_found`; nothing posted |
| `GET /audit/verify` | `{"valid": true, "entries": 9, "broken_at": null}` |
| Human decision | Not yet recorded - left for me to make in the browser |

### Chunk 3 - Post-commit CI/CD endpoint tests (TL-NFR-11), 22 October 2026

**Why:** the Release 2 brief (marking criterion 4) requires `student-5.yml` to test
two endpoint functions of the Student 5 backend/API after every push. Until now the
workflow only ran the Release 1 suites and smoke checks.

**Prompt (summary):** "Chunk 3 of my plan". Follow the Student 1/3 pattern
(`test_endpoints_cicd.py`, `--junitxml`, `junit_summary.py`, `upload-artifact`) and
Student 2's four AI flags set to `"false"`. For `POST /api/destinations` and
`PUT /api/destinations/<id>`, test valid input (status, body, exact forwarded
request), invalid input (database 400 relayed), not-found for PUT and database down
(503). Add a live create -> update -> read -> delete check against the running
containers with a unique country and guaranteed cleanup. Validate the YAML, run the
same commands locally (AI off, then restore) and write the endpoint-testing report.

**AI-written change:**

- `backend/tests/test_endpoints_cicd.py` (new, 13 tests). It uses the existing
  `ai_off_client` and `database_url` fixtures and `responses`. Each test asserts
  exactly one forwarded request (method, URL, JSON body) plus the relayed status and
  body. The 400/404 bodies are copied from `database/app.py`. Extra cases: a
  non-JSON POST is forwarded as no body, and a non-integer PUT id is a backend `404`
  with no database call.
- `backend/tests/live_endpoint_check.py` (new, standard library, not collected by
  pytest). It runs 12 checks over HTTP against the containers with a
  `CI Endpoint Check <8 hex>` country, and writes a table to `$GITHUB_STEP_SUMMARY`.
- `.github/workflows/student-5.yml`:
  - a "Post-commit endpoint tests (POST and PUT /api/destinations)" step with the
    four flags `"false"`, producing `student-5/endpoint-tests-junit.xml`;
  - "Publish endpoint test report" (`junit_summary.py`) and "Upload endpoint test
    results" (`student-5-endpoint-test-results`);
  - the four flags on "Start Student 5 services";
  - an `ai_disabled` advisory assertion in the smoke step;
  - the live-check step, and container logs on failure;
  - `scripts/test/junit_summary.py` added to the push/PR triggers.

  The Release 1 steps are unchanged.
- `scripts/test/student-5.ps1` was **not** changed. Students 1 and 3 keep their JUnit
  runs in the workflow, not in their `.ps1`. The script's existing `pytest tests`
  run in `backend/` already picks up the new file (backend 186 -> 199).
- `docs/evidence/release-2/endpoint-testing-report.md` and `endpoint-tests/01`-`05`.

**Corrections during the session:**

- The first live-check draft returned the new id from the function that also ran the
  later checks, so an exception part-way would have skipped the cleanup. The create
  now happens in `main()` and everything after it is inside `try/finally`.
- One scripted workflow edit failed on backslash escaping and wrote nothing. It was
  redone with direct edits and the YAML was re-parsed.
- After the independent review:
  - the cleanup now finds the row by its unique country if the create reply had no
    usable id;
  - any exception, not just `OSError`/`ValueError`, is recorded so the step summary
    is always written;
  - `|` and newlines in summary cells are escaped;
  - the workflow comment notes that the fixture also pins the flags.

**Validation:**

| Check | Result |
| --- | --- |
| Endpoint tests, workflow command (repo `.venv`, Python 3.13.2) | `13 passed in 0.32s`; `junit_summary.py`: **13 of 13 passed** |
| Mutation check (4 deliberate bugs in `app.py`, then restored) | each caught: 1, 3, 7 and 3 failing tests |
| Full Student 5 suites | database 26, backend 199 (186 + 13), MCP logistics 34, RAG student-5 retrieval 17 passed |
| Workflow YAML / Compose | `yaml.safe_load` OK (13 steps, push and PR paths identical); `docker compose config --quiet` OK |
| Live stack, backend recreated with all four flags `false` (checked with `env` in the container) | smoke step run with `bash` passed, including `ai_disabled`; `live_endpoint_check.py` **12/12 checks passed**; 12 seed rows left, no `CI Endpoint Check` row |
| Live check failure paths | unreachable backend: exit 1, one `FAIL` row in the summary; create reply with no usable id: row found by country and deleted |
| Independent AI code review | 0 critical/important, 4 minor, 3 nits; 4 fixed, 3 kept - see `review-record.md` (Release 2 - Chunk 3) |
| Pre-commit hooks on the changed files | Ruff security rules Passed; detect-secrets Passed; pip-audit Skipped (no requirements changed) |
| Local stack restored | backend recreated from `.env` (`AI_ENABLED=true`, MCP/RAG `true`, Multi-Agent `false`) |
| GitHub Actions run | Not yet run: needs the push. To be added to the endpoint-testing report. |
