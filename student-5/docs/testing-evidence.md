# Testing and Evidence Index

Student 5 (Alex Chen), Release 0. Every artefact in `student-5/docs/evidence/`,
what it proves, and the exact commands to reproduce the results.

## Evidence index

| File | Type | What it proves |
|---|---|---|
| `agentic-loop-run-part1.png` | Terminal screenshot | The `run` command with all five flags (`--task`, `--context`, `--pre-test-command`, `--pre-test-result`, `--reviewer-prompt`), then `[PLAN]`, `[ACT]` with the proposed `formatElapsed` and its assertion snippet, the first reviewer `[OBSERVE]`, and the loop's `Reviewer output was malformed; requesting one format correction` retry. Establishes that the run used the custom reviewer prompt and two distinct models. |
| `agentic-loop-run-part2.png` | Terminal screenshot | `[ADAPT] Implementer model producing one bounded revision`, the revised proposal, the second `[OBSERVE]` on the adapted proposal (`Verdict: REVISE`), and `Agentic-loop record awaiting human finalisation: /workspace/docs/agentic-loop-records/20260906T053024Z-ad4b32c67df446e8af9e1fca8cc22044.json`. Proves the full Plan -> Act -> Observe -> Adapt -> Observe cycle ran and that the loop stopped for a human rather than self-applying. |
| `agentic-loop-finalise.png` | Terminal screenshot | The `finalise` command with `--record`, `--decision changed`, `--notes`, `--post-test-command` and `--post-test-result`, and the confirmation `Finalised agentic-loop record: /workspace/docs/agentic-loop-records/20260906T053024Z-ad4b32c67df446e8af9e1fca8cc22044.json`. Proves the human Adapt decision was recorded, with its reasoning, against that specific record. |
| `agentic-loop-run-final-record.json` | Record | The finalised record: task text, context file and its SHA-256, both model tags, both prompt versions and their SHA-256 hashes, generation options, Ollama version, `preTest`, `planAct`, `observe`, `reviewerVerdict`, `adaptedProposal`, `adaptedProposalReview`, `finalReviewerVerdict`, `humanDecision`, `humanNotes`, `postTest`, `finalisedAt`. The primary artefact for criterion 4. |
| `agentic-loop-records-index.txt` | Directory listing | The records directory contains `20260906T053024Z-ad4b32c67df446e8af9e1fca8cc22044.json` at 7812 bytes, written 6/09/2026 3:52 PM. Confirms the record cited above exists in the shared records volume, not only as a copy in this folder. |
| `agentic-loop-models.txt` | Health output | `{"status":"healthy","implementerModel":"qwen2.5-coder:7b","reviewerModel":"llama3.2:3b"}`. Confirms the loop was configured with two **distinct** approved model tags, as the unit requires. |
| `formatelapsed-assertions.txt` | Test output | `all assertions passed` - the post-test for the agentic-loop change, covering the seven `formatElapsed` cases recorded on the run. |
| `prompt-engineering-and-context-management-documentation.txt` | Session transcript | The build session for the advisory endpoint and HTMX fragments: the written context brief carried into the session, the prompt-tuning iterations (passport-validity invention, the negative-instruction failure, the Fiji no-transit-rows check), the notes-clearing bug found against a live database, and the suite reaching 68 tests. Supporting evidence for `prompt-engineering.md`. |
| `pytest-database.txt` | Test output | The database suite: a `[100%]` progress line followed by `26 passed in 0.84s`. Proves the count claimed for `student-5/database` in `requirements.md` and `sprint-backlog.md`. |
| `pytest-backend.txt` | Test output | The backend suite: a `[100%]` progress line followed by `68 passed in 0.54s`. Proves the count claimed for `student-5/backend`, run offline against mocked HTTP. |
| `compose-build.txt` | Build output | The tail of `docker compose build student5-database student5-backend student5-frontend`, ending in `Image advanced-software-development-project-student5-database Built`, `... -student5-backend Built` and `... -student5-frontend Built`. The capture starts mid-stream at BuildKit step `#31`, so it evidences the export stages and the result rather than every layer. |
| `compose-ps.txt` | Container status | `docker compose ps` with the stack up. `student5-database`, `student5-backend` and `student5-frontend` are each `Up About an hour (healthy)`, published on `0.0.0.0:5305->8080/tcp`, `0.0.0.0:5205->8080/tcp` and `0.0.0.0:5105->80/tcp`. The shared `ollama` shows `Up 3 hours (healthy)`. |

