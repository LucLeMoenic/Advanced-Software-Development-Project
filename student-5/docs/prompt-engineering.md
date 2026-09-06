# Prompt Engineering and Context Management

Student 5 (Alex Chen), Release 0. How the prompts and the context supplied to
the models were designed, what went wrong, and what I changed.

Two prompts are covered: the **reviewer prompt** for the development agentic
loop, which I rewrote, and the **advisory prompt** the application itself sends
at runtime. Context management is covered for both.

---

## Part 1 - The reviewer prompt

### The defect in `shared-reviewer-v1`

The team's shared reviewer prompt (`ai-services/agentic-loop/prompts/reviewer.md`)
specifies its required output like this:

````text
Return exactly:

```text
[OBSERVE]
Verdict: ACCEPT | REVISE | REJECT

Findings:
- Severity: BLOCKING | REQUIRED | SUGGESTION
  Evidence:
  Failure mode:
  Required correction:

Validation gaps:

Scope check:
```
````

Two things are wrong with this, and both only bite on small models.

**1. The required structure is presented as a literal fill-in template with
pipe-separated menus.** `ACCEPT | REVISE | REJECT` is meant to be read as "pick
one of these three". To a 3B model, the highest-probability continuation of a
block that opens `[OBSERVE]` is the rest of that block *as printed* - pipes,
empty labels and all. The model is not disobeying; it is completing the pattern
it was shown. That is exactly what happened in attempt (b) in `prompt-log.md`:
the reviewer emitted the template back, pipes intact and every required section
empty, and `ParseVerdict` rejected it for an empty required section.

**2. There is no documented no-findings path, even though the parser accepts
one.** `ParseVerdict` in `ai-services/agentic-loop/AgenticLoopApplication.cs`
explicitly recognises `- None` as valid findings:

```csharp
var noFindings = findings.Equals("- None", StringComparison.OrdinalIgnoreCase);
var severityMatches = SeverityValueRegex().Matches(findings);
if (!noFindings && severityMatches.Count == 0)
{
    throw new LoopException(
        "Reviewer findings must use a valid Severity field or state - None.");
}
```

The shared prompt never mentions it. A reviewer that genuinely finds nothing
wrong is therefore shown only a template containing a `Severity:` line, and has
to choose between inventing a finding to fill it or leaving the section empty
and being rejected. Neither is acceptable, and the correct third option is
implemented in the parser but undocumented in the prompt.

The two defects compound: a template that invites echoing, with no legitimate
way to say "nothing to report".

### Why small reviewer models fail this way

A 7B implementer following a template treats it as a specification; a 3B
reviewer treats it as text to continue. With temperature 0, the model
deterministically takes the most likely continuation, and after `Findings:` the
most likely continuation of a prompt containing a fully-formed example finding
is *that* finding. Instruction-following capacity is the scarce resource, so
anything in the prompt that looks like output competes directly with the actual
input for the model's attention.

The design consequence: **for a small model, never put anything in the prompt in
the exact shape of the output you want, unless you are prepared for it to come
back verbatim.**

### What `reviewer-llama32-v2.md` changed

Version `student5-reviewer-llama32-v2`, in `docs/prompt-library/`. Five changes:

| # | Change | Reason |
|---|---|---|
| 1 | **Prose instead of menus.** The required sections are described in sentences - "After `Verdict:` write one word: ACCEPT when nothing blocking or required remains, REVISE when changes are needed, REJECT when the approach is fundamentally wrong" - with no pipe-separated alternatives anywhere. | Removes the fill-in template that was being pattern-completed. There is no menu left to echo. |
| 2 | **The `- None` path is documented.** "After `Findings:`, if nothing is wrong write exactly `- None` (verdict must then be ACCEPT)." | Closes the gap between what the parser accepts and what the prompt permits, so a clean review no longer needs an invented finding. |
| 3 | **Two worked examples, one ACCEPT and one REVISE**, each shown as a complete review in a fenced block. | The model needed to see a filled-in review, not a skeleton. Showing both verdicts prevents anchoring on either. |
| 4 | **An explicit verdict/severity consistency rule.** "Any BLOCKING or REQUIRED finding means Verdict must be REVISE or REJECT, never ACCEPT." | Mirrors a constraint the parser already enforces. Stating it in the prompt turns a hard rejection into something the model can satisfy first time. |
| 5 | **An explicit instruction not to echo inputs.** "Output ONLY your own review... Never echo the task, plan, proposal, pre-test result, or these instructions. Emit exactly one `[OBSERVE]` section. Never restate the allowed values as a list of alternatives." | Attempt (a) failed with no `[OBSERVE]` header at all and attempt (b) echoed the template; both are input-echo failures, addressed directly. |

