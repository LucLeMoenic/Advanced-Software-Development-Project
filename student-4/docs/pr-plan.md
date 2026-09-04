# Student 4 Pull Request Plan

Status date: 2026-09-03

The Release 0 work is split into three stacked pull requests. All three local
branch names currently point to the original `main` commit because branches
cannot capture uncommitted file subsets. After Liam commits each layer, move
the next branch to the new tip using the transition command shown below.

Do not use `git add .` or `git add -A`; each command intentionally stages only
one reviewable commit.

## PR 1: `LZ/budget-data-foundation`

Base: `main`

Purpose: land the approved design, SQLite owner, migrations, constraints,
idempotent 12/24 demonstration data, internal HTTP CRUD, health, and database
integration tests.

### Commit 1: `Document budget design`

Files (already staged):

- `student-4/docs/architecture.md`
- `student-4/docs/context.md`
- `student-4/docs/feature-plan.md`
- `student-4/docs/requirements.md`
- `student-4/docs/risk-plan.md`

```powershell
git diff --cached --check
git commit -m "Document budget design"
```

### Commit 2: `Implement budget database`

Files:

- `student-4/database/.dockerignore`
- `student-4/database/Api/Contracts.cs`
- `student-4/database/Api/DataEndpoints.cs`
- `student-4/database/appsettings.json`
- `student-4/database/Data/BudgetDbContext.cs`
- `student-4/database/Data/DemoDataSeeder.cs`
- `student-4/database/Data/Migrations/202609030001_InitialBudgetTracker.cs`
- `student-4/database/Data/Models.cs`
- `student-4/database/Database.csproj`
- `student-4/database/Dockerfile`
- `student-4/database/Program.cs`
- `student-4/database/storage/.gitkeep`

```powershell
git add -- student-4/database/.dockerignore student-4/database/Api student-4/database/appsettings.json student-4/database/Data student-4/database/Database.csproj student-4/database/Dockerfile student-4/database/Program.cs student-4/database/storage/.gitkeep
dotnet build student-4/database/Database.csproj --configuration Release
git diff --cached --check
git commit -m "Implement budget database"
```

### Commit 3: `Test budget database`

Files:

- `student-4/database/tests/Database.Tests.csproj`
- `student-4/database/tests/DatabaseApiTestBase.cs`
- `student-4/database/tests/DatabaseApiTests.cs`
- `student-4/database/tests/SeedTests.cs`

```powershell
git add -- student-4/database/tests
dotnet test student-4/database/tests/Database.Tests.csproj --configuration Release
git diff --cached --check
git commit -m "Test budget database"
```

PR validation: database tests must report 12 passed. The workflow inherited
from `main` must also pass after push.

Transition to PR 2 after all three commits:

```powershell
git branch -f LZ/budget-service-api HEAD
git switch LZ/budget-service-api
```

## PR 2: `LZ/budget-service-api`

Base while stacked: `LZ/budget-data-foundation`

Purpose: add the public backend, typed database boundary, deterministic
conversion/dashboard rules, strict Ollama advice, retry/fallback, and tests.

### Commit 1: `Implement budget API`

Files:

- `student-4/backend/.dockerignore`
- `student-4/backend/Api/BudgetEndpoints.cs`
- `student-4/backend/Api/Contracts.cs`
- `student-4/backend/Api/Validation.cs`
- `student-4/backend/appsettings.json`
- `student-4/backend/Backend.csproj`
- `student-4/backend/Clients/DatabaseApiClient.cs`
- `student-4/backend/Clients/OllamaInsightsClient.cs`
- `student-4/backend/Dockerfile`
- `student-4/backend/Program.cs`
- `student-4/backend/Prompts/budget-insights-v1.txt`
- `student-4/backend/Services/AdviceService.cs`
- `student-4/backend/Services/DashboardCalculator.cs`
- `student-4/backend/Services/ExchangeRateProvider.cs`

```powershell
git add -- student-4/backend/.dockerignore student-4/backend/Api student-4/backend/appsettings.json student-4/backend/Backend.csproj student-4/backend/Clients student-4/backend/Dockerfile student-4/backend/Program.cs student-4/backend/Prompts student-4/backend/Services
dotnet build student-4/backend/Backend.csproj --configuration Release
git diff --cached --check
git commit -m "Implement budget API"
```

### Commit 2: `Test budget API`

Files:

- `student-4/backend/tests/Backend.Tests.csproj`
- `student-4/backend/tests/CalculationTests.cs`
- `student-4/backend/tests/DatabaseApiClientTests.cs`
- `student-4/backend/tests/EndpointTests.cs`
- `student-4/backend/tests/OllamaInsightsTests.cs`

```powershell
git add -- student-4/backend/tests
dotnet test student-4/backend/tests/Backend.Tests.csproj --configuration Release
git diff --cached --check
git commit -m "Test budget API"
```

