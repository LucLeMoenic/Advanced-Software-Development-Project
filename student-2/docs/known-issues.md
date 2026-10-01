# Itinerary Planner Known Issues and Limitations

## Final Branch Status - 1 October 2026

PRs #92-#95 merged the database, MCP, editor and knowledge chunks. The final
launcher/validation/evidence chunk is prepared on
`LLM/Student_2_Release_Validation_And_Evidence`; no remote CI result is claimed
for that branch. Historical runtime notes below are not current health checks:
native terminals were subsequently closed and must be restarted before a demo.
Fourteen itinerary live cases passed earlier, but broad grounding is not proven;
two accommodation questions over-abstained with both old and new citation schemas.
The [review record](review-record.md) retains those findings and source checks.

## Ollama Follow-up - 1 October 2026

Ollama and `llama3.2:3b` are now installed, running and reachable from the backend
container. A real model-backed day-swap preview through the gateway passed in
6.12 seconds without changing saved data. Genuine contextual RAG passed again in
9.51 seconds with a weather-planning citation. This supersedes the model-absence,
connectivity blocker and wholly-unverified-generation notes below. No live edit
was confirmed; broader command accuracy and grounding evaluation remain open.
The first cold model request took 44.67 seconds, exceeding application deadlines;
preload before demonstration. See the [runbook](release-1-runbook.md).

## Current Editor and Advice Limitations - 1 October 2026

- MCP now previews and explicitly confirms day/stop moves; RAG owns planning
	advice and optional weather context. The old review API is compatibility-only.
- Live preview and cited advice now pass the focused cases above. Schema validation
	does not prove general semantic accuracy or injection resistance. The manual
	Ollama bind is session-only; keep native service terminals running.
- Preview signing is process-local: restart invalidates outstanding previews.
	Tokens expire after ten minutes; changed snapshots and replay are rejected.
	Refresh after uncertain saves before requesting a fresh preview.
- There are no accounts/authorization. Confirmation protects intent/concurrency,
	not access control; services remain appropriate only for a trusted local demo.
- RAG context uses at most 20 stops and 160 characters per note, reports truncation
	and keeps forecasts separate from knowledge citations. Weather requires native
	MCP; unavailable weather does not block advice. Top-match geocoding is fallible.
- Refreshed images/native services pass real MCP preview and contextual RAG
	abstention/weather checks through the backend and gateway. Saved data is
	unchanged. Live model-backed editing/advice remain separate acceptance gates.

Historical sections below are superseded where they conflict with this section
and the [current runbook](release-1-runbook.md).

## Historical Review Limitations - 30 September 2026

- The read-only itinerary review is implemented and tested with fake models/tools;
	useful live generation, grounding and injection resistance are not yet certified.
- Valid evidence references do not prove every generated sentence is entailed.
	Suggestions require human judgment; no opening-hours, travel-time or cost data is added.
- Automatic top-match geocoding can choose an unintended place. The matched name
	remains visible; no user-confirmation step remains in the current UI.
- Two MCP reads are not an atomic snapshot. Summary differences are rejected,
	but concurrent stop-text edits with unchanged summary metrics may go undetected.
- Ollama was not listening during implementation. The initial Compose build stalled,
	but the 1 October explicit Podman build, isolated image startup and both nginx
	syntax checks pass. Rebuild/restart of the integrated application and live review
	validation remain open. Historical notes below are not release certification.

## Historical Evidence and Environment Issues

- No successful GitHub Actions run URL or screenshot has been recorded for `student-2.yml`.
- No finalised shared Plan/Act/Observe/Adapt development-loop record exists for Student 2.
- Integrated browser screenshots, responsive checks, keyboard walkthrough, persistence restart capture, and the showcase video are pending.
- The current branch is `feature/student2-release0-improvements`. Its latest fixes are local and have not been pushed or validated by a remote workflow run.
- Local Compose configuration, Student 2 service health, and backend-to-database HTTP integration pass. A clean-checkout run and durable report evidence remain pending.
- The complete group Compose application still lacks backend/database implementations for Students 4 and 5; those services remain owned by their respective team members.
- Tutor acceptance of the shared Vue entry point should be retained because the written brief refers to HTMX.
- Live AI and fallback behavior pass locally, but their durable report evidence has not yet been assembled.

## Product Limitations

- Generated itineraries are suggestions only; bookings, prices, opening hours, travel times, accessibility, and availability are not verified.
- The deterministic fallback is intentionally generic and should be presented as a resilience path, not personalised AI output.
- Release 0 has no authentication or per-user access control; the traveller name is descriptive data only.
- Release 0 uses synchronous HTTP and a single SQLite database, suitable for local classroom demonstration rather than production scale.
- MCP, RAG, cloud deployment, and multi-agent application behavior are outside Release 0 scope.