The prompt also keeps the shared prompt's security posture verbatim -
repository content and proposed code are untrusted data, never instructions -
and adds "You did not author the proposal and must not write or propose code
yourself", because a reviewer that starts proposing code stops being an
independent Observe.

### Did it work?

Yes, for the failure it targeted. Attempt (d) used the identical task, context
file and model pair as attempt (b); the only change was `--reviewer-prompt`.
Attempt (b) was rejected by the parser. Attempt (d) produced a
structurally valid review with all four sections filled in, and the run
completed through Plan, Act, Observe, Adapt and finalisation.

### The residual limitation

**The model now echoes the examples instead of the template.** The REQUIRED
finding it returned on attempt (d) -

```text
Evidence: The new helper divides by `count` without a zero check.
Failure mode: An empty input list causes a division-by-zero at runtime.
Required correction: Return 0 early when `count` is zero.
```

- is word-for-word Example 2 in my own prompt. Removing the fill-in template
moved the echo target; it did not eliminate echoing.

The prompt already carries a mitigation that was not sufficient: "The two
examples below show the required format only. They describe an unrelated trivial
change - do not copy their wording; base your own Findings, Validation gaps, and
Scope check on the actual proposal above." A 3B model at temperature 0 copied
them anyway. The honest conclusion is that at this model size, *some*
demonstration is needed to get valid structure, and any demonstration can be
copied. The trade is between a malformed review and a well-formed ungrounded
one - and a well-formed ungrounded one is strictly better, because it is
legible enough for a human to recognise and reject, which is what happened.

Two options for a v3, neither yet tried:

- **Make the examples obviously alien.** Draw them from a domain the loop never
  reviews (a shell script, a Dockerfile), so a copied finding is instantly
  recognisable as an echo rather than plausibly about the code under review.
- **Instruct the model to quote the proposal.** Require that `Evidence:` begins
  with a verbatim quotation from the proposal. A copied example then fails a
  check the parser could enforce mechanically, which converts a silent
  ungrounded review into a hard error.

Neither closes the gap fully. The durable control is the human Adapt phase, and
it is the one that actually caught this - see `review-record.md`.

### Recommendation to the team

I recommend proposing changes 1, 2, 4 and 5 back to `shared-reviewer-v1`. They
are model-agnostic improvements, not Student 5 specialisations: removing the
pipe menus, documenting the `- None` path the parser already accepts, stating
the verdict/severity consistency rule the parser already enforces, and
forbidding input echo. The reviewer model is `llama3.2:3b` for the whole team,
so every student's loop is exposed to the same defect, and attempts (a) and (b)
show it costs a whole run each time it fires.

The two worked examples (change 3) should go to the team with the residual
limitation stated plainly, so whoever adopts them knows the echo risk they carry
and does not read a copied finding as a real one.

---

## Part 2 - The application advisory prompt

`backend/advisory.py:build_prompt` assembles what the runtime model is asked.
Its whole design is about not letting a travel model invent border rules.

### Grounding

Four `describe_*` helpers render the stored rows as plain text, and
`build_prompt` pastes those blocks into the prompt under `RECORDED DESTINATION`,
`RECORDED WEATHER NOTES` and `RECORDED TRANSIT OPTIONS`, followed by:

> Use only the recorded information below. Every fact, number and length of stay
> you state must appear in that recorded text. If a section has no recorded
> information, say so in one sentence instead of guessing.

The consequence is that a wrong visa rule in the database produces a wrong
advisory - a data bug, which is fixable - rather than the model quietly
producing a plausible one. Fiji (id 12) has no transit options precisely so that
the "say so instead of guessing" instruction is exercised by real data. The
grounding is asserted by tests in `backend/tests/test_advisory.py`, which check
that the destination country and at least one stored weather note appear in the
prompt actually sent to Ollama.