That table is the complete contents of `student-5/docs/evidence/` - twelve
files. Two things are worth knowing before opening them. The text captures
were written by PowerShell redirection, so they are UTF-16 with a BOM; read
them with `Get-Content` or an editor that detects the encoding rather than a
tool that assumes UTF-8. And `ollama-model-setup` is absent from
`compose-ps.txt` because it is a one-shot container that has already exited,
and `docker compose ps` does not list exited containers without `-a`; its
successful completion is instead implied by `student5-backend` being up at
all, since that service gates on `service_completed_successfully`.

Only two items remain uncaptured - the CI run and the application
screenshots - both listed under **Outstanding evidence** below.

## Reproduction commands

### Automated tests - run the two suites SEPARATELY

Both services define a module named `app`, so a single combined `pytest`
invocation collides on import and fails during collection. This is why
`.github/workflows/student-5.yml` has two separate test steps, and why these
commands each set their own working directory.

```bash
cd student-5/database && python -m pytest tests
```

Expected: **26 passed**.

```bash
cd student-5/backend && python -m pytest tests
```

Expected: **68 passed**.

Both suites run fully offline. The database suite gives each test its own
SQLite file through pytest's `tmp_path` fixture, so it never touches `/data` or
the checked-in `storage/` directory. The backend suite mocks the database
service and Ollama with `responses`, which is only possible because the backend
has no file access to stub - see TL-NFR-01 in `requirements.md`.

Dependencies, if not already installed:

```bash
pip install -r student-5/database/requirements.txt -r student-5/backend/requirements.txt
```

Captured output: `evidence/pytest-database.txt` ends `26 passed in 0.84s` and
`evidence/pytest-backend.txt` ends `68 passed in 0.54s`, each after a `[100%]`
progress line. Both were produced by the two commands above.

### Compose configuration and image builds

From the repository root:

```bash
docker compose config --quiet
```

Expected: no output, exit 0 - every variable and service definition resolves.

```bash
docker compose build student5-database student5-backend student5-frontend
```

Expected: all three images build.

Captured output: `evidence/compose-build.txt`, whose closing three lines are
`Image advanced-software-development-project-student5-database Built`,
`... -student5-backend Built` and `... -student5-frontend Built`. The file is a
tail of the build log - it begins at BuildKit step `#31` - so it evidences the
outcome of the build, not every layer. `docker compose config --quiet` has no
output to attach: on success it prints nothing and exits 0, which is the whole
point of `--quiet`. It runs as its own step in `.github/workflows/student-5.yml`,
so a config that stopped resolving would fail the workflow.

### Running the stack

```bash
docker compose up --build student5-database student5-backend student5-frontend ollama ollama-model-setup
```

The advisory endpoint needs `ollama` and `ollama-model-setup`; the read-only
panels and all CRUD work without them.

Captured output: `evidence/compose-ps.txt`, taken with the stack up, shows
`student5-database`, `student5-backend` and `student5-frontend` all
`Up About an hour (healthy)` on host ports 5305, 5205 and 5105 respectively,
alongside `ollama` at `Up 3 hours (healthy)`. All three Student 5 healthchecks
therefore pass in the integrated stack, not just in isolation.

### Health checks

```bash
curl http://localhost:5305/health
```

Expected: `{"service":"student5-database","status":"ok"}`

```bash
curl http://localhost:5205/health
```

Expected: `{"service":"student5-backend","status":"ok"}`

```bash
curl http://localhost:5105/health
```

Expected: `ok` (plain text, served by nginx itself - it deliberately reports
nothing about the backend, so a backend outage does not restart the frontend).

On Windows PowerShell use `curl.exe`, not `curl` (which is an alias for
`Invoke-WebRequest`).

### Data endpoints

```bash
curl http://localhost:5205/api/destinations
```

Expected: 12 destination rows on a fresh database.

```bash
curl "http://localhost:5205/api/weather-notes?destination_id=1"
```

Expected: the weather notes recorded for Japan.

### The AI advisory endpoint (the marked workflow)

```bash
curl -X POST http://localhost:5205/api/advisory -H "Content-Type: application/json" -d "{\"destination_id\":1,\"month\":\"October\",\"interests\":\"hiking, street food\"}"
```

Expected: `{"advisory": "...", "model": "llama3.2:3b", "destination": {...}}`.
A cold 3B model on CPU can take well over a minute on the first call; the client
timeout is 120s.

To prove grounding, ask for Fiji (id 12), which has no transit options recorded:

```bash
curl -X POST http://localhost:5205/api/advisory -H "Content-Type: application/json" -d "{\"destination_id\":12}"
```

Expected: the Transit section states that no transit options are recorded rather
than inventing ferries.

To see the failure path, stop the database and repeat any data call:

