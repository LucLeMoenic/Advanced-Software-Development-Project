# Student 3 — Multi-Agent Integration Evidence (Release 2, Chunk 4)

Feature: "Plan a Day with Agents" · Backend: `student-3/backend/{multi_agent_client,agent_evidence}.py`, `/api/agents/*` in `app.py` · UI: `student-3/frontend/` · Flow diagram: `student-3/docs/architecture.md` (Release 2 section)

## What was built

| Item | Where |
|---|---|
| Backend client and `/api/agents/{status,workflows,workflows/<id>,workflows/<id>/decision}` | `multi_agent_client.py`, `app.py` |
| Evidence the agents may use (catalogue entries plus up to two review comments each) | `agent_evidence.py` |
| `MULTI_AGENT_ENABLED` (default **false**) and `MULTI_AGENT_SERVER_URL` | `docker-compose.yml`, `.env.example` |
| UI panel: progress for Planner / Worker / Reviewer / You, plan, items with evidence ids, verdict and findings, four-way decision form | `index.html`, `app.js`, `style.css` |
| CI: routes fail closed when disabled | `student-3.yml` step "Assert Multi-Agent routes are disabled by default" |

Design points: the backend, not the browser, chooses the evidence; the reviewer identity (`decided_by`) is fixed to
`student-3-ui` and unknown decision fields are dropped; workflow ids are validated before being forwarded; all
server and model text is HTML-escaped (attribute positions use a quote-escaping helper).

## Results

| Evidence | Result |
|---|---|
| `multi-agent-integration/01-tests.txt` | 49 new integration tests pass; whole Student 3 suite 130/130; shared server suite 66/66 |
| `multi-agent-integration/02-mutation-check.txt` | Eight deliberately injected bugs (enabled by default, browser-chosen reviewer, relayed extra fields, unvalidated id, DB hit while disabled, leaked statuses, evidence order, comment count); all eight fail the suite |
| `multi-agent-integration/03-disabled-by-default-api.txt` | Disabled (503), offline (502) and healthy responses from the real backend |
| `multi-agent-integration/server-data/` | The three workflows and the audit log produced by the UI runs (30 entries, chain valid) |
| `multi-agent-integration/screenshots/` | See below |
| GitHub Actions run | Green on the PR branch (run 39567326531) and on `main` for the merge of PR #113 (`cbb57ed`): run 39567695254, including "Test Multi-Agent Server" and "Assert Multi-Agent routes are disabled by default". Links: `ci/04-github-actions-runs.md` |

## Live UI runs (real browser, real model, Student 3 catalogue, via `http://localhost:5103`)

| Workflow | Task | Verdict | Human decision (UI) | Screenshots |
|---|---|---|---|---|
| `wf-20261019T020258Z-51e73481` | Relaxed food-focused afternoon (restaurants) | **fail**: 4 blocking findings (first Worker prompt, see Problems) | **Rejected**; client-side check first blocked a rejection with no notes | 01, 02, 03 |
| `wf-20261019T020834Z-cac9cdd6` | Same task, after the fix | **pass**, 0 blocking | **Partial**: kept i1-i3, dropped i4 (described as "loud") | 04, 05, 06 |
| `wf-20261019T021218Z-057c2796` | Two things for a sunny morning (activities) | **concerns** (plan evidence unused) | **Corrected**: edited one item's wording; automatic checks re-run and recorded | 08, 09 |

Other screenshots: `07-narrow-375px.png` (no horizontal overflow, document 360px in a 375px viewport),
`10-state-offline.png`, `11-state-disabled-by-default.png`. Each run took roughly two to four minutes.
Decisions are labelled development test runs; the showcase decision should be the group's own.
The **approve** route was not exercised in the browser (it is covered by the server and backend tests).

## Problems found along the way

1. **Worker used descriptions as subjects (first UI run).** With the v1 Worker prompt the 3B model wrote each
   restaurant's description where its name belonged. The automatic check flagged all four items as blocking and
   forced the verdict to `fail`, which is the guard working, but the demo was unusable. Fix at the structural
   level: the JSON schema sent to Ollama now restricts `subject` to the exact evidence titles, backed by a v2
   Worker prompt with a worked example. The check still verifies the subject belongs to the entry the item cites.
   Re-run on the same task: pass, 0 blocking.
2. **Repeated findings.** The Reviewer repeated an identical finding four times; identical model findings are now
   shown once (test added).
3. **Reviewer asserted an unsupported fact** ("restaurants are open on a weekend"; the evidence has no opening
   hours) in the first run. **Not fixed.** It is the reason the human decision exists, and it is listed under limits.
4. **Weak test found by mutation checking:** the "best-rated first" test passed even when sorting by id, because the
   fixture ids happened to follow rating order. Rewritten with ids that do not.
5. **Screenshots initially saved outside the repo** (the browser tool resolved relative paths elsewhere); moved in
   and the stray folder removed. Later screenshots used absolute paths.

## Limits

- The review step has no authentication: anyone who can open the page can record the decision. The cloud security
  bonus (endpoint security) would need to cover this.
- The Reviewer model is unreliable (item 3 above); the deterministic checks and the human decision are the controls.
- One workflow runs at a time; a second start returns `503 busy`.
- The agentic-loop record for this chunk is still to do (needs the human Adapt and finalise steps).
