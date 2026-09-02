# Itinerary Planner Known Issues and Limitations

## Open Evidence and Environment Issues

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
