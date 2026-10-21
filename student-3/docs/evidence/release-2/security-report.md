# Cloud security controls (Release 2 bonus B5 and B6) — implementation and evidence

Scope: the controls that protect the public gateway's endpoints (B5) and the application's data, secrets and credentials (B6).
The pipeline itself was built by teammates; this adds controls it lacked and the tooling to validate them. **Nothing here has
run against a real cloud deployment.** Everything marked "proven" was exercised locally against real software: a real Caddy 2.10.2,
the real rebuilt nginx gateway, and Student 3's real services.

## What the audit of the existing pipeline found

Already in place (teammates): TLS through Caddy with automatic certificates and HTTP to HTTPS redirect; every backend, database and
AI-service address on an `internal: true` network with only `tls-gateway` publishing ports; blank API key and unreachable AI URLs in the
bundle; pinned SSH host keys, image checksums and runner credentials removed after the deploy; secret scanning in pre-commit.

Missing: security headers, a request-size limit, any rate limiting, a method allow-list, and the version-bearing `Server` header was
exposed. For data: backups (which I wrote in Chunk 7) used the default umask, so they would have been world-readable.

## B5 — endpoint security

| Control | Where | Proven how |
|---|---|---|
| Security headers: HSTS, nosniff, `X-Frame-Options: DENY`, referrer and permissions policy, CSP `frame-ancestors/base-uri/object-src/form-action`, `Server` removed | `prepare_cloud.py` Caddyfile | `caddy validate`; `validate_security.py` against a live Caddy: all pass |
| Method allow-list (`TRACE` and other verbs refused with 405) | Caddyfile | live: `TRACE / -> 405` |
| 1 MB request-body limit (413) | Caddyfile `request_body` and nginx `client_max_body_size` | live: 2 MB POST -> 413 |
| Client address cannot be forged for rate limiting | Caddyfile `header_up X-Forwarded-For {remote_host}` | by construction; Caddy validated |
| Per-client rate limit, 30 req/s sustained, burst 60, answered 429 | nginx gateway `limit_req` | live, on four routes: allowed counts match the formula exactly (129/129, 151/151, 182/182); normal traffic never limited; recovers |
| nginx version hidden | `server_tokens off` | live: `Server: nginx` |
| Only the gateway publishes ports | bundle (teammates) and a new test | test; `validate_security.py` ports check, which correctly flags the open ports of the *local* dev stack |
| TLS 1.2+, HTTP to HTTPS | Caddy defaults | live: negotiated TLSv1.3; `308` redirect |

Validator: `scripts/deploy/validate_security.py <public URL>` runs all of these checks against a deployment and exits non-zero on any
failure. It refuses `--insecure` for any host except localhost. 58 offline tests; 14 mutations of its decisions are all caught.

## B6 — data, secrets and credentials

| Control | Where | Proven how |
|---|---|---|
| Backups and restore snapshots are private (directories 700, files 600) even if the caller's umask is permissive | `backup-data.sh`, `restore-data.sh` | Linux tests with umask 022 |
| Online SQLite backups with integrity check and checksums; restore verifies both and snapshots first | `backup-data.sh`, `restore-data.sh` | 23 Linux tests |
| No secret in the bundle (`LITEAPI_KEY` blank), no secret-looking value in any container, no credential file left on the VM, data and backups not accessible to other users | `scripts/deploy/audit-data-security.sh` | Linux tests; the audit never prints a secret value |
| Secrets kept out of the repository | detect-secrets pre-commit hook and audited baseline (Chunk 1) | hook evidence in `precommit/` |
| Deploy credentials: GitHub secrets, pinned host keys, key deleted from the runner after the run | `cloud-deployment.yml` (teammates) | workflow review |
| Encryption of data at rest | the cloud platform's disk encryption | **not provable locally**; the runbook says what to capture |

The audit is read-only and exits 1 on any failure; it also reports which `*_ENABLED` flags are on and flags what a script cannot know (disk encryption).

## Bugs found by testing this work (all fixed)

1. **The restore snapshot was world-readable.** `cp -a data/. snapshot/` copies the source directory's own mode onto the snapshot, overriding the `umask 077` I had set, so a snapshot of private data was `755`. Fixed with an explicit `chmod -R go-rwx`; caught by the new permission test.
2. **The validator's rate-limit check gave a false failure.** It built a new TLS context and connection per request, so it ran at exactly 30 req/s, the limiter's own rate, and could never exceed it. Measured 30 req/s before and 722 req/s after using one cached context and persistent connections. The deployment's limit was working all along.
3. **The first rate-limit test targeted an exempt endpoint.** `/health` is answered by an nginx `return` (rewrite phase), which runs before `limit_req`, so a flood there is never limited. That is desirable for healthchecks, and the evidence now records it; the limit is proven on real routes.
4. **A mutation run risked real network traffic.** With a validator guard deliberately broken, a test would have sent a burst and a 2 MB POST to `example.org`. I stopped it, restored the one guard it left disabled (verified byte for byte), then added a no-network fixture to the guard tests and made the mutation harnesses work on temporary copies.
5. Two of my own tests were wrong and were fixed: the `script-src` test inspected the Caddyfile's comments instead of its directives, and the dead-server burst test made 240 slow refused connections (28 seconds); it now uses a small burst.

## Evidence (`security/` and `cloud/`)

| File | Shows |
|---|---|
| `security/01-gateway-hardening.txt` | nginx config valid, version hidden, normal traffic served, flood limited on four routes, recovery |
| `security/02-validator-mutation-check.txt` | 14 injected bugs in the validator, all caught |
| `security/03-live-validator-run.txt` | the validator against a real Caddy in front of the real gateway: 13 of 13 pass; and the ports check failing on the dev stack as it should |
| `cloud/08-vm-scripts-mutation-check.txt` | 24 injected bugs in the VM scripts, all caught |

## Limits (what would still need doing)

- **No cloud run.** The bonus needs the validator and the audit run against the deployed site, with screenshots. The runbook lists the commands.
- **No script-src CSP.** The UIs use inline and CDN scripts; a strict policy would break them, so only the safe directives are applied.
- **Rate limiting trusts `X-Forwarded-For` from private networks.** Behind Caddy that is correct; reaching the gateway container directly (as in local development) allows a client to spoof it.
- **No authentication on the Multi-Agent review step.** Relevant if the Multi-Agent bonus (B4) is enabled in the cloud.
- **Disk encryption at rest** depends on the platform setting, not on this repository.
