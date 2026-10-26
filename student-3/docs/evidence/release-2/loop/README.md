# Release 2 agentic-loop report reviews (Student 3)

The shared loop's Release 2 review modes (`review-testing`, `review-multi-agent`, `review-cloud`) were run on Student 3's
real evidence with the two-model loop (`qwen2.5:3b` implementer, `llama3.2:3b` reviewer, Ollama 0.34.3) and finalised by the human.

| Mode | Record (`docs/agentic-loop-records/`) | Reviewer verdict | Human decision | Write-up |
|---|---|---|---|---|
| `review-testing` | `20261021T082731Z-036d7933be304da5b39b842752adeb94.json` | ACCEPT | **changed** | `reviewrecord.md`, 2026-10-21 (testing) |
| `review-multi-agent` | `20261021T084545Z-c559fb77d71d447c9a3755a535f3590a.json` | ACCEPT | **changed** | `reviewrecord.md`, 2026-10-21 (multi-agent) |
| `review-cloud` | **not run** | n/a | n/a | No genuine cloud deployment exists yet; see below |

Files here: `testing-review-run-terminal.txt`, `multi-agent-review-run-terminal.txt`, `finalise-terminal.txt`,
`post-test-results.txt`, and copies of both finalised records.

**Do not edit the evidence files these reviews read.** Each record stores their SHA-256 hashes, so a later edit breaks the
provenance. They are listed in each record's `evidenceHashes.contextSha256`.

## `review-cloud`: attempted ten times, no record

Two real cloud runs now exist: the AI-off baseline `cloud-deployment.yml` run 39741981906 on `main` at `851bdd7`, and the protected AI run
39893640923 at `4c1e71a` (`ai,mcp,rag,multi-agent` behind gateway authentication). Both smoke outputs include
`PASS: Student 3 cloud profile and CRUD checks`. Student 3's evidence is `../cloud-deployment-evidence.md` (the digest the loop hashes),
`../cloud/10-public-url-readonly-check.txt`, and, added afterwards, `../cloud/11` to `13` (an authenticated read-only check, a screenshot of the deployed
page, and the human decision on the Student 3 cloud workflow). It also lists what has no cloud evidence (persistence, backup and rollback on the VM,
live private boundaries).

`review-cloud` was run on that evidence ten times and **produced no record**. The loop rejected or lost every run, and nothing was hand-edited to get past it.
The terminal logs are kept:

| Attempt | Models (implementer / reviewer) | Outcome | Log |
|---|---|---|---|
| 1 | `qwen2.5:3b` / `llama3.2:3b` | Implementer output lacked exactly one `[PLAN]` and one `[ACT]` | `cloud-review-attempt1-failed-terminal.txt` |
| 2, 5, 6 | same | Reviewer REJECT lacking the required severity, evidence and correction fields; it also misread the AI-off baseline as a defect | `cloud-review-attempt2-failed-terminal.txt`, `attempt5`, `attempt6` |
| 3 | same | Killed by Claude Code for low system memory | `cloud-review-attempt3-killed-low-memory-terminal.txt` |
| 4 | `llama3.2:3b` for both | Refused at once: the loop requires different models | `cloud-review-attempt4-same-model-rejected-terminal.txt` |
| 7 | `qwen2.5:3b` / `llama3.2:3b`, both runs' evidence | Ended after `[ACT]` with no exit line; 174 MB of memory was free | `cloud-review-attempt7-incomplete-terminal.txt` |
| 8 | same | Hit the loop's default 600 s per-call limit (`operation timed out`) | `cloud-review-attempt8-timeout-terminal.txt` |
| 9 | same, `--timeout-seconds 1800` | Killed for low system memory | `cloud-review-attempt9-killed-low-memory-terminal.txt` |
| 10 | same, `--timeout-seconds 1800`, digest updated | Killed for low system memory after the implementer step, while the reviewer was assessing | `cloud-review-attempt10-killed-low-memory-terminal.txt` |

The binding limit is memory: this host has 8 GB, with about 0.8 to 1 GB free, and the loop alternates two 3B models over a prompt of about 26 KB.
Attempts 1, 2, 5 and 6 ran to the reviewer step when the evidence was smaller. To produce the record, run the command in the head of the attempt 10 log on a machine
with more free memory, or with a stronger model (Student 5's record used `qwen2.5-coder:7b`), then run `finalise`; the decision (kept, changed or rejected) is the
human's. The digest was frozen for these runs, so it still describes the Student 3 cloud workflow as awaiting a decision; it was approved on 2026-10-26
(`../cloud/13-human-decision-cloud-workflow.txt`).
