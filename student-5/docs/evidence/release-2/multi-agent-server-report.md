# Student 5 - Multi-Agent Workflow Evidence (Release 2)

Feature: Travel Logistics & Advisory, trip readiness review (TL-FR-16, TL-FR-17, TL-NFR-10) ·
Server: shared `ai-services/multi-agent-server/` (native, `127.0.0.1:5600`, not a Compose
service) · Model: `llama3.2:3b` for all three agents · Plan: Chunks 2 and 6 in
[`release-2-plan.md`](../../release-2-plan.md) · Run: 22 October 2026, see the
[local deployment report](local-deployment-report.md).

## Flow

```
Browser /logistics/ --HTMX--> student5-frontend (nginx) --> student5-backend /ui/readiness-reviews
   readiness.py: load_context(destination) -> build_evidence() -> POST /workflows (202)
Multi-Agent Server: Planner -> Worker -> automatic checks -> Reviewer -> awaiting_human_review
   backend polls GET /workflows/<id> every 2 s (204 while unchanged); shows plan, checklist, findings
Human: approve | correct | partial | reject  -> POST /workflows/<id>/decision -> audit log
Terminal: cli.py run --evidence-file <same evidence>  ...  cli.py decide <id> --decided-by ...
```

The server never reads application data. The Student 5 backend builds the evidence: one item
for the entry requirement (`destination-<id>`), one per weather note and per transit option (up
to 6 each), with texts clipped to 400 characters. Titles are made distinct because the server's
subject check is a substring match. The first evidence id binds a workflow to its destination,
and every poll and decision checks it. Decisions are stored on the server, in the workflow
record's `human_decision` and in the hash-chained audit log. No Student 5 database row
changes.

## Agent roles and what each one sees

| Stage | Prompt | Input | Output |
|---|---|---|---|
| Planner | `ai-services/agentic-loop/prompts/multi-agent-planner-v1.txt` | Task + evidence | Objective, steps, required evidence ids, success criteria |
| Worker | `multi-agent-worker-v2.txt` | Task + evidence + plan | Checklist items; each `subject` must be an exact evidence title and each item cites evidence ids |
| Automatic checks | `checks.py` (deterministic) | Worker items + evidence | Blocking finding if a subject does not match its cited evidence; warnings for repeated subjects or unused evidence |
| Reviewer | `multi-agent-reviewer-v1.txt` | Plan + items + evidence + automatic findings | Verdict, findings, recommendations; any blocking finding forces `fail` |
| Human | Student 5 UI form or `cli.py` | Everything above | `approve`, `correct` (edited items, re-checked), `partial` (kept item ids) or `reject` (notes required) |

## Workflows

All five are genuine model runs against the live Student 5 database. None is a fixture, and no
review was `degraded`.

| Workflow | Entry point | Destination, evidence | Agents (planner / worker / reviewer) | Verdict (model said) | Human decision |
|---|---|---|---|---|---|
| `wf-20261022T110825Z-db0bcb00` | **UI, fully in the browser**, Chunk 6 | Thailand, 3 | 12.8 s / 5.4 s / 3.1 s | `concerns` (concerns); 2 automatic warnings (repeated subject, `i4`, `i5`) | **`partial`** by Alex Chen, kept `i1`-`i4` |
| `wf-20261022T100857Z-16996759` | UI (started over HTTP, decided in the browser), Chunk 6 | Indonesia, 5 | 5.6 s / 5.8 s / 5.3 s | `pass` (pass); 5 `info` findings | **`correct`** by Alex Chen |
| `wf-20261022T100101Z-f83e9cc6` | **Terminal**, Chunk 6 | Vietnam, 3 | 5.9 s / 5.0 s / 3.0 s | `concerns` (pass); 2 automatic warnings (repeated subject, `i4`, `i5`) | **`partial`** by Alex Chen, `cli.py decide`, kept `i1,i3,i4` |
| `wf-20261021T233233Z-96e03a60` | UI, Chunk 2 | Japan, 5 | 15.2 s / 5.1 s / 6.0 s | `concerns` (pass); the model's own warning on `i2`, no automatic findings | `partial`, kept `i1,i3,i4,i5` |
| `wf-20261021T230750Z-6cded4a6` | UI, Chunk 2 | Japan, 5 | 14.5 s / 5.2 s / 7.5 s | `concerns` (pass); the model's own warning on `i2`, no automatic findings | `approve` from the terminal |

Between them, the human decisions cover `approve`, `correct` and `partial`. `reject` (notes
required) was not used on a real review. Its rules are covered by the server's own test suite.

### Who did what

Alex Chen chose every Chunk 6 decision: the three Multi-Agent decisions and the three
agentic-loop `finalise` decisions. Each was approved before anything was recorded. An AI coding
assistant ran the services and the terminal commands. It drafted the recommendations, the
correction text and the decision notes for Alex's approval, and it entered the approved
decisions: through `cli.py decide`, in Chrome (form filling and clicking), and with `finalise`.
`decided_by: Alex Chen` therefore names the person who made each decision, not who typed it.
The Chunk 2 decisions were recorded by Alex directly.

### UI review, fully in the browser (Thailand): partial acceptance

Started with **Start readiness review** on `http://localhost:5100/logistics/` and polled by the
page's own HTMX: `Queued` (`screenshots/04`), `Planner is drafting the plan...` (`05`), then
the review with its decision form (`06`). The Worker gave five items for three records. `i5`
("Records supplied: 1 of 1 weather notes, 1 of 1 transit options.") is the evidence's own
bookkeeping line, not a traveller action. It is filed under the entry-requirement subject while
citing all three records. The automatic checks flagged only the repeated subject on `i4` and
`i5`. `i1`-`i4` were kept and `i5` dropped. `i4` was kept because it adds the visa-free
requirement that `i1` leaves out (`07` form, `08` outcome: "Partially accepted by Alex Chen").

