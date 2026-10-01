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
