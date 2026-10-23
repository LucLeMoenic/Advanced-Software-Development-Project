# Student 4 Release 2 Validation - 2026-10-23

Scope: implemented preview-only What-If planner in the **uncommitted workspace**.
The results below were observed during local implementation and validation on
2026-10-23. No Release 2 commit, push, grade, human approval or sign-off is claimed.
See the [runbook](../../release-2-runbook.md) for startup and demo instructions.

## Recorded Results

| Evidence | Supplied result | Boundary |
|---|---|---|
| Calculator tests | 74 focused tests passed. | Included within the full backend total below; do not add twice. |
| Backend after review fixes | 322 tests passed. | Local automated tests, including dependency fakes; not a real human decision. |
| Two required endpoint functions | Exact CI selection passed five cases for preview and workflow start, including the four decision variants; TRX generated locally. | Successful local execution, not a published GitHub Actions run. |
| Frontend | 79 tests passed; production build passed. | Automated UI behavior/build, separate from browser evidence below. |
| Cloud tooling tests | 35 Student 4 cloud tests and 210 related cloud-suite tests passed. | Related scopes, not an asserted disjoint total; not a live cloud deployment. |
| Compose/images | Configuration validated; Student 4 database/backend/frontend plus shared frontend images built. | Four images, not a full-group image/runtime result. |
| Local runtime | Those four containers reported healthy; gateway `http://localhost:5100/budget/` exercised. | Deliberate subset, not all 16 application services. |
| Native AI | Existing host Ollama on 11434; shared native Multi-Agent Server on `127.0.0.1:15600`; backend container reached `http://host.docker.internal:15600`. | Windows denied the normal 5600 bind with error 13. Trusted-local setup only. |
| Disabled-mode rehearsal | Recreated the local backend with all four AI flags false; preview returned 200 with unchanged actual spending and workflow start returned 503. Restored local multi-agent mode afterwards. | Real local runtime check, not an Azure/AWS deployment. Backend recreation invalidated the browser run's old token. |
| Security hook | Actual Git hook installed using Python tooling under `%TEMP%/asd-student4-r2-security`; pre-commit Ruff security rules and detect-secrets passed. | pip-audit was skipped because no requirements changed; do not report it as a passed audit. No runtime package changes. |
| .NET dependency audit | `dotnet list student-4/backend/Backend.csproj package --vulnerable --include-transitive` reported no vulnerable packages. | Point-in-time package-advisory result, not a general security certification. |

The final source-and-generated-evidence hook scan passed Ruff and detect-secrets.
The secret detector initially flagged fifteen public SHA-256 input/prompt
fingerprints in the three report-review JSON records. Those exact findings were
classified `is_secret: false` in the existing baseline; no rule or file category
was disabled. The baseline alone was temporarily staged as required by the hook,
then restored to its original unstaged state. No source/evidence was committed.
`git diff --check` also passed. The closing architectural review confirmed both
earlier runtime blockers resolved, with no new high-confidence issue in scope.

## Real Gateway Workflow

Workflow `wf-20261022T231153Z-60c02c5c` ran through the real shared gateway and
native Planner -> Worker -> Reviewer. Its UTC identifier is dated 2026-10-22;
this local evidence summary is dated 2026-10-23.

| Observation | Recorded value |
|---|---|
| Journey | `Europe Escape` |
| Proposed category change | Accommodation EUR 1500 -> EUR 1600 (+EUR 100). |
| Journey planned | 375000 -> 385000 cents (EUR 3750 -> EUR 3850). |
| Journey actual | Unchanged at EUR 4126.85. |
| Persistence | Saved budget and expense response bodies were byte-identical before/after. No financial write was performed. |
| Native outcome | `status=awaiting_human_review`; Reviewer raised concerns; `degraded=false`. |
| Human outcome | `human_decision=null`; not human-finalised or accepted. |

Automated coverage exercises `approve`, `correct`, `partial` and `reject` using
fake dependencies. It does not prove any real human exercised those choices.
Approval only accepts commentary; no decision saves limits or expenses.

## Browser Evidence

Node/Chromium exercised the real gateway preview at 1280, 768 and 320 pixels;
no horizontal page overflow was observed. Existing captures:
[1280px](what-if-preview-1280.png), [768px](what-if-preview-768.png),
[320px](what-if-preview-320.png).

These captures establish the exercised preview layout, not live human review,
keyboard/accessibility completeness, full CRUD regression or group acceptance.
The final real browser run also reached [awaiting human review](what-if-awaiting-human.png)
for workflow `wf-20261022T233115Z-b048fe46`. All three model stages completed;
the name and decision fields remained blank, no decision was submitted, no page
errors occurred, and budget/expense responses remained unchanged. The final
backend image was used for that run.

