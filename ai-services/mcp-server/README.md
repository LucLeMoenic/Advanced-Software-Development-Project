# Shared MCP Server (Release 1)

**Status: scaffolding only.** No feature tools are registered yet — each
student adds their own module under `tools/` in their own Stage 1 branch.
Built on `KSS/shared-mcp-rag-setup`; ownership of this shared component is
an **assumption** pending group sign-off (see the Release 1 contracts
discussion) — flag this in the report if it changes.

## What this is

One process, run natively on the host, exposing every feature's read-only
MCP tools over streamable HTTP. It is deliberately **not** a Docker Compose
service (the Release 1 brief excludes AI-Mode, MCP, RAG and the loop from
Compose), the same way Ollama already runs natively on this machine.

- Transport: MCP streamable HTTP (`mcp.server.mcpserver.MCPServer`, official
  Python SDK — note the SDK renamed `FastMCP` to `MCPServer` in `mcp` 2.x;
  §4.3's default contract named `FastMCP`, but the installed SDK version is
  the 2.x one, so this scaffolding follows the current API).
- Address: `http://localhost:5400` by default (`MCP_HOST` / `MCP_PORT`).
- From a container: `http://host.docker.internal:5400`, which needs
  `extra_hosts: ["host.docker.internal:host-gateway"]` on the backend
  service in `docker-compose.yml` (Linux CI runners need the same entry).

## Adding a feature's tools

1. Create `tools/<feature>.py` with a `register(mcp: MCPServer) -> None`
   function that calls `@mcp.tool(name="<feature>.<action>")` for each tool.
2. In `tools/__init__.py`, import the module and append `register` to
   `REGISTRARS`.
3. Tools are **read-only** and validate their own inputs — reject unknown
   fields and out-of-range values with a structured error rather than
   letting an exception surface as a generic 500.

Student 3's tools (`attractions.search`, `attractions.get_reviews`) are a
Stage 1 deliverable on a separate branch (`KSS/r1-knowledge-and-tools`) and
are not part of this scaffolding commit.

## Running it

```powershell
pip install -r ai-services/mcp-server/requirements.txt
python ai-services/mcp-server/server.py
```

## Env vars

| Var | Default | Purpose |
|---|---|---|
| `MCP_HOST` | `127.0.0.1` | Bind address |
| `MCP_PORT` | `5400` | Bind port |

Backends consume `MCP_SERVER_URL` / `MCP_ENABLED` (Stage 2) — those are
backend-side settings, not server-side ones, and are documented in each
feature's own backend README/client.
