# Review Record - Agentic Loop Run, 6 September 2026

Student 5 (Alex Chen), Release 0, with the Release 1 validation runs and code review at the end. The completed Plan/Act/Observe/Adapt cycle.

## Run identity

| Field | Value |
|---|---|
| Record file | `20260906T053024Z-ad4b32c67df446e8af9e1fca8cc22044.json` |
| Saved copy | `docs/evidence/agentic-loop-run-final-record.json` |
| Created / finalised | 2026-09-06T05:30:24Z / 2026-09-06T05:41:30Z |
| Task | Implement `formatElapsed(seconds)` in `student-5/frontend/index.html` at the `TODO(you)` marker, plus a commented-out `node -e` assertion snippet |
| Context file | `student-5/frontend/index.html` (SHA-256 `95A6AFCB...E017518`) |
| Implementer model | `qwen2.5-coder:7b`, prompt `shared-implementer-v1` |
| Reviewer model | `llama3.2:3b`, prompt `student5-reviewer-llama32-v2` |
| Generation options | temperature 0, context 16384, max output 4096 |
| Reviewer verdict | **REVISE** (both the first corrected review and the review of the adapted proposal) |
| Human decision | **changed** |
| Resulting commit | `6dd3fd2`, PR #50 |

## Phase mapping

| Loop phase | What performed it | Artefact |
|---|---|---|
| **Plan** | Implementer model - restated the requirements, named the single file, listed two steps, risks and a validation method | `[PLAN]` section of `planAct` in the record; `agentic-loop-run-part1.png` |
| **Act** | Implementer model - proposed the `formatElapsed` implementation and the commented assertion snippet | `[ACT]` section of `planAct`; `agentic-loop-run-part1.png` |
| **Observe** | Reviewer model's critique **plus my own test runs** - the recorded pre-test before the run, and the seven `node -e` assertions after it | `observe` and `adaptedProposalReview` in the record; `preTest` / `postTest`; `agentic-loop-run-part1.png`, `-part2.png`, `formatelapsed-assertions.txt` |
| **Adapt** | The bounded revision requested from the implementer, then **my applied change and finalise decision** - accepting the proposal, rejecting the reviewer's REQUIRED finding, and recording why | `adaptedProposal`, `humanDecision`, `humanNotes` in the record; `agentic-loop-finalise.png` |

Observe is deliberately two things. The reviewer model contributes a critique;
the evidence that the code actually works comes from tests I ran and recorded on
the run itself. Neither alone is enough - this run is exactly the case where the
model's half of Observe was wrong and the test half was right.

## Pre-test

```text
command: Select-String -Path student-5/frontend/index.html -Pattern 'TODO\(you\)'
result:  formatElapsed stub present at the TODO(you) marker, returns empty
         string - no elapsed counter renders during generation
```

The stub existed and returned an empty string unconditionally, so no counter
ever appeared while an advisory generated.

## Post-test

```text
command: node -e (formatElapsed assertions, 7 cases)
result:  all 7 assertions passed
```

Captured in `docs/evidence/formatelapsed-assertions.txt`.

## The reviewer's finding, and why I rejected it

The reviewer returned, both before and after the Adapt revision:

```text
[OBSERVE]
Verdict: REVISE

Findings:
- Severity: REQUIRED
  Evidence: The new helper divides by `count` without a zero check.
  Failure mode: An empty input list causes a division-by-zero at runtime.
  Required correction: Return 0 early when `count` is zero.
```

**This finding corresponds to nothing in the proposed function.** The proposal
is nine lines of comparison and template-literal return:

```javascript
function formatElapsed(seconds) {
  if (seconds < 2) {
    return "";
  } else if (seconds < 45) {
    return `${seconds}s`;
  } else {
    return `still working - ${seconds}s`;
  }
}
```

There is no division operator, no list, and no variable named `count`. I
verified this by inspection before deciding.

The finding is instead a **verbatim reproduction of Example 2 in my own reviewer
prompt**, `docs/prompt-library/reviewer-llama32-v2.md` - the same four lines,
word for word. The 3B reviewer pattern-completed the worked example in its
instructions rather than grounding its review in the proposal above it. This is
the same class of failure as attempt (b) in `prompt-log.md`, where the reviewer
echoed the shared prompt's fill-in template; v2 removed the template but left
two examples, and the model found those instead.

