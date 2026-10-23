# Budget & Expense Tracker Risk Plan

**Current scope - 2026-10-23:** the authorised implemented Release 2 What-If
planner extends the historical R0/R1 scope. In particular, R-12's older
multi-agent/cloud exclusion is not a prohibition on this authorised R2 work.
The R2 controls below supplement the retained historical register.

Scale: likelihood and impact are 1 (low) to 5 (high). Score is their product.

| ID | Risk | L | I | Score | Preventive control | Trigger and response | Owner |
|---|---|---:|---:|---:|---|---|---|
| R-01 | Model is unavailable or returns unusable output. | 4 | 3 | 12 | Strict timeout, full response validation, one retry, deterministic fallback, fake-client tests. | Any Ollama failure returns labelled fallback without blocking dashboard or CRUD. | Liam |
| R-02 | Floating-point conversion corrupts money. | 2 | 5 | 10 | Integer minor units, decimal rates, one final midpoint-away-from-zero rounding, persisted snapshot. | Conversion mismatch fails focused tests and blocks integration. | Liam |
| R-03 | Backend bypasses the database HTTP boundary. | 1 | 5 | 5 | No EF/SQLite backend packages; typed HTTP client only; dependency scan/test. | Any database assembly or file access in backend is removed before merge. | Liam |
| R-04 | Seed initialization duplicates or drops below ten rows. | 2 | 5 | 10 | Stable natural keys, transaction, idempotency and count tests. | Count below thresholds blocks CI smoke completion. | Liam |
| R-05 | Budget/expense invariants differ between API and SQLite. | 3 | 4 | 12 | Shared documented allow lists, API validation, check/unique/FK constraints, atomic journey-currency triggers, integration tests. | Constraint/API mismatch is fixed at both layers and regression-tested. | Liam |
| R-06 | Mixed base currencies make journey totals invalid. | 2 | 5 | 10 | Database conflict rule and backend validation; dashboard rejects unusable dependency data. | Mixed journey data returns stable conflict/unusable-dependency response. | Liam |
| R-07 | Model prompt injection changes behavior. | 3 | 4 | 12 | Allow-listed structured summary, labels treated as untrusted, schema plus semantic validation, no model writes. | Invalid category/field/text output is retried once then falls back. | Liam |
| R-08 | Shared routing collides with another feature. | 2 | 4 | 8 | Namespaced `/budget/` and `/budget-api/` routes; targeted nginx and Compose checks. | Route/config failure is repaired without changing other student services. | Liam |
| R-09 | Frontend exposes unsafe HTML or inaccessible controls. | 2 | 4 | 8 | DOM text APIs, semantic forms, native dialogs, focus restoration, live status, tests and browser checklist. | Any unsafe interpolation or keyboard trap blocks completion. | Liam |
| R-10 | CI requires a large live model and becomes unreliable. | 3 | 4 | 12 | Unit fakes and smoke startup with an Ollama-independent backend fallback path. | CI must prove fallback behavior without pulling a model. | Liam |
| R-11 | Docker Desktop/model/image availability blocks live checks. | 3 | 3 | 9 | Complete local tests/config first; record exact command/error; separate unverified evidence. | Environmental failure is documented and never reported as passed. | Liam |
| R-12 | Scope expands beyond the authorised release or into itinerary coupling. | 2 | 4 | 8 | Explicit per-release exclusions and local `journeyLabel`; Release 1 permits the bounded MCP/RAG features below. | Reject unapproved multi-agent, cloud, live-rate, auth, bank, or cross-feature additions. | Liam |
| R-13 | AI-generated work is accepted without human validation. | 3 | 5 | 15 | Prompt/review logs, executable checks, pending evidence markers, Liam-owned Adapt decision. | Unreviewed human evidence remains pending and cannot close ACT evidence. | Liam |

Risks are reviewed after each implementation stage and whenever Liam supplies an
OBSERVE result.

## Release 1 Risks

