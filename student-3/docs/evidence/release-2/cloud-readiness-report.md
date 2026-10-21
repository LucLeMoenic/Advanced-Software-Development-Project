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
| GitHub Actions | **TODO**: run URL after this PR (the `student-3.yml` baseline step is new) |

## Not proven, and risks for the group

These are outside Student 3's files and I have not been able to verify them:

1. **No real deployment has run.** `cloud-deployment.yml` is manual-dispatch only; the only completed "Cloud Deployment" runs on GitHub are from the old placeholder. Whether the repository variables and secrets it needs (`CLOUD_HOST`, `CLOUD_USER`, `CLOUD_DOMAIN`, `CLOUD_SSH_KEY`, `CLOUD_KNOWN_HOSTS`) are set cannot be seen from outside.
2. **Target platform.** The pipeline deploys over SSH to a pre-provisioned Linux VM ("approved Azure or AWS Linux VM"). Nothing in the repository provisions that VM. The brief lists Azure Container Apps / App Service or AWS ECS Fargate; confirm a VM-based deployment is acceptable, and consider adding infrastructure as code for the VM, network rules and Docker setup.
3. **The smoke test still skips Students 4 and 5.** It now covers Students 1, 2 and 3; the rubric asks for the integrated application's required CRUD.
4. **Rollback and backup/restore** are not evidenced (`deploy-vm.sh` records the previous release, but nothing exercises a rollback).
5. **The review step in the Multi-Agent panel has no authentication**, which matters if the Multi-Agent bonus is enabled in the cloud.
