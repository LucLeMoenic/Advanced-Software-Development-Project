# Scripts

Scripts are grouped by purpose:

- `build/`: build automation. No standalone build script is currently required; service builds are run through Compose and CI.
- `test/`: one runner per student (`student-1.ps1` through `student-5.ps1`) plus `verify-agentic-models.ps1`.
- `deploy/`: `start-app.ps1` and `start-student1.ps1` for local startup.

Use the root `docker compose` commands for integrated container startup and shutdown. Add scripts only when their corresponding implementation exists.
