# Student 4 Release 2 Runbook

Status: 2026-10-23, implemented in the uncommitted workspace. This is a
Student 4 rehearsal and handoff, not group acceptance or release sign-off.
Results and limitations: [validation record](evidence/release-2/validation-2026-10-23.md).
The [Release 2 brief](../../docs/Project_Specifications/Release_2_brief.md)
requires the integrated group application and retained native AI services.

## Contract

The What-If planner compares category aggregates, not individual saved budget
rows. Supply every existing category once, including unchanged limits. Limits
and their total must be positive JavaScript-safe integer minor units, at most
`9_007_199_254_740_991`. Actual spending is authoritative and unchanged;
planned, remaining, percentage and category status are deterministic. Exactly
80% and 100% are warning; only above 100% is overspent, using the unrounded ratio.
Neither preview nor any human decision saves budgets or expenses. There are no
schema changes, new runtime packages, or cross-student data calls.

Source pointers: [API and snapshot binding](../backend/Api/WhatIfEndpoints.cs),
[bounded native client and validation](../backend/Clients/MultiAgentClient.cs),
[human-review controls](../frontend/index.html).

Backend routes below become `/budget-api/what-if/...` through the shared gateway:

| Backend route | Request and response |
|---|---|
| `POST /api/what-if/preview` | `{journeyLabel,limits}`; each limit is `{category,limitAmountMinor}`. Returns `{original,proposed,snapshotHash}`. No model is required. |
| `POST /api/what-if/workflows` | Same complete proposal plus the preview's `snapshotHash`. Returns HTTP 202 `{id,status,token,preview,workflow}`. |
| `GET /api/what-if/workflows/{id}` | Header `X-WhatIf-Token`; returns `{id,status,preview,workflow}`. |
| `POST /api/what-if/workflows/{id}/decision` | Same token header; `{decision,decidedBy,notes}` plus only the applicable `acceptedItemIds` or `correctedOutput`; returns the updated envelope. |

`decidedBy` is the actual human's name, 1-60 characters; notes are at most 1000
characters. Bounded commentary permits CR/LF/tab, not arbitrary control text.

| Explicit decision | Required human action |
|---|---|
| `approve` | Accept the commentary; do not supply correction or item IDs. |
| `correct` | Supply valid corrected commentary through the existing correction fields, not replacement financial numbers. |
| `partial` | Select 1-8 distinct existing Worker item IDs, not invented IDs; no corrected output. |
| `reject` | Supply a nonblank reason in notes; no correction or item IDs. |

The name is self-declared, not authenticated identity. The protected token binds
the workflow and preview, expires after two hours, and is invalidated by a
backend restart because protection is ephemeral. Missing/tampered/expired or
wrong-workflow tokens return 403. A changed source snapshot returns 409 at start
or decision: obtain a fresh preview and a new workflow; never reuse old approval
for changed data. An already-decided workflow also requires status inspection.
Requests are bounded to 16 KiB; shared-service responses to 256 KiB with a
10-second per-request deadline. Model stages can take longer asynchronously.

## Local Startup

Run the following in separate PowerShell terminals from the repository root.
Prerequisites: Docker Desktop, existing native Ollama on 11434, configured local
models, .NET, and the existing Python environment with Multi-Agent requirements.
These commands are instructions, not additional execution evidence.

Terminal A, keep the one shared native Multi-Agent process running:

```powershell
$multiAgentPython = (Resolve-Path ./ai-services/venv-mcp/Scripts/python.exe).Path
./scripts/deploy/start-multi-agent.ps1 -Python $multiAgentPython -Port 15600
```

Resolve Python first: the helper changes directory before invoking it, so the
relative interpreter argument would break. It binds `127.0.0.1:15600`; 5600
failed with Windows bind error 13 on the recorded host. The backend container
reaches it through `http://host.docker.internal:15600`. Keep this trusted-local
service private; do not expose it publicly or add it to Compose.

