# Itinerary Planner Known Issues and Limitations

## Open Evidence and Environment Issues

- The current Docker installation does not provide Docker Compose v2 or the legacy `docker-compose` binary. A manual seven-container topology is running, but a clean Compose execution still needs to be captured on a correctly configured machine.
- No successful GitHub Actions run URL or screenshot has been recorded for `student-2.yml`.
- No finalised shared Plan/Act/Observe/Adapt development-loop record exists for Student 2.
- Integrated browser screenshots, responsive checks, keyboard walkthrough, persistence restart capture, and the showcase video are pending.
- Five selective local commits exist on `student-2/release-0-itinerary-planner`; the branch has not been pushed and no pull request exists yet.

## Product Limitations

- Generated itineraries are suggestions only; bookings, prices, opening hours, travel times, accessibility, and availability are not verified.
- The deterministic fallback is intentionally generic and should be presented as a resilience path, not personalised AI output.
- Release 0 has no authentication or per-user access control; the traveller name is descriptive data only.
- Release 0 uses synchronous HTTP and a single SQLite database, suitable for local classroom demonstration rather than production scale.
- MCP, RAG, cloud deployment, and multi-agent application behavior are outside Release 0 scope.
