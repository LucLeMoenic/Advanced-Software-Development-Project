# Advanced Software Development Project

Template repository for the 2026 Advanced Software Development project. The project will grow into a containerised Agentic AI application composed of five student-owned frontend, backend/API, and database microservice sets.

## Current Status

The integrated Compose application includes the shared Vue home page, the Student 1 Accommodation Recommender, the Student 2 Itinerary Planner, the shared Ollama runtime, and the bounded .NET agentic loop. Other student services remain independently owned.

## Repository Structure

```text
.
├── .github/workflows/       GitHub Actions workflow templates
├── ai-services/             Shared Ollama, MCP, RAG, and agent services
├── docs/                    Architecture diagrams, reports, and evidence
├── scripts/                 Build, test, and deployment scripts
├── shared/                  Shared application assets and Vue frontend
├── student-1/ ... student-5/ Frontend, backend, database, and tests per student
├── docker-compose.yml       Local multi-container application configuration
└── Project_Specifications/  Project requirements
```

## Prerequisites

- Git
- Docker Desktop
- Node.js 22 for local frontend builds and tests
- .NET 8 SDK for local backend, database, and agentic-loop tests

## Student 1 Accommodation Setup

Run these commands from the repository root in PowerShell.

1. Configure the application and development model tags:

   ```powershell
   Copy-Item .env.example .env
   docker compose config --quiet
   ```

2. Restore dependencies, run every Student 1 test, and build the integrated images:

   ```powershell
   npm ci --prefix student-1/frontend
   npm test --prefix student-1/frontend
   npm run build --prefix student-1/frontend
   dotnet restore student-1/backend/tests/Backend.Tests.csproj
   dotnet test student-1/backend/tests/Backend.Tests.csproj --configuration Release --no-restore
   dotnet restore student-1/database/tests/Database.Tests.csproj
   dotnet test student-1/database/tests/Database.Tests.csproj --configuration Release --no-restore
   docker compose build shared-frontend student1-frontend student1-backend student1-database
   ```

3. Start the shared page and Student 1 services. Compose starts one shared Ollama runtime, installs any missing models from `OLLAMA_MODELS`, and preloads `APPLICATION_MODEL` before the backend starts:

   ```powershell
   docker compose up -d --build --wait shared-frontend
   ```

   On a Windows machine with an NVIDIA GPU available to Docker, start the Student 1 services with automatic GPU acceleration:

   ```powershell
   .\scripts\start-student1.ps1
   ```

   To start the complete integrated application with GPU acceleration explicitly enabled for Ollama:

   ```powershell
   .\scripts\start-app.ps1 -Gpu
   ```

   Omit `-Gpu` to run the complete application in CPU mode.

   CPU-only machines continue to use the main Compose file without the optional `docker-compose.gpu.yml` override.

4. Open `http://localhost:5100` and select **Accommodation Recommender**, or open `http://localhost:5100/accommodation/` directly.

5. Check service health:

   ```powershell
   Invoke-WebRequest http://localhost:5100/health
   Invoke-WebRequest http://localhost:5101/health
   Invoke-WebRequest http://localhost:5201/health
   Invoke-WebRequest http://localhost:5301/health
   docker compose ps shared-frontend student1-frontend student1-backend student1-database ollama
   ```

6. The tracked SQLite file already contains the required search-history examples. Accommodation records are intentionally not automatically seeded; create the demonstration catalogue through the database API and confirm both tables through:

   ```powershell
   Invoke-RestMethod "http://localhost:5301/api/data/accommodations"
   Invoke-RestMethod "http://localhost:5301/api/data/searches"
   ```

7. Stop the integrated services without deleting the persistent SQLite file or Ollama models:

   ```powershell
   docker compose down
   ```

## Student 2 Itinerary Planner

Start the shared page and Student 2 services from the repository root:

```powershell
docker compose up -d --build shared-frontend
```

Open `http://localhost:5100` and select **Itinerary Planner**, or open `http://localhost:5100/itinerary/` directly. Ports `5102`, `5202`, and `5302` expose the individual services for diagnostics only.

Student 2 requirements and current readiness evidence are indexed in [`student-2/docs/README.md`](student-2/docs/README.md).

## Shared Release 0 Agentic Loop

The shared .NET service under `ai-services/agentic-loop/` uses two distinct models from the same shared Ollama runtime used by application microservices:

- Qwen implementer for Plan and Act;
- Llama reviewer for Observe;
- one bounded implementer revision plus a human-controlled Adapt decision.

Configure the shared model list and each consumer's selected model tags, then start the service. The single `ollama-model-setup` job pulls only models missing from the shared persistent Ollama volume and preloads the application model:

```powershell
Copy-Item .env.example .env
docker compose up -d agentic-loop
```

See [`ai-services/agentic-loop/README.md`](ai-services/agentic-loop/README.md) for the run/finalisation commands and evidence format.

## Development Workflow

1. Create a feature branch from `main`.
2. Implement changes in the relevant `student-x/`, `shared/`, or service directory.
3. Run the relevant local build or tests.
4. Commit with a meaningful message and open a pull request.
5. Update documentation and testing evidence in `docs/`.

See [`Project_Specifications/Project_Specifications.md`](Project_Specifications/Project_Specifications.md) for the full release requirements and assessment criteria.