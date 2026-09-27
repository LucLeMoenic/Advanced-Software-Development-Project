# Shared MCP Server (Release 1)

Registered tools include Student 3 attractions search/reviews and Student 2's
read-only `itinerary.get_summary`. One shared native process serves these tools.
Student 2's real native SDK invocation was verified; container-to-host access on
the current VM-backed Windows environment remains unresolved.

## What this is

One process, run natively on the host, exposing every feature's read-only
MCP tools over streamable HTTP. It is deliberately **not** a Docker Compose
service (the Release 1 brief excludes AI-Mode, MCP, RAG and the loop from
Compose). Native Ollama must be installed separately for AI generation.

- Transport: MCP streamable HTTP (`mcp.server.mcpserver.MCPServer`, official
  Python SDK — note the SDK renamed `FastMCP` to `MCPServer` in `mcp` 2.x;
  §4.3's default contract named `FastMCP`, but the installed SDK version is
  the 2.x one, so this scaffolding follows the current API).
- Transport URL: `http://localhost:5400/mcp` (`MCP_HOST` / `MCP_PORT`).
- From a container: `http://host.docker.internal:5400/mcp`. Compose maps this
   name through `LOCAL_AI_HOST`, default `host-gateway`. Some VM-backed engines
   require an explicit private Windows host address and matching private bind.

## Adding a feature's tools

1. Create `tools/<feature>.py` with a `register(mcp: MCPServer) -> None`
   function that calls `@mcp.tool(name="<feature>.<action>")` for each tool.
2. In `tools/__init__.py`, import the module and append `register` to
   `REGISTRARS`.
3. Tools are **read-only** and validate their own inputs — reject unknown
   fields and out-of-range values with a structured error rather than
   letting an exception surface as a generic 500.

`itinerary.get_summary` accepts `{"params":{"trip_id":10}}` with strict positive
integer validation and no extra parameters. It reads only the configured database
API, returns inclusive day/stop coverage and indicative daily budget allocation,
and omits traveller names, interests and stop notes. Success is
`{ok:true,summary:...}`; controlled domain failures use `{ok:false,error:{code,message}}`.
SDK callers must handle protocol `is_error` as well as domain errors.

## Running it

```powershell
python -m pip install -r ai-services/mcp-server/requirements.txt
python ai-services/mcp-server/server.py
```

## Env vars

| Var | Default | Purpose |
|---|---|---|
| `MCP_HOST` | `127.0.0.1` | Bind address |
| `MCP_PORT` | `5400` | Bind port |
| `STUDENT2_DATABASE_API_URL` | `http://127.0.0.1:5302` | Fixed database API origin for itinerary reads |

Backends consume `MCP_SERVER_URL` / `MCP_ENABLED`. Itinerary database reads have
a 3-second socket timeout; the backend SDK session has a 5-second outer deadline.
The server limits requests to 8192 bytes and 64 sessions, with a 30-second idle
timeout. DNS-rebinding protection remains enabled for localhost, the configured
bind host, and `host.docker.internal`. These are development protections, not
authentication. Never expose the service publicly.

See [Student 2 deployment](../../student-2/docs/release-1-runbook.md) for native
setup and current validation limitations.