There is a second, smaller symptom worth recording. The reviewer's *first*
response paired that `REQUIRED` finding with `Verdict: ACCEPT` - a combination
`ParseVerdict` in `ai-services/agentic-loop/AgenticLoopApplication.cs` refuses.
The loop printed `Reviewer output was malformed; requesting one format
correction` and asked once more; the corrected response returned `REVISE` with
the same finding. So the model was not even internally consistent about the
severity it had copied.

Acting on the finding would have meant adding a zero-check for a variable that
does not exist, to guard a division that is never performed. I rejected it and
recorded the reasoning in `humanNotes` on the record.

## Why this is the control working, not a failure

The unit's loop is not "the reviewer model decides". It is Plan/Act/Observe/
Adapt with a human owning Adapt, and this run is precisely why that ordering
matters. Three independent controls stood between a fabricated finding and the
codebase, and all three did their job:

1. **Machine-side format validation.** `ParseVerdict` refused the reviewer's
   first response because a `REQUIRED` finding cannot coexist with an `ACCEPT`
   verdict, and forced one correction rather than recording an incoherent
   verdict.
2. **The loop refuses to self-apply.** After the Adapt revision the run stopped
   with `Agentic-loop record awaiting human finalisation`. Nothing was written
   to the repository by the loop. A REVISE verdict cannot merge itself.
3. **The human Adapt decision.** I read the finding against the actual proposal,
   found it described code that does not exist, rejected it, applied the
   implementer's proposal on its merits, and proved the result with seven
   assertions - which is stronger evidence than either model produced.

The recorded outcome is therefore an *honest* one: a REVISE verdict, a human
decision of `changed`, and a note explaining that the change made was the
implementer's proposal and not the reviewer's correction. A run where I had
silently obeyed a fabricated REQUIRED finding would have looked tidier in the
record and would have been worse engineering.

## Human notes as recorded on the run

> Applied the implementer's formatElapsed proposal, choosing the 45-second
> boundary as inclusive of the reassurance form. REJECTED the reviewer's
> REQUIRED finding: it describes a division-by-zero on a 'count' variable with
> an empty input list, none of which exist in the proposed function - the 3B
> reviewer reproduced the worked example from the reviewer prompt instead of
> grounding its review in the actual proposal. Verified by inspection that the
> proposed code contains no division, no list and no count variable. Human
> judgement overrode the model verdict; the change is correct and covered by
> seven node assertions.

## One judgement call I made that neither model raised

The task specified `still working - Ns` "past 45 seconds", which is ambiguous at
exactly 45. I resolved the boundary as `seconds < 45` for the compact form, so
45 itself takes the reassurance form, and asserted that boundary explicitly in
the post-test. Recorded here because it is a decision, not an implementation
detail - and because neither the implementer nor the reviewer flagged the
ambiguity.

## Follow-up

The residual defect in `reviewer-llama32-v2.md` - the model now echoes the
worked examples rather than the template - is analysed in
`prompt-engineering.md`, along with the recommendation to take the fix back to
the team's shared prompt.

## Release 1 - validation runs (e) and (f)

Both records are in `docs/agentic-loop-records/`; terminal output is in
`evidence/release-1/loop/`. Models and reviewer prompt as for (d). In both, the
pre-test was a **live** call to the Student 5 backend with the loop's own
contract check passing, and the implementer proposed no change.

### (e) `validate-mcp` - `20261001T114821Z-cafe2142e4624e52807d4b54c983d954.json`

