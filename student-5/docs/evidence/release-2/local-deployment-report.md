# Student 5 - Local Deployment Report (Release 2)

Brief requirement: *"A report showing the integrated application running locally with the
non-containerised Multi-Agent Server. Include multi-service system-testing logs from multiple
terminals."* Plan: Chunk 6 in [`release-2-plan.md`](../../release-2-plan.md).

Run on 22 October 2026, Windows 11, Docker Desktop 29.8.2, native Ollama 0.40.8 with an
NVIDIA RTX 2000 Ada Laptop GPU (`local/09-host-info.txt`), branch `AC/student5-r2-evidence`
(no code changes from `main` at `457b247`). Evidence is in [`local/`](local/). Times in the
evidence are UTC; the Multi-Agent CLI prints local time (UTC+11).

Alex Chen made every human decision in this run. An AI coding assistant ran the services,
the terminal commands and the browser, and entered each decision after Alex approved it (see
"Who did what" in the [Multi-Agent report](multi-agent-server-report.md)).

## What ran, and where

| Terminal | Process | Port | Containerised? | Log |
|---|---|---|---|---|
| 1 | `scripts/deploy/start-release1.ps1`: reuses native Ollama, starts native MCP and RAG, then `docker compose up -d --build --wait` | 11434, 5400, 5500, 5100 | Ollama, MCP and RAG no; Compose yes | `local/01-terminal-1-release1-launcher.txt`; MCP and RAG output in `local/terminal-logs/native-{mcp,rag}-server.txt` |
| 2 | `scripts/deploy/start-multi-agent.ps1 -NativeHost 127.0.0.1` (`uvicorn server:app --workers 1`) | 5600 | No | `local/terminal-logs/terminal-2-multi-agent-server.txt` |
| 3 | `ai-services/multi-agent-server/cli.py` (terminal workflow) | n/a | No | `multi-agent-server/transcripts/T-run.txt` |
| 4 | Git Bash: health checks, the Student 5 calls through the gateway, the UI review and the agentic loop | n/a | No | `local/02`-`05`, `multi-agent-server/transcripts/U-*.txt`, `loop/*-terminal.txt` |
| Compose | 5 students' frontend, backend and database, plus the shared gateway (17 containers: 16 running, and `student3-db-init`, which exits after seeding) | 5100-5305 | Yes | `local/terminal-logs/compose-logs-student5.txt` |

Terminal 1 was started with `MULTI_AGENT_ENABLED=true` and
`MULTI_AGENT_SERVER_URL=http://host.docker.internal:5600` in its environment. The launcher
itself sets `AI_ENABLED`, `MCP_ENABLED` and `RAG_ENABLED` to `true`. So Compose gave
`student5-backend` all four flags `true`. `local/02-health-checks.txt` shows the backend's
environment and that it reaches all four native services from inside the container.

No AI service is a Compose service: `docker compose config --services | grep -i -E
'ollama|mcp|rag|multi|agent'` prints `none`, and the four listening ports belong to host
processes (`ollama`, three `python`).

## How to reproduce

```powershell
# Terminal 1 (repository root)
$env:MULTI_AGENT_ENABLED = "true"
$env:MULTI_AGENT_SERVER_URL = "http://host.docker.internal:5600"
pwsh -NoProfile -File scripts/deploy/start-release1.ps1        # do not pipe its output
# Terminal 2
pwsh -NoProfile -File scripts/deploy/start-multi-agent.ps1 -Python <python with multi-agent requirements> -NativeHost 127.0.0.1
# Terminal 3 (ai-services/multi-agent-server)
python cli.py run --feature student-5 --task "<readiness task>" --evidence-file <evidence.json>
# Browser: http://localhost:5100/logistics/
# Stop everything: pwsh -File scripts/deploy/start-release1.ps1 -Stop, then Ctrl+C in terminal 2
```

Do not pipe the launcher's output (`| Select-Object`, `| Tee-Object`). The MCP and RAG
processes it starts inherit the pipe, so the call never returns.

## Results

