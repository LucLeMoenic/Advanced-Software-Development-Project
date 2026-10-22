# Release 2 agentic-loop report reviews (Student 5)

The shared loop's three Release 2 review modes were run on Student 5's real evidence on 22
October 2026. Settings: `IMPLEMENTER_MODEL=qwen2.5-coder:7b`, `REVIEWER_MODEL=llama3.2:3b`,
native Ollama 0.40.8, `temperature: 0`. Alex Chen chose each `finalise` decision. An AI coding
assistant ran the loop and the `finalise` commands at Alex's direction, with notes Alex had
approved. `finalise` has no "decided by" field, so each note starts with "Decided by Alex Chen".

| Mode | Record (`docs/agentic-loop-records/`) | Reviewed | Reviewer verdict | Human decision |
|---|---|---|---|---|
| `review-testing` | `20261022T102258Z-4f0d8097f2ce49c7b53f587589c6b9cc.json` | `precommit-security-report.md`, `precommit/04-blocked-commit.txt`, `endpoint-testing-report.md`, `endpoint-tests/07-ci-run-39698558980-excerpt.txt` | ACCEPT, 1 suggestion | **rejected**: the finding (a pytest floor of 8.0) misread the report's "before" row |
| `review-cloud` | `20261022T102407Z-ab4cb094c4db4950a1e18263432f55d2.json` | `cloud-deployment-report.md`, `cloud/02`-`04` | ACCEPT, 1 suggestion | **changed**: screenshots added; the persistence/rollback and revision gaps (already in the report) recorded as not raised by the loop |
| `review-multi-agent` | `20261022T105130Z-7addf2c373e943898b24ab42ee3dbff4.json` | `multi-agent-server-report.md`, `multi-agent-server/transcripts/T-run.txt`, `T-decide-audit-verify.txt` | ACCEPT, 1 suggestion | **changed**: finding true but out of scope; report corrected afterwards (see errata) |

Files here: one `*-run-terminal.txt` per mode (the run that wrote the record), the failed
attempts, `finalise-terminal.txt`, and copies of the three finalised records
(`*-review-record.json`). The full human notes are in each record's `humanNotes` and in
`finalise-terminal.txt`, which also lists errata. `student-5/docs/review-record.md`
(Release 2, Chunk 6) summarises the outcome.

## Failed attempts, kept as evidence

| Attempt | What happened | Record |
|---|---|---|
| `testing-review-attempt1/2-reviewer-echoed-example-terminal.txt` | With the Student 5 reviewer prompt `student-5/docs/prompt-library/reviewer-llama32-v2.md`, `llama3.2:3b` copied that prompt's Example 2 finding word for word ("The new helper divides by `count` without a zero check") under `Verdict: ACCEPT`. The loop rejected it: "Reviewer output cannot ACCEPT blocking or required findings." Attempt 2 was identical, as expected at temperature 0. | none |
| `multi-agent-review-attempt1-malformed-findings-terminal.txt` | With the shared `reviewer.md`, the reviewer copied the report's own "Limits" bullets as findings with no valid `Severity` field. Refused. | none |
| `multi-agent-review-attempt2-repetition-loop-terminal.txt` | Same inputs. The reviewer repeated one bullet dozens of times (swapping the two Chunk 2 workflow ids) until its output was cut off mid-sentence. After one format retry it was refused: "Reviewer findings must use a valid Severity field or state - None." | none |

The three records therefore use the shared reviewer prompt
`ai-services/agentic-loop/prompts/reviewer.md`, not the Student 5 prompt. The v2 prompt's
examples are about code diffs. In report mode, the proposal comes after the prompt, and the
proposal is often just "No changes required". So the 3B model has nothing concrete to review,
and it copies an example. A report-mode version of that prompt is a separate, later decision.
The multi-agent record came from a smaller context (the report and two terminal transcripts,
without the 40-line audit listing and the HTML fragment). That was a bounded change to get
well-formed output, not to change the verdict.

## Evidence hashes

Each record stores the SHA-256 of every file it read (`evidenceHashes.contextSha256`). Three
reviewed files were edited after review, so their current hashes differ from the recorded ones:

- `cloud-deployment-report.md`: the screenshots were added. This was the human Adapt step for
  the cloud finding. Errata were also added after the independent review.
- `endpoint-testing-report.md`: the CI screenshots and the run citations were added. This is
  unrelated to the testing finding, as that record's notes say.
- `multi-agent-server-report.md`: the finding attributions were corrected after the
  independent review, and the Thailand run and "Who did what" were added (after finalisation).

All other reviewed files still match their recorded hashes. Do not edit them.

## Errata to the finalise notes

Records cannot be re-finalised, so corrections are listed at the end of
`finalise-terminal.txt`. In short, the cloud and multi-agent notes say gaps were "added by the
human". In fact those gaps were already stated in the reports the loop read; the loop did not
raise them.
