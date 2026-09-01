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
| IT-R07 | Automated coverage misses frontend regressions and API failure paths. | 3 | 4 | 12 | Run frontend Vitest plus backend/database pytest in Student 2 CI; expand edge tests with defects. | Basic suites complete; broader failure coverage pending |
| IT-R08 | Required agentic-loop evidence is confused with application trace text. | 4 | 5 | 20 | Run and finalise the shared two-model development loop; cite the JSON record and terminal output. | Open |
| IT-R09 | Missing planning/report/video evidence loses marks despite working code. | 4 | 5 | 20 | Maintain the Release 0 checklist and capture evidence incrementally. | Open |
| IT-R10 | Uncommitted work provides no durable contribution history. | 4 | 5 | 20 | Use a Student 2 feature branch, meaningful commits, and a reviewed pull request; only the user commits/pushes. | Open |
| IT-R11 | Responsive or keyboard defects appear during the showcase. | 3 | 3 | 9 | Complete the browser checklist at 320px, 768px, and 1280px and capture evidence. | Open |
| IT-R12 | Local Docker lacks Compose, preventing reproducible startup evidence. | 4 | 4 | 16 | Install/repair Docker Compose v2, then run the repository command and capture output. Manual Docker topology is temporary only. | Open |

Review this register before AI, schema, Compose, CI, or public API changes and after any failed evidence run.
