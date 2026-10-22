# Student 2 Release 2 Runbook

## Scope

Student 2 reuses the native Multi-Agent Server from PR #112. **Edit assessment**
sends the existing editor's exact MCP preview and saved-trip evidence through
Planner, Worker and Reviewer, then records an explicit assessment decision.
Only a separate confirmation applies the bound preview. Generation/fallback,
manual CRUD and RAG Advice remain unchanged. With Multi-Agent disabled, the
Release 1 editor continues without agent assessment.

See the [spec mapping](release-2-plan.md). Small shared-server changes handle
interrupted runs, serialize decisions in one worker and constrain Worker subjects
to evidence titles. No second agent system or database table is introduced.

## Local operation

Use the [Release 1 runbook](release-1-runbook.md) for Ollama, MCP and RAG.
Install the shared Multi-Agent requirements in a native Python environment, load
`llama3.2:3b` in Ollama, then run from the repository root:

```powershell
.\scripts\deploy\start-multi-agent.ps1 -Python <python-executable> -NativeHost 127.0.0.1
$env:MULTI_AGENT_ENABLED = "true"
$env:AI_ENABLED = "true"
$env:MCP_ENABLED = "true"
$env:MULTI_AGENT_SERVER_URL = "http://host.docker.internal:5600"
docker compose up --build --detach
```

Open `http://localhost:5100/itinerary/`, select a saved trip and choose Edit.
Request a change, inspect the exact preview and wait for its inline assessment.
Approve, correct, accept selected assessment items or reject. These decisions
concern assessment text, not executable edits: partial acceptance never applies
only some changes. To change the proposed operation, cancel and request a new
preview/assessment. After accepting the assessment, explicitly confirm the
whole preview to save it. An accepted assessment is not proof that saving succeeded.
The browser calls only the backend. For containers, native services must bind to
an approved reachable private interface; set `LOCAL_AI_HOST` accordingly.
Check native `/health` **from the backend container** before model testing.
Do not expose the native server publicly or change firewall policy implicitly.
Run one server worker. Keep the workflow ID to reopen saved history via the CLI
or backend GET route. Cancelling the preview does not cancel native agent work.

On this Podman host, the legacy Docker root-context build stalls. Use:

```powershell
podman build --format docker --ignorefile student-2\backend\Dockerfile.dockerignore `
  -f student-2\backend\Dockerfile `
  -t docker.io/library/advanced-software-development-project-student2-backend .
docker compose build student2-frontend
docker compose up -d --no-build --wait
```

## API and limits

- `GET /api/capabilities` adds `multiAgentEnabled`, default false.
- `POST /api/trips/{id}/edit-preview` accepts `{question}` (1-1000 characters).
  When enabled, it starts assessment and returns `preview.workflowId` with the
  existing signed preview. Clarification responses do not start agents.
  `edit-operation-preview` likewise assesses validated reorder/undo previews.
  The standalone workflow-creation route is removed.
- `GET /api/trips/{id}/multi-agent-workflows/{workflowId}` returns status/history.
- `POST .../{workflowId}/decision` records approve/correct/partial/reject.
- `POST /api/trips/{id}/edit-confirm` requires `{token, workflowId}` when enabled:
  the workflow must be accepted, belong to this trip and contain the exact token
  hash. Otherwise it keeps the Release 1 `{token}` contract. A workflow can stay
  approved even if saving fails; the database response determines save success.
- Evidence excludes traveller identity: trip overview, interests and up to 28
  stops, reduced to reserve space for the full request and proposed changes.
  Candidate text is split into labelled parts of at most 800 characters, within
  30 evidence entries. Oversized edits fail explicitly; request a smaller edit
  or use manual CRUD. Saved context notes are capped at 400 characters, with
  visible truncation/omissions. The snapshot fingerprint covers all stops.
  The signed token is not sent to the model, only its SHA-256 hash.
- Changed/deleted trips make reviews historical; new decisions are blocked.
  Feature/trip association is an integrity check, not account authentication.
- Signed preview expiry remains ten minutes, including agent processing time.
  Expired previews require a new preview/assessment; never reuse approval for
  another token. Database revision/expiry and atomic application remain authoritative.
- HTTP calls have a ten-second timeout and bounded response size. No POST retries.
  The UI polls for up to twenty minutes; stopping polling does not cancel work.
  After an uncertain decision, read status before trying again.
- Reviewer degradation/failure stays visible. Human corrections retain automatic
  findings. Server restart marks interrupted runs failed; completed records persist.

### Terminal parity

Start an edit using the same backend route, then inspect/decide using the shared
CLI (set `MULTI_AGENT_SERVER_URL` to the native loopback URL for CLI use):

