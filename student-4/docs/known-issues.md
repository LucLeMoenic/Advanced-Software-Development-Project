# Student 4 Known Issues and Limitations

Status date: 2026-09-04

## Current Verification Gaps

1. Docker Desktop and Docker Compose are now available, and `docker compose
   config --quiet` passes. Student 4 no longer keeps a separate container
   lifecycle script; CI uses direct shared-Compose commands. A 2026-09-04 run
   confirmed shared route, health, 12/24 containerised counts, and live AI
   advice.
2. Forced-unavailable Ollama evidence is still pending in the Compose stack.
   Fake-handler tests verify strict response handling and one corrective retry.
   A direct backend request with Ollama unavailable returned deterministic
   fallback; live successful model evidence now exists with `source: ai`.
3. Manual browser and responsive checks have not been performed. Vitest/jsdom
   covers behavior and focus paths but does not replace visual evidence.
4. The Student 4 GitHub Actions workflow has not run because no commit or push
   was made.
5. The shared two-model agentic loop has not yet been finalised for Student 4.
   Liam's explicit Adapt decision also remains pending by design.

## Intentional Release 0 Limitations

- Exchange rates are versioned demonstration data dated 2026-08-01, not live rates.
- There is no authentication, authorization, cloud deployment, bank/payment integration, MCP, RAG, or multi-agent runtime.
- Journey labels are local grouping text and are not linked to an itinerary.
- AI advice is optional and cannot mutate records or control totals/statuses.
- SQLite is suitable for the assessed local deployment, not concurrent distributed production writes.

These intentional Release 0 constraints are not defects or missing deferred
Release 1/2 work.