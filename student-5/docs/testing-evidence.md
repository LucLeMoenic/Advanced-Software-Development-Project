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

There are **no other Student 5 evidence artefacts**. Everything marked TODO
below has not been captured yet.

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

**TODO: attach pytest output** - capture both invocations above.

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

**TODO: attach Docker Compose output** - capture both commands above.

### Running the stack

```bash
docker compose up --build student5-database student5-backend student5-frontend ollama ollama-model-setup
```

The advisory endpoint needs `ollama` and `ollama-model-setup`; the read-only
panels and all CRUD work without them.

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

## Outstanding evidence

| Item | How to obtain |
|---|---|
| **TODO: attach CI run screenshot or URL** | GitHub Actions tab, workflow "Student 5 CI" (`.github/workflows/student-5.yml`). It triggers on any push or PR touching `student-5/**`, `docker-compose.yml`, or the workflow file. |
| **TODO: attach application screenshots** | `http://localhost:5105/` with the stack up: (1) the page loaded with weather, visa and transit panels populated; (2) a generated advisory in `#advisory-panel` with the model tag in its footer; (3) the elapsed counter mid-generation showing `Ns` or `still working - Ns`; (4) the Manage destinations section through a create, an inline edit, and a delete confirmation. |
| **TODO: attach pytest output** | The two commands above. |
| **TODO: attach Docker Compose output** | `docker compose config --quiet` and `docker compose build ...` above. |
| **TODO: attach a `docker compose ps` capture** | Shows all three Student 5 services reporting `healthy`. |
