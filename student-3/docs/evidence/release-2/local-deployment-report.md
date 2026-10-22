# Release 2 local deployment report (Student 3)

Brief requirement: *"A report showing the integrated application running locally with the non-containerised Multi-Agent
Server. Include multi-service system-testing logs from multiple terminals."*

Run on 22 Oct 2026, Windows 11, 8 GB RAM, CPU-only Ollama, Docker Desktop. Evidence is in
[`local-deployment/`](local-deployment/).

## What ran, and where

| Terminal | Process | Port | Containerised? | Log |
|---|---|---|---|---|
| 1 | Ollama (`llama3.2:3b`, model preloaded, `keep_alive` 30m) | 11434 | No (host install) | `terminal-logs/terminal-1-ollama-preload.log`, `02-native-services.txt` |
| 2 | MCP server (`ai-services/mcp-server/server.py`) | 5400 | No | `terminal-logs/terminal-2-mcp-server.log` |
| 3 | RAG server (`uvicorn server:app`) | 5500 | No | `terminal-logs/terminal-3-rag-server.log` |
| 4 | Multi-Agent Server (`uvicorn server:app --workers 1`) | 5600 | No | `terminal-logs/terminal-4-multi-agent-server.log` |
| 5 | System test (`scripts/deploy/system_test_local.py`) | n/a | No | `terminal-logs/terminal-5-system-test.log` |
| 6 | Docker Compose: 5 students' frontend, backend and database, plus the shared gateway (16 services) | 5100 | Yes | `terminal-logs/terminal-6-docker-compose-logs.log`, `01-compose-ps.txt` |

No AI service is a Compose service (`01-compose-ps.txt` ends with `none` for any AI-named service). The containers reach the native
services through `host.docker.internal`, and `02-native-services.txt` shows the environment Student 3's backend
actually received (all four AI flags `true`, the three native URLs, `OLLAMA_MODEL=llama3.2:3b`).

## How to reproduce (one command per terminal)

```powershell
# 1  Ollama is already running as the host service; load the model
ollama run llama3.2:3b ""            # or: curl http://127.0.0.1:11434/api/generate -d '{"model":"llama3.2:3b","keep_alive":"30m"}'
# 2  MCP server        (repository root)
python ai-services/mcp-server/server.py
# 3  RAG server
python -m uvicorn server:app --host 127.0.0.1 --port 5500 --app-dir ai-services/rag-server
# 4  Multi-Agent Server (the group's official script)
.\scripts\deploy\start-multi-agent.ps1 -Python <python> -NativeHost 127.0.0.1
# 5  Compose with every AI flag on, then the system test
$env:AI_ENABLED="true"; $env:MCP_ENABLED="true"; $env:RAG_ENABLED="true"; $env:MULTI_AGENT_ENABLED="true"
$env:STUDENT3_MODEL="llama3.2:3b"
$env:MCP_SERVER_URL="http://host.docker.internal:5400/mcp"; $env:RAG_SERVER_URL="http://host.docker.internal:5500"
$env:MULTI_AGENT_SERVER_URL="http://host.docker.internal:5600"
docker compose up -d --build --wait
python scripts/deploy/system_test_local.py http://localhost:5100
```

## Results

`terminal-5-system-test.log` (exit 0, `ALL SYSTEM CHECKS PASSED`):

1. **Native services**: Ollama has `llama3.2:3b`; MCP listens (a bare GET is refused with 406, which proves the transport is up);
   RAG and Multi-Agent `/health` are `ok`.
2. **Gateway**: `/health` and all five students' front ends (`/accommodation/`, `/itinerary/`, `/attractions/`, `/budget/`,
   `/logistics/`) return 200.
3. **Student 3 CRUD through the gateway**: create, read back, update, list, delete, then 404. The row is removed in a `finally`
   block, so a failing step cannot leave data behind.
4. **AI through Student 3's backend** (reusing `smoke_cloud_ai.py`): capabilities all `true`; MCP returned restaurant rows;
   AI-Mode answered from the model, not the fallback; RAG returned a grounded answer with citations; a Multi-Agent workflow ran
   Planner, Worker, Reviewer to `awaiting_human_review` and was then approved.

Also captured: `03-multi-agent-audit.txt` (the hash-chained audit verifies: `valid: true`, 10 entries, the workflow listed as
`approved`); `01-integrated-app-student3.png` (the integrated UI with the AI, MCP, RAG and Multi-Agent sections; the browser console
had no errors, which also covers the cross-origin check through the gateway).

Tests of the system-test script itself: `05-system-test-unit-tests.txt` (32 passing offline tests) and
`04-system-test-mutation-check.txt` (11 injected bugs, all caught). Both are wired into `student-3.yml`.

## Limits to state honestly

- **The workflow approval in the log is the script's, not a human's.** `system_test_local.py` says so in its output. The human
  decision for the showcase has to be made in the browser (see `contributionlog.md`'s open items).
- **The native processes were started as background processes with their output redirected to the log files**, one per
  service, not typed into six visible terminal windows. The commands above start the same processes in real terminals.
- **Student 3 used `llama3.2:3b` instead of its default `qwen2.5:3b`** (`STUDENT3_MODEL`). The host has 8 GB RAM and a second resident
  3B model risks the out-of-memory crashes recorded in `knownissues.md`. The shared servers already use `llama3.2:3b`.
- **One earlier run failed once**: the first RAG question returned a 502 because the application's own model deadline expired while
  Ollama was still busy with the previous AI-Mode answer. The identical question succeeded straight afterwards with citations.
  `system_test_local.py` therefore retries that one call once and logs `RETRY`; a second failure still fails the run. The final
  logged run needed no retry. The failed run's log was overwritten by the passing run and is not kept.
- Only Student 3's feature was exercised beyond a page load; the other students' backends were started and healthy but are
  covered by their own evidence.
- This is a local run. It is not evidence of a cloud deployment.