Terminal B, deliberately start only Student 4 and the existing shared gateway:

```powershell
$env:STUDENT4_MULTI_AGENT_ENABLED = 'true'
$env:MULTI_AGENT_SERVER_URL = 'http://host.docker.internal:15600'
docker compose up --detach --no-deps --build --wait student4-database student4-backend student4-frontend shared-frontend
```

Open `http://localhost:5100/budget/`. This is four containers, not evidence that
all 16 application services or all Release 1 native integrations are healthy.
Current MCP/RAG modes are false; their earlier evidence is historical.
The backend's strict `MULTI_AGENT_ENABLED` defaults to false and appears as
`multiAgentEnabled` in `/api/capabilities` (`/budget-api/capabilities` at gateway).
Compose maps `STUDENT4_MULTI_AGENT_ENABLED` to that backend flag, default false;
`MULTI_AGENT_SERVER_URL` is the shared URL variable. Flags accept lowercase
`true`/`false` only.

For the full-group demonstration, coordinate the retained native MCP/RAG startup
with their owner using the [existing team startup guide](../../scripts/README.md).
Keep Terminal A running and the two Multi-Agent environment values above in
Terminal B. Use the team's existing full-stack entry point, not the subset:

```powershell
$env:STUDENT4_AI_ENABLED = 'true'
$env:STUDENT4_MCP_ENABLED = 'true'
$env:STUDENT4_RAG_ENABLED = 'true'
./scripts/deploy/start-release1.ps1
```

The helper refreshes native MCP/RAG and starts the full Compose application;
coordinate this lifecycle with their owner. Retain the native shared agentic
loop too. Full-group health and live R0/R1 acceptance need separate evidence.

## Demonstration

1. Open the supported gateway route and choose `Europe Escape`. Record the
   original dashboard; do not edit saved budgets or expenses for this demo.
2. In **What-If planner**, keep every category present. Change accommodation
   from EUR 1500 to EUR 1600, then select **Preview**. The recorded fixture
   changes planned EUR 3750 to EUR 3850 (+100), keeps actual EUR 4126.85,
   and changes remaining from EUR -376.85 to EUR -276.85. Inspect before/after
   category percentages and statuses; these are not model-authored numbers.
3. Select **Request agent review** once. Allow roughly 1-3 minutes on this local
   model setup, not a guaranteed SLA. Inspect the Planner, Worker, Reviewer,
   findings and history. Reviewer concerns remain visible to the human. Compare
   every monetary claim with the deterministic table: the recorded model runs
   include inaccurate commentary even after clearer currency evidence. They are
   useful correction/rejection examples, not evidence that the advice is true.
4. At `awaiting_human_review`, the actual reviewer chooses a genuine explicit
   decision, enters their own name and notes, and supplies correction/selection
   only where applicable. Use one real decision per workflow, not four invented
   approvals to imitate test coverage. Approval accepts commentary only.
5. Refresh the original dashboard and saved lists: original budgets and actuals
   must remain unchanged, including after approval. Preserve genuine workflow
   history and the human decision as evidence; never publish the token.
6. Set a proposed limit to zero and show validation/error handling, then restore
   the valid proposal. Use **Stop polling** and **Retry status** on an active
   workflow; stopping checks does not cancel the native workflow. Inspect network
   requests to confirm retries use GET for the same ID, not another start POST.

If a start/decision request times out, it may already have applied. Poll the
known ID/token first. A start error may include an accepted ID/token: retain
them privately. If no ID was returned, inspect shared workflow history before
starting again. Do not automatically repeat a POST. After token expiry/restart,
inspect the existing history before deliberately creating a replacement.

## Disabled Baseline

The required cloud baseline has `AI_ENABLED`, `MCP_ENABLED`, `RAG_ENABLED` and
`MULTI_AGENT_ENABLED` false. For a Student 4 **local rehearsal** of that behavior,
run in Terminal B; this changes the local backend mode, not a cloud deployment:

