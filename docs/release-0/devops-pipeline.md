# Release 0 DevOps Pipeline Architecture

How a change travels from a developer's machine to validated, buildable
containers: GitHub as the shared repository, five path-filtered GitHub Actions
workflows, and local Docker Compose execution where AI-Mode is actually
exercised.

## Diagram

```mermaid
flowchart TD
    dev["<b>Developer</b><br/>feature branch from main<br/>commit and push"]
    gh["<b>GitHub repository</b><br/>pull request into main<br/>human review and merge"]
    paths{"Path filters on push and pull_request<br/>each workflow watches its own paths"}
    skip["No run<br/>the change touched none of a<br/>workflow's declared paths"]

    subgraph ci["GitHub Actions - ubuntu-latest, permissions: contents read"]
        w1["<b>student-1.yml</b> - Student 1 CI<br/>job accommodation-services:<br/>npm test + npm run build, dotnet test backend,<br/>dotnet test database, compose config, compose build<br/>job agentic-loop:<br/>dotnet test AgenticLoop.Tests, docker build,<br/>compose build agentic-loop"]
        w2["<b>student-2.yml</b> - Student 2 CI<br/>Vitest frontend, pytest backend, pytest database,<br/>compose config, compose build,<br/>compose up the 3 services,<br/>smoke: 3 health endpoints,<br/>plus /api/trips returns at least 10 trips"]
        w3["<b>student-3.yml</b> - Student 3 CI<br/>pytest tests, compose config, compose build,<br/>run student3-db-init, compose up the 3 services,<br/>smoke: 3 health endpoints,<br/>plus /api/attractions returns at least 10 rows"]
        w4["<b>student-4.yml</b> - Student 4 CI<br/>npm run validation, compose config, compose build,<br/>compose up 3 services + shared-frontend,<br/>smoke: health, budgets, expenses, dashboard,<br/>and the /budget/ page through the gateway"]
        w5["<b>student-5.yml</b> - Student 5 CI<br/>pytest database, pytest backend,<br/>compose config, compose build"]
    end

    cd["<b>cloud-deployment.yml</b><br/>workflow_run after the five CI workflows<br/>echo placeholder only - not Release 0 work"]

    subgraph local["Local Docker Compose execution - AI-Mode"]
        up["docker compose up -d --build --wait<br/>all 20 services from one shared file"]
        models["ollama-model-setup pulls missing tags,<br/>preloads APPLICATION_MODEL, exits 0"]
        app["Integrated app at http://localhost:5100<br/>five features behind the shared gateway"]
        aim["AI-Mode end to end<br/>frontend -> backend/API -> ollama:11434 -> LLM<br/>llama3.2:3b and qwen2.5:3b"]
        loop["agentic-loop container<br/>implementer qwen2.5-coder:7b plans and acts,<br/>reviewer llama3.2:3b observes,<br/>human adapts and finalises the record"]
        up --> models --> app --> aim
        app --> loop
    end

    note["No workflow starts Ollama or pulls a model.<br/>AI behaviour is evidenced locally, not in CI."]

    dev --> gh --> paths
    paths -->|"no match"| skip
    paths -->|"student-1 paths"| w1
    paths -->|"student-2 paths"| w2
    paths -->|"student-3 paths"| w3
    paths -->|"student-4 paths"| w4
    paths -->|"student-5 paths"| w5
    w1 --> cd
    w2 --> cd
    w3 --> cd
    w4 --> cd
    w5 --> cd
    ci -.- note
    w1 -->|"images proven to build"| up
    w5 -->|"images proven to build"| up
```

## Commit to GitHub

Work happens on a feature branch cut from `main`, is pushed to the shared GitHub
repository, and reaches `main` through a pull request. Both events matter to the
pipeline: every student workflow declares `push` and `pull_request` triggers, so
a branch push validates work in progress and the pull request validates the
merge candidate. All five workflows run on `ubuntu-latest` with
`permissions: contents: read` and nothing more.

## Path filters

Each workflow watches only the paths it owns, so an unrelated change does not
spend CI minutes on all five features.

| Workflow | Watched paths |
|---|---|
| `student-1.yml` | `student-1/**`, `shared/vue-frontend/**`, `ai-services/agentic-loop/**`, `docker-compose.yml`, `.env.example`, `scripts/verify-agentic-models.ps1`, itself |
| `student-2.yml` | `student-2/**`, `shared/vue-frontend/**`, `docker-compose.yml`, itself |
| `student-3.yml` | `student-3/**`, `shared/vue-frontend/**`, `docker-compose.yml`, itself |
| `student-4.yml` | `student-4/**`, `shared/vue-frontend/**`, `package.json`, `scripts/test-student4.ps1`, `.env.example`, `docker-compose.yml`, itself |
| `student-5.yml` | `student-5/**`, `shared/vue-frontend/**`, `docker-compose.yml`, itself |

