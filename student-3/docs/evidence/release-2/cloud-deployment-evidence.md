# Student 3 cloud deployment evidence (Release 2)

Evidence digest for the Cloud Deployment Report Review. It records what exists and what does not; it does not certify a release.

## The deployment

| Item | Value | Source |
|---|---|---|
| Workflow | `.github/workflows/cloud-deployment.yml`, `workflow_dispatch` on `main` | `student-5/docs/evidence/release-2/cloud/02-cloud-run-39741981906-excerpt.txt` (shared run) |
| Run | 39741981906, conclusion **success**, 2026-10-22T07:39:13Z | same |
| Run URL | https://github.com/LucLeMoenic/Advanced-Software-Development-Project/actions/runs/39741981906 | same |
| Revision | `851bdd7f4a7bc455e751b020c05a977608989e3a` | same |
| Target | AWS Linux VM behind a Caddy TLS gateway, public URL https://asd-epic-assignment.duckdns.org | same; `04-public-url-readonly-check.txt` there |
| Full log | 2,848 lines, secrets masked by GitHub | `student-5/docs/evidence/release-2/cloud/01-cloud-run-39741981906-full-log.txt` |

This run is the group's shared baseline deployment, run by the cloud owner, not by Student 3. Student 3 did not deploy it.

## Steps of the run (from the excerpt)

Succeeded: "Require all CI for the deployed revision", "Prepare and validate cloud configuration", "Build immutable application images",
"Configure pinned SSH access", "Deploy to the approved Azure or AWS Linux VM", "Wait for public HTTPS readiness",
"Verify public gateway and Student 1 to 5 CRUD", "Retain deployment evidence".
Skipped: "Require protected AI credentials", "Package AI preparation without deployment", "Prepare private gateway credentials",
"Verify protected group CRUD and AI integrations". So this run deployed the **AI-off baseline**; no AI service was part of it.

## Student 3 in that run

The run's smoke output (`.../cloud/03-cloud-smoke.txt`) contains the line `PASS: Student 3 cloud profile and CRUD checks.`
The log line only says PASS. What `check_student3` asserts is in `scripts/deploy/smoke_cloud.py` on `main`: all four capability flags
false; at least ten attractions; `/recommend` answers from the deterministic fallback; MCP, RAG and Multi-Agent routes answer 503;
then attraction create, update, read-back, review create and read-back, and delete (in a `finally`) followed by a 404.
Offline tests for it exist (`scripts/test/test_cloud_smoke_student3.py`), and its mutations were checked
(`student-3/docs/evidence/release-2/cloud/02-ai-flag-mutation-check.txt`).

## Student 3 on the public URL, checked separately

`cloud/10-public-url-readonly-check.txt` (2026-10-22T14:05Z, GETs plus AI routes that refuse before any write or model call):
`/health` 200; `/attractions/` 200; `/attractions-api/capabilities` all four flags `false`; 12 attractions listed;
`/recommend` 200 with `"source": "fallback"`; `/mcp/tools` and `/mcp/invoke` 503 `mcp_disabled`; `/rag/ask` 503 `rag_disabled`;
`/agents/workflows` 503 `multi_agent_disabled`. This check wrote nothing.

## Later dispatches (after the successful run)

Four later runs of `cloud-deployment.yml` failed, three at "Require all CI for the deployed revision" and one at "Require protected AI
credentials" (`CLOUD_AUTH_USER` invalid); see `student-5/docs/evidence/release-2/cloud/10-later-cloud-dispatches.txt`.
Cloud AI services (the optional bonus) therefore have **no successful cloud run**.

## Not evidenced

- **Persistence across a redeploy on the VM.** `cloud/05-persistence-across-redeploy.txt` is a local proof of the mechanism and is labelled
  "NOT a cloud run".
- **Backup, restore and rollback on the VM.** The scripts exist with Linux tests (`cloud/08`, `cloud/09`) but have not been run on a VM.
- **Private backend and database boundaries, live.** Established by the generated bundle (internal network, only the gateway publishes
  ports) and offline tests, not by a probe from outside the VM.
- **The deployed Student 3 container environment** was not read (no VM access from Student 3).
- **TLS and header hardening live.** `scripts/deploy/validate_security.py` has not been run against the public URL by Student 3.
