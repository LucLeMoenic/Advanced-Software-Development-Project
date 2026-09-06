# Review Record - Agentic Loop Run, 6 September 2026

Student 5 (Alex Chen), Release 0. The completed Plan/Act/Observe/Adapt cycle.

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
