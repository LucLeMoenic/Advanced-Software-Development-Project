# Cloud deployment and validation runbook (Release 2)

How to deploy the integrated application to the group's Azure or AWS Linux VM, prove it works, and capture the evidence
the rubric and the `review-cloud` loop mode need. Everything here follows the scripts in `scripts/deploy/` and
`.github/workflows/cloud-deployment.yml`; nothing is assumed beyond them.

**Status when this was written:** the pipeline and every check below were exercised locally and in offline tests, but
**no real cloud deployment has been run**. This runbook is the procedure for the first one. Fill in the evidence as you go.

## 1. One-time VM setup (needs the platform decision and a VM)

The deploy script (`deploy-vm.sh`) assumes a Linux VM that already exists. Nothing in the repository provisions it.

| Requirement | Why |
|---|---|
| Docker with the Compose plugin; the deploy user can run `docker` | `deploy-vm.sh` loads images and runs `docker compose` |
| `python3` | `backup-data.sh` and `restore-data.sh` use SQLite's backup API |
| `/opt/asd`, `/opt/asd/releases`, `/opt/asd/data` writable by the deploy user | `deploy-vm.sh` refuses to run otherwise |
| A DNS name pointing at the VM's public IP | Caddy obtains the TLS certificate for it |
| Inbound 80 and 443 open (and 22 from the runners or your IP) | Caddy uses both ports to obtain and serve the TLS certificate |
| Nothing else published | Backends and databases must stay on the internal network (see section 4) |

One-time, copy the operations scripts to the VM. The deploy does **not** ship them, so rollback and backup are not available
until you do this:

```bash
scp scripts/deploy/rollback-vm.sh scripts/deploy/backup-data.sh scripts/deploy/restore-data.sh <user>@<vm>:/opt/asd/bin/
```

## 2. GitHub configuration

| Kind | Name | Value |
|---|---|---|
| Variable | `CLOUD_HOST` | VM hostname or IP (letters, digits, dots, hyphens only) |
| Variable | `CLOUD_USER` | deploy user on the VM |
| Variable | `CLOUD_DOMAIN` | the public DNS name, no scheme or path |
| Secret | `CLOUD_SSH_KEY` | private key for the deploy user |
| Secret | `CLOUD_KNOWN_HOSTS` | the VM's host key line (`ssh-keyscan -t ed25519 <host>`) |
| Environment | `production` | the workflow runs in it; add required reviewers if the group wants a manual gate |

The workflow only runs from `main`, and `assert-cloud-ci.ps1` requires all six CI workflows to have succeeded for the exact
commit being deployed.

## 3. Deploy

Actions, then **Cloud Deployment**, then **Run workflow** on `main`. The workflow: checks the six CI runs for the commit, runs
`prepare_cloud.py` (AI-disabled bundle), builds images, ships them over SSH with pinned host keys and checksums, runs
`deploy-vm.sh`, then runs `smoke_cloud.py` against `https://$CLOUD_DOMAIN`.

**Capture:** the run URL and its uploaded artifact `cloud-deployment-<sha>` (`compose.json`, `revision.txt`, `SHA256SUMS`,
`cloud-smoke.txt`). A successful smoke prints these lines:

```
PASS: six gateway pages; four AI modes disabled; deterministic create; trip/stop CRUD.
PASS: Student 1 AI modes disabled; cached-catalogue search create, rename and delete.
PASS: Student 3 AI modes disabled; deterministic recommendation; attraction and review CRUD.
PASS: Student 4 AI modes disabled; deterministic advice; budget and expense CRUD.
PASS: Student 5 reference data served; MCP, RAG and advisory disabled (read-only: it has no update or delete).
```

## 4. Validate what the smoke test cannot

| Check | How | Rubric / bonus |
|---|---|---|
| The deployed UI loads for every feature | Open `https://<domain>/` and each of `/accommodation/`, `/itinerary/`, `/attractions/`, `/budget/`, `/logistics/`; screenshot each | 7 |
| AI services are visibly off | Screenshot Student 3's "Ask the AI" note and the disabled Multi-Agent panel; the other features' disabled states | 7 |
| Only the gateway is public | On the VM: `docker ps --format '{{.Names}}\t{{.Ports}}'`; only `tls-gateway` shows `0.0.0.0:80/443`. From outside: `curl -m 5 http://<domain>:5203/health` must fail | B5 |
| Backends and database are on an internal network | `docker network inspect asd-cloud_private --format '{{.Internal}}'` prints `true` | B5 |
| TLS is valid | `curl -vI https://<domain>/` shows a verified certificate | B5 |
| No secret reaches the app | `docker compose --project-name asd-cloud -f /opt/asd/current/compose.json config` shows `LITEAPI_KEY` blank and every `*_ENABLED` flag `false` | B6 |
| Data is stored on the VM volume | `ls -l /opt/asd/data/student-*/` | B6 |

## 5. Persistence across a redeploy

1. Create a record through the UI or API (for example a Student 3 attraction named `persistence-check`).
2. Deploy a newer commit (run the workflow again after merging a change).
3. Confirm the record still exists, and that the seed data has not been duplicated.
4. Delete the test record.

Locally the same mechanism is proven in `student-3/docs/evidence/release-2/cloud/05-persistence-across-redeploy.txt`; this step
is the cloud proof.

## 6. Backup, restore and rollback

Run on the VM (scripts copied in section 1). Each prints what it did and exits non-zero on any problem.

```bash
# Backup: consistent online copies of every SQLite database, with checksums; keeps the newest 7.
bash /opt/asd/bin/backup-data.sh

# Restore (replaces live data; takes a pre-restore snapshot first; needs --yes):
bash /opt/asd/bin/restore-data.sh /opt/asd/backups/<timestamp> --yes

# Rollback to the release deploy-vm.sh recorded as previous (needs at least two deployments):
bash /opt/asd/bin/rollback-vm.sh
```

A rollback changes code only. If a release changed a database schema, restore a backup as well. Rollback refuses if the previous
release's images were pruned, and in that case leaves `current` unchanged. After either operation, run the public smoke test again:

```bash
python scripts/deploy/smoke_cloud.py https://<domain>
```

**Capture** a terminal transcript of: a backup, a restore from it (with data changed in between), and a rollback followed by a
passing smoke test. The scripts' behaviour is covered by `scripts/test/test_vm_scripts.py` (23 tests, Linux).

## 7. Evidence map

| Rubric item | Evidence to keep |
|---|---|
| 5 Cloud scripts | `prepare_cloud.py`, `deploy-vm.sh`, `rollback-vm.sh`, `backup-data.sh`, `restore-data.sh` and a log of a real run |
| 6 `cloud-deployment.yml` | the successful run URL and its logs |
| 7 Cloud app and CRUD | the smoke transcript, the section 4 screenshots |
| `review-cloud` mode | one finalised record whose context files include: the run URL and `cloud-smoke.txt`, the section 4 and 5 outputs, and the section 6 transcript. Run it only on a real deployment's evidence |
| B5 / B6 | the section 4 outputs for endpoint and data security |

## 8. Known gaps

- Nothing provisions the VM, its firewall or Docker; it is set up by hand.
- The deploy does not ship the operations scripts (section 1). Adding them to the bundle would remove the manual copy.
- Student 5's API has no update or delete and no explicit AI switch, so its smoke check is read-only and treats the unreachable-model `503` as "AI disabled".
- The review step in the Multi-Agent panel has no authentication, which matters if the Multi-Agent bonus is enabled in the cloud.