```powershell
$preview = Invoke-RestMethod http://localhost:5202/api/trips/1/edit-preview `
  -Method Post -ContentType application/json -Body '{"question":"Swap days 1 and 2"}'
$id = $preview.preview.workflowId
python ai-services\multi-agent-server\cli.py show $id
python ai-services\multi-agent-server\cli.py review $id
python ai-services\multi-agent-server\cli.py audit $id
python ai-services\multi-agent-server\cli.py verify
```

Wait for `awaiting_human_review` before the interactive review. CLI decisions
record assessment only; they do not save edits. Retain the preview token locally
and explicitly confirm it through the backend if desired, while still valid.
Use only synthetic trips for developer checks; do not claim automated decisions
as genuine human showcase evidence.

## Tests and reviews

```powershell
cd student-2\backend
python -m pytest tests -q
cd ..\database
python -m pytest tests -q
cd ..\..
npm test --prefix student-2\frontend
npm run build --prefix student-2\frontend
dotnet test ai-services\agentic-loop\tests
python -m pytest scripts\test\test_cloud_config.py -q
.\scripts\test\cloud-ci.ps1
python -m pre_commit run --all-files
```

Run the shared Multi-Agent suite from its own directory. Separate Python suites
avoid collisions between the features' `app.py` modules. Student 2 CI publishes
explicit POST create-trip / PUT update-trip results, plus existing regressions.
The dependency hook only audits changed requirements; use the
[existing audit runner](../../scripts/security/README.md) for release-wide evidence.

`review-multi-agent`, `review-testing` and `review-cloud` use the loop's existing
`--context` input and human `finalise` command. See the
[shared loop README](../../ai-services/agentic-loop/README.md#release-2-report-reviews).
Supply ordinary reports and actual evidence files, including revision and CI URLs.
No custom JSON manifest is needed. Missing/failed evidence is not a release pass;
the review modes do not execute tests or deploy anything.

## Cloud baseline

The [workflow](../../.github/workflows/cloud-deployment.yml) runs manually on
`main`, in the protected `production` environment, only after all six required CI
workflows succeed for that SHA. Root Compose changes trigger all six workflows.
For other revisions, arrange missing runs before deployment; missing is not passed.

The [bundle builder](../../scripts/deploy/prepare_cloud.py) derives the integrated
Compose services, tags images by SHA, keeps backend/database ports private,
disables all four AI modes and uses persistent `/opt/asd/data/student-N` storage.
Student 1/3/5 AI-off guards have since merged under their respective owners.
Their presence is not a substitute for running the full integrated cloud smoke.
Caddy provides the shared HTTPS entry point; native AI services are not deployed.

Operator prerequisites: an approved **Azure or AWS Linux VM**, budget, DNS,
Docker/Compose, Python 3, and a restricted deployment account with Docker access
and write access to `/opt/asd`. Docker access is privileged. Configure production
variables `CLOUD_HOST`, `CLOUD_USER`, `CLOUD_DOMAIN` and secrets `CLOUD_SSH_KEY`,
`CLOUD_KNOWN_HOSTS` using a verified host key. Restrict SSH to approved sources.
These scripts do not provision infrastructure or choose the group's cloud account.

Deployment transfers checksummed images/configuration over pinned SSH, runs
[the VM script](../../scripts/deploy/deploy-vm.sh) and
[gateway/Student 2 CRUD smoke checks](../../scripts/deploy/smoke_cloud.py).
Before manual rollback, back up databases and check schema compatibility.
Use the previous release's Compose file with project `asd-cloud`; image rollback
does not restore data. All-feature CRUD and redeploy persistence need live evidence.

### Student 2 deployment preparation - 22 October 2026

- Backend and database now use pinned Waitress 3.0.2 with their existing
  `python app.py` entry points and `PORT` configuration. One process per service
  preserves the database's process-local preview signing key; threaded requests
  retain concurrent health/CRUD handling. A database container replacement
  invalidates outstanding edit previews by design, but not saved trips or stops.
- Flask 3.1.3 and requests 2.33.0 replace the vulnerable pins documented in the
  audit policy. Student 2's accepted exceptions were removed; both complete
  requirement sets passed the existing pip-audit runner with no known findings.
- Student 2 CI now starts the actual shared gateway and runs the existing
  disabled-mode/CRUD/regeneration smoke through `/itinerary-api/` on port 5100.
  The persistence check replaces the database container with `--force-recreate`
  while keeping its storage, rather than merely restarting the same container.
  Cloud smoke script changes now trigger Student 2 CI.
- Local validation: backend 257 passed/11 opt-in live skips; database 39 passed;
  frontend 45 passed and production build; cloud configuration 6 passed.
  All four images built. A disposable four-service stack derived from the cloud
  configuration passed the gateway smoke, including every disabled AI route
  checked by the script, fallback generation, trip/stop CRUD, regeneration and
  exact saved-itinerary equality after database container replacement.
  Both live Python services returned the `waitress` server header.
- Browser check through `/itinerary/`: created a four-stop fallback itinerary,
  updated its budget, verified Edit/Advice controls were disabled, and confirmed
  deletion. API readback returned 404 and the original ten seeded trips remained.
  The hidden browser's normal click stability wait stalled, so DOM-driven
  interactions were used; this is not a keyboard/responsive acceptance test.
- The disposable stack used a separate named volume and loopback port 55102,
  without touching the existing integrated app or its databases. It validates
  Student 2 plus the real shared gateway, not other students, public TLS, cloud
  access controls or a full group deployment. Native AI services were not used.
- Scoped Ruff security, detect-secrets and pip-audit hooks passed. On this
  Windows host the existing virtual environment must be on `PATH` for the
  hook's `python` command; the initial run hit the Microsoft Store alias and
  passed after correcting the command environment.

For a deployed group stack, use the full
[`smoke_cloud.py`](../../scripts/deploy/smoke_cloud.py) against its public HTTPS
origin. The Student 2 PowerShell `-Smoke` check also **replaces the database
container**, so run it only against an explicitly selected disposable/test
Compose project or during an approved maintenance window.

## Evidence and remaining acceptance

22 October: captured fresh tests/scans and live Testing/Multi-Agent reviews;
both await human finalisation. Cloud review failed output validation twice;
the inspected green cloud run was only a placeholder. See the
[review notes and records](review-record.md) and
[evidence report](evidence/release-2/review-input-20261022.txt).

21 October inline-edit validation: backend suites total 257 passed/11 opt-in
live skips, frontend 45 passed plus production build, Ruff and whitespace checks
passed. An isolated native browser/CLI developer test completed all three real
agent stages for an undo preview (`wf-20261021T031345Z-b9269ae2`), returned
non-degraded Reviewer `concerns`, recorded a labelled automated-test approval,
and saved only after separate browser confirmation. CLI audit verification
reported 10 valid entries. The synthetic database was separate from user data.
Natural-language edit generation timed out at the existing 20-second model
deadline twice, including after preload; that live path remains an acceptance
limitation, not a successful demonstration. The workflow store is retained in
the development session, not committed as human acceptance evidence.

Historical local results from 20 October: backend 238 passed/11 opt-in live skips,
database 39, frontend 40 plus build, Multi-Agent 64, cloud config 6;
Student 1 search tests 25, Student 3 targeted tests 9, Student 5 backend 127.
Those historical counts included AI-off tests removed on 21 October when the
user returned ownership of these changes to the respective students.
Shared loop now passes 95 tests after replacing manifest-specific tests with
context-mode tests. On 21 October, backend/frontend/server/cloud suites and the
frontend build, CI gate, Ruff and secret checks passed again. Dependency policy previously passed with existing
exceptions (backend four ignored advisories, database two, shared server none).

The [native-only capture](evidence/release-2/native-quality-rerun.json) records
Reviewer `pass`, unchanged trip and a verified audit. The first run failed because
Worker subjects did not match evidence titles; the schema constraint fixed the
observed case. Its raw failed capture is archived in the session, not duplicated
in this change. The retained capture's audit is workflow-filtered, not a standalone
full audit chain. Ten baseline entries are checked audit hashes, not credentials.
Neither run submitted a human decision or proves integrated browser acceptance.
That capture predates inline edit assessment. The updated
`scripts\test\student2_multi_agent_live.py --trip-id <id> --question "<edit>" --output <path>`
now checks edit assessment through native MCP/Ollama/Multi-Agent dependencies;
use synthetic data only. It does not decide or save.

The merged Student 2 baseline passed main CI run
[`39694482270`](https://github.com/LucLeMoenic/Advanced-Software-Development-Project/actions/runs/39694482270).
The 22 October deployment-preparation changes above are locally validated;
they still need their own pushed CI run.

**Pending for full Release 2 acceptance:** container-to-native connectivity (LAN and WSL adapter probes timed
out; loopback forwarding was refused), genuine terminal/UI human decisions,
all-feature local AI demonstration, approved cloud deployment,
all-feature cloud CRUD/persistence, current-evidence human finalisation of the
Student 2 testing/Multi-Agent reviews, a successful cloud review, complete group
review coverage, report and showcase. Student 3 already has finalised testing
and Multi-Agent records; these do not cover Student 2 or certify the group.
No firewall changes, paid provisioning or approvals are inferred.
The app runs with existing local configuration; disabled capabilities do not
demonstrate enabled AI functionality. This is not a certified group release.
