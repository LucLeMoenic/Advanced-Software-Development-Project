# Student 5 - Cloud Deployment Report (Release 2)

Workflow: `.github/workflows/cloud-deployment.yml` (shared, cloud owner) · Check:
`check_student5` in `scripts/deploy/smoke_cloud.py` · Test:
`scripts/test/test_cloud_smoke_student5.py` · Plan: Chunk 5 in
[`release-2-plan.md`](../../release-2-plan.md)

## Student 5 cloud smoke check

After `deploy-vm.sh` starts the bundle, the workflow step "Verify public gateway and
Student 1 and 2 CRUD" runs `python scripts/deploy/smoke_cloud.py
"https://$CLOUD_DOMAIN"`. That runs every student's check, including Student 5's,
and saves the output as `cloud-smoke.txt` in the `cloud-deployment-<sha>` artifact.
Every Student 5 call goes through the public gateway:

`Caddy (TLS) -> shared-frontend /logistics/* -> student5-frontend /api/* -> student5-backend -> student5-database`

| Step | Request (under `/logistics/api`) | Pass condition |
|---|---|---|
| Seed data | `GET /destinations`, `/weather-notes`, `/transit-options` | At least 10 destinations. Both reference tables are non-empty. |
| AI-Mode off | `POST /advisory` | `503 {"error": "ai_disabled"}` |
| MCP off | `GET /mcp/tools` | `503 {"error": "mcp_disabled"}` |
| RAG off | `POST /rag/ask` | `503 {"error": "rag_disabled"}` |
| Multi-Agent off | `POST /destinations/<seeded id>/readiness-reviews` | `503 {"error": "multi_agent_disabled"}` |
| Create | `POST /destinations` with country `R2 smoke <8 hex>` | `201` |
| Read | `GET /destinations/<id>` | `200`, same country |
| Update | `PUT /destinations/<id>` (new `visa_requirement`, notes) | `200` |
| Read the change | `GET /destinations/<id>` | `200`, new `visa_requirement`, country kept |
| Delete | `DELETE /destinations/<id>` | `204`, in a `finally`, so it also runs when a step after the create fails |
| Gone | `GET /destinations/<id>` | `404` |

Design choices:

- **The error body is checked, not only the `503`.** A backend that is down also
  answers `503` through the gateway. Only the named error shows that the switch is
  off.
- **The AI routes are checked before the create.** If a deployment has AI enabled,
  the check fails without writing a row.
- **Multi-Agent is included.** The brief requires all four AI services off in the
  baseline (TL-NFR-10), not only the three named in the plan.

Release 2 replaces the earlier read-only Student 5 check (PR #130). That check
assumed Student 5 had no update or delete. In fact `PUT` and `DELETE` have existed
on every Student 5 table since Release 0.

## Offline test

`scripts/test/test_cloud_smoke_student5.py` (18 tests) uses a stateful fake
gateway, like Student 1's test. It covers:

- the happy path: the row is deleted, the last call is the `404` readback, and all
  four AI refusals come before the create;
- too few seeded destinations, and empty weather or transit data;
- each AI route answering `200` on its own (4 cases): the check fails and no
  destination is created;
- each AI route answering `503` without its disabled body (4 cases);
- five failure points after the create, each of which must still delete the row: a
  lost update, a dropped country, a wrong country at readback, and a `500` on the
  readback or on the update;
- a deleted row that is still readable.

Result: `18 passed`. All of `scripts/test` gives 229 passed, 58 skipped (the
skipped tests need Linux symlink semantics). A mutation check removed each key
assertion in turn and every removal was caught: create readback (1 failing test),
country kept (1), disabled body (4), cleanup in `finally` (5), and the `404` after
delete (2).

## Local run (22 October 2026)

`student5-backend` was recreated with `AI_ENABLED`, `MCP_ENABLED`, `RAG_ENABLED`
and `MULTI_AGENT_ENABLED` set to `false` as shell overrides, and `env` in the
container showed all four `false`. `.env` was not edited. The real `check_student5`
was then called against the local gateway (`http://localhost:5100`) through a
harness that uses the same `call()` logic as `run()`. The HTTPS-only origin check
was left out because there is no local TLS.

```text
# check_student5 against http://localhost:5100, 2026-10-22T01:45:48Z
  ok  GET    /logistics/api/destinations                          -> 200 (expected 200)     61 ms
  ok  GET    /logistics/api/weather-notes                         -> 200 (expected 200)     24 ms
  ok  GET    /logistics/api/transit-options                       -> 200 (expected 200)     22 ms
  ok  POST   /logistics/api/advisory                              -> 503 (expected 503)      7 ms
        body: {"error": "ai_disabled", "message": "AI-Mode is disabled."}
  ok  GET    /logistics/api/mcp/tools                             -> 503 (expected 503)      6 ms
        body: {"error": "mcp_disabled", "message": "MCP is disabled."}
  ok  POST   /logistics/api/rag/ask                               -> 503 (expected 503)      6 ms
        body: {"error": "rag_disabled", "message": "RAG is disabled."}
  ok  POST   /logistics/api/destinations/1/readiness-reviews      -> 503 (expected 503)     21 ms
        body: {"error": "multi_agent_disabled", "message": "Multi-Agent is disabled."}
  ok  POST   /logistics/api/destinations                          -> 201 (expected 201)     61 ms
  ok  GET    /logistics/api/destinations/16                       -> 200 (expected 200)     24 ms
  ok  PUT    /logistics/api/destinations/16                       -> 200 (expected 200)     67 ms
  ok  GET    /logistics/api/destinations/16                       -> 200 (expected 200)     25 ms
  ok  DELETE /logistics/api/destinations/16                       -> 204 (expected 204)     53 ms
  ok  GET    /logistics/api/destinations/16                       -> 404 (expected 404)     21 ms
PASS: Student 5 AI modes disabled; reference data served; destination CRUD.
exit=0
```

Results:

- After the run, 12 destinations were listed and none was an `R2 smoke` row.
- All four refusals took 6-21 ms, inside the 1 s limit in TL-NFR-10.
- The backend was then restored from `.env` (AI-Mode, MCP and RAG `true`,
  Multi-Agent `false`) and the check was run again. It stopped at its first AI call:
  `POST /advisory` waited for the model and hit the 30 s client timeout. No
  destination was created (still 12).

This is local evidence only. It does not show the cloud deployment.

## Cloud run

Filled in on 22 October 2026 (Chunk 6) from `gh run view`, the run's artifact and a
read-only check of the public URL. Evidence files are in [`cloud/`](cloud/).

| Item | Value |
|---|---|
| `cloud-deployment.yml` run | [39741981906](https://github.com/LucLeMoenic/Advanced-Software-Development-Project/actions/runs/39741981906), `workflow_dispatch` on `main`, 2026-10-22 07:39 UTC, **success** (5 min 21 s) |
| Deployed revision | `851bdd7f4a7bc455e751b020c05a977608989e3a` (`revision.txt` in the artifact matches the run's head SHA) |
| CI gate | Step "Require all CI for the deployed revision" (`assert-cloud-ci.ps1 -Sha $GITHUB_SHA`): success |
| AI services | `prepare_cloud.py`: "Prepared 18 cloud services (AI disabled)". `ai-services.txt` is empty. The deployed `student5-backend` environment has `AI_ENABLED`, `MCP_ENABLED`, `RAG_ENABLED` and `MULTI_AGENT_ENABLED` all `false`, and every AI URL set to `http://127.0.0.1:9` (`cloud/02-cloud-run-39741981906-excerpt.txt`) |
| Smoke output | Step "Verify public gateway and Student 1 to 5 CRUD": success. `cloud-smoke.txt` from the artifact `cloud-baseline-evidence-851bdd7…`: `PASS: Student 5 cloud profile and CRUD checks.` (all five students `PASS`; `cloud/03-cloud-smoke.txt`) |
| Public URL | `https://asd-epic-assignment.duckdns.org/logistics/` (`CLOUD_DOMAIN` is a repository variable and is printed in the run log) |
| Live read-only check, 2026-10-22 10:12 UTC | `cloud/04-public-url-readonly-check.txt`: page `200`, 12 destinations, weather and transit `200`, then `ai_disabled`, `mcp_disabled`, `rag_disabled` and `multi_agent_disabled`, each `503` in 0.14-0.22 s. Nothing was written. |
| Screenshot: Student 5 page on the public URL | `cloud/05-public-logistics-page.jpg`: the page loaded with Japan selected in the trip form. The results row is squeezed to a sliver here (see the layout defect below); Japan's weather and entry records are visible in `06` and `07` |
| Screenshot: advisory panel showing "AI disabled" | `cloud/06-advisory-disabled.jpg`: "AI advisories are switched off for this deployment (AI-Mode is disabled)." |
| Screenshot: readiness review disabled | `cloud/07-multi-agent-disabled.jpg`: "Trip readiness reviews are switched off for this deployment (Multi-Agent is disabled)." |
| Screenshot: workflow run | `cloud/08-workflow-run-summary.jpg` (Success, `851bdd7`, `main`, one artifact) and `cloud/09-workflow-smoke-step.jpg` (the CI gate and the smoke step green, with all five `PASS` lines) |

Limits, stated as found:

- **The deployed revision is one commit behind `main`.** `457b247` (PR #144) followed
  `851bdd7` and changes no Student 5 file (`git diff --name-only 851bdd7 457b247`).
  Four later dispatches failed within about 20 s, before any deploy step, so the
  public URL still serves `851bdd7`. 39743453917 (`851bdd7`), 39744896831 and
  39745249227 (`457b247`) stopped at "Require all CI for the deployed revision".
  39747268117 (`457b247`) stopped at "Require protected AI credentials" with
  `Set CLOUD_AUTH_USER ...`, an attempt at the optional protected-AI (bonus)
  deployment. These belong to the cloud workflow owner. The run list, failed steps and error
  lines are in `cloud/10-later-cloud-dispatches.txt`.
  **Update, 23 October 2026:** run 39893640923 at `4c1e71a` has since deployed the
  protected AI mode, so the public URL no longer serves `851bdd7` and now asks for the
  gateway password. Student 5's checks passed in that run (`cloud/11`, `known-issues.md`).
- **Persistence and rollback are not shown here.** `cloud-smoke.txt` itself says
  "Persistence across redeploy and rollback require separate evidence". That belongs
  to the cloud workflow owner.
- **The page screenshots also show a layout defect.** On a short viewport (about 790 px
  high) the results row of the Student 5 page gets about 57 px, as in `05`. Collapsing the
  trip form, as in `06`, raises it to about 200 px, and the advisory still scrolls inside a
  small box. This is recorded in `known-issues.md`; it is not a cloud problem, and it
  happens locally too.
- **The screenshots are page captures without the browser's address bar.** The public URL
  is shown by the read-only check (`cloud/04`). The "switched off for this deployment"
  notices in `06` and `07` appear only where the AI flags are off, which locally they are not.
- **Erratum in `cloud/02-cloud-run-39741981906-excerpt.txt`.** Its header line says "Secrets
  (host, domain, credentials) are masked as *** by GitHub". That is wrong for the host and the
  domain: `CLOUD_HOST`, `CLOUD_USER` and `CLOUD_DOMAIN` are repository variables and are
  printed in clear in the run log. Credentials (`GH_TOKEN`, the SSH key, known hosts) are
  masked. The file is left unchanged because the `review-cloud` record stores its hash.

## Workflow dependencies (owner: cloud workflow owner)

`cloud-deployment.yml` needs no change for Student 5:

- `assert-cloud-ci.ps1` already requires a green "Student 5 CI" for the deployed SHA;
- `prepare_cloud.py` already sets all four flags `false` and the AI URLs to
  `127.0.0.1:9` on `student5-backend`, and rebinds `student5-database`'s single
  `/data` volume to `/opt/asd/data/student-5`;
- the smoke step runs the whole script, so the new check is picked up automatically.

One cosmetic point for the owner, not changed here: the step is still named "Verify
public gateway and Student 1 and 2 CRUD", but it now runs the checks for all five
students.