| Phase | What happened |
|---|---|
| Pre-test | `POST http://127.0.0.1:5205/api/mcp/invoke` with the fixed visa call for destination 1: `200`, `contractPassed: true` (tool name, `ok`, id 1, country, visa category, Smartraveller reminder). |
| Plan / Act | Restated the four properties in the task and concluded no change to `logistics.py` was needed. |
| Observe (1st) | **Malformed.** The reviewer returned a REQUIRED finding, "The new helper divides by `count` without a zero check", under `Verdict: ACCEPT`. That is the worked example from `reviewer-llama32-v2.md` again: there is no new helper and no division. `ParseVerdict` rejected the REQUIRED-under-ACCEPT combination and asked for one correction. |
| Observe (2nd) | `ACCEPT` with one SUGGESTION: "add a plain text version of the official-source reminder". The reminder is already a plain-text string field (`official_source_reminder`), so the suggestion has no basis. The validation gap it names - "does not prove that the result is bounded to the requested destination" - is also wrong: the pre-test contract checks `id == 1`. |
| Adapt | None generated (verdict ACCEPT). |

**My assessment:** the tool result is correct and the implementer was right
that no change is needed. Both reviewer findings are unsupported. This is
TL-R10 occurring, and the controls worked the same way as in (d).

### (f) `validate-rag` - `20261001T114858Z-e3385d8dc6f1499db6c99f34beee5180.json`

| Phase | What happened |
|---|---|
| Pre-test | `POST http://127.0.0.1:5205/api/rag/ask` with "What is the difference between visa on arrival and an eVisa?": `200`, `contractPassed: true`; the answer cites `visa-categories#2` and `#3` inline. |
| Plan / Act | Checked each sentence against the cited snippets; proposed no change to `visa-categories.md`. |
| Observe | `ACCEPT` with one SUGGESTION: add more about visa-on-arrival requirements. |
| Adapt | None generated. |

**My assessment:** both sentences in the answer are supported by the cited
chunks. The suggestion is about the answer's length, not its grounding, and the
requirement details it asks for are already in chunk `visa-categories#2` - so
the knowledge base needs no change. Low confidence on a correct answer is
recorded in `known-issues.md`.

### Finalising

The `humanDecision` field is mine to set, so the assistant left both records
pending. After reviewing the runs above I finalised them myself: (e) `kept`, (f) `kept`.
My notes and the post-test are stored in each record. The command has this
form:

```powershell
dotnet run --project ai-services/agentic-loop -- finalise `
  --record docs/agentic-loop-records/20261001T114821Z-cafe2142e4624e52807d4b54c983d954.json `
  --decision kept `
  --notes "Reviewer's first output echoed the prompt's worked example; final SUGGESTION unsupported - the reminder is already plain text and the contract checks id 1. No change to logistics.py." `
  --post-test-command "pwsh -NoProfile -File scripts/test/student-5.ps1" `
  --post-test-result "26 + 125 + 34 + 17 passed"
```

## Release 1 - review of the AI-written code

Before committing, the working-tree diff (code only, not docs) was given to an
independent AI code-review agent. It was asked to look for logic errors,
contract mismatches with the shared MCP/RAG servers (compared with Student 3's
clients), template XSS, SSRF or allow-list bypass, anyio misuse, CI script
mistakes, and regressions for Students 1-4 in the shared agentic-loop files.

| Finding | Severity | Outcome |
|---|---|---|
| `logistics.get_transit` applied the `type` filter **after** the 20-row cap, so with more than 20 transit rows for a destination, a matching row with a higher id was dropped and the tool wrongly reported "no matching options". Not reachable with the seed data (at most 2 rows per destination), but reachable after admin creates. | Medium | **Accepted and fixed.** `_children` now returns the full sorted list; `get_transit` filters, then caps, and `get_weather` caps. Regression test `test_transit_filter_runs_before_cap` (20 bus rows, then a ferry at id 21). MCP suite 122 -> 123 passed (135 on the current `main`, which has more Student 2 tools); live call re-checked after restarting the server. |

The reviewer reported nothing else: the clients match the shared servers'
contracts, Jinja autoescape is on with no `|safe`, `destination_id` is a
validated int and tool names go through a fixed allow-list, the smoke-test bash
parses correctly, and the shared agentic-loop changes only add `student-5`
branches without changing behaviour for Students 1-4.

Also checked during the session: the four 503 bodies in the CI smoke test
against the running backend (`ci-smoke-local.txt`), and the 375px layout for
horizontal overflow (0px, `assist-mobile-375.png`).
