# Student 4 Known Issues and Limitations

Status date: 2026-09-03

## Current Verification Gaps

1. Docker Desktop or the Docker CLI was not available on local `PATH` during
   implementation. Compose parsing, image builds, container health, shared
   route smoke tests, and containerised row counts remain unverified locally.
   Direct .NET service startup verified health and exact 12/24 runtime counts.
2. Live Ollama advice was not run. Fake-handler tests verify strict response
   handling and one corrective retry. A real backend request with Ollama
   unavailable returned deterministic fallback; live successful model evidence
   remains a human/environment action.
3. Manual browser and responsive checks have not been performed. Vitest/jsdom
   covers behavior and focus paths but does not replace visual evidence.
4. The Student 4 GitHub Actions workflow has not run because no commit or push
   was made.
5. The shared two-model agentic loop was not run because model/runtime
   availability could not be established without Docker. Liam's explicit Adapt
   decision also remains pending by design.

## Intentional Release 0 Limitations

- Exchange rates are versioned demonstration data dated 2026-08-01, not live rates.
- There is no authentication, authorization, cloud deployment, bank/payment integration, MCP, RAG, or multi-agent runtime.
- Journey labels are local grouping text and are not linked to an itinerary.
- AI advice is optional and cannot mutate records or control totals/statuses.
- SQLite is suitable for the assessed local deployment, not concurrent distributed production writes.

These intentional Release 0 constraints are not defects or missing deferred
Release 1/2 work.