PR validation: backend tests must report 31 passed; database tests must remain
12 passed. The workflow inherited from the stacked base must also pass.

Transition to PR 3 after both commits:

```powershell
git branch -f LZ/budget-app-integration HEAD
git switch LZ/budget-app-integration
```

## PR 3: `LZ/budget-app-integration`

Base while stacked: `LZ/budget-service-api`

Purpose: add the browser UI and complete shared routing, Compose, developer
commands, CI, and evidence documentation.

### Commit 1: `Build budget tracker UI`

Files:

- `student-4/frontend/.dockerignore`
- `student-4/frontend/.gitignore`
- `student-4/frontend/app.js`
- `student-4/frontend/Dockerfile`
- `student-4/frontend/index.html`
- `student-4/frontend/nginx.conf`
- `student-4/frontend/package-lock.json`
- `student-4/frontend/package.json`
- `student-4/frontend/scripts/build.mjs`
- `student-4/frontend/style.css`

```powershell
git add -- student-4/frontend/.dockerignore student-4/frontend/.gitignore student-4/frontend/app.js student-4/frontend/Dockerfile student-4/frontend/index.html student-4/frontend/nginx.conf student-4/frontend/package-lock.json student-4/frontend/package.json student-4/frontend/scripts student-4/frontend/style.css
npm ci --prefix student-4/frontend
npm run build --prefix student-4/frontend
git diff --cached --check
git commit -m "Build budget tracker UI"
```

### Commit 2: `Test budget tracker UI`

Files:

- `student-4/frontend/tests/app.test.js`

```powershell
git add -- student-4/frontend/tests
npm test --prefix student-4/frontend
git diff --cached --check
git commit -m "Test budget tracker UI"
```

### Commit 3: `Integrate budget services`

Files:

- `.env.example`
- `.github/workflows/student-4.yml`
- `docker-compose.yml`
- `package.json`
- `scripts/README.md`
- `scripts/start-student4.ps1`
- `scripts/stop-student4.ps1`
- `scripts/test-student4.ps1`
- `scripts/validate-student4-docker.ps1`
- `shared/vue-frontend/nginx.conf`
- `shared/vue-frontend/src/App.vue`

```powershell
git add -- .env.example .github/workflows/student-4.yml docker-compose.yml package.json scripts/README.md scripts/start-student4.ps1 scripts/stop-student4.ps1 scripts/test-student4.ps1 scripts/validate-student4-docker.ps1 shared/vue-frontend/nginx.conf shared/vue-frontend/src/App.vue
npm --prefix student-4/frontend run validation
npm --prefix student-4/frontend run docker-validation
git diff --cached --check
git commit -m "Integrate budget services"
```

`npm --prefix student-4/frontend run docker-validation` requires Docker Desktop locally. If unavailable,
push only after `npm --prefix student-4/frontend run validation` passes and require the Student 4 GitHub
Actions job to supply the container result before approval.

### Commit 4: `Document release evidence`

Files:

- `README.md`
- `student-4/README.md`
- `student-4/docs/contribution-log.md`
- `student-4/docs/frontend-browser-checklist.md`
- `student-4/docs/known-issues.md`
- `student-4/docs/pr-plan.md`
- `student-4/docs/prompt-log.md`
- `student-4/docs/release-0-checklist.md`
- `student-4/docs/review-record.md`

```powershell
git add -- README.md student-4/README.md student-4/docs/contribution-log.md student-4/docs/frontend-browser-checklist.md student-4/docs/known-issues.md student-4/docs/pr-plan.md student-4/docs/prompt-log.md student-4/docs/release-0-checklist.md student-4/docs/review-record.md
git diff --cached --check
git commit -m "Document release evidence"
```

PR validation:

```powershell
npm --prefix student-4/frontend run validation
npm --prefix student-4/frontend run docker-validation
```

Expected source result: frontend 10, backend 31, and database 12 tests pass;
both frontend production builds pass. The GitHub Actions workflow must pass its
source and container jobs before merge.

## Push and PR Order

Liam performs these operations after creating the listed commits:

1. Push `LZ/budget-data-foundation` and open PR 1 against `main`.
2. Push `LZ/budget-service-api` and open PR 2 against
   `LZ/budget-data-foundation` (or wait for PR 1 and target `main`).
3. Push `LZ/budget-app-integration` and open PR 3 against
   `LZ/budget-service-api` (or wait for PR 2 and target `main`).
4. Merge PR 1, then PR 2, then PR 3. Retarget each remaining PR to `main` after
   its base merges and confirm GitHub Actions reruns successfully.

Suggested PR descriptions should state the matching purpose above, validation
commands/results, dependency on the preceding PR, and any pending human or
Docker evidence. Liam reviews and approves each PR; Copilot does not commit,
push, create, approve, or merge repository changes.