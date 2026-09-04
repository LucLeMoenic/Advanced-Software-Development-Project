# Scripts

- `verify-agentic-models.ps1`: checks that the configured application, implementer, and reviewer models already exist locally. It never downloads models.
- `start-student1.ps1`: builds and starts the Student 1 Compose dependency chain, then prints service status and localhost URLs.
- `test-student4.ps1`: runs all Student 4 source validation or one .NET test suite.

Use `start-app.ps1` or root `docker compose` commands for integrated container startup and shutdown. Feature build, test, and deployment scripts should be added only when their corresponding implementation exists.
