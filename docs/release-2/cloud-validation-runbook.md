# Cloud deployment and validation runbook (Release 2)

How to deploy the integrated application to the group's Azure or AWS Linux VM, prove it works, and capture the evidence
the rubric and the `review-cloud` loop mode need. Everything here follows the scripts in `scripts/deploy/` and
`.github/workflows/cloud-deployment.yml`; nothing is assumed beyond them.

**Status (22 October 2026):** AI-off baseline run `39741981906` passed public
CRUD checks. However, it preceded the CI-gate correction and deployed without
all six successful CI checks; its green status is not complete acceptance
evidence. The corrected gate rejects absent, pending or failed checks, including
the final workflow. Protected AI activation is implemented and locally tested,
but has **not been deployed or model-tested on AWS**. Collect real deployment
evidence using the procedure below.

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
scp scripts/deploy/rollback-vm.sh scripts/deploy/backup-data.sh scripts/deploy/restore-data.sh scripts/deploy/audit-data-security.sh <user>@<vm>:/opt/asd/bin/
```

## 2. GitHub configuration

| Kind | Name | Value |
|---|---|---|
| Variable | `CLOUD_HOST` | VM hostname or IP (letters, digits, dots, hyphens only) |
| Variable | `CLOUD_USER` | deploy user on the VM |
| Variable | `CLOUD_DOMAIN` | the public DNS name, no scheme or path |
| Secret | `CLOUD_SSH_KEY` | private key for the deploy user |
| Secret | `CLOUD_KNOWN_HOSTS` | the VM's host key line (`ssh-keyscan -t ed25519 <host>`) |
| Secret | `CLOUD_AUTH_USER` | required for `ai`: 1-64 letters, digits, dots, underscores or hyphens |
| Secret | `CLOUD_AUTH_PASSWORD` | required for `ai`: a strong, unique password of 16-72 UTF-8 bytes, without line breaks or NUL |
| Environment | `prod` | must match the workflow exactly; add required reviewers if the group wants a manual gate |

The workflow only runs from `main`, and `assert-cloud-ci.ps1` requires all six CI workflows to have succeeded for the exact
commit being deployed.

**Start Cloud Deployment directly; no manual CI preparation is needed.** Path
filters can legitimately skip student CI on a new `main` revision. The deployment
uses `assert-cloud-ci.ps1 -RunMissing` to dispatch only missing workflows on
`main`, reuse passing checks for the same commit and wait for queued/running
checks. It polls every 15 seconds for up to one hour. Each missing workflow is
requested at most once per deployment, including while GitHub registers the run.

Failed, cancelled or skipped checks stop deployment with links to the CI runs;
they are not automatically retried or bypassed. Fix failures (or explicitly rerun
a transiently failed CI run), then start deployment again. A timeout leaves CI
running so it can finish; the next deployment can reuse its results. If `main`
changes while waiting or before dispatch, start a **new Cloud Deployment** run
on the new revision rather than rerunning an old deployment.

The workflow's built-in `GITHUB_TOKEN` has `contents: read` and `actions: write`
to dispatch the six existing CI workflows. No personal access token or additional
secret is needed. Repository/organization policy must permit workflow dispatch.
Calling the script without `-RunMissing` remains a read-only, immediate gate.
For protected AI, credential validation runs before CI dispatch to avoid waiting
for builds only to discover missing gateway secrets.

Set the host, user and domain as Actions **variables**, not secrets; the SSH
key, known-hosts entry and AI gateway credentials belong in **secrets**. Verify
the scanned SSH fingerprint through a trusted VM console before saving it.
Empty variables in a deployment
log mean the workflow cannot see the required settings. Configuring the
`prod` environment requires repository administration access. Settings in a
different environment, such as `production`, are not visible to this job.

The deployment runner is pinned to Ubuntu 24.04 and its checkout, Python setup
and artifact actions use Node.js 24. Evidence upload is skipped if deployment
fails before producing any evidence files.

## 3. Deploy

Actions, then **Cloud Deployment**, then **Run workflow** on `main`, leaving
**mode** set to **baseline**. The workflow starts/waits for required CI for the commit, runs
`prepare_cloud.py` (AI-disabled bundle), builds images, ships them over SSH with pinned host keys and checksums, runs
`deploy-vm.sh`, waits for public HTTPS readiness, then runs `smoke_cloud.py`
against `https://$CLOUD_DOMAIN`.

Containers starting does not mean Caddy has obtained its first TLS certificate.
The readiness step retries only a read-only HTTPS GET, with certificate
verification enabled, every five seconds within a 180-second retry window
(each request has a 15-second limit). Persistent failures stop verification;
the subsequent CRUD smoke requests are not retried. If readiness fails, check
the Caddy logs, public DNS and inbound ports 80/443 rather than disabling TLS
verification.