| ID | Risk | Control | Current state |
|---|---|---|---|
| R1-01 | Invalid or disabled mode configuration is silently accepted, or disabled AI still contacts Ollama. | Exact lowercase parsing, startup validation, capability combinations, and a counting fake proving zero disabled-mode calls. | Covered by the implemented mode-control tests. |
| R1-02 | MCP introduces duplicate financial rules, writes, or recursive dashboard calls. | Keep `budget.get_summary` read-only and route it through a fixed callback to the existing MCP-free deterministic dashboard; add no database or money-calculation path. | Recorded integrated callback matched dashboard totals and left data unchanged; combined main-merge regression checks are separate. |
| R1-03 | RAG guidance is mistaken for live budget facts or selects irrelevant/unsupported passages. | Keep RAG separate from saved spending data; Student 4 accepts only retrieved passage IDs and renders exact source text; validate known IDs, markers, score/confidence, and exact insufficient-context abstention. | Recorded direct and integrated cases returned exact cited text and abstention. Passage relevance remains model-dependent; human loop finalisation and broader hold-out review remain open. |
| R1-04 | Native MCP/RAG/Ollama dependencies are unavailable during local or CI validation. | Preserve explicit mode flags; test disabled behavior without calls and record live connectivity separately from offline evidence. | Student4-prefixed Compose flags default MCP/RAG off; live host connectivity was recorded, not guaranteed on a changed showcase machine. |

## Release 2 Risks - 2026-10-23

| ID | Verified risk or evidence gap | Control and current limit | Owner |
|---|---|---|---|
| R2-01 | Proposed limits or model commentary could be mistaken for saved financial changes. | Complete category aggregates, safe-integer validation and deterministic calculation; no financial writes for preview or any decision. Live saved budget/expense responses were byte-identical. | Liam |
| R2-02 | Source data can change after preview; protected handles expire or become invalid after backend restart. | Snapshot check at start/decision returns 409; two-hour ephemeral token binds workflow/preview, invalid tokens return 403. Refresh preview/start deliberately; never apply an old decision to changed data. | Liam |
| R2-03 | A timeout can occur after a workflow start or decision has applied. | Bounded 16 KiB request/256 KiB response and 10-second dependency deadline; poll known ID/token first. If start returned no ID, inspect shared history before another POST. Stop polling does not cancel work. | Liam |
| R2-04 | Reviewer concerns or valid multiline prose were previously hidden/rejected. | Main-session fixes allow bounded CR/LF/tab commentary and readable structurally valid flagged native records; corrected output remains strictly validated. Expanded backend suite passed 322 tests; human judgement is still required. | Liam |
| R2-05 | A named decision could be misrepresented as authenticated approval. | Actual self-declared name <=60 and notes <=1000; reject requires notes, partial selects existing items, correction is commentary only. Protected tokens are not user authentication; keep native service trusted-local and tokens out of evidence. | Liam |
| R2-06 | Windows denied port 5600, and a relative Python path fails after helper directory change. | Resolve interpreter to an absolute path before startup; recorded native service uses 127.0.0.1:15600 and container host URL. No public bind or firewall change is implied. | Liam |
| R2-07 | Four healthy containers and historical R1 evidence do not prove complete local/cloud integration. | Label the subset; current MCP/RAG modes are false. Coordinate full-group/native R1 replay separately. Required cloud baseline has all four AI modes false; no live cloud, credentials or provisioning evidence yet. | Liam and team |
| R2-08 | Unit fakes, model findings, local tests and configured CI can be mistaken for human acceptance or post-push evidence. | Real workflow still has null human decision; new report-review modes, remote CI/TRX, live deployment and showcase remain pending. Preserve provenance in the dated evidence record. | Liam and team |
| R2-09 | The submission date conflicts across source documents while release gates remain open. | Follow the specific R2 brief: 25 October 2026, 11:59 PM AEST, not the general specification's historical 18 October date. Prioritise genuine human decision, CI, group/cloud evidence and report/video; do not fabricate sign-off to close gaps. | Liam and team |

Current results and outstanding gates: [validation](evidence/release-2/validation-2026-10-23.md).
Operational recovery and human demo: [runbook](release-2-runbook.md).