| Check | Evidence | Result |
|---|---|---|
| Native services | `local/02-health-checks.txt` | Ollama `200` (`llama3.2:3b` loaded), MCP `400 Missing session ID` (the transport is up; the launcher accepts 400/406), RAG `{"status":"ok"}`, Multi-Agent `{"status":"ok","busy":false}` |
| Student 5 containers | `local/02-health-checks.txt` | `student5-frontend`, `-backend`, `-database` and `shared-frontend` all `healthy`; each `/health` `200`; `/logistics/` `200` through the gateway |
| AI-Mode advisory | `local/03-ai-advisory.txt` | `POST /logistics/api/advisory` (Vietnam, December): `200` in 3.4 s, `model: llama3.2:3b`; packing, documents and transit taken from the stored records, ending with the Smartraveller reminder |
| MCP tool call | `local/04-mcp-tool-call.txt` | `POST /logistics/api/mcp/invoke` `logistics.check_visa_requirement` for destination 3: `200` in 0.38 s, `ok: true`, the stored eVisa row and the official-source reminder |
| RAG grounded answer | `local/05-rag-grounded-answer.txt` | `POST /logistics/api/rag/ask` "What is the difference between visa on arrival and an eVisa?": `200` in 2.7 s, two citations (`visa-categories#2`, `#3`), `confidence: low` |
| Multi-Agent through the UI, fully in the browser | `multi-agent-server/screenshots/04`-`08` | Thailand: **Start readiness review** clicked in Chrome -> `wf-20261022T110825Z-db0bcb00`, Queued -> Planner working -> awaiting review in 22 s, then `partial` (Alex Chen) submitted from the same page |
| Multi-Agent through the UI, started over HTTP | `multi-agent-server/transcripts/U-*.txt`, `screenshots/01`-`03` | Indonesia: the page's own `POST /logistics/ui/readiness-reviews` from Git Bash -> `wf-20261022T100857Z-16996759`, Planner -> Worker -> Reviewer in 17 s; decided (`correct`, Alex Chen) in Chrome. See the [Multi-Agent report](multi-agent-server-report.md). |
| Multi-Agent from the terminal | `multi-agent-server/transcripts/T-run.txt`, `T-decide-audit-verify.txt` | `cli.py run` with Student 5 evidence (Vietnam) -> `wf-20261022T100101Z-f83e9cc6`, `awaiting_human_review` in 14 s (10:01:01.4 to 10:01:15.7 in the record); decided with `cli.py decide` (`partial`, Alex Chen) |
| Integrated UI in Chrome | `local/06-integrated-app-advisory.jpg`, `local/07-mcp-and-rag-panels.jpg` | Indonesia selected on `http://localhost:5100/logistics/`: its records and a generated advisory; the MCP visa tool result and a cited RAG answer (`visa-categories#2`, `airport-arrival#1`, low confidence) |
| Student 5 CRUD through the gateway | `local/08-local-crud-through-gateway.txt` | Create `201` -> read `200` -> update `200` -> read the change `200` -> delete `204` -> `404`, on a uniquely named row; 12 destinations before and after |
| Cross-terminal trace | `local/terminal-logs/compose-logs-student5.txt` and `terminal-2-multi-agent-server.txt` | The UI review at 10:08:58 UTC appears in order in the gateway, Student 5 frontend and backend logs, and as `POST /workflows 202` then `GET /workflows/wf-20261022T100857Z-16996759` in the Multi-Agent terminal. The advisory, MCP and RAG calls appear the same way at 10:00:23-27. |

## Limits to state honestly

- **The launcher exited with code 1 even though every service was up.** Its last step checks
  Student 2's `/api/capabilities` against an exact dictionary,
  `dict(aiEnabled=True, mcpEnabled=True, ragEnabled=True)`. With `MULTI_AGENT_ENABLED=true`,
  Student 2 also returns `multiAgentEnabled: True`, so the assertion fails
  (`01-terminal-1-release1-launcher.txt`, last lines). All running containers had already
  reported `Healthy`, and every check above was run afterwards. The script belongs to the
  shared deployment owner and was not changed here. The fix is to compare only the three keys
  it means to check.
- **Two output-quality defects, recorded rather than hidden.** The advisory shows doubled
  bullets (`- - Pack ...`) in its packing list. The RAG answer calls a visa on arrival "an
  electronic visa issued at the border". The cited chunk says only that it is issued at the
  border, so "electronic" is not supported. The server itself rated the answer
  `confidence: low`.
- **Terminals 1 and 2 were background processes, not visible windows.** Their console output
  was captured unmodified to the files above. The commands in "How to reproduce" start the
  same processes in real terminals. Uvicorn and the native MCP/RAG logs carry no timestamps,
  so the cross-terminal order is taken from the timestamped Compose logs.
- **One UI review was started over HTTP, then decided in the browser.** For Indonesia the
  start and poll requests were sent from the terminal, exactly as the page's HTMX sends them
  (same paths, form fields and `HX-Request` header, through the gateway); see `U-start.txt`
  and `U-poll.txt`. Later, in Chrome, the page had no control to reopen an existing review, so
  the page's own `htmx.ajax` loaded it into `#readiness-panel`. The decision form was then
  filled and submitted there. The Thailand review was then run entirely in the browser. A
  "reopen review" control is listed in `known-issues.md`.
- **The Multi-Agent Server was restarted once.** Its terminal process ended when an earlier
  working session closed (the exact time was not recorded). It was started again with the
  same script shortly before the first decision at 10:36 UTC. Both
  waiting workflows survived on disk unchanged, and `GET /audit/verify` was still valid
  (38 entries) before any decision was made. That check was seen in the terminal but not
  saved; the first saved check comes after the first decision (39 entries,
  `T-decide-audit-verify.txt`). `terminal-2-multi-agent-server.txt` covers the
  first process; `terminal-2-multi-agent-server-restart.txt` covers the second.
- **The page squeezes its results on a short viewport.** At about 790 px high the results
  row gets about 57 px. With the trip form collapsed, as in most screenshots, it gets about
  200 px, so the advisory scrolls inside a small box. This is recorded in `known-issues.md`.
- **Only Student 5 was exercised beyond start-up.** The other students' services were healthy
  and are covered by their own evidence.
- This is a local run. Cloud evidence is in the [cloud deployment report](cloud-deployment-report.md).

## Screenshots (`local/`, Chrome, 22 October 2026)

- `06-integrated-app-advisory.jpg`: the integrated Student 5 page on the local gateway, with
  Indonesia's records and a generated advisory.
- `07-mcp-and-rag-panels.jpg`: the MCP tool result and a cited RAG answer on the same page.

There is no screenshot of the terminals side by side: terminals 1 and 2 ran as background
processes.
