# Agentic AI Trip Planning & Travel Management Platform

Group 45's Release 0 application with Release 1 integration in progress for Advanced Software Development.
The platform is a containerised, microservice-based trip planning and travel
management system: five student-owned feature sets, each of which is its own
frontend, backend/API and SQLite database microservice, plus shared AI services
(one Ollama runtime and a two-model agentic development loop). A single shared
Vue home page at `http://localhost:5100` is the entry point and routes to every
feature, and one shared `docker-compose.yml` at the repository root builds and
runs the feature microservices. Shared AI services now run natively on the host;
see the [Release 1 runbook](student-2/docs/release-1-runbook.md) for setup and current validation gaps.

## Features

| # | Feature | Owner | Gateway path | Direct host ports (frontend / backend / database) |
|---|---|---|---|---|
| 1 | Accommodation Recommender | Mitchell Harris | `/accommodation/` | 5101 / 5201 / 5301 |
| 2 | Itinerary Planner | Luc Le Moenic | `/itinerary/` | 5102 / 5202 / 5302 |
| 3 | Local Experience & Attraction Recommender | Khushi Sharma | `/attractions/` | 5103 / 5203 / 5303 |
| 4 | Budget & Expense Tracker | Liam Zelmanowski | `/budget/` | 5104 / 5204 / 5304 |
| 5 | Travel Logistics & Advisory | Alex Chen | `/logistics/` | 5105 / 5205 / 5305 |

Gateway paths are relative to `http://localhost:5100`. The direct host ports are
for diagnostics; the supported browser route for every feature is through the
shared home page.

Shared services: `shared-frontend` (home page and reverse proxy, port 5100),
native Ollama (port 11434), native MCP (5400), native RAG (5500), and the native
agentic-loop CLI. Only the shared frontend is a Compose service.

## Prerequisites

Required to run the application:

- Docker Desktop, with Docker Compose
- Git
- Native Ollama and the configured model tags
- Native Python 3.11+ for MCP/RAG and .NET 8 for the shared loop

Required only to run tests or builds outside containers:

- Node.js 22 - Student 1, 2 and 4 frontend test suites and the shared Vue frontend build
- .NET 8 SDK - Student 1 and Student 4 backend/database test suites and the agentic-loop test suite
- Python 3.11 - Student 2, 3 and 5 backend/database pytest suites

## Run the whole application

From the repository root:

1. Create an environment file only if one does not already exist. Configure native
  services and private host access using the [runbook](student-2/docs/release-1-runbook.md).

   ```powershell
  if (!(Test-Path .env)) { Copy-Item .env.example .env }
   ```

  On bash: `test -f .env || cp .env.example .env`.

2. Start native MCP/RAG/Ollama separately, then build the feature services:

   ```powershell
   docker compose up -d --build --wait
   ```

  `scripts/deploy/start-app.ps1` runs the same command and opens the browser.
  `scripts/deploy/start-release1.ps1` starts native Ollama, MCP and RAG, then
  every Compose service with MCP/RAG enabled; `-Stop` shuts all of them down.
   Native Ollama controls GPU use; the old GPU override contains no services.

3. Open `http://localhost:5100` and choose a feature.

Pull required model tags explicitly with native `ollama pull` before demonstrating
AI paths. Compose no longer downloads models or verifies native AI readiness.
Healthy feature containers alone do not prove MCP/RAG/model connectivity.

Useful checks and shutdown:

```powershell
docker compose ps
docker compose down
```

`docker compose down` does not stop native AI processes and keeps SQLite files, which
are bind-mounted from each student's `database/storage/` directory.

Optional configuration: `LITEAPI_KEY` in `.env` enables the Student 1 backend's
LiteAPI sandbox catalogue import. Everything else runs without it.

## Repository structure

```text
.
├── .github/workflows/           student-1.yml .. student-5.yml, cloud-deployment.yml
├── ai-services/
│   ├── agentic-loop/            .NET 8 two-model Plan/Act/Observe/Adapt service
│   └── README.md
├── docs/
│   ├── Project_Specifications/  Project specification and Release 0 brief
│   ├── agentic-loop-records/    Finalised JSON records from the agentic loop
│   ├── release-0/               Release 0 deliverable index and architecture docs
│   └── README.md
├── scripts/                     PowerShell startup and validation helpers
├── shared/
│   └── vue-frontend/            Shared home page and nginx gateway (port 5100)
├── student-1/ .. student-5/     One feature each:
│   ├── frontend/                nginx-served UI
│   ├── backend/                 Backend/API service
│   ├── database/                SQLite database API service and storage/
│   └── docs/                    That student's Release 0 documentation
├── docker-compose.yml           The single shared Compose configuration
├── docker-compose.gpu.yml       Empty compatibility override; GPU is host-native
└── .env.example                 Model tags and optional API keys
```

Test locations vary by stack: Students 1, 2, 4 and 5 keep tests under
`backend/tests/` and `database/tests/`, while Student 3 keeps a single
`student-3/tests/` suite covering both of its services.

## AI services

- **Ollama runtime** - one native host runtime serves every model
  for the whole group on port 11434. No frontend calls it; every AI request goes
  frontend -> backend/API -> Ollama -> LLM.
- **Model setup** - install and pull the configured models natively. No model
  provisioning container or Compose dependency remains.