```powershell
$env:STUDENT4_AI_ENABLED = 'false'
$env:STUDENT4_MCP_ENABLED = 'false'
$env:STUDENT4_RAG_ENABLED = 'false'
$env:STUDENT4_MULTI_AGENT_ENABLED = 'false'
docker compose up --detach --no-deps --wait student4-backend
```

Refresh capabilities: deterministic preview and core CRUD remain usable, and
agent review is disabled in the UI; a direct workflow start returns 503
`feature_disabled`. Recreating the backend invalidates old workflow tokens.
Restore the required local flags before a later native-AI demo. Existing shared
cloud deployment tooling was reused and Student 4 smoke coverage updated for
all four flags and preview without financial writes. No live cloud deployment,
credentials access or provisioning is evidenced here.

## Report Reviews

The existing shared loop supports the following commands from repository root,
with its configured distinct implementer/reviewer models and native Ollama.
All three modes produced pending records linked from the validation record.
Their model ACCEPT verdicts are not human approval and do not close missing CI,
cloud or human evidence. Attach actual later outputs and rerun before claiming
those requirements complete. Shells do not load Compose's `.env` automatically.

```powershell
$env:IMPLEMENTER_MODEL = 'qwen2.5-coder:7b'
$env:REVIEWER_MODEL = 'llama3.2:3b'
$env:OLLAMA_URL = 'http://127.0.0.1:11434'

dotnet run --project ai-services/agentic-loop -- review-multi-agent `
  --task 'Review Student 4 What-If workflow evidence and missing genuine human decision.' `
  --context student-4/docs/evidence/release-2/validation-2026-10-23.md `
  --context student-4/docs/release-2-runbook.md

dotnet run --project ai-services/agentic-loop -- review-testing `
  --task 'Review Student 4 security and endpoint-test evidence; distinguish local results from pending remote CI.' `
  --context student-4/docs/evidence/release-2/validation-2026-10-23.md `
  --context student-4/docs/release-2-runbook.md

dotnet run --project ai-services/agentic-loop -- review-cloud `
  --task 'Review Student 4 cloud baseline readiness; identify missing live deployment and workflow evidence.' `
  --context student-4/docs/evidence/release-2/validation-2026-10-23.md `
  --context student-4/docs/release-2-runbook.md
```

After actual human review and actual post-testing only, substitute real values
in this single template. The loop's Adapt decision is distinct from the four
What-If decisions. Do not invent a record, decision, test result or commit ID.

```powershell
dotnet run --project ai-services/agentic-loop -- finalise `
  --record '<actual generated record path>' `
  --decision '<actual allowed Adapt decision>' `
  --notes '<actual human review notes>' `
  --post-test-command '<command actually run>' `
  --post-test-result '<result actually observed>'
```

## Repeatable Checks

These are manual rerun instructions, not checks performed by this documentation
pass. The two endpoint functions match the explicit filter in
[Student 4 CI](../../.github/workflows/student-4.yml).

```powershell
dotnet test student-4/backend/tests/Backend.Tests.csproj --filter FullyQualifiedName~CalculationTests
dotnet test student-4/backend/tests/Backend.Tests.csproj --filter 'FullyQualifiedName~EndpointTests.WhatIfPreviewUsesCurrentActualsAndDoesNotMutateSource|FullyQualifiedName~EndpointTests.WhatIfStartPollAndAllHumanDecisionsArePreviewOnly'
dotnet test student-4/backend/tests/Backend.Tests.csproj
npm.cmd test --prefix student-4/frontend -- --run
npm.cmd run build --prefix student-4/frontend
docker compose config --quiet
docker compose build student4-database student4-backend student4-frontend shared-frontend
dotnet list student-4/backend/Backend.csproj package --vulnerable --include-transitive
```