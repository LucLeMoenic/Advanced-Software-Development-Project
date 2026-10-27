# Release 2 agentic-loop report reviews (Student 3)

The shared loop's Release 2 review modes (`review-testing`, `review-multi-agent`, `review-cloud`) were run on Student 3's real evidence and finalised by the
human. `review-testing` and `review-multi-agent` used the two-model loop on this laptop (`qwen2.5:3b` implementer, `llama3.2:3b` reviewer, Ollama 0.34.3).
`review-cloud` could not complete here (see below) and was run on another machine with larger models (`qwen2.5-coder:7b` implementer, `llama3.1:8b` reviewer, Ollama 0.40.11).

| Mode | Record (`docs/agentic-loop-records/`) | Reviewer verdict | Human decision | Write-up |
|---|---|---|---|---|
| `review-testing` | `20261021T082731Z-036d7933be304da5b39b842752adeb94.json` | ACCEPT | **changed** | `reviewrecord.md`, 2026-10-21 (testing) |
| `review-multi-agent` | `20261021T084545Z-c559fb77d71d447c9a3755a535f3590a.json` | ACCEPT | **changed** | `reviewrecord.md`, 2026-10-21 (multi-agent) |
| `review-cloud` | `20261027T071604Z-5d3ef36790834a07a8fd8ac8d79033da.json` | ACCEPT | **changed** | `reviewrecord.md`, 2026-10-27 (cloud) |

Files here: `testing-review-run-terminal.txt`, `multi-agent-review-run-terminal.txt`, `finalise-terminal.txt`, `post-test-results.txt`, copies of the
`review-testing` and `review-multi-agent` records, and for `review-cloud`: `cloud-review-run-terminal.txt` (the run that produced the record),
`cloud-review-finalise-terminal.txt`, `cloud-review-record.json` (copy of the finalised record) and `cloud-review-attempt*-terminal.txt` (the failed attempts).

**Do not edit the evidence files these reviews read.** Each record stores their SHA-256 hashes, so a later edit breaks the
provenance. They are listed in each record's `evidenceHashes.contextSha256`.

## `review-cloud`: how the record was produced

Two real cloud runs exist: the AI-off baseline `cloud-deployment.yml` run 39741981906 on `main` at `851bdd7`, and the protected AI run 39893640923 at `4c1e71a`
(`ai,mcp,rag,multi-agent` behind gateway authentication). Both smoke outputs include `PASS: Student 3 cloud profile and CRUD checks`. The loop reviewed
`../cloud-deployment-evidence.md` (the digest), `../cloud/10-public-url-readonly-check.txt` and the group's stored run excerpts under `student-5/docs/evidence/release-2/cloud/`
(`02`, `03`, `10`, `11`). Evidence added afterwards (`../cloud/11` to `13`: an authenticated read-only check, a screenshot of the deployed page and the human decision on the
Student 3 cloud workflow) is not part of the record's hashed context. The digest was frozen, so it still says the cloud workflow is awaiting a decision; it was approved on
2026-10-26 (`../cloud/13-human-decision-cloud-workflow.txt`).

It took **14 attempts**. Attempt 14 produced the record, `20261027T071604Z-5d3ef36790834a07a8fd8ac8d79033da.json`, which was finalised as `changed`
(`cloud-review-finalise-terminal.txt`). Nothing was edited by hand to get past a failure, and every failed log is kept:

| Attempt | Where | Models (implementer / reviewer) | Outcome | Log |
|---|---|---|---|---|
| 1 | this laptop (8 GB) | `qwen2.5:3b` / `llama3.2:3b` | Implementer output lacked exactly one `[PLAN]` and one `[ACT]` | `cloud-review-attempt1-failed-terminal.txt` |
| 2, 5, 6 | this laptop | same | Reviewer REJECT lacking the required severity, evidence and correction fields; it also misread the AI-off baseline as a defect | `cloud-review-attempt2-failed-terminal.txt`, `attempt5`, `attempt6` |
| 3 | this laptop | same | Killed for low system memory | `cloud-review-attempt3-killed-low-memory-terminal.txt` |
| 4 | this laptop | `llama3.2:3b` for both | Refused at once: the loop requires different models | `cloud-review-attempt4-same-model-rejected-terminal.txt` |
| 7 | this laptop | same as 1, evidence now covering both runs | Ended after `[ACT]` with no exit line; 174 MB of memory was free | `cloud-review-attempt7-incomplete-terminal.txt` |
| 8 | this laptop | same | Hit the loop's default 600 s per-call limit | `cloud-review-attempt8-timeout-terminal.txt` |
| 9, 10 | this laptop | same, `--timeout-seconds 1800` | Killed for low system memory (attempt 10 after the implementer step, while the reviewer was assessing) | `cloud-review-attempt9-...`, `attempt10-killed-low-memory-terminal.txt` |
| 11, 12 | another machine | `qwen2.5-coder:7b` / `llama3.2:3b` | Reviewer wrote `Verdict: BLOCKING`, which is not a valid verdict | `cloud-review-attempt11-reviewer-invalid-verdict-terminal.txt`, `attempt12-...` |
| 13 | another machine | `qwen2.5-coder:7b` / `llama3.1:8b` | Reviewer's REVISE findings malformed (a leading `- ` before `Evidence:`, which the parser rejects) | `cloud-review-attempt13-reviewer-malformed-findings-terminal.txt` |
| **14** | another machine | `qwen2.5-coder:7b` / `llama3.1:8b` | **Completed; record written** | `cloud-review-run-terminal.txt` |

What the models produced, and how the human review treated it (full notes are in the record's `humanNotes` and in `../../../reviewrecord.md`): the final verdict was ACCEPT on a
"No changes required" proposal with no recommended actions, its five findings were SUGGESTIONs that repeated the digest's own "Not evidenced" list, and its two REQUIRED
validation gaps were wrong (they claimed the baseline did not have AI disabled and the AI run did not have it enabled, the opposite of the evidence). The reviewer model is
therefore not the documented `llama3.2:3b`: that model returned an invalid verdict on both of its runs on the larger machine. The binding limit on this laptop was memory.
