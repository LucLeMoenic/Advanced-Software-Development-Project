# Student 1 Release 1 Runbook - Trip Assistant (MCP and RAG)

This runbook covers how to start, enable, demonstrate and validate the
Accommodation Recommender's Trip assistant:

- **Catalogue lookup** (MCP): [MCP HLD](release-1-mcp-hld.md)
- **Destination guide** (RAG): [RAG HLD](release-1-rag-hld.md)

Run every command from the repository root.

## 1. Prerequisites

- Docker Desktop (or another Compose-compatible engine), .NET 8, Node 22, and
  Python 3.11+.
- Native Ollama with the approved models:

  ```powershell
  ollama pull llama3.2:3b
  ollama pull qwen2.5-coder:7b
  ```

  - The application uses `llama3.2:3b` for lookup-argument extraction, for RAG
    generation and for opt-in ranking.
  - The loop also needs `qwen2.5-coder:7b` as the implementer model.
  - Do not run Ollama, MCP, RAG or the loop in Compose.
- Separate Python virtual environments, one per shared service. Create them
  outside the repository or in an ignored folder:

  ```powershell
  python -m venv ..\venv-mcp
  python -m venv ..\venv-rag
  ..\venv-mcp\Scripts\python -m pip install -r ai-services/mcp-server/requirements.txt
  ..\venv-rag\Scripts\python -m pip install -r ai-services/rag-server/requirements.txt
  ```

## One-command start

`scripts/deploy/start-release1.ps1` does sections 2 and 3 in one step:

1. Starts native Ollama if it is not already running, pulls `APPLICATION_MODEL` if it is missing, and preloads it.
2. Creates the MCP and RAG virtual environments on first use (`../venv-mcp` and `../venv-rag`).
3. Starts the MCP and RAG servers in the background.
4. Starts every Compose service (with the empty GPU override) with `MCP_ENABLED`/`RAG_ENABLED=true`.
5. Checks that the backend container can reach the native services.

```powershell
pwsh -File scripts/deploy/start-release1.ps1
pwsh -File scripts/deploy/start-release1.ps1 -Stop
```

The script is safe to rerun: services that are already running are reused.
`-Stop` shuts down every Compose service, the MCP and RAG servers and Ollama.
Installed models stay on disk. From inside `scripts/deploy`, PowerShell needs
the `.\` prefix: `.\start-release1.ps1 -Stop`.

Native logs and process IDs are kept in `$env:TEMPsd-release1`. `-Stop` stops
only the native processes the script started, then runs `docker compose down`
(volumes are kept).

## 2. Start the native services

Start each service in its own terminal. They bind to loopback only:

```powershell
..\venv-mcp\Scripts\python ai-services/mcp-server/server.py
```

```powershell
..\venv-rag\Scripts\python -m uvicorn server:app --host 127.0.0.1 --port 5500 --app-dir ai-services/rag-server
```

- Ollama must already be listening on `127.0.0.1:11434`.
- The MCP tools read the database API at `STUDENT1_DATABASE_API_URL`, which
  defaults to `http://127.0.0.1:5301` (the published port of
  `student1-database`).
- Restart the RAG server after editing `knowledge/student-1/`, because indexes
  are cached.

Warm the model before the first demo question. Lookup extraction allows 60 s for
a cold load, but a cold load can exceed the RAG server's 20 s model deadline:

```powershell
ollama run llama3.2:3b "ready" --keepalive 30m
```

## 3. Enable the modes and start the containers

`docker-compose.yml` defaults `MCP_ENABLED` and `RAG_ENABLED` to `false`, which
is the CI setting. For the demo, set both to `true` in `.env` (see
`.env.example`), or set them for the shell:

```powershell
$env:MCP_ENABLED = 'true'
$env:RAG_ENABLED = 'true'
docker compose up --detach --build --wait shared-frontend student1-frontend student1-backend student1-database
```

The backend refuses to start if a flag has any value other than `true` or
`false`. `GET http://localhost:5201/` reports the active modes under `modes`.

Verify container-to-host reachability from inside the backend container, not
only from the host:

```powershell
docker compose exec -T student1-backend curl -sS -m 5 http://host.docker.internal:5500/health
docker compose exec -T student1-backend curl -sS -m 5 -o /dev/null -w "%{http_code}\n" http://host.docker.internal:5400/mcp
docker compose exec -T student1-backend curl -sS -m 5 http://host.docker.internal:11434/api/tags
```

If `host-gateway` points at a container VM rather than Windows, do the
following. Never bind these unauthenticated services to a public interface or
disable MCP DNS-rebinding protection.

1. Set `LOCAL_AI_HOST` to a verified private host address.
2. Bind MCP (`MCP_HOST`), RAG (`--host`) and Ollama to that same private address.
3. Follow Student 2's runbook, `student-2/docs/release-1-runbook.md`.

## 4. Demo questions

Open http://localhost:5100/accommodation/. The Trip assistant sits above the
search form.

| Mode | Question | Expected |
|---|---|---|
| Catalogue lookup | `Find stays in Tokyo for 2 guests under $200` | Tool `accommodation.find`, arguments `destination=Tokyo, guests=2, max_nightly_price=200`, and a table of active Tokyo stays, cheapest first. Expand "Raw tool result" for evidence. |
| Catalogue lookup | `Show saved search 11` | Tool `accommodation.get_search`, and saved search 11 in rank order. Preferences are not shown. |
| Catalogue lookup | `What is the weather?` | Rephrase notice with an example (`422 lookup_not_understood`); no tool call. |
| Destination guide | `Is Tokyo safe for families?` | A grounded answer with `[tokyo#…]` markers, the Tokyo citation(s), a confidence badge, and "Search accommodation in Tokyo". |
| Destination guide | `Is Barcelona or Dubai better for nightlife?` | Cross-city answer citing both guides, with one pre-fill button per city. |
| Destination guide | `Tell me about Bali` | Insufficient-context notice with no citations. |