### Model Accuracy Limitation

The [initial captured workflow](what-if-initial-workflow.json) misstated money
units/currencies and included misleading evidence findings. The backend was
then changed to supply exact major-unit/currency display strings alongside the
bound minor-unit values, with instructions not to recalculate or invent figures.
Focused planner tests passed 186 cases and the final full backend suite passed
322 cases after that change.

The [final captured workflow](what-if-final-workflow.json) quoted the category
amounts more accurately but still overgeneralised which categories were below
their actual spending and included questionable conclusions. Its Reviewer
reported concerns, not financial certification. Neither model stage is an
authoritative calculator or proof of factual correctness. Use the deterministic
comparison and supplied evidence to correct or reject such advice; the human
decision is deliberately still absent. Do not claim a clean model-quality pass.

## Review Corrections

Two independent implementation reviews, supplied by the main session, found:

| Finding | Applied correction and evidence |
|---|---|
| Valid multiline commentary was rejected. | Allow bounded CR/LF/tab prose while retaining length/control-character constraints. Expanded backend suite passed 322 tests. |
| A native record with a Reviewer-flagged subject/citation mismatch was hidden from human review. | Keep structurally valid flagged native records readable and eligible for explicit human decisions; human-corrected output retains strict validation. Expanded backend suite passed 322 tests. |

These are supplied implementation-review outcomes, not new independent reviews
or new test runs performed by this documentation session.

## CI And Cloud

[Student 4 CI](../../../../.github/workflows/student-4.yml) explicitly selects
`EndpointTests.WhatIfPreviewUsesCurrentActualsAndDoesNotMutateSource` and
`EndpointTests.WhatIfStartPollAndAllHumanDecisionsArePreviewOnly`, with TRX upload.
No new remote CI run exists for the unpushed Release 2 changes. Earlier Release 1
Actions results do not certify this workspace.

Existing shared cloud deployment tooling was reused; Student 4 smoke checks now
cover all four disabled flags and deterministic preview without financial
writes. Local tooling tests do not establish Azure/AWS access or deployment:
live cloud was not run, credentials were not accessed, and nothing was
provisioned. The required cloud baseline keeps AI-Mode, MCP, RAG and Multi-Agent
off while core frontend/backend/database/CRUD and deterministic preview work.

## Report-Review Records

All three existing modes ran successfully with implementer `qwen2.5-coder:7b`
and reviewer `llama3.2:3b`, producing parsed Plan/Act and Observe output:

- [Multi-Agent Workflow Review](../../../../docs/agentic-loop-records/20261022T233511Z-9eb2d3713774405d8ea30122aeae6207.json)
- [Testing Report Review](../../../../docs/agentic-loop-records/20261022T233542Z-83639481bac64d00805ae07628655a0d.json)
- [Cloud Deployment Report Review](../../../../docs/agentic-loop-records/20261022T233613Z-0e8d026ea57240e0be6b63c54fc57608.json)

Each model verdict was ACCEPT, but `humanDecision`, `postTest` and `finalisedAt`
remain null. These are execution records, not trustworthy release verdicts:
the cloud review underweighted the explicitly missing live deployment evidence.
That requirement remains an open gate regardless of the model's verdict. The
initial CLI invocation lacked the required model environment variables and
failed before these successful runs; the runbook now shows the configuration.
The records hash their input documents before this final reconciliation update;
their original context hashes and outputs are preserved unchanged.

## Open Evidence Gates

- Actual human decision, name/notes and resulting workflow history; no automatic
  finalisation, self-declared name is not authenticated identity.
- Genuine human decision replay; the awaiting-human capture above is confirmed.
- Fresh full-group local run, multi-terminal logs and retained native R0/R1
  acceptance. Current MCP/RAG modes are false; existing functionality is retained
  but not freshly live-accepted by this run.
- Real post-push Student 4 CI execution and retained endpoint/TRX artifacts.
- Live integrated cloud deployment, deployment-workflow logs and core CRUD checks.
- Genuine human review of the three records above and Adapt finalisation after
  actual post-tests. Re-run with later CI/cloud/human evidence before claiming
  final acceptance; the existing pending records do not close those gaps.
- Identifiable published Release 2 contributions, group PDF/video, Q&A and final
  human release decision. No commit/push or showcase sign-off was performed here.

Feature acceptance IDs are in [requirements](../../requirements.md), not a grade
prediction. The specific Release 2 brief sets submission to **25 October 2026,
11:59 PM AEST**; the general specification's 18 October date is historical and
conflicting. This summary follows the specific brief without modifying sources.