# Student 4 Budget & Expense Tracker

Owner: Liam Zelmanowski

The Release 0 feature records category budgets and expenses, performs
deterministic demonstration-rate conversion, compares planned and actual
spending, and requests optional strictly validated advice from the shared
Ollama runtime.

## Services

| Service | Responsibility | Diagnostic URL |
|---|---|---|
| `student4-frontend` | Static HTML/CSS/JavaScript/HTMX and nginx | `http://localhost:5104` |
| `student4-backend` | Public API, conversion, dashboard, Ollama/fallback | `http://localhost:5204` |
| `student4-database` | EF Core, SQLite, migrations, constraints, seeds | `http://localhost:5304` |

The supported browser route is `http://localhost:5100/budget/`. The diagnostic
ports do not replace shared integration.

## Source Validation

The npm aliases live in [frontend/package.json](frontend/package.json). Run
them from the Student 4 frontend package:

```powershell
cd student-4/frontend
```

| Command | Purpose |
|---|---|
| `npm run validation` | Install dependencies, run all 53 tests, and build both frontends. |
| `npm run fe-test` | Run only the 10 frontend tests. |
| `npm run be-test` | Run only the 31 backend tests. |
| `npm run db-test` | Run only the 12 database tests. |

From the repository root, use the same scripts with `--prefix`, for example
`npm --prefix student-4/frontend run validation`.

## Integrated Startup

Student 4 does not have a separate Compose file or Student 4-only startup path.
Use the shared root Compose application for Release 0 evidence:

```powershell
./scripts/start-app.ps1
```

Use `docker compose down` from the repository root to stop the integrated
application without deleting the SQLite file or Ollama model volume.

Open `http://localhost:5100/budget/` after startup.

## Database

The application uses **SQLite**, not SQL Server. SSMS cannot connect to it.
Use DB Browser for SQLite, the VS Code SQLite extension, or `sqlite3`.

The physical runtime file is:

`student-4/database/storage/budget.db`

Normal application access is through `http://localhost:5304/api/data/*`.
Fresh initialization creates 12 budgets and 24 expenses.

## Compose and Health

The Compose file is [../docker-compose.yml](../docker-compose.yml). It is the
single shared Compose file for the integrated group application.

Startup order is health-gated:

`database healthy -> model setup complete -> backend healthy -> frontend healthy -> shared frontend`

Health URLs are `http://localhost:5100/health`, `5104/health`, `5204/health`,
and `5304/health`.

## AI Success and Fallback

With Ollama and `STUDENT4_MODEL` running, select a journey and choose **Generate
budget advice**. A valid first response is labelled `ai`; a valid corrective
response is labelled `ai_retry`.

To demonstrate fallback after normal startup:

```powershell
docker compose stop ollama
$body = @{ journeyLabel = "Sydney Weekender" } | ConvertTo-Json
Invoke-RestMethod http://localhost:5204/api/insights -Method Post -ContentType application/json -Body $body
docker compose start ollama
```

The unavailable-model response must have `source` equal to `fallback`.
Dashboard calculations and CRUD continue to use deterministic backend logic.

## Documentation

- [Context](docs/context.md)
- [Requirements and traceability](docs/requirements.md)
- [Feature plan](docs/feature-plan.md)
- [Risk plan](docs/risk-plan.md)
- [Architecture and data design](docs/architecture.md)
- [Release 0 checklist](docs/release-0-checklist.md)
- [Browser checklist](docs/frontend-browser-checklist.md)
- [Prompt log](docs/prompt-log.md)
- [Review record](docs/review-record.md)
- [Contribution log](docs/contribution-log.md)
- [Known issues](docs/known-issues.md)

Liam performs all commits, pushes, pull requests, human approvals, attendance
records, screenshots, and showcase publication.
