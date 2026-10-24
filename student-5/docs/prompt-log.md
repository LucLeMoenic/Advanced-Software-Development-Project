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

The Release 1 implementation was written by an AI coding assistant in one
supervised session, working from the Release 1 brief, the
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

### Chunk 4 - Pre-commit security testing evidence, 22 October 2026

**Why:** the Release 2 brief requires Ruff security rules, detect-secrets and
pip-audit to run locally during the commit workflow, with a report of results and
findings. Student 5 still had an accepted pip-audit exception
(`PYSEC-2026-1845`, pytest below 9 in `database/requirements.txt`). That pin also
made a combined install with the shared MCP/RAG requirements (`pytest==9.0.3`)
impossible.

**Prompt (summary):** "Chunk 4 of my plan": retire the Student 5 pip-audit
exception, run the three hooks over every tracked Student 5 file, fix or document
each finding, prepare a blocked-commit demo for me to run, and write the
pre-commit report with captures.

**AI-written change:**

- `database/requirements.txt` and `backend/requirements.txt`:
  `pytest>=9.0.3,<10.0` (database was `>=8.0,<9.0`; backend was `>=8.0,<10.0`).
- `scripts/security/pip-audit-accepted.json`: Student 5 entry removed. The Student 2
  entries are unchanged.
- `database/app.py`: reasons added to three bare `# noqa: S608` comments. Comment
  only, no code change.
- `docs/evidence/release-2/precommit-security-report.md` and `precommit/01`-`03`.
  `04-blocked-commit.txt` is captured by me from a real `git commit`.
- Shared config (`.pre-commit-config.yaml`, `pyproject.toml`, `.secrets.baseline`)
  is unchanged. pip-audit 2.10.1 was installed into the repo `.venv`.

**Corrections during the session:**

- The pip-audit hook is `language: system` with `entry: python`. It ran the
  WindowsApps Python, which has no `pip_audit`, so a commit changing a
  requirements file would have been blocked. This is worked around by committing
  with `.venv` activated. It is flagged in the report for the shared config owner,
  not changed.
- After the independent review:
  - the report no longer describes the real blocked commit as done. It gives the
    dry-run result and points to `04`;
  - `03` now shows the resolver's "would install" output and the pytest version,
    not comments;
  - wording on ignore scope was corrected;
  - the backend floor was raised;
  - the `noqa` reasons were added.

**Validation:**

| Check | Result |
| --- | --- |
| pip-audit, database as on `main` (exception off) | 2 entries for `PYSEC-2026-1845` (pytest 8.4.2, fix 9.0.3), exit 1 |
| pip-audit hook, both Student 5 requirements files after the bump | Passed: "No known vulnerabilities found" for both, no exceptions applied |
| Combined install, database + MCP + RAG requirements (`--dry-run`) | Before: `ResolutionImpossible`. After: exit 0, pytest 9.0.3, Flask 3.1.3 |
| Ruff hook, all 111 tracked Student 5 files | Passed. Raw with ignores off: 369 `S101` (tests only), 2 `S104`. With `noqa` ignored: 5 `S608`, traced and safe |
| detect-secrets hook, all 111 files | Passed. 4 raw candidates (3 SHA-256 evidence hashes, 1 SRI hash), already `is_secret: false`; baseline unchanged |
| Blocked-commit dry run (`pre-commit run --files` on an untracked insecure file) | Ruff `S602` and detect-secrets "AWS Access Key", exit 1; file deleted |
| Full Student 5 suites (pytest 9.1.1) | database 26, backend 199, MCP logistics 34, RAG student-5 retrieval 17 passed |
| Independent AI code review | 0 critical, 1 important, 3 minor, 2 nits; all addressed. See `review-record.md` (Release 2 - Chunk 4) |
| Pre-commit hooks on the changed files | Ruff Passed; detect-secrets Passed; pip-audit Passed |
| Real blocked `git commit` | Run by me after handover; recorded in `precommit/04-blocked-commit.txt` |

### Chunk 5 - Cloud deployment smoke coverage, 22 October 2026

