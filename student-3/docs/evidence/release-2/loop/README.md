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

## `review-cloud`: attempted, no record yet

A real cloud deployment now exists: `cloud-deployment.yml` run 39741981906 on `main` at `851bdd7` (AWS VM behind a Caddy TLS
gateway, AI-off baseline), whose smoke output includes `PASS: Student 3 cloud profile and CRUD checks`. Student 3's evidence for it
is `../cloud-deployment-evidence.md` and `../cloud/10-public-url-readonly-check.txt`, which also list what has no cloud
evidence (persistence, backup and rollback on the VM, live private boundaries, the optional cloud AI services).

`review-cloud` was run on that evidence six times and **produced no record**. The loop rejected every run, and nothing was
hand-edited to get past it. The terminal logs are kept:

| Attempt | Models (implementer / reviewer) | Outcome | Log |
|---|---|---|---|
| 1 | `qwen2.5:3b` / `llama3.2:3b` | Implementer output lacked exactly one `[PLAN]` and one `[ACT]` | `cloud-review-attempt1-failed-terminal.txt` |
| 2 | same | Reviewer REJECT without the required severity, evidence and correction fields; also asserted things the evidence does not say | `cloud-review-attempt2-failed-terminal.txt` |
| 3 | same | Killed by Claude Code for low system memory | `cloud-review-attempt3-killed-low-memory-terminal.txt` |
| 4 | `llama3.2:3b` for both | Refused at once: the loop requires different models | `cloud-review-attempt4-same-model-rejected-terminal.txt` |
| 5 | `qwen2.5:3b` / `llama3.2:3b` | Same reviewer failure as attempt 2 | `cloud-review-attempt5-failed-terminal.txt` |
| 6 | same, task reworded to say the AI-off baseline is required | Reviewer again misread the evidence and failed the format check | `cloud-review-run-terminal.txt` |

The 3B reviewer treats the required AI-off baseline as a defect and cannot produce a well-formed REJECT. A record needs a run that
completes, then the human `finalise` decision. Run the command in the head of `cloud-review-run-terminal.txt` with a stronger
implementer or reviewer model (Student 5's record used `qwen2.5-coder:7b`).
