# Itinerary Planner Risk Plan

Scores use probability and impact from 1 to 5; score is `P x I`.

| ID | Risk | P | I | Score | Mitigation | Current status |
|---|---|---:|---:|---:|---|---|
| IT-R01 | Feature is not reachable from the unified app and receives no integration marks. | 2 | 5 | 10 | Keep `/itinerary/` on shared nginx and use port 5100 as the user entry point. | Mitigated in source; clean Compose evidence pending |
| IT-R02 | Multi-call persistence leaves an orphan trip or destroys stops during regeneration. | 3 | 5 | 15 | Generate first and commit trip/stops or replacement stops in one database transaction. | Mitigated and regression-tested |
| IT-R03 | Malformed AI output creates missing days or inconsistent itineraries. | 4 | 4 | 16 | Require exact fields, valid day range, complete day coverage, and exactly two stops per day; otherwise use fallback. | Mitigated and tested |
| IT-R04 | Ollama is unavailable or too slow during demonstration. | 3 | 4 | 12 | Use one shared preloaded approved model, bounded timeout, visible deterministic fallback, and capture success/fallback evidence beforehand. | Fallback implemented; live evidence pending |
| IT-R05 | Browser bypasses the backend or backend opens SQLite. | 2 | 5 | 10 | Same-origin `/itinerary-api/` proxy; only database service includes SQLite access. | Mitigated by architecture |
| IT-R06 | External CDN fails in the local demonstration. | 3 | 3 | 9 | Keep all frontend runtime assets inside the Student 2 image. | Resolved; HTMX CDN removed |
| IT-R07 | Automated coverage misses frontend regressions and API failure paths. | 2 | 4 | 8 | Run frontend Vitest plus backend/database pytest in Student 2 CI; expand edge tests with defects. | Stop ownership/order and stale-status regressions covered; broader failure coverage remains useful |
| IT-R08 | Required agentic-loop evidence is confused with application trace text. | 4 | 5 | 20 | Run and finalise the shared two-model development loop; cite the JSON record and terminal output. | Open |
| IT-R09 | Missing planning/report/video evidence loses marks despite working code. | 4 | 5 | 20 | Maintain the Release 0 checklist and capture evidence incrementally. | Open |
| IT-R10 | Work without durable remote history cannot support contribution evidence. | 2 | 5 | 10 | Keep selective commits on the Student 2 branch, push with approval, and open a reviewed pull request. | Local branch and commits complete; push/PR open |
| IT-R11 | Responsive or keyboard defects appear during the showcase. | 3 | 3 | 9 | Complete the browser checklist at 320px, 768px, and 1280px and capture evidence. | Open |
| IT-R12 | Compose services build but fail when started together. | 2 | 4 | 8 | Validate Compose, wait for Student 2 health checks, and exercise backend-to-database HTTP integration in CI. | Mitigated locally and in workflow; remote run evidence pending |
| IT-R13 | Weather provider outage, wrong location match, or forecasts used beyond their horizon mislead travellers. | 3 | 4 | 12 | Return the selected top-match location explicitly; validate supplied location IDs; use fixed provider URLs, response bounds and deadlines; retain summary after weather failures; show missing dates/values and attribution; never claim feasibility. | Automatic top-match tool behavior covered by MCP tests; recording should verify the matched place |
| IT-R14 | A tool caller bypasses confirmation or replays an edit. | 3 | 5 | 15 | UI requires confirmation; database enforces signed, expiring, revision-bound previews and atomic writes. No automatic save retries; keep unauthenticated MCP local-only. | Database/MCP foundations merged; backend/UI confirmation, cancellation and undo regression-tested |
| IT-R15 | Context-aware advice is deployed against an older RAG server. | 3 | 4 | 12 | Deploy matching backend and shared RAG context contract, restart native RAG and verify a selected-trip query. Treat context as untrusted and keep identity excluded. | Context producer/consumer included together; live deployment not repeated for this branch |

Review this register before AI, schema, Compose, CI, or public API changes and after any failed evidence run.

## Protected Cloud AI - 22 October 2026

- The approved optional AI deployment gates every browser/API route behind
  HTTPS Basic Auth, strips credentials before forwarding and retains only a
  private bcrypt snippet on the VM. Real isolated Caddy tests verify anonymous
  and incorrect-password rejection and credential stripping. This is shared
  demo access, not per-user record or human-decision authorization (P=3, I=5).
- The `m7i-flex.large` target has 2 vCPU/8 GiB and no measured AI capacity.
  Provisioning verifies and warms one shared model; backend timeouts, schema
  failures, grounding and concurrency still require live evidence (P=4, I=4).
  The deployment smoke rejects fallback and stops agents at human review.
- Failed provisioning or smoke may leave changed containers, even if a previous
  release link is retained. Inspect and explicitly roll back; do not assume an
  atomic deployment (P=3, I=4). Baseline rollback disables AI and removes the
  password gate; older AI rollback restores the older password hash.
- See the [cloud runbook](../../docs/release-2/cloud-validation-runbook.md) for
  credentials, activation, rollback and remaining AWS acceptance checks.

## Release 2 Inline Edit Assessment - 21 October 2026

- Bind assessment acceptance to the exact signed preview token and full saved-trip
  fingerprint. A corrected operation requires a new preview and assessment;
  assessment text is never executable. Approval and database save are separate
  outcomes; retain no-retry handling for uncertain saves.
- The existing ten-minute preview lifetime includes agent processing. Expired
  or stale previews must restart; do not silently renew a token under old approval.
- Bound shared evidence to 30 entries of 800 characters without truncating the
  request or proposed changes. Reject oversized candidates explicitly; disclose
  saved-context omissions and retain manual CRUD.
- Real native undo assessment completed with visible model concerns, but two
  natural-language preview attempts hit the existing 20-second editor-model
  deadline. Automated regressions pass; live natural-language acceptance remains
  open. Do not treat the model's verdict as a deterministic correctness guarantee.

## Editor and Validation Follow-up - 1 October 2026

- Model intent and source support remain separate from schema validity. Restrict
	model authority to one action/replacement field, ground new text/day in the
	request, derive existing stop days from saved IDs and show exact before/after
	values. Ambiguous names and embedded instructions still require human review.
- A save timeout has an uncertain outcome (P=3, I=4): never retry automatically;
	discard the preview and refresh before requesting another edit.
- Removal and undo can lose intended content (P=3, I=5). Atomically journal dates
	and full stops, including IDs/creation times; undo removes added stops and rejects
	intervening changes. Database restart invalidates outstanding preview tokens.
- Weather context can be mistaken for cited knowledge (P=3, I=4). Keep provider
	data/attribution separate, preserve abstention and report missing forecasts and
	truncated plan context. Automatic geocoding is fallible; weather failure must not
	block knowledge-based advice.
- Earlier universal-schema extraction failed live intent cases. Action-specific
	schemas and text/day grounding passed eleven retained cases and five isolated
	confirmation/undo flows. This is historical, narrow evidence, not general model
	accuracy or injection certification.
- The launcher restarts MCP/RAG and binds native APIs to the chosen interface.
	Use a local private address and administrator-managed access policy; the script
	does not edit firewall rules. Full startup remains a separate acceptance check.
