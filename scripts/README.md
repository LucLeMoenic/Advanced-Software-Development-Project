# Scripts

- `verify-agentic-models.ps1`: checks that the configured application, implementer, and reviewer models already exist locally. It never downloads models.
- `start-student1.ps1`: builds and starts the Student 1 Compose dependency chain, then prints service status and localhost URLs.
- `test-student4.ps1`: runs all Student 4 source validation or one .NET test suite.
- `start-student4.ps1`: builds and starts Student 4 behind the shared `/budget/` route.
- `stop-student4.ps1`: stops Student 4 and the shared frontend.
- `validate-student4-docker.ps1`: performs the same container build, health, seed, route, and fallback smoke checks used by Student 4 CI.

Feature build, test, and deployment scripts should be added only when their corresponding implementation exists.
