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
The existing database tests keep a temporary file open and fail on Windows;
their Linux run is the recorded database regression check. Shared service suites
must run from their own directories to avoid `server` module name collisions.
Run `dotnet test ai-services/agentic-loop/tests/AgenticLoop.Tests.csproj` separately.

Run the [cross-feature grounding evaluation](../../ai-services/rag-server/README.md#grounding-evaluation)
after native model setup. Nine opt-in cases include real Student 3 knowledge and
misleading keyword/instruction-injection queries. Offline candidate tests do not
prove source support; record human claim-by-claim review and keep a genuinely
untouched held-out set separate from these development cases.

## Current Evidence and Gaps

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