**Capture:** the run URL and its uploaded artifact `cloud-baseline-evidence-<sha>`
(`compose.json`, `revision.txt`, `SHA256SUMS`, `cloud-smoke.txt`, `ai-services.txt`,
`vm-pull-images.txt`). A successful smoke prints these lines:

```
PASS: six gateway pages; Student 2 capability/generation mode and trip/stop CRUD.
PASS: Student 1 cloud profile and CRUD checks.
PASS: Student 3 cloud profile and CRUD checks.
PASS: Student 4 cloud profile and CRUD checks.
PASS: Student 5 cloud profile and CRUD checks.
```

### Prepare cloud AI without enabling it

The user-selected target is an `m7i-flex.large` (2 vCPU, 8 GiB RAM, CPU-only).
The user has approved **HTTPS username/password protection for the entire AI
demo**. Use the protected activation mode below, rather than enabling flags in
the running baseline. Never expose Ollama/MCP/RAG/Multi-Agent ports directly.

Select **mode: prepare-ai** to build the integrated application plus the existing
[cloud AI profile](../../deploy/cloud/ai.compose.yml). This mode:

- Uses the same six-workflow, exact-main-revision CI gate.
- Builds the MCP, RAG and Multi-Agent images and prepares the Ollama service.
- Uploads `cloud-ai-preparation-<sha>` containing a checksummed
  `cloud-ai-bundle.tar` with application images, Compose configuration, AI
  metadata, VM deployment/model-pull helpers, and both smoke scripts.
- Does **not** configure SSH, contact EC2, download models, run live smoke tests,
  or enable any public AI feature. The artifact expires after seven days.
- Retains preparation evidence as `cloud-prepare-ai-evidence-<sha>`; a successful
  preparation run is not evidence of a successful deployment or live AI.

The VM installer consumes the bundle's upstream-image list, explicitly pulls
Ollama, and provisions `llama3.2:3b` against the new release's Compose file before
marking that release current. All enabled application consumers use this one
cloud model. MCP-only bundles do not pull a model. Pull, listing or nonempty
inference warm-up failures stop activation; they can still leave changed containers, so inspect before
retrying. Redeploying the same revision preserves its real rollback predecessor.
Both baseline and AI metadata/scripts are covered by bundle checksums.

### Activate protected cloud AI

1. Merge the feature branch. Set `CLOUD_AUTH_USER` and `CLOUD_AUTH_PASSWORD` in
   the `prod` environment's secrets. Deployment starts missing CI automatically
   and requires all six checks to pass for its exact revision. Do not put
   credentials in source, artifacts or commands.
2. Check free disk space and memory on the VM. Allow space for the roughly 8 GB
   upstream Ollama image, roughly 2 GB model, application images, retained
   releases and databases. Eight GiB RAM is not a measured capacity guarantee.
3. Run **Cloud Deployment** on `main` with **mode: ai**. The workflow validates
   credentials, builds all application/AI images, hashes the password using Caddy,
   transfers only the bcrypt snippet separately over pinned SSH, provisions and
   warms `llama3.2:3b`, then verifies authenticated HTTPS and anonymous rejection
   for every feature. The snippet is not included in either artifact.
4. The authenticated `smoke_cloud_ai.py --all-features` check runs group CRUD and
   every implemented AI, MCP, RAG and Multi-Agent integration. AI generation must
   report real AI success, not deterministic fallback. Cited RAG responses and
   agent stages are checked. Multi-Agent smoke stops at `awaiting_human_review`
   and prints workflow IDs; it never submits decisions or confirms an itinerary
   edit. **Student 4 has AI/MCP/RAG but no Multi-Agent implementation.**
5. Open the HTTPS site, sign in using the configured credentials, and complete the
   browser and human-decision checks. Keep the run URL and
   `cloud-ai-evidence-<sha>`, including `cloud-smoke.txt`. A failed smoke is not a
   successful deployment and does not automatically roll containers back.

The gate covers every browser/API route. Caddy strips `Authorization` before
forwarding to the application; plaintext credentials are not passed to app/AI
containers. The hash is stored in the release's `gateway-auth.caddy` with mode
0600. Missing credentials fail closed. Redeploy `ai` to rotate the password;
rollback to an older AI release also restores that release's credentials.
This is a shared demonstration account, **not per-user access control or tenant
isolation**: authenticated participants share records and decision permissions.

AI releases use `/opt/asd/releases/<sha>-ai`; baseline releases use
`/opt/asd/releases/<sha>`, so changing modes at the same revision preserves a
rollback target. Baseline redeployment/rollback removes orphaned AI containers
and **returns to the unprotected, AI-off assessment profile**. Persistent models
and app data are not removed. Copy the updated rollback script in section 1.

Benchmark sequential real requests on the target. Ollama permits one loaded
model and one parallel request, but CPU inference can still exceed backend,
gateway and UI deadlines. Model warm-up removes cold-start overhead, not this
capacity limit. Longer smoke-client timeouts do not change backend deadlines.
Retain baseline, backup and rollback evidence; live model accuracy, CPU latency
and concurrent-user capacity are not established by local regression tests.