**Why:** the Release 2 brief (marking criterion 7) requires the deployed application's
frontend, backend/API, database and CRUD to work in the cloud with AI-Mode, MCP,
RAG and Multi-Agent disabled. `cloud-deployment.yml` proves this with
`scripts/deploy/smoke_cloud.py`. The existing Student 5 check (added in PR #130)
was read-only, because it assumed Student 5 had no update or delete. It also
accepted any `503` from the AI routes, including one from a backend that was down.

**Prompt (summary):** "Chunk 5 of my plan". Read `cloud-deployment.yml`,
`prepare_cloud.py`, `smoke_cloud.py` and Student 1's commit `cfcb7e6`. Add a Student 5
check through the public gateway: create a uniquely named destination, read it back,
update it, read the change, delete it and confirm it is gone, always cleaning up.
Also assert that the advisory, MCP and RAG routes return their `503` disabled bodies.
Add a mocked test covering the happy path, CRUD failure and AI unexpectedly enabled.
Run the check against the local stack with the AI flags off, then restore them.
Check whether the workflow needs a Student 5 change (describe it, don't make it).
Write the cloud-deployment report section and a message for the cloud owner.

**AI-written change:**

- `scripts/deploy/smoke_cloud.py`: `check_student5` rewritten, and the Student 5
  `PASS` line in `run()` updated. Nothing else in the shared file was changed.
  - It keeps the seed checks (at least 10 destinations, weather and transit data
    non-empty).
  - It asserts `503` **and** the named error for `ai_disabled`, `mcp_disabled`,
    `rag_disabled` and `multi_agent_disabled`, all before anything is written.
  - Then it runs create -> read -> update -> read -> delete -> `404` on an
    `R2 smoke <8 hex>` destination, with the delete in `finally`.
  - Multi-Agent was added beyond the prompt, because the brief requires all four AI
    services off in the baseline (TL-NFR-10).
- `scripts/test/test_cloud_smoke_student5.py`: rewritten for the new behaviour, with
  a stateful fake gateway like Student 1's. 18 tests:
  - the happy path;
  - seed and reference data;
  - each AI route answering `200` (no row created);
  - each AI route answering a `503` without its body;
  - five failure points after the create (each must still delete the row);
  - a deleted row that is still readable.
- `docs/evidence/release-2/cloud-deployment-report.md` (new), with placeholders
  for the real cloud run.
- `cloud-deployment.yml` and `prepare_cloud.py` were **not** changed. No Student 5
  change is needed; one stale step name is noted in the report for the owner.

**Corrections during the session:**

- The first mutation run for "no cleanup" and "no gone check" did not apply. The
  anchor text also occurs in the Student 3/4 functions, so the uniqueness guard
  refused the edit. The two "all passed" lines were therefore not evidence. Both
  were re-run with anchors unique to `check_student5`, and both were caught.
- After the independent review, the fake can now corrupt the created row, drop the
  country on update, and answer `500` on the first readback or on the update. The
  create readback, the "country kept" check and the `finally` cleanup are each
  shown to matter (14 -> 18 tests).

**Validation:**

| Check | Result |
| --- | --- |
| Student 5 smoke tests (repo `.venv`, Python 3.13.2) | `18 passed` |
| All `scripts/test` | `229 passed, 58 skipped` (skipped: needs Linux symlink semantics) |
| Mutation check on `check_student5` (5 mutations, file restored byte-for-byte) | no create readback: 1 failing; no country-kept check: 1; no disabled-body check: 4; no cleanup on failure: 5; no gone check: 2 |
| Live local run: real `check_student5` via local gateway `http://localhost:5100`, backend recreated with all four flags `false` (checked with `env`) | 14/14 calls as expected, `PASS`, exit 0; four refusals in 6-21 ms; 12 destinations afterwards, no `R2 smoke` row |
| Same check with flags restored (AI-Mode on) | Failed at its first AI call (`POST /advisory` hit the 30 s client timeout); no row created (still 12) |
| Full Student 5 suites | database 26, backend 199, MCP logistics 34, RAG student-5 retrieval 17 passed |
| Independent AI code review | 0 bugs, 2 minor test-strength findings, both fixed. See `review-record.md` (Release 2 - Chunk 5) |
| Pre-commit hooks on the changed files | Ruff security rules Passed; detect-secrets Passed; pip-audit Skipped (no requirements changed) |
| Local stack restored | backend recreated from `.env` (`AI_ENABLED=true`, MCP/RAG `true`, Multi-Agent `false`) |
| `cloud-deployment.yml` run | Not yet run: needs merge to `main` and the cloud owner to dispatch it. To be added to the cloud-deployment report. |

### Chunk 6 - Local deployment, Multi-Agent workflow and agentic-loop review evidence, 22 October 2026

**Why:** the Release 2 brief requires real evidence of the integrated local run with the
native Multi-Agent Server (multi-terminal logs), a completed Planner -> Worker -> Reviewer ->
Human Review workflow from both the UI and the terminal with audit verification, and the
three agentic-loop review modes with their review logs. Chunks 2-5 had built and tested the
pieces; none of this had been run end to end with real decisions.

**Prompt (summary):** "Chunk 6 of my plan". Start Ollama, MCP and RAG with
`start-release1.ps1` and the Multi-Agent Server with `start-multi-agent.ps1`, without piping
either. Bring the stack up with `MULTI_AGENT_ENABLED=true`. Capture health checks, an advisory,
an MCP call and a RAG answer through `:5100/logistics/`. Run one readiness review from the UI
and one from `cli.py` with Student 5 evidence. Copy the workflow and audit records and capture
`GET /audit/verify`. Run `review-multi-agent`, `review-testing` and `review-cloud` with
`qwen2.5-coder:7b` / `llama3.2:3b` and my reviewer prompt, then `finalise` each. Write the
Multi-Agent and local deployment reports, modelled on Student 3's. Never fabricate output, and
leave the human decisions to me. Later: take the screenshots in Chrome and finish the chunk end
to end.

**AI-assisted work (no application code changed):**

- **Local run:**
  - The launcher ran unpiped. Its transcript is `local/01`. MCP, RAG, Multi-Agent and Compose
    logs are in `local/terminal-logs/`.
  - Health checks for the four native services and the Student 5 containers (`local/02`).
  - Advisory, MCP and RAG calls through the gateway (`local/03`-`05`).
  - Local CRUD through the gateway (`local/08`) and host information (`local/09`).
  - Chrome screenshots of the integrated page (`local/06`-`07`).
- **Multi-Agent:**
  - A terminal run with an evidence file built by the backend's own `build_evidence()`
    (Vietnam).
  - A UI review started over HTTP and decided in Chrome (Indonesia).
  - A review run fully in Chrome (Thailand).
  - Five workflow records and the 50-entry audit log copied to
    `multi-agent-server/workflow-data/`, with transcripts and 8 screenshots.
- **Loop:**
  - Three records, the failed attempts, the finalise transcript and the record copies are in
    `loop/`.
  - The records are in `docs/agentic-loop-records/20261022T10{2258,2407,5130}Z-*.json`.
- **Reports:**
  - New: `multi-agent-server-report.md` and `local-deployment-report.md`.
  - Placeholders filled with the real runs:
    - `endpoint-testing-report.md`: runs 39697590918 and 39698558980, the JUnit artifact,
      and CI screenshots.
    - `cloud-deployment-report.md`: run 39741981906 at `851bdd7`, the artifact, a read-only
      check of the public URL, and 5 screenshots.
  - These were needed before `review-testing` and `review-cloud`, whose criteria reject
    placeholders.
- **Other:**
  - `known-issues.md`: new Release 2 section.
  - `.secrets.baseline`: 87 SHA-256 digests in the new loop records and audit log, added as
    audited false positives, following the existing records' precedent. Additions only.

**Human decisions (Alex Chen):** an AI coding assistant prepared a recommendation for each
decision. Alex approved each one before it was entered by the assistant (the CLI, Chrome form
and `finalise` commands):

- Vietnam `partial`, keeping i1, i3 and i4;
- Indonesia `correct`, all five items rewritten as actions;
- Thailand `partial`, keeping i1-i4;
- `review-testing` `rejected` (false-positive finding);
- `review-cloud` `changed`;
- `review-multi-agent` `changed`, by a rule Alex set in advance: `kept` / `changed` /
  `rejected` depending on whether the findings are correct.

**Corrections during the session:**

- The first health capture labelled MCP "406 = up". The server answered `400 Missing session
  ID`, which is also a valid transport-up reply. The capture also had a broken pipe in it, so
  it was re-run.
- The first cloud draft claimed the domain was a hidden secret, then "five commits" behind
  main, and that all later dispatches failed at the protected-AI step. All three claims were
  wrong. It is a repository variable. The deployed revision is one commit behind. Three
  dispatches failed at the CI gate and one at the protected-AI step.
- The local report gave the wrong Ollama version (0.34; it is 0.40.8) and container count (16;
  it is 17).
- It also claimed, unchecked, that two output defects were "not new in Release 2". That claim
  was removed.
- Hash check: comparing lowercase digests with the loop's uppercase `Convert.ToHexString`
  output first made every file look changed.
- `.secrets.baseline`: the first regeneration re-sorted it (361 deletions). It was redone as
  additions only, with forward-slash filenames like the existing entries.
- A Thailand review was first refused with `multi_agent_disabled`. The backend had just been
  restored from `.env`, so the refusal was correct. The backend was recreated with the flag on
  before the real run.
- After the independent review:
  - the multi-terminal logs were renamed from `.log` to `.txt`, because `.gitignore` excludes
    `*.log`;
  - the report wrongly said the automatic checks raised the Japan verdicts; the model's own
    warning did. This was corrected;
  - the report missed that the Indonesia Reviewer did recommend Smartraveller. This was added;
  - claims with no saved file now have one: `cloud/10`, `endpoint-tests/11`, `local/09`;
  - the screenshot 05 description and the viewport wording were fixed;
  - an erratum was added for the `cloud/02` header;
  - "Who did what" sections were added;
  - the finalise commands were added to their transcript, with errata for notes that cannot be
    re-finalised;
  - the fully browser-driven Thailand run and the local CRUD check were added.

**Validation:**

| Check | Result |
| --- | --- |
| Native services | Ollama `200` (0.40.8, `llama3.2:3b` loaded), MCP `400` transport up, RAG `ok`, Multi-Agent `ok` |
| Student 5 containers | frontend, backend, database and gateway `healthy`; backend env shows all four flags `true` |
| Launcher exit code | `1`, from its own Student 2 probe (an exact-dict comparison fails once `multiAgentEnabled` is present); all services were up. Shared script, not changed |
| Advisory / MCP / RAG through `:5100/logistics/` | `200` in 3.4 s (`llama3.2:3b`) / `200` in 0.38 s (`ok: true`) / `200` in 2.7 s (2 citations, low confidence) |
| Local CRUD through the gateway | `201`, `200`, `200`, `200`, `204`, `404`; 12 destinations before and after |
| Multi-Agent runs | Vietnam (terminal) 14 s, Indonesia 17 s, Thailand (browser) 22 s to `awaiting_human_review` |
| `GET /audit/verify` (final) | `{"valid": true, "entries": 50, "broken_at": null}`; committed copy re-verified offline: same |
| `review-testing` | 2 failed attempts with `reviewer-llama32-v2.md` (example echoed, no record); record `20261022T102258Z-4f0d8097...` with the shared prompt, ACCEPT, finalised `rejected` |
| `review-cloud` | record `20261022T102407Z-ab4cb094...`, ACCEPT, finalised `changed` |
| `review-multi-agent` | 2 malformed attempts (no record); record `20261022T105130Z-7addf2c3...` with reduced context, ACCEPT, finalised `changed` |
| Evidence hashes | 3 reviewed reports edited after review (documented); all other reviewed files match |
| Full Student 5 suites | database 26, backend 199, MCP logistics 34, RAG student-5 retrieval 17 passed |
| Independent AI review | 6 important, 4 minor and 4 nit findings; all acted on. Terminals 1-2 running in the background stays a stated limit. See `review-record.md` (Release 2 - Chunk 6) |
| Pre-commit hooks on the changed files | Ruff security rules Skipped (no Python files); detect-secrets Passed; pip-audit Skipped (no requirements changed) |
| Local stack afterwards | `student5-backend` left with `MULTI_AGENT_ENABLED=true` (shell override) for further runs; `.env` unchanged |

### Chunk 7 - Release 2 documentation and report sections, 24 October 2026

**Why:** the brief's technical report needs:

- a Release 2 design flow;
- the cloud and CI/CD flow;
- each student's reports, review outputs and contribution log.

The Student 5 planning documents still described Release 0/1 only.

**Prompt (summary):** "Chunk 7 of my plan":

- Read everything under `student-5/docs/` and the brief's report requirements.
- Add a Release 2 section to `architecture.md` with Mermaid diagrams of:
  - the design flow, including Planner -> Worker -> Reviewer -> Human Review;
  - the local vs cloud boundary;
  - the DevOps flow.
- Update `feature-plan.md` (PR numbers from `git log`), `requirements.md`,
  `testing-evidence.md`, `known-issues.md`, `sprint-backlog.md`, `risk-plan.md` and
  `contribution-log.md`.
- Check that every path and number matches its source. List anything missing instead of
  inventing it.
- Draft `release-2-report-sections.md` at about 400-500 words, with a word count.
- Docs only.

**AI-assisted work (no application code changed):**

- `architecture.md`:
  - a Release 2 section with three Mermaid diagrams (design flow, local and cloud boundary,
    DevOps flow);
  - a table linking each pipeline stage to its evidence.
- `feature-plan.md`:
  - a Release 2 deliverables table (R2-1 to R2-7, with branches, work commits, PRs and
    evidence);
  - the plan's acceptance gates;
  - changes to Student 5 files by other team members;
  - the Release 2 decisions.
- `requirements.md`:
  - the TL-NFR-11 row (it was in the plan but missing here);
  - the Multi-Agent Server in the scope diagram;
  - a Release 2 evidence section.
- `testing-evidence.md`: a Release 2 index, the Release 2 `student-5.yml` steps, the
  reproduction commands and the outstanding items.
- `known-issues.md`, `sprint-backlog.md` (TL-26 to TL-32), `risk-plan.md` (TL-R11 to
  TL-R14) and `contribution-log.md` (a Release 2 record with PR links).
- New file `release-2-report-sections.md` (498 counted words).
- New evidence file `evidence/release-2/cloud/11-protected-ai-run-39893640923-excerpt.txt`,
  made with `gh run list` and `gh run view`. It records the protected-AI cloud run at
  `4c1e71a`, which came after the Chunk 6 evidence.

**Found while checking sources:**

- Cloud run 39893640923 (protected AI mode, 23 October) is now the live deployment. Student 5's
  CRUD and AI checks passed in it. Readiness review `wf-20261023T035316Z-6feb1b81` is waiting
  for a human decision.
- The shared runbook says baseline run 39741981906 deployed before the CI gate was corrected.
  No baseline run has succeeded since.
- Another team member changed Student 5 files:
  - PR #143 added an `enabled` parameter to `check_student5`, so the smoke tests went from
    18 to 19;
  - PR #147 added `CLOUD_AI_SLOW_MODE` to the backend, so the backend tests went from 199
    to 201.

**Corrections during the session:**

- The first draft said "three from the UI" when there were four UI workflows. It also said
  pip-audit ran on the 111 files, but it runs on the two requirements files.
- The draft said five dispatches failed after the baseline run. Nine did.
- The endpoint-test reproduction command did not match the workflow, because it ran from
  `student-5/backend`. It now runs from the repository root, as `student-5.yml` does, and
  was re-run: 13 passed.
- The loop folder holds 12 files, not 14. The CI-gate log range is lines 131-146.
- Corrections made after the independent review are listed in `review-record.md` (Release 2
  - Chunk 7).

**Validation:**

| Check | Result |
| --- | --- |
| Full Student 5 suites at `4c1e71a` (repo `.venv`, Python 3.13.2) | database `26 passed in 1.70s`, backend `201 passed in 6.26s`, MCP logistics `34 passed in 2.64s`, RAG student-5 retrieval `17 passed in 0.23s` |
| Endpoint tests with the documented command | `13 passed in 0.47s` |
| Cloud smoke test collection | `scripts/test/test_cloud_smoke_student5.py`: 19 tests collected |
| Referenced paths | 77 path references in the new text checked; all exist |
| Report word count | 498 (whitespace split, headings excluded) |
| Independent AI review | 1 important, 9 minor and 7 nit findings; all acted on. See `review-record.md` (Release 2 - Chunk 7) |
| Pre-commit hooks on the changed files | detect-secrets Passed; Ruff security rules and pip-audit Skipped (no Python or requirements files) |
| Mermaid diagrams | Checked by hand by the reviewer. No Mermaid CLI is installed, so they were not rendered |

### Final submission-readiness check, 24 October 2026

**Why:** verify, before the 25 October deadline, that nothing would cost marks under the
Release 2 brief's criteria 1-10 and bonus, and fix only small documentation problems.

**Prompt (summary):** "Final submission-readiness check for my Release 2 work. Verify, do
not build": repository state, all Student 5 test suites, CI, pre-commit hooks, a full local
deployment with every AI flag on and then off, read-only cloud checks, Multi-Agent and loop
evidence, and documentation consistency. Documentation fixes only, on
`AC/student5-r2-final-check`, uncommitted.

**Documentation changed:**

- Tool names replaced by "an AI coding assistant" in `contribution-log.md` (Release 1) and
  this log (Release 1); the two speaker labels in
  `evidence/prompt-engineering-and-context-management-documentation.txt` relabelled
  `ASSISTANT:`. No other text in the transcript changed.
- PR #151 (`07eb996`) recorded as merged in `contribution-log.md`, `feature-plan.md` and
  `sprint-backlog.md`; the Release 2 totals are now 24 work commits in 7 PRs (also in
  `release-2-report-sections.md`, now 499 words).
- `cloud-deployment-report.md`: dated note that run 39893640923 replaced `851bdd7` on the
  public URL.
- `release-2-plan.md`: acceptance-gate status pointer and resolved open items.

**Validation (main at `07eb996`):**

| Check | Result |
| --- | --- |
| Student 5 suites (repo `.venv`) | database `26 passed`, backend `201 passed` (endpoint CI file `13 passed`), MCP logistics `34 passed`, RAG student-5 `17 passed`, cloud smoke student-5 `19 passed` |
| Shared suites | agentic loop `dotnet test`: `95 passed`; Multi-Agent Server (`venv-rag`, which has its requirements): `71 passed` twice, after one teardown `PermissionError [WinError 5]` on Windows in the first run |
| CI | `student-5.yml` run 40067116729 at `07eb996` green, POST and PUT tested, artifact `student-5-endpoint-test-results`; all five student workflows and Integrated Compose CI green at `4c1e71a`; `cloud-deployment.yml` 39893640923 success, `PASS: Student 5 cloud profile and CRUD checks.` |
| Pre-commit | Ruff security rules, detect-secrets and pip-audit Passed over the 184 tracked Student 5 files; no Student 5 entry in `pip-audit-accepted.json` |
| Local stack, all four AI flags on | 16 containers healthy, Ollama, MCP, RAG and Multi-Agent health OK; CRUD on destinations, weather notes and transit options; advisory 3.2 s; MCP visa tool; cited RAG answer; readiness review `wf-20261024T055638Z-811f76bd` reached `awaiting_human_review` in 12 s (no decision made); `GET /audit/verify` `valid: true`, 137 entries |
| Local stack, all four AI flags off | each AI route `503` with its `*_disabled` body in 6-19 ms; CRUD unaffected; flags restored afterwards |
| Cloud, read-only | every path `401` with Basic authentication (protected AI mode); authenticated checks not run (no credentials held locally) |
| Referenced paths | every path in `student-5/docs` resolves, apart from files that exist only inside CI artifacts |
