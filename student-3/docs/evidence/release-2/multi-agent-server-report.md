# Multi-Agent Server — Implementation and Workflow Evidence (Release 2, Chunk 3)

Server: `ai-services/multi-agent-server/` (native, port 5600, not a Compose service) · Model: `llama3.2:3b` via native Ollama for all three agents · Docs: `ai-services/multi-agent-server/README.md`

## What was built

| Requirement | Where |
|---|---|
| Shared non-containerised Multi-Agent Server | `server.py` (FastAPI, `uvicorn server:app --port 5600`) |
| Planner, Worker, Reviewer with defined responsibilities | `agents.py`; versioned prompts `ai-services/agentic-loop/prompts/multi-agent-{planner,worker,reviewer}-v1.txt` |
| Evidence flow | Caller supplies `evidence`; each agent sees only that plus the previous agent's validated output; every Worker item must cite supplied evidence ids |
| Human review: approve, correct, partial acceptance, reject | `workflow.decide()`; `POST /workflows/{id}/decision` and `cli.py review/decide` |
| Workflow history | `GET /workflows/{id}` -> `history[]` (stage, prompt, model, timings, output) |
| Coordination / audit log | `audit.log.jsonl`, SHA-256 hash chain, `GET /audit`, `GET /audit/verify` |
| Callable from the terminal | `cli.py` (`run`, `review`, `decide`, `show`, `list`, `audit`, `verify`) |
| Callable from the application | HTTP API; Student 3 backend routes and UI panel are Chunk 4 (not yet done) |

## Live workflows (real Ollama, real Student 3 catalogue as evidence)

Files: `multi-agent-server/workflow-data/` (workflow records and the audit log) and `multi-agent-server/transcripts/` (terminal sessions).

| Workflow | Task | Outcome | Time (planner / worker / reviewer) |
|---|---|---|---|
| `wf-20261018T073546Z-5b4ec451` | Relaxed food-focused afternoon (4 restaurants) | Reviewer: `concerns` (plan-required evidence `attraction-11` unused). **Human: partial acceptance** via interactive `cli.py review`, kept i1 and i2, dropped i3 (the evidence calls it "loud") | 27 s / 21 s / 11 s |
| `wf-20261019T011611Z-0ccf5c1c` | Two things for a sunny morning (4 activities) | Reviewer: `concerns` (`attraction-8`, `attraction-12` unused). **Human: correction** with a validated edited output; automatic checks re-run on it | 50 s / 40 s / 46 s |
| `wf-20261018T073712Z-56f37adc` | Same task as above | **`failed`** at the Worker: `dependency_timeout`. The host was suspended mid-run (log timestamps jump from 07:37 to 08:38 UTC), so this is a sleep artifact, not a model fault. Kept as evidence that failure is recorded and audited | n/a |

Human decisions in these runs are labelled `decided_by: dev-test-run`. They are development test runs, not the
group's showcase review. The audit chain verifies: `{"valid": true, "entries": 25, "broken_at": null}`
(`transcripts/B-decide-audit-verify.txt`).

Terminal transcripts: `A-run.txt`, `A-review.txt` (interactive partial acceptance), `B-run.txt`,
`B-decide-audit-verify.txt` (correction, list, audit, verify), `F-failed-run-host-suspended.txt`,
`attempt1-reviewer-validation-failed.txt`.

## Test evidence

| Evidence | Result |
|---|---|
| `ai-services/multi-agent-server/tests/` | 62 passed, offline, scripted fake model |
| `03-mutation-check.txt` | Six deliberately injected bugs, each on its own; all six make the suite fail (see below) |
| `04-ci-step-local-run.txt` | The new `Test Multi-Agent Server` steps of `student-3.yml` run locally: 62/62 |
| GitHub Actions run | Green on `main` for the merge of PR #112 (`473399d`): run 39187245823, step "Test Multi-Agent Server" = success. Links: `ci/04-github-actions-runs.md` |

Mutations: blocking finding ignored (M1), subject check disabled (M2), second decision allowed (M3),
audit link check removed (M4), retry removed (M5), reject without notes allowed (M6).

## Problems found along the way

1. **Reviewer validation failure (live attempt 1).** The 3B Reviewer produced output my validation
   rejected twice, and the whole workflow failed, discarding a good plan and Worker result. I could not tell
   why, because the rejected output was not recorded. The only `ValueError` the Reviewer path raised itself
   was "finding cites an unknown item", so that is the likely cause, but this was not confirmed.
   Fixes: record the raw rejected output and reason in the history and audit log; constrain
   `item_id` to real items in the JSON schema; keep a finding that still cites an unknown item but detach it;
   and, if the Reviewer still fails, hand over to the human as a clearly marked `degraded` automatic-checks-only
   review that can never be a `pass`. Re-run: workflows A and B succeeded.
2. **Duplicate findings.** The model restated the automatic "evidence not used" finding. Model findings
   whose message equals an automatic finding are now dropped (test added).
3. **Mutation gap (M4).** Removing the audit `prev_hash` link check was *not* caught by the first 61 tests:
   they detected edits and deletions but not an edit whose own hash had been recomputed. A test for that case
   was added and M4 is now caught. The first mutation run was also cumulative, which hid this gap; the saved
   evidence is from a clean one-bug-at-a-time run.
4. **detect-secrets flagged the audit log** (21 SHA-256 chain values). All were checked to be hex digests in
   the audit data and marked as audited false positives in `.secrets.baseline`.

## Limits and outstanding items

- **Agentic-loop record for this chunk is not done.** A Release 2 loop record needs the human Adapt and
  finalise steps, which only the group member who runs the loop can do honestly. To do: run `run` on a
  bounded Chunk 3 task, finalise it, and save the record and transcript here.
- The Student 3 backend routes, `MULTI_AGENT_ENABLED` flag and UI panel (Chunk 4) are not built, so the
  "through the frontend UI" half of the rubric is not yet evidenced.
- The Planner's output from a 3B model is generic (it plans steps like "make a reservation" that no tool
  can do). The deterministic checks and the human decision are the real controls.
- The server holds one workflow at a time and stores files locally.

## Update from Chunk 4 (found while testing through the UI)

- The first live UI run showed the Worker writing each entry's description where its name belonged (all four
  items blocked by the automatic check). The Worker schema now restricts `subject` to the exact evidence
  titles, and the Worker prompt is `multi-agent-worker-v2.txt` (worked example; v1 kept for history).
- Identical Reviewer findings are shown once.
- The server suite is now 66 tests. The integration evidence is in `multi-agent-integration-report.md`.