Pressing "Search accommodation in {city}" only fills and focuses Destination;
it never submits a search or changes ranking.

Terminal equivalents through the backend container's published port:

```powershell
curl.exe -s -H "Content-Type: application/json" -d '{\"mode\":\"lookup\",\"question\":\"Find stays in Tokyo for 2 guests under $200\"}' http://localhost:5201/api/assistant
curl.exe -s -H "Content-Type: application/json" -d '{\"mode\":\"guide\",\"question\":\"Is Tokyo safe for families?\"}' http://localhost:5201/api/assistant
```

## 5. Agentic-loop validation modes

With the services and containers running, and both loop model tags available:

```powershell
$env:IMPLEMENTER_MODEL = 'qwen2.5-coder:7b'
$env:REVIEWER_MODEL = 'llama3.2:3b'
dotnet run --project ai-services/agentic-loop -- validate-mcp --feature student-1 `
  --task 'Validate the accommodation lookup tool boundary and captured result against the MCP HLD.' `
  --context ai-services/mcp-server/tools/accommodation.py `
  --context student-1/backend/Prompts/assistant-lookup-v1.txt `
  --question 'Find stays in Tokyo for 2 guests under $200'
dotnet run --project ai-services/agentic-loop -- validate-rag --feature student-1 `
  --task 'Validate the captured destination guide answer against its cited knowledge; report unsupported claims.' `
  --context ai-services/rag-server/knowledge/student-1/tokyo.md `
  --question 'Is Tokyo safe for families?'
```

- Each command writes a pending record under `docs/agentic-loop-records/`.
- Commit the pending records. Finalise them only after a human has checked the
  cited sources and run a post-test.
- Context files must stay under the loop's 16000-byte limit; the HLDs are too
  large to pass as context.

## 6. Tests

| Command | What it covers |
|---|---|
| `pwsh -NoProfile -File scripts/test/student-1.ps1 -Area All` | Everything CI runs: frontend tests and build, backend, database, Student 1 MCP tool tests, Student 1 RAG retrieval tests, and the loop. Set `STUDENT1_PYTHON` to a virtual environment's `python.exe` locally. |
| `python -m pytest tests` in `ai-services/mcp-server` and `ai-services/rag-server` | Full shared suites; run each from its own directory. |
| `$env:RAG_LIVE_EVAL='1'; python -m pytest tests/test_query.py -k live_grounding -s -v` (in `rag-server`) | Live grounding evaluation. Needs Ollama; a human must review every claim against its cited source. |

CI (`student-1.yml`) runs with `MCP_ENABLED=false` and `RAG_ENABLED=false`, uses
fakes and offline retrieval only, and never calls a model, MCP or RAG.

## 7. Known issues and limitations

| Issue | Impact | Workaround |
|---|---|---|
| On the development machine used for chunks 1-9, Docker Desktop 4.89.0 crashed at startup: "initializing Ingest server ... rename sailor-ingest.sock ... The file cannot be accessed by the system". The stale socket could not be deleted without a reboot or elevated tools. | Container-to-host reachability, container `curl` checks and the integrated `http://localhost:5100/accommodation/` checks were **not run**. | Reboot (or have Docker Desktop reset its run directory), then rerun sections 3-5. Live checks so far used natively run backend and database processes (`dotnet run`) against a scratch copy of the SQLite file. |
| Native Ollama was not installed on that machine. | Successful live lookups (extraction), grounded RAG answers, `RAG_LIVE_EVAL`, both loop modes, and the Release 0 AI-ranking re-check are **not demonstrated**. The backend returned mapped `503 dependency_unavailable`, and the loop stopped with "Ollama request failed". | Install Ollama and pull the models (section 1), then rerun sections 4-5 and capture the output. |
| Docker Desktop on Windows can leave stale socket files after sleep or an unclean shutdown. | Docker Desktop shows "An unexpected error occurred" on start-up, and `docker compose` fails with `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`. | Run `pwsh -File scripts/deploy/start-docker.ps1` (`start-release1.ps1` runs it automatically). It moves the stale sockets aside and restarts Docker Desktop. Do not choose "Reset to factory defaults"; that deletes images and volumes. Ollama models live on the host in `%USERPROFILE%\.ollama\models`, so `docker compose down` never removes them. |
| TF-IDF matches exact tokens only, and unknown words (e.g. "Bali") carry no weight. | "Where should I stay in Bali?" retrieves other cities' paragraphs at low confidence instead of insufficient; abstention then depends on the model. | Offline tests keep these cases below medium confidence. The live evaluation requires abstention. The shared thresholds are unchanged (see the RAG HLD calibration note). |
| The RAG server admits one generation at a time. | A concurrent guide question returns `503` ("busy"). | The single-question panel prevents duplicate submits; retry shortly. |
| Lookup requires the destination to appear in the question. | "NYC" or misspellings get a rephrase notice. | Use the city name as listed in the catalogue. |
| Guide content is curated demonstration text, last reviewed 2026-09. | It is not live or authoritative travel advice. | The UI labels answers as general guidance. |
