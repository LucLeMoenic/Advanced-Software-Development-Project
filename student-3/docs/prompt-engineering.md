# Prompt Engineering and Context Management — student-3

How the reviewer prompt for the shared development agentic loop was designed for
student-3's Release 1 work, what evidence drove it, and how it will be checked.
The application's own runtime prompt (`/api/recommend`) is covered in
`prompt-log.md`, "Why this prompt shape".

---

## The reviewer prompt: `student3-reviewer-llama32-v1`

File: `student-3/docs/prompt-library/reviewer-student3-v1.md`.

### Why a new prompt

Release 0's only student-3 loop run (record `20260906T104055Z`, analysed in
`reviewrecord.md` 2026-09-25) used Student 5's `student5-reviewer-llama32-v2`.
That prompt fixed the shared prompt's template-echo failure, but on student-3
work it showed the residual defect Student 5 had already documented in
`student-5/docs/prompt-engineering.md`: the reviewer copied an example instead of
reviewing the proposal.

| Observed in `20260906T104055Z` | Consequence |
|---|---|
| Both reviewer passes returned the v2 REVISE example's finding verbatim (division by `count`), and no such code existed in the proposal. | The machine Adapt phase had nothing real to fix; `adaptedProposal` came back byte-identical to `planAct`. |
| The reviewer missed the real defect: `seconds - 2` / `seconds - 45` made `formatElapsed(14)` return `'12s'`. | Only the human Adapt phase caught it. The model review added no value on this run. |
| The prompt was tuned for Student 5's code. | Nothing in it directed attention to student-3's Release 1 risks (MCP tool boundaries, RAG grounding). |

### What changed from v2

| # | Change | Reason |
|---|---|---|
| 1 | **Grounding rule.** Every `Evidence:` line must quote, in backticks, text copied from the proposal. If the reviewer cannot quote it, the finding is not real. | Targets the exact failure above. An echoed finding cannot quote the proposal, so the rule gives the model a self-check, and it gives the human a mechanical one: search the proposal for the quoted text. |
| 2 | **Work one stated example through the code.** When the task gives inputs and expected outputs, the reviewer must trace at least one before choosing a verdict. | The missed `'12s'` bug was visible from the task's own example (`14` → `'14s'`). |
| 3 | **Examples review their own tiny proposal, using `example_only_` names.** Each example shows the proposal and the review of it together, and every identifier in them is prefixed `example_only_`. | The examples still demonstrate the format and the quoting rule. If the model echoes an example anyway, the output contains an `example_only_` name, and that is detectable with a single search. In v2 the echoed `count` looked plausible. |
| 4 | **Student-3 review focus section** for Release 1 MCP/RAG work. | Points a small model at the failure modes that matter for this feature, not generic checks. |

Kept unchanged from v2: the prose output rules (no pipe-separated menus), the
documented `- None` path, the verdict/severity consistency rule, the no-echo
instruction, and the untrusted-input security line. All of these are also
required by the loop's `ParseVerdict` gate.

The prompt declares exactly one `Version:` line, which the loop's
`ExtractPromptVersion` requires and hashes into every record. That was checked
with the same regex and flags the loop uses.

### How it is used

```powershell
docker compose exec agentic-loop dotnet /app/AgenticLoop.dll run `
  --task "<bounded task>" `
  --context "<student-3 file>" `
  --reviewer-prompt "/workspace/student-3/docs/prompt-library/reviewer-student3-v1.md" `
  --implementer-model "qwen2.5:3b" `
  --pre-test-command "<command>" `
  --pre-test-result "<result>"
```

`qwen2.5:3b` is the implementer because the default `qwen2.5-coder:7b` cannot
load on this host (see `prompt-log.md`, "Operational note"). The reviewer stays
`llama3.2:3b`. When the Release 1 loop moves outside Docker, the
`--reviewer-prompt` path becomes the repository-relative path instead of
`/workspace/...`.

### Did it work?

Not yet evaluated. The planned check reruns the Release 0 task from
`20260906T104055Z` with the same context file, models, and pre-test, and changes
only `--reviewer-prompt`. Pass criteria:

1. The loop's parser accepts the review on the first attempt (no format correction).
2. No `example_only_` name appears anywhere in the reviewer output.
3. Every `Evidence:` line quotes text present in the proposal.
4. If the implementer repeats the `seconds - 2` arithmetic, the reviewer flags it.

The result, pass or fail, will be recorded here and in `reviewrecord.md`.

### Known limitation

A 3B reviewer can still ignore instructions. The grounding rule reduces the
chance of invented findings and makes them easy to spot, but it cannot stop
them. The human Adapt phase, and tests the human runs, remain the real check.
