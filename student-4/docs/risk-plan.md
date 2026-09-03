# Budget & Expense Tracker Risk Plan

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
| R-12 | Scope expands into Release 1/2 or itinerary coupling. | 2 | 4 | 8 | Explicit exclusions and local `journeyLabel`; code search during final validation. | Remove MCP, RAG, multi-agent, cloud, live-rate, auth, bank, or cross-feature code. | Liam |
| R-13 | AI-generated work is accepted without human validation. | 3 | 5 | 15 | Prompt/review logs, executable checks, pending evidence markers, Liam-owned Adapt decision. | Unreviewed human evidence remains pending and cannot close ACT evidence. | Liam |

Risks are reviewed after each implementation stage and whenever Liam supplies an
OBSERVE result.