```bash
docker compose stop student5-database && curl -i http://localhost:5205/api/destinations
```

Expected: `503` with `{"error": "database service unavailable"}` - distinct from
the `{"error": "ai service unavailable"}` body an Ollama outage produces.

### Reproducing the agentic-loop run

```bash
docker compose exec agentic-loop dotnet /app/AgenticLoop.dll healthcheck
```

Expected: the JSON in `agentic-loop-models.txt`. The `run` and `finalise`
commands as executed are in `prompt-log.md`. A re-run will not reproduce the
same record id, and the reviewer's output is not guaranteed to repeat - the
saved record and screenshots are the evidence.

## `student-5.yml` workflow description

`.github/workflows/student-5.yml` defines one job, `logistics-services`, on
`ubuntu-latest`. It has `permissions: contents: read` - the job only ever reads
the repository, so it is given nothing else. It triggers on both `push` and
`pull_request`, filtered to three path sets: `student-5/**`, `docker-compose.yml`
and `.github/workflows/student-5.yml`. The second path matters as much as the
first: this feature's ports, dependency conditions and bind mount live in the
shared Compose file, so a change made there by another student re-runs these
checks rather than silently breaking the stack.

| # | Step | What it validates |
|---:|---|---|
| 1 | `actions/checkout@v4` | The workflow runs against the pushed tree, not a cached one. |
| 2 | `actions/setup-python@v5`, `python-version: "3.11"`, `cache: pip` keyed on both `requirements.txt` files | That the code runs on the same minor version the containers use (`python:3.11-slim`), so a 3.12-only syntax or stdlib change cannot pass CI and then fail in the image. The cache key covers both requirement files, so adding a dependency to either service invalidates it. |
| 3 | `pip install -r student-5/database/requirements.txt` | The database service's declared dependencies are complete and installable from a clean machine. |
| 4 | `pip install -r student-5/backend/requirements.txt` | The same for the backend, including the test-only `responses` mock library. |
| 5 | `Test database API` - `working-directory: student-5/database`, `python -m pytest tests` | The 26 database tests: schema, seed-once behaviour, CRUD, partial-merge `PUT`, cascade deletes, and error bodies. Each test gets its own `tmp_path` SQLite file, so CI never needs the checked-in `storage/` directory. |
| 6 | `Test backend orchestration` - `working-directory: student-5/backend`, `python -m pytest tests` | The 68 backend tests: JSON passthrough, advisory grounding, both distinct 503 paths, 404 forwarding, and every `/ui/` fragment. Kept as a **separate step with its own working directory** because both services define a module named `app`; one combined `pytest` invocation collides on import and fails at collection. |
| 7 | `docker compose config --quiet` | That the whole Compose file still resolves - every variable, every `depends_on` target, every port. It prints nothing on success, so a non-zero exit is the signal. This is what catches a typo in a service name or an unset variable before anyone tries to start the stack. |
| 8 | `docker compose build student5-database student5-backend student5-frontend` | That all three images build from their Dockerfiles on a clean machine. |

No step needs a live model. Ollama is never started in CI, and no test calls it:
the backend suite mocks `/api/generate` with `responses`. That is deliberate -
pulling a 3B model on every push would make the workflow slow and flaky, and the
generation itself is the one thing a unit test cannot assert on anyway. The AI
path is instead evidenced by the local run captured in `compose-ps.txt` and by
the advisory commands above.

## Outstanding evidence

Two items, and only these two, are still missing.

| Item | How to obtain |
|---|---|
| **TODO: attach CI run screenshot or URL** | GitHub Actions tab, workflow "Student 5 CI" (`.github/workflows/student-5.yml`). It triggers on any push or PR touching `student-5/**`, `docker-compose.yml`, or the workflow file. The locally captured equivalents of its test and build steps are in `pytest-database.txt`, `pytest-backend.txt` and `compose-build.txt`, but those are not evidence of a green run on GitHub. |
| **TODO: attach application screenshots** | `http://localhost:5105/` with the stack up: (1) the page loaded with weather, visa and transit panels populated; (2) a generated advisory in `#advisory-panel` with the model tag in its footer; (3) the elapsed counter mid-generation showing `Ns` or `still working - Ns`; (4) the Manage destinations section through a create, an inline edit, and a delete confirmation. |

Everything else on this page now points at a committed file: pytest output at
`pytest-database.txt` and `pytest-backend.txt`, the image builds at
`compose-build.txt`, the healthy integrated stack at `compose-ps.txt`, and the
agentic-loop run at the three screenshots plus
`agentic-loop-run-final-record.json`.
