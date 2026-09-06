# Agentic Loop Prompt Log

Student 5 (Alex Chen), Release 0. Every attempt I made at a Plan/Act/Observe/
Adapt run through the shared development loop, in order, including the three
that failed.

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
