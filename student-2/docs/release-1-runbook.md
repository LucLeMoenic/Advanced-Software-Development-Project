# Student 2 Release 1 Runbook

## Prerequisites

Use native Python 3.11+, .NET 8 and Ollama, plus a Compose-compatible container
engine. Run commands from the repository root. Never run MCP, RAG, Ollama or the
loop in Compose. The GPU override is now an empty compatibility file; native
Ollama manages GPU selection. Existing database/model storage is not deleted.

Create separate virtual environments for the shared services to preserve their
dependency pins:

```powershell
python -m venv .venv-mcp
python -m venv .venv-rag
.\.venv-mcp\Scripts\python -m pip install -r ai-services/mcp-server/requirements.txt
.\.venv-rag\Scripts\python -m pip install -r ai-services/rag-server/requirements.txt
ollama pull llama3.2:3b
```

## Start Native Services

Run each command in a separate terminal. The safe defaults listen on loopback:

```powershell
.\.venv-mcp\Scripts\python ai-services/mcp-server/server.py
```

```powershell
.\.venv-rag\Scripts\python -m uvicorn server:app --host 127.0.0.1 --port 5500 --app-dir ai-services/rag-server
```

Native Ollama must already be serving on port 11434. For the shared loop, follow
the [native loop instructions](../../ai-services/agentic-loop/README.md), including
the second distinct model. Shell processes do not load `.env` automatically.

## Container Connectivity

Compose gives each backend the host URLs and a `host.docker.internal` mapping.
Default `LOCAL_AI_HOST=host-gateway` works only when that gateway reaches native
host services. With some Windows VM-backed engines it resolves to the Linux VM,
not Windows. Set `LOCAL_AI_HOST` to a verified private host interface, set
`MCP_HOST` to that interface, and use the same private bind with uvicorn `--host`.
Ollama also needs a reachable private bind, configured through its native startup
settings. Do not bind unauthenticated services publicly or disable MCP protection.
Any required restricted firewall rule must be reviewed and applied by the user.

On the current Podman/WSL host, `podman machine inspect` reports user-mode
networking disabled. The VM's default route is `172.23.64.1`, matching the private
Windows service bind; a direct VM request to RAG still times out despite a
successful Windows-native request. This locates the problem at the VM-to-Windows
boundary, not the Compose hostname or application response parser. IP addresses
are machine-specific and can change after restarting WSL.