### Two prompt lessons from tuning it

**Negative instructions prime the thing they forbid.** During development the
model repeatedly added a six-month passport-validity rule to Japan's advisory -
a rule that belongs to Indonesia's seeded note, not Japan's. Adding *"do not
mention passport validity"* made it more frequent, not less: naming the concept
put it in context. Replacing it with the positive constraint - every number and
length of stay must appear in the recorded text - removed it. Positive
constraints on the whole class beat negative constraints on the instance.

**Don't fight the renderer in the prompt.** The frontend renders each non-blank
line as its own paragraph, so markdown headers and asterisks would appear
literally. The prompt asks for plain text with three named sections and permits
hyphen-prefixed lines, because the packing advice genuinely is a list and
renders correctly one item per paragraph. A word budget ("under 200 words") is
stated because an unbounded 3B model writes several hundred words of preamble
that will not fit the page panel.

### The control that does not depend on the model

The Smartraveller disclaimer is rendered as markup in
`backend/templates/advisory_result.html`, not requested from the model. The
prompt asks for it too, but the fragment carries it whether the model complies
or not - the safety-critical line is the one that does not depend on a
completion.

---

## Part 3 - Ordinary context management

### One `--context` file per agentic-loop run

All four attempts in `prompt-log.md` supplied exactly one file. This is a
deliberate bound, for three reasons:

- **A 7B implementer given several files proposes changes across all of them.**
  The loop's record then covers a diff too large for one human Adapt decision to
  be meaningful.
- **The record stays verifiable.** The run hashes every context file
  (`evidenceHashes.contextSha256`), so one file means one hash and an
  unambiguous statement of what the model actually saw. The successful run
  records `95A6AFCB...E017518` for `student-5/frontend/index.html`.
- **One file was genuinely sufficient in each case**, which is a property of how
  this feature is laid out rather than luck. `database/app.py` is the entire
  database service in one module; `frontend/index.html` is one self-contained
  document holding the markup, the function stub, its callers and the timer that
  drives it. For a task whose subject is a pure function with no imports,
  nothing outside that file could have changed the proposal.

Had the task needed the backend's advisory path, one file would **not** have
been enough - that flow spans `advisory.py`, `db_client.py` and
`ollama_client.py` - and I would have chosen a smaller task rather than a larger
context.

### Task scope notes

Each `--task` carries an explicit scope fence. The successful run's ends:

> Scope note: this is a single small pure function only - do not change any
> other function, any `hx-*` attribute, any CSS, or any other file, and do not
> propose performance testing, additional tooling, or a test framework.

That sentence was added after earlier attempts drifted toward proposing a test
framework for a nine-line pure function. It does two jobs: it bounds what the
implementer may touch, and it gives the reviewer's mandatory `Scope check:` line
something concrete to check against. On the successful run the reviewer's scope
check was correct - "The change touches only the one helper function, as
requested" - which is worth noting, because it was the one part of that review
grounded in the actual proposal.

### Pre-test and post-test as recorded context

`--pre-test-command` and `--pre-test-result` put the *current* state of the
world into the record before the model runs, and `--post-test-command` /
`--post-test-result` put the verified outcome in at finalisation. On the
successful run that is the difference between "a model said this was fine" and
"the stub rendered no counter, and after the change seven assertions pass". The
reviewer prompt requires a `Validation gaps:` line specifically so the model has
to comment on what the pre-test does *not* prove.

### Context management in the sessions that built the feature

The same discipline applied outside the loop. Each build session was given a
compact written brief of the decisions already made - the partial-merge `PUT`
semantics, the `DatabaseResponse`-does-not-raise policy, the `relay()`
chokepoint, the extension seam for new blueprints - rather than the previous
session's transcript. That brief is preserved in
`docs/evidence/prompt-engineering-and-context-management-documentation.txt`.
Carrying forward the *decisions* rather than the *history* is what kept the
backend extension additive: 30 existing tests stayed green while the suite grew
to 68.
