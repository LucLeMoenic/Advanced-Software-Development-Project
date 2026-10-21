# Student 3 — Cloud Readiness Evidence (Release 2, Chunk 6)

Scope: Student 3's part of the group's cloud deployment. The deployment pipeline itself (`cloud-deployment.yml`,
`scripts/deploy/prepare_cloud.py`, `deploy-vm.sh`, `assert-cloud-ci.ps1`, the Caddy gateway) was built by teammates and is reused,
not rebuilt. **Nothing here is a real cloud deployment**: no Azure or AWS resource was created or contacted. Everything marked
"proven" was run locally against the real services with the exact environment the cloud bundle applies.

## What the audit of the existing pipeline found

Good (reused as is): a same-revision CI gate that requires all six CI workflows to have succeeded for the deployed commit; an
immutable bundle with every AI flag forced to `false` and every AI URL pointed at an unreachable address; backends and databases on an
`internal: true` network with only the Caddy TLS gateway public; per-student bind-mounted data under `/opt/asd/data/student-N`;
image checksums; pinned SSH host keys; and a public HTTPS smoke test.

Gaps for Student 3 (fixed in this chunk):

| Gap | Fix |
|---|---|
| Student 3 had no explicit AI-Mode switch. The bundle sets `AI_ENABLED=false`, but the backend ignored it and always tried Ollama, relying on an unreachable URL to fall back. | `AI_ENABLED` flag in `recommend.py` (default `true`, unchanged locally). When off, `/api/recommend` answers from the catalogue and makes **no model call**. |
| Students 1 and 2 expose `/api/capabilities`, which the smoke test asserts. Student 3 did not. | New `GET /api/capabilities` returning `aiEnabled`, `mcpEnabled`, `ragEnabled`, `multiAgentEnabled`. |
| The cloud smoke test only loaded the `/attractions/` page. Student 3 CRUD was never exercised against a deployment. | `check_student3` in `scripts/deploy/smoke_cloud.py`: capabilities all off, seeded data, deterministic recommendation, MCP/RAG/Multi-Agent routes return 503, attraction create/update/readback/delete and review create/readback, cleanup in `finally`. |
| Users could not tell AI-Mode was off. | The "Ask the AI" panel states it when `aiEnabled` is false. |
| `student-3.yml` did not assert the baseline. | New step asserts all four capabilities are false and the recommendation is a deterministic fallback. |

## Results

| Evidence | Result |
|---|---|
| `cloud/01-live-student3-cloud-smoke.txt` | `check_student3` against the **real** Student 3 services behind the **real** shared gateway, started with the bundle's environment: 13 requests, all as expected, exit 0 |
| `cloud/02-ai-flag-mutation-check.txt` | Seven injected bugs (switch ignored, wrong default, hard-coded capabilities, empty fallback and others); all fail the suite |
| `cloud/03-ai-mode-disabled-ui.png`, `04-multi-agent-disabled-ui.png` | The disabled states in the browser through the gateway |
| `cloud/05-persistence-across-redeploy.txt` | A record survives a full teardown and redeploy; the re-run seeder adds no duplicates (local proof of the mechanism, not a cloud run) |
| Tests | Student 3 146/146 (16 new); the teammates' cloud tests and my 7 new smoke tests pass (22 together); Ruff clean |
| `prepare_cloud.py` on the modified Compose file | Still prepares all 18 services; Student 3's backend gets `AI_ENABLED`, `MCP_ENABLED`, `RAG_ENABLED`, `MULTI_AGENT_ENABLED` = `false` and AI URLs = `http://127.0.0.1:9`, no published ports, internal network only |
| `cloud/06-live-student4-student5-cloud-smoke.txt` | `check_student4` (16 requests) and `check_student5` (7 requests) against the real stacks behind the real gateway with the cloud environment: all as expected |
| `cloud/07-student4-student5-smoke-mutation-check.txt` | 12 injected bugs in the new smoke sections; all fail the suite (one test was weakened by my first draft and fixed: Student 5's AI routes now leak one at a time) |
| `cloud/08-vm-scripts-mutation-check.txt` | 15 injected bugs in the rollback, backup and restore scripts; all caught (one test fixed: it opened the database before checking for a stale WAL file) |
| `cloud/09-linux-test-run.txt` | The exact CI test command run on Linux: 67 passed |
| GitHub Actions | Green on `main` for the Chunk 6 merge (see `ci/04-github-actions-runs.md` for the earlier chunks); the Chunk 7 run is added to that file after the PR |

## Not proven, and risks for the group

These are outside Student 3's files and I have not been able to verify them:

1. **No real deployment has run.** `cloud-deployment.yml` is manual-dispatch only; the only completed "Cloud Deployment" runs on GitHub are from the old placeholder. Whether the repository variables and secrets it needs (`CLOUD_HOST`, `CLOUD_USER`, `CLOUD_DOMAIN`, `CLOUD_SSH_KEY`, `CLOUD_KNOWN_HOSTS`) are set cannot be seen from outside.
2. **Target platform.** The pipeline deploys over SSH to a pre-provisioned Linux VM ("approved Azure or AWS Linux VM"). Nothing in the repository provisions that VM. The brief lists Azure Container Apps / App Service or AWS ECS Fargate; confirm a VM-based deployment is acceptable, and consider adding infrastructure as code for the VM, network rules and Docker setup.
3. **Smoke coverage was extended to Students 4 and 5 (Chunk 7).** `check_student4` runs full budget and expense CRUD with cleanup and asserts every AI mode is off; `check_student5` is read-only plus AI-off assertions, because Student 5's API has no update or delete (a created row could never be cleaned up from the deployed database) and no explicit AI switch (its advisory endpoint answers `503` only because the bundle points the model URL at an unreachable address). Both were run against the real services behind the real gateway with the bundle's environment.
4. **Rollback, backup and restore now exist** (`rollback-vm.sh`, `backup-data.sh`, `restore-data.sh`) with 23 Linux tests and 15 mutation checks, but they have **not been run on a VM**, and `deploy-vm.sh` does not ship them (see `docs/release-2/cloud-validation-runbook.md`).
5. **The review step in the Multi-Agent panel has no authentication**, which matters if the Multi-Agent bonus is enabled in the cloud.
