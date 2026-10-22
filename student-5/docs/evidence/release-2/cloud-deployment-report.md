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

## Cloud run (to be completed after merge)

| Item | Value |
|---|---|
| `cloud-deployment.yml` run | _TODO: run link_ |
| Deployed revision | _TODO: commit SHA from `revision.txt`_ |
| Public URL | _TODO: `https://<CLOUD_DOMAIN>/logistics/`_ |
| Smoke output | _TODO: Student 5 PASS line from `cloud-smoke.txt` in the `cloud-deployment-<sha>` artifact_ |
| Screenshot: Student 5 page on the public URL | _TODO: `cloud/01-logistics-page.png`_ |
| Screenshot: advisory panel showing "AI disabled" | _TODO: `cloud/02-advisory-disabled.png`_ |
| Screenshot: workflow run with the smoke step green | _TODO: `cloud/03-workflow-run.png`_ |

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