### UI review (Indonesia): correction

The Worker gave one item per record, each citing the right evidence, so the automatic checks
found nothing and the Reviewer said `pass`. The human review found what the verdict did not
reflect:

- every item copied its record word for word instead of stating an action;
- no item told the traveller to confirm entry rules with Smartraveller, which the task asked
  for. The Reviewer did recommend "Check Smartraveller for the most up-to-date visa requirement
  information", but only as a recommendation, while still passing the checklist;
- the Reviewer's five `info` findings only restated the items, and its "buy travel insurance"
  recommendation is not supported by any record.

All five items were corrected. For example, i1 became "Check your passport has at least six
months' validity. Visa on arrival is issued at major airports including Bali (DPS); confirm the
current rules with Smartraveller before booking." The server re-ran its automatic checks on the
correction: `correction_findings: []`. The page then showed "Corrected by Alex Chen" with the
accepted checklist (`screenshots/03`).

This review was started and polled over HTTP from Git Bash, using the page's own requests
(`U-start.txt`, `U-poll.txt`). The page has no control to reopen an existing review, so in
Chrome the page's own `htmx.ajax` loaded it into the panel. The form was then filled and
submitted there.

### Terminal review (Vietnam): partial acceptance

The evidence file was built from the live database by the backend's own `build_evidence()`
(`transcripts/T-evidence-vietnam.json`), so the terminal run received exactly what the UI would
send. Five items for three records: the automatic checks flagged the two repeated subjects.
`i1`, `i3` and `i4` were kept. `i2` was dropped because it leaves out the record's "south stays
hot and dry". `i5` was dropped because it repeats the rail subject with no action. The decision
notes also record that Planner step s2 calls the south "cool and dry", which the record
contradicts. No Worker item carried that error.

## Audit verification

| Check | Result |
|---|---|
| `GET /audit/verify` after all three Chunk 6 decisions | `{"valid": true, "entries": 50, "broken_at": null}` (`transcripts/audit-verify-final.txt`) |
| The committed copy, re-checked offline with the server's `Store.verify()` | `{'valid': True, 'entries': 50, 'broken_at': None}` (same file) |
| Thailand (UI) audit trail | #41 `workflow_created`, then Planner, Worker, `automatic_checks`, Reviewer, #49 `awaiting_human_review`, #50 `decision_partial` by `human` |
| Vietnam (terminal) audit trail | #21-#29 the same stages, then #39 `decision_partial` (`transcripts/T-decide-audit-verify.txt`) |
| After the server restart, before any Chunk 6 decision | `valid: true`, 38 entries, both waiting workflows unchanged. This was seen in the terminal but not saved to a file. The first saved check, `valid: true` with 39 entries, follows the first decision in `T-decide-audit-verify.txt`. |

## Evidence files (`multi-agent-server/`)

| File | Shows |
|---|---|
| `workflow-data/workflows/*.json` | The five complete records: evidence, plan, work, review, `history` (stage, prompt, model, timings, raw output), human decision, final output |
| `workflow-data/audit.log.jsonl` | All 50 hash-chained audit entries |
| `transcripts/U-start.txt`, `U-poll.txt` | The Indonesia review's start and poll requests through the gateway, with the rendered review fragment |
| `transcripts/T-evidence-vietnam.json`, `T-run.txt` | Terminal evidence file and `cli.py run` |
| `transcripts/T-decide-audit-verify.txt` | `cli.py decide`, `show`, `audit <id>`, `verify` |
| `transcripts/audit-verify-final.txt` | Final `GET /audit/verify`, `cli.py list`, the full `cli.py audit`, and the offline re-check |
| `screenshots/01`-`03` | Indonesia in Chrome: awaiting review; the correction form filled (Decided by Alex Chen); the corrected outcome |
| `screenshots/04`-`08` | Thailand in Chrome: queued; Planner working; awaiting review; the partial form (`i5` unticked); the partially accepted outcome |

## Limits and findings

- **The 3B Reviewer adds little.** Its own verdict was `pass` on four runs and `concerns` on
  Thailand. Its findings were mostly `info` restatements of the items. The `concerns` verdicts
  come from `checks.final_verdict`, which turns any warning into `concerns`. On Vietnam and
  Thailand the warnings were the automatic repeated-subject checks. On both Japan runs the
  warning was the model's own (`i2` "could be improved by mentioning the cherry blossom
  crowds"), which the Chunk 2 human agreed with. The human decision caught the problems that
  mattered.
- **Schema validity is not truth.** Citing the right evidence id did not stop the Planner's
  "cool and dry" error, `i2` dropping half its record, or Thailand's bookkeeping line becoming
  a checklist item. Only the human review caught them.
- **The Chunk 2 decisions have weak attribution.** `6cded4a6` was approved through `cli.py`
  with its default `decided_by: terminal-reviewer` and no notes. On `96e03a60` the reason
  ("The reviewer raises a valid warning for item 2") was typed into **Decided by**, and
  **Notes** is empty. Both are kept unchanged. A clearer label for the field is noted in
  `known-issues.md`.
- **The Multi-Agent Server was restarted once**, between the first two runs and their
  decisions (see the local deployment report). Both waiting records survived, and the chain
  stayed valid.
- Single model, one workflow at a time, file-backed. This is local evidence only: Multi-Agent is
  disabled in the cloud baseline (`cloud/07-multi-agent-disabled.jpg`).
- **This report was edited after `review-multi-agent` read it.** The finding attributions were
  corrected after the independent review, and the Thailand run and "Who did what" were added.
  The loop record's hash of this file therefore no longer matches; see `loop/README.md`.