To reproduce without modifying any network policy:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 5400,5500,11434
podman machine ssh 'ip route'
podman machine ssh "curl --noproxy '*' --connect-timeout 3 --max-time 5 -sS http://172.23.64.1:5500/health"
```

An administrator must investigate Windows/Hyper-V firewall and private-interface
reachability before container acceptance can pass. Any allow rule must be limited
to the current VM source/interface and required ports; do not disable the firewall
or expose these unauthenticated services publicly. No elevated command or firewall
change was performed. Ollama was also absent from PATH and had no listener on port
11434. Install/start native Ollama and prepare the approved models before attempting
generated-answer or two-model-loop acceptance. Do not substitute containerised Ollama.

Verify from the backend container, not just a host browser:

```powershell
$env:MCP_ENABLED = 'true'
$env:RAG_ENABLED = 'true'
docker compose up --detach --build --wait
docker compose exec -T student2-backend python -c "import requests; print(requests.get('http://host.docker.internal:5500/health', timeout=3).status_code)"
```

The shared gateway derives its DNS resolver from the container's own configuration
using the official nginx entrypoint template, rather than assuming Docker DNS.
If a bind-mount storage directory is absent, create that empty directory before
startup; never replace existing database files.

Use the integrated UI at http://localhost:5100/itinerary/. The direct Student 2
frontend at http://localhost:5102 is diagnostic only and does not demonstrate
group integration. After recreating a backend, restart its nginx frontend if it
retains the old upstream IP. Do not use `down --volumes` to troubleshoot.

## Modes and Checks

Student 2 accepts exact `true`/`false` configuration. AI defaults on; MCP/RAG
default off unless explicitly configured. `AI_ENABLED=false` directly uses the
existing deterministic fallback for all three generation paths. CI sets all
three modes false and uses test doubles for enabled-path coverage.

Open a seeded trip and inspect its summary. Submit `Is budget the total for the
trip?` for a cited answer, then an unrelated question for insufficient context.
Stop a shared service and verify a distinct dependency error without stale
results. Advice is general feature knowledge, not a private-trip analysis.

Run `scripts/test/student-2.ps1` on Linux CI or a supported Python environment.
Database tests now use a temporary directory and pass on Windows without holding
an open SQLite temporary-file handle. Shared service suites
must run from their own directories to avoid `server` module name collisions.
Run `dotnet test ai-services/agentic-loop/tests/AgenticLoop.Tests.csproj` separately.

Run the [cross-feature grounding evaluation](../../ai-services/rag-server/README.md#grounding-evaluation)
after native model setup. Nine opt-in cases include real Student 3 knowledge and
misleading keyword/instruction-injection queries. Offline candidate tests do not
prove source support; record human claim-by-claim review and keep a genuinely
untouched held-out set separate from these development cases.

## Current Evidence and Gaps

### Review Handoff - 29 September 2026

The user explicitly deferred the Podman-to-Windows networking problem. Keep the
required containerised frontend/backend/database and native MCP/RAG architecture;
no native-backend workaround, firewall change, or VM networking change is included.

The updated Student 2 frontend/backend images were deployed and native MCP started.
The shared itinerary page and saved-trip API returned HTTP 200 with ten trips.
Windows could reach MCP, but both the VM probe and backend connection timed out;
the integrated overview returned HTTP 504 `dependency_timeout`. Firewall filtering
is suspected, not proven. Machine-specific addresses were runtime settings only,
not changes to the committed Compose defaults. Integrated MCP/weather acceptance
remains blocked and is not a release-completion claim.

Fresh offline checks: MCP 86, backend 49, database 5 and frontend 16 tests passed
(156 total); the Vite production build and PowerShell test-runner syntax check
passed. Generated frontend output and local Playwright artifacts are ignored.
The data-mutating `-Smoke` path was not run against saved trips. Remote CI and
live MCP/RAG acceptance must be checked separately before release sign-off.
No commit, push, or merge was performed during this handoff.

### Trip Overview Update - 28 September 2026

The frontend now combines coverage/budget information and destination weather in
**Trip overview**. Rebuild the Student 2 backend/frontend and restart the shared
native MCP process after updating code; a previously running MCP process does not
discover the new `itinerary.get_overview` tool automatically. The old
`itinerary.get_summary` tool remains available for existing clients and loop checks.

Open a saved trip, choose **Check overview**, then confirm the forecast location
when multiple matches appear. Open-Meteo requires no key for this non-commercial
use, but requires attribution and is subject to its public API limits. See
[provider terms](https://open-meteo.com/en/terms). Outbound HTTPS access to
`geocoding-api.open-meteo.com` and `api.open-meteo.com` is required from the native
MCP process. Do not expose that MCP process publicly to fix host connectivity.

The refreshed seed trips start beyond the forecast horizon. They should show
their saved-trip summary and **outside the current forecast window**, not invented
weather. A trip overlapping the next 16 days can show forecasts; missing days and
null fields remain explicit. No saved data was changed during overview validation.

Fresh checks: MCP 86 tests, backend 49 tests, frontend 16 tests; production build
passes. `docker compose build student2-backend student2-frontend` also succeeded;
running containers were not recreated and the native MCP process was not restarted.
A real Open-Meteo Tokyo request returned two dated forecasts. SDK execution
of `itinerary.get_overview` against persisted Copenhagen trip 21 returned location
choices and, after selecting Denmark, a validated `outside_window` result for
3-4 December. An initial live attempt failed its assertion before capturing the
result; repeated calls and the backend validator passed. This is not a container
connectivity success claim.

Playwright checked location choice/focus, partial forecasts, null values and
attribution with intercepted API fixtures in the Vite preview. No page, panel or
weather overflow at 320/768/1280px. Screenshots:
`.playwright-mcp/student2-overview-{320,768,1280}.png` (local test artefacts).
The forecast browser fixtures are not live integrated-app evidence. Existing
container-to-host connectivity and generated-RAG acceptance remain separate gates.

As of the 27 September 2026 defect-fix follow-up: backend 35, MCP 26, RAG 31 and
shared loop 38 tests pass (130 fresh passes); nine live RAG cases are skipped
without opt-in. Frontend 9 and database 5 Linux passes are previous evidence, not
fresh runs. Student 2 production
images built and all integrated containers became healthy after creating Student
5's absent storage directory. Native SDK invocation returned the persisted
Copenhagen summary for trip 10; native RAG returned insufficient context without
calling a model. The gateway returns ten trips. Integrated browser layouts were
checked at 320/768/1280 pixels without horizontal overflow or JavaScript page
exceptions, and a diagnostic dependency timeout hid results and restored controls.
Native loop publishing and nginx syntax checks pass. These are not successful
end-to-end MCP/RAG model demonstrations.

The follow-up fixed loop root discovery and bounded example context, strict
top-level itinerary arguments, streaming byte bounds in both RAG clients, and
malformed database JSON error mapping. An actual native SDK session verified the
strict discovery schema, rejected extra keys, returned persisted trip 10 and closed
successfully. Restarted native RAG passes no-context abstention. The updated backend
image built and became healthy. Both documented loop modes now load context/prompts
and reach the unavailable native Ollama connection; no model record was completed.

The local engine mapped the default host gateway to its Linux VM; a private
Windows-interface attempt timed out, including a direct Podman VM probe. Native
Ollama was not found at its standard installation location or on PATH and no model
listener was present. Genuine generated answers, both live model loop outputs,
full five-feature behavior checks, final cross-feature calibration/live grounding,
remote CI and report/showcase evidence remain pending. Never replace these gates
with mocked output. Record model, prompt/corpus commit, request/response and
human source-support checks when the environment is ready.