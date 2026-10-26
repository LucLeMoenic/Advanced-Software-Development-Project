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

## Dispatches between the two successful runs

`cloud-deployment.yml` was dispatched nine more times after the baseline run and failed each time before the AI run succeeded:
four runs listed in `student-5/docs/evidence/release-2/cloud/10-later-cloud-dispatches.txt` (three stopped at "Require all CI for the
deployed revision", one at "Require protected AI credentials" because `CLOUD_AUTH_USER` was invalid) and five more
(39860759422, 39862262391, 39862608083, 39869072831, 39873301495) listed in `11-protected-ai-run-39893640923-excerpt.txt`, whose
failure causes are not in the evidence files reviewed here.

## The protected AI run (optional bonus B1 to B4)

| Item | Value | Source |
|---|---|---|
| Run | 39893640923, `workflow_dispatch`, conclusion **success**, created 2026-10-23T03:11:08Z | `student-5/docs/evidence/release-2/cloud/11-protected-ai-run-39893640923-excerpt.txt` |
| Revision | `4c1e71acd34793ca5a7a2171c64c3d73dbaf137d` | same |
| Run URL | https://github.com/LucLeMoenic/Advanced-Software-Development-Project/actions/runs/39893640923 | same (the run number is listed there; the URL follows the baseline run's pattern) |
| Mode | `DEPLOY_MODE: ai`, `CLOUD_AI_SERVICES: ai,mcp,rag,multi-agent`; "Prepared 22 cloud services" | same |
| CI gate | Student 5 CI on main for that revision passed before deployment | same |
| Gateway | "PASS: anonymous access rejected at the gateway for every feature" | same |

Steps that succeeded include "Require protected AI credentials", the CI gate, "Deploy to the approved Azure or AWS Linux VM", "Wait
for public HTTPS readiness" and "Verify protected group CRUD and AI integrations". "Verify public gateway and Student 1 to 5 CRUD" was
skipped in this mode, and its checks ran inside the protected step instead.

Output of the protected step that concerns Student 3 and the shared AI services, from that excerpt:

- `PASS: Student 3 cloud profile and CRUD checks.` (the same `check_student3`, run with the AI components enabled)
- `PASS: capabilities match the enabled components: ai, mcp, multi-agent, rag`
- `PASS: B2 MCP: a tool call through the application returned real catalogue data`
- `PASS: B1 AI-Mode: the model answered through the application`
- `PASS: B3 RAG: a grounded answer with citations from retrieved context`
- `PASS: B4 Multi-Agent: Planner, Worker and Reviewer reached human review; decision pending`, for the Student 3 workflow
  `wf-20261023T032459Z-f1ad495f`, with the line `MANUAL: ... no human approval has been submitted.`

So the optional cloud AI bonus has one successful cloud run. **The Student 3 cloud workflow is still waiting for a human decision**;
the workflow does not submit one. The excerpt shows the same pending-decision pattern for Students 1, 2 and 5.

## Student 3 on the AI deployment, checked with credentials (2026-10-26)

The read-only check of 2026-10-22 above describes the AI-off baseline, and the gateway has required authentication since the AI run.
`cloud/11-authenticated-readonly-check.txt` repeats it with the gateway credentials supplied by the project owner (not recorded), using GETs only:
anonymous `/attractions/` -> 401; with credentials `/health` 200 and `/attractions/` 200; `/attractions-api/capabilities`
`{"aiEnabled":true,"mcpEnabled":true,"multiAgentEnabled":true,"ragEnabled":true}`; `/mcp/tools` lists `attractions.search` and
`attractions.get_reviews`; `/agents/status` `ok` with `busy: true`; the Student 3 workflow `wf-20261023T032459Z-f1ad495f` is still
`awaiting_human_review`, `human_decision` empty, history planner, worker, reviewer, reviewer verdict `pass`, four items
(Mr. Wong, Chin Chin Melbourne, Chat Thai Sydney CBD, Queen Victoria Market).

Observation, cause not established: the deployed list now has **10** attractions, where the 2026-10-22 baseline check listed 12
(the page no longer shows Bondi to Coogee Coastal Walk or Federation Square). The cloud smoke test only requires at least ten.

`cloud/12-deployed-student3-page.png` is a screenshot of the deployed `/attractions/` page: the catalogue, the MCP tool selector
populated, and the Multi-Agent form enabled. It was taken through a local, GET-only proxy that adds the Basic-auth header. A first
attempt with the credentials in the URL showed "MCP service is offline" and "The Multi-Agent Server is offline"; that was an artefact of the
method, not the site: a browser's `fetch()` refuses relative URLs from a page whose address contains credentials, so those requests were
never sent (Chrome's network log showed no request for them). Through the proxy every request returned 200.

## Not evidenced

- **Persistence across a redeploy on the VM.** `cloud/05-persistence-across-redeploy.txt` is a local proof of the mechanism and is labelled
  "NOT a cloud run".
- **Backup, restore and rollback on the VM.** The scripts exist with Linux tests (`cloud/08`, `cloud/09`) but have not been run on a VM.
- **Private backend and database boundaries, live.** Established by the generated bundle (internal network, only the gateway publishes
  ports) and offline tests, not by a probe from outside the VM.
- **The deployed Student 3 container environment** was not read (no VM access from Student 3).
- **TLS and header hardening live.** `scripts/deploy/validate_security.py` has not been run against the public URL by Student 3.