- **Shared MCP/RAG** - native services expose read-only tools and generated,
  cited feature-knowledge answers through feature backends. See their
  [MCP](ai-services/mcp-server/README.md) and [RAG](ai-services/rag-server/README.md) contracts.
- **Approved models in use** (from `.env.example` and `docker-compose.yml`):

  | Tag | Used by |
  |---|---|
  | `llama3.2:3b` | `APPLICATION_MODEL` for Students 1, 2 and 5; `STUDENT4_MODEL` for Student 4; reviewer role in the agentic loop |
  | `qwen2.5:3b` | `STUDENT3_MODEL` for Student 3's `/api/recommend` |
  | `qwen2.5-coder:7b` | implementer role in the agentic loop |

- **Shared agentic loop** - `ai-services/agentic-loop/` is a native .NET 8 CLI
  implementing Plan -> Act -> Observe -> Adapt with two distinct models from the
  same Ollama runtime: the implementer (`IMPLEMENTER_MODEL`) plans and acts, the
  reviewer (`REVIEWER_MODEL`) observes, and the Adapt decision is made by a
  human. Release 1 adds MCP/RAG validation modes using bounded read-only backend
  observations. The service never writes source files or runs shell commands; it writes
  auditable JSON records to `docs/agentic-loop-records/`. Run and finalisation
  commands are in [`ai-services/agentic-loop/README.md`](ai-services/agentic-loop/README.md).

## Continuous integration

Six workflows in `.github/workflows/`, each triggered by pushes and pull
requests touching its own paths.

| Workflow | Triggering paths | What it validates |
|---|---|---|
| `student-1.yml` | `student-1/**`, `shared/vue-frontend/**`, `ai-services/agentic-loop/**`, `docker-compose.yml`, `.env.example`, `scripts/test/verify-agentic-models.ps1`, `scripts/test/student-1.ps1`, the workflow file | Feature tests and container builds; shared loop tests and native .NET publishing. |
| `student-2.yml` | `student-2/**`, `shared/vue-frontend/**`, `docker-compose.yml`, the workflow file | Frontend Vitest suite, backend and database pytest suites, Compose config validation, Compose builds, then starts the three Student 2 services and smoke-tests their `/health` endpoints and `/api/trips`. |
| `student-3.yml` | `student-3/**`, `shared/vue-frontend/**`, `docker-compose.yml`, the workflow file | Single `pytest tests` run covering both services, Compose config validation, Compose builds, a `student3-db-init` run to create and seed the schema, service startup with health waits, and a smoke test of the three `/health` endpoints and `/api/attractions`. |
| `student-4.yml` | `student-4/**`, `shared/vue-frontend/**`, `package.json`, `scripts/test/student-4.ps1`, `.env.example`, `docker-compose.yml`, the workflow file | `scripts/test/student-4.ps1` runs the frontend, backend, and database suites plus both frontend builds; the workflow validates Compose, builds the containers, starts the Student 4 services behind the shared frontend, and smoke-tests `/health`, seeded budgets and expenses, the dashboard endpoint, and the `/budget/` page through the gateway. It also exposes `workflow_dispatch` for manual runs. |
| `student-5.yml` | `student-5/**`, `shared/vue-frontend/**`, `docker-compose.yml`, `scripts/test/student-5.ps1`, the workflow file | Database and backend pytest suites run as separate steps, followed by Compose config validation and builds of the three Student 5 images. |
| `integration-ci.yml` | `student-*/**`, `shared/**`, `ai-services/**`, `docker-compose.yml`, `.env.example`, the workflow file | Builds all Compose-defined images and runs a model-independent smoke gate against database, API, frontend, and shared gateway health endpoints. The model-dependent agentic loop remains covered by `student-1.yml`; local full-stack AI evidence is separate. |

No workflow starts Ollama or pulls a model, so AI behaviour is evidenced by
local native-service integration runs rather than by CI. Student 2 smoke tests
explicitly disable AI/MCP/RAG; other feature teams must verify their own mode controls.

`.github/workflows/cloud-deployment.yml` also exists. It triggers after the five
student workflows complete successfully and currently only echoes a placeholder
message; cloud deployment is not Release 0 work.

## Documentation

- [Release 0 deliverable index](docs/release-0/README.md) - integrated architecture, Compose architecture and DevOps pipeline diagrams, and the evidence map
- [Project specification](docs/Project_Specifications/Project_Specifications.md) and [Release 0 brief](docs/Project_Specifications/Release_0_brief.md)
- [Shared AI services](ai-services/README.md)

Per-student documentation:

| Student | Feature | Docs |
|---|---|---|
| 1 | Accommodation Recommender | [`student-1/docs/`](student-1/docs/) |
| 2 | Itinerary Planner | [`student-2/docs/`](student-2/docs/README.md) |
| 3 | Local Experience & Attraction Recommender | [`student-3/docs/`](student-3/docs/) |
| 4 | Budget & Expense Tracker | [`student-4/docs/`](student-4/docs/) |
| 5 | Travel Logistics & Advisory | [`student-5/docs/`](student-5/docs/) |

## Development workflow

1. Create a feature branch from `main`.
2. Implement changes in the relevant `student-N/`, `shared/`, or service directory.
3. Run the relevant local build or tests.
4. Commit with a meaningful message and open a pull request.
5. Update documentation and evidence under `student-N/docs/` or `docs/`.

Release 1 (MCP, RAG), Release 2 (multi-agent services) and cloud deployment are
out of scope for Release 0 and are not implemented in this repository.