## 4. Validate what the smoke test cannot

| Check | How | Rubric / bonus |
|---|---|---|
| The deployed UI loads for every feature | Open `https://<domain>/` and each of `/accommodation/`, `/itinerary/`, `/attractions/`, `/budget/`, `/logistics/`; screenshot each | 7 |
| AI state matches the selected profile | Baseline: capture disabled controls. AI: sign in and capture real model/tool/citation output and human review without automatic approval | 7 |
| Only the gateway is public | On the VM: `docker ps --format '{{.Names}}\t{{.Ports}}'`; only `tls-gateway` shows `0.0.0.0:80/443`. From outside: `curl -m 5 http://<domain>:5203/health` must fail (the validator below also checks this) | B5 |
| Backends and database are on an internal network | `docker network inspect asd-cloud_private --format '{{.Internal}}'` prints `true` | B5 |
| TLS is valid | `curl -vI https://<domain>/` shows a verified certificate | B5 |
| No secret reaches the app | Compose shows `LITEAPI_KEY` blank and no gateway password in container environment; enabled flags match the selected profile. AI gateway hash is mounted only into Caddy | B6 |
| Data is stored on the VM volume | `ls -l /opt/asd/data/student-*/` | B6 |

### Endpoint security validation (bonus B5)

Run against the **baseline** site (it sends a few hundred requests in a few
seconds, so use it only on your own deployment). This validator does not supply
AI gateway credentials; its rate-limit/body-size checks are not authenticated AI
evidence. Protected AI has separate authenticated readiness and route checks:

```bash
python scripts/deploy/validate_security.py https://<domain>
```

It checks the HTTP to HTTPS redirect, TLS version and certificate, the security headers, that `TRACE` is refused (405), that a 2 MB
body is refused (413), that no backend, database or AI-service port is reachable from outside, and that a burst from one client is
rate-limited (429). It exits 1 if anything fails. **Capture the full output.** Its local run is in
`student-3/docs/evidence/release-2/security/03-live-validator-run.txt`.

### Data security validation (bonus B6)

On the VM (script copied in section 1):

```bash
bash /opt/asd/bin/audit-data-security.sh
```

It is read-only and checks that data and backups are not accessible to other users, that no container has a secret in its
environment (names only are printed), that `LITEAPI_KEY` is blank in the release,
and scans for common credential filenames under `/opt/asd`. For AI, separately
verify each intentionally retained `gateway-auth.caddy` is owned by the deploy
user, mode 0600, and never included in evidence; do not print its contents.
It also reports which `*_ENABLED` flags are on. It cannot see disk encryption, so capture the provider's evidence for the VM's disk:

```bash
# Azure (check the output shows platform-managed or customer-managed encryption at rest)
az disk show --resource-group <group> --name <os-disk-name> --query "encryption"
# AWS (check Encrypted is true)
aws ec2 describe-volumes --volume-ids <volume-id> --query "Volumes[].Encrypted"
```

(Commands to adapt to your resource names; confirm the output rather than assuming it.)

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

For a protected AI release, supply gateway credentials through environment
variables from a trusted secret source (not command history), then run:

```bash
python scripts/deploy/cloud_auth.py verify https://<domain> --required
python scripts/deploy/smoke_cloud_ai.py https://<domain> --components ai,mcp,rag,multi-agent --all-features
```

**Capture** a terminal transcript of: a backup, a restore from it (with data changed in between), and a rollback followed by a
passing smoke test. The scripts' behaviour is covered by `scripts/test/test_vm_scripts.py` (72 tests, Linux).

## 7. Evidence map

| Rubric item | Evidence to keep |
|---|---|
| 5 Cloud scripts | `prepare_cloud.py`, `deploy-vm.sh`, `rollback-vm.sh`, `backup-data.sh`, `restore-data.sh` and a log of a real run |
| 6 `cloud-deployment.yml` | the successful run URL and its logs |
| 7 Cloud app and CRUD | the smoke transcript, the section 4 screenshots |
| `review-cloud` mode | one finalised record whose context files include: the run URL and `cloud-smoke.txt`, the section 4 and 5 outputs, and the section 6 transcript. Run it only on a real deployment's evidence |
| B5 | the full `validate_security.py` output against the deployed URL, plus the section 4 checks |
| B6 | the `audit-data-security.sh` output, the provider's disk-encryption evidence, and the section 4 data checks |

## 8. Known gaps

- Nothing provisions the VM, its firewall or Docker; it is set up by hand.
- The deploy does not ship the operations scripts (section 1). Adding them to the bundle would remove the manual copy.
- Shared-password access does not isolate authenticated users or assign decision roles.
- Student 4 has no Multi-Agent path; other owners must explicitly implement any new feature scope.
- Protected AI has not yet passed real inference, complete browser flows, persistence
  and rollback checks on the target EC2 instance. Its 2-vCPU/8-GiB capacity remains unmeasured.