Two entries are on every list, and both are deliberate. `docker-compose.yml`
holds every feature's ports, dependency conditions and bind mounts in one shared
file, so a change there re-runs all five sets of checks rather than silently
breaking another feature. `shared/vue-frontend/**` is the gateway and home page
every feature is reached through, so a change there is validated against all five
features' builds.

Aside from paths, the five triggers are uniform: `push` and `pull_request` on any
branch. `student-4.yml` additionally exposes `workflow_dispatch` for manual runs.

## What each workflow builds and validates

Every workflow follows the same shape - install, test, validate the shared
Compose file, build images - and three of them go on to start containers and
smoke-test them.

- **`student-1.yml`** runs two independent jobs. `accommodation-services` sets up
  Node 22 and .NET 8, runs `npm ci`, `npm test` and `npm run build` for the Vue
  frontend, `dotnet test` for the backend and database API projects, then
  `docker compose config --quiet` and a Compose build of `shared-frontend` and
  the three Student 1 images. `agentic-loop` restores and tests
  `ai-services/agentic-loop/tests/AgenticLoop.Tests.csproj`, builds the image
  directly with `docker build`, and builds it again through Compose. It is the
  only workflow that validates the shared agentic loop.
- **`student-2.yml`** sets up Python 3.11 and Node 22, runs the frontend Vitest
  suite and both pytest suites, validates the Compose config, builds the shared
  and Student 2 images, starts the three Student 2 services with
  `--no-deps --wait`, and smoke-tests the three `/health` endpoints plus
  `/api/trips`, asserting at least 10 seeded trips. It tears down with
  `docker compose down` in an `if: always()` step.
- **`student-3.yml`** runs one `pytest tests` invocation from `student-3/` that
  covers both services, validates the Compose config, builds the shared and
  Student 3 images including `student3-db-init`, runs that init container to
  create and seed the schema, starts the three services, and smoke-tests the
  three `/health` endpoints plus `/api/attractions`, asserting at least 10 seeded
  attractions.
- **`student-4.yml`** runs `npm --prefix student-4/frontend run validation`,
  which installs dependencies, runs the frontend, backend and database suites and
  builds both frontends. It then validates the Compose config, builds the shared
  and Student 4 images, starts the Student 4 services together with
  `shared-frontend`, and smoke-tests health endpoints, seeded budgets and
  expenses, the dashboard endpoint, and the `/budget/` page fetched through the
  gateway on port 5100. It is the only workflow that asserts a feature is
  reachable through the shared entry point.
- **`student-5.yml`** installs both requirements files with pip caching and runs
  the database and backend pytest suites as two separate steps with different
  `working-directory` values - both services define a module named `app`, so a
  single combined run collides on import. It then validates the Compose config
  and builds the three Student 5 images. It starts no containers.

`.github/workflows/cloud-deployment.yml` triggers on `workflow_run` completion of
the five student workflows and runs a single `echo` step. It deploys nothing;
cloud deployment is not a Release 0 deliverable.

## Local Docker Compose execution and AI-Mode

CI proves that source is tested and that every image builds. It deliberately does
not run a model: no workflow starts the `ollama` service, and the backend suites
mock Ollama, which keeps CI fast and deterministic. AI-Mode is therefore
evidenced by the local integrated run.

```powershell
Copy-Item .env.example .env
docker compose up -d --build --wait
```

`ollama-model-setup` pulls any missing tag into the shared `ollama-data` volume,
preloads `APPLICATION_MODEL`, and exits; only then do the five backends start.
With the stack healthy, `http://localhost:5100` serves the shared home page and
each feature is exercised through it, including the AI request path
frontend -> backend/API -> Ollama -> approved LLM. The shared `agentic-loop`
container runs beside the application on port 5180 and is driven from the
terminal: the implementer model plans and acts, the reviewer model observes, the
loop writes a JSON record under `docs/agentic-loop-records/`, and a human makes
the Adapt decision and finalises the record.

Evidence of both - a healthy Compose stack and a finalised agentic-loop record -
belongs in the technical report; see [`README.md`](README.md) in this folder for
where each artefact currently lives.
