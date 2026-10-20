# Student 2 Release 2 Runbook

## Scope

Student 2 reuses the native Multi-Agent Server from PR #112. **Plan review**
sends a saved itinerary through Planner, Worker and Reviewer, then records an
explicit human decision. It never edits trips or stops. Release 0/1 editing,
generation/fallback and advice remain separate.

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
$env:MULTI_AGENT_SERVER_URL = "http://host.docker.internal:5600"
docker compose up --build --detach
```

Open `http://localhost:5100/itinerary/`, select a saved trip and choose Plan review.
The browser calls only the backend. For containers, native services must bind to
an approved reachable private interface; set `LOCAL_AI_HOST` accordingly.
Check native `/health` **from the backend container** before model testing.
Do not expose the native server publicly or change firewall policy implicitly.
Run one server worker. Keep the workflow ID to reopen saved history.

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
- `POST /api/trips/{id}/multi-agent-workflows` accepts `{task}` and returns `202`.
- `GET /api/trips/{id}/multi-agent-workflows/{workflowId}` returns status/history.
- `POST .../{workflowId}/decision` records approve/correct/partial/reject.
- Evidence excludes traveller identity: trip overview, interests and up to 28
  stops. Notes are capped at 400 characters, with visible truncation/omissions.
  The snapshot fingerprint covers all stops. Task length is 3-500 characters.
- Changed/deleted trips make reviews historical; new decisions are blocked.
  Feature/trip association is an integrity check, not account authentication.
- HTTP calls have a ten-second timeout and bounded response size. No POST retries.
  The UI polls for up to twenty minutes; stopping polling does not cancel work.
  After an uncertain decision, read status before trying again.
- Reviewer degradation/failure stays visible. Human corrections retain automatic
  findings. Server restart marks interrupted runs failed; completed records persist.

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
Student 1/3/5 AI-off guards are pending work for their respective owners, not
included here. Do not accept the cloud baseline until they are implemented and tested.
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

## Evidence and remaining acceptance

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
Reproduce with `scripts\test\student2_multi_agent_live.py`; use synthetic data only.

**Pending:** container-to-native connectivity (LAN and WSL adapter probes timed
out; loopback forwarding was refused), genuine terminal/UI human decisions,
all-feature local AI demonstration, pushed CI, approved cloud deployment,
all-feature cloud CRUD/persistence, three live finalised report reviews, report
and showcase. No firewall changes, paid provisioning or approvals are inferred.
The app runs with existing local configuration; disabled capabilities do not
demonstrate enabled AI functionality. This is not a certified group release.
