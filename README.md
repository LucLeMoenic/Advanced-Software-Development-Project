# Advanced Software Development Project

Template repository for the 2026 Advanced Software Development project. The project will grow into a containerised Agentic AI application composed of five student-owned frontend, backend/API, and database microservice sets.

## Current Status

The repository currently contains the initial project structure and a working Vue 3 + Vite frontend boilerplate. The remaining microservice, AI, testing, CI/CD, and deployment folders contain templates for team development.

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
- Node.js 18 or newer for the Vue frontend
- Python 3.x for backend services
- Ollama for local approved open-source LLM integration

## Vue Frontend

The shared frontend is located in `shared/vue-frontend/` and uses Vue 3 with Vite.

Install dependencies and start the development server:

```bash
cd shared/vue-frontend
npm install
npm run dev
```

Open the URL shown by Vite, normally `http://localhost:5173`.

Create a production build:

```bash
cd shared/vue-frontend
npm run build
```

## Docker

Build and run the Vue frontend as an nginx container from the repository root:

```bash
docker build -t asd-vue-frontend:latest \
	-f shared/vue-frontend/Dockerfile shared/vue-frontend
docker run --rm -p 5100:80 asd-vue-frontend:latest
```

The current Compose file is a starting point for the integrated application. Services should be added as each student implements and integrates their microservice set.

```bash
docker compose up --build
```

Start only the Student 1 application and print its localhost URLs:

```powershell
.\scripts\start-student1.ps1
```

## Shared Release 0 Agentic Loop

The shared .NET service under `ai-services/agentic-loop/` uses two distinct models from the local Ollama runtime:

- Qwen implementer for Plan and Act;
- Llama reviewer for Observe;
- one bounded implementer revision plus a human-controlled Adapt decision.

Configure the local model tags and start the service. Compose pulls a configured model only when it is missing from the persistent Ollama volume:

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