# Shared MCP Server (Release 1)

Registered tools include Student 3 attractions search/reviews, Student 2's
read-only `itinerary.get_summary`, `itinerary.get_itinerary`, `itinerary.get_overview`,
edit tools `itinerary.preview_edit` and `itinerary.apply_edit`, and Student 1's read-only `accommodation.find`
and `accommodation.get_search`. One shared native process serves these tools.
Student 2's real native SDK invocation was verified; container-to-host access on
the current VM-backed Windows environment remains unresolved.

## What this is

One process, run natively on the host, exposing every feature's bounded
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
3. Read tools are **read-only**; write tools require a bounded confirmation
   contract. Tools validate their own inputs — reject unknown
   fields and out-of-range values with a structured error rather than
   letting an exception surface as a generic 500.

`itinerary.get_summary` accepts `{"params":{"trip_id":10}}` with strict positive
integer validation and no extra parameters. It reads only the configured database
API, returns inclusive day/stop coverage and indicative daily budget allocation,
and omits traveller names, interests and stop notes. Success is
`{ok:true,summary:...}`; controlled domain failures use `{ok:false,error:{code,message}}`.
SDK callers must handle protocol `is_error` as well as domain errors.

`itinerary.get_itinerary` accepts the same trip parameter and returns
`{ok:true,summary,stops}` with at most 200 validated, uniquely identified stops
(ID, day, activity, notes and sortOrder). Traveller identity is omitted; saved
text remains untrusted data.

`itinerary.preview_edit` accepts `{params:{trip_id,operation}}`. Actions are
`move_day`, `swap_days`, `move_stop`, `reorder_before`, `reorder_after`, `add_stop`,
`remove_stop`, `update_stop`, `shift_dates` and `undo`. Each operation supplies
`sourceDay`, `targetDay` and `stopId`, with optional `targetStopId`, `activity`,
`notes` and `startDate`. Strict schemas reject unknown fields and invalid types;
the database enforces action-specific details, ownership and revision checks.
The tool returns `{ok:true,tripId,token,changes,expiresIn}` without saving.

After user confirmation, `itinerary.apply_edit` accepts only
`{params:{trip_id,token}}`. The database verifies the ten-minute signature and
full-state revision atomically, then returns `{ok:true,tripId,applied:true,changes}`.
Invalid/expired previews return `invalid_edit`; stale/replayed previews return
`stale_preview`. Saves must not be automatically retried. The database supports
one revision-guarded undo snapshot. These tools do not authenticate users or prove
that a human clicked Confirm: the caller must enforce that interaction and the
service must stay within the trusted local environment. Backend/UI editor wiring
is a separate change.

`itinerary.get_overview` defaults to the first Open-Meteo geocoding result when
no `location_id` is supplied. Explicit IDs must still match provider results;
invalid selections return `choose_location`. Matched location and attribution
remain in the response, and forecasts are limited to available provider dates.

Student 1's tools (annotated `readOnlyHint`) issue only `GET` requests to the
Student 1 database API with a 3-second timeout and validate every record:

- `accommodation.find` accepts `{"params":{"destination":"Tokyo","guests":2,"max_nightly_price":200}}`
  (`destination` 1-100 non-blank characters is required; `guests` 1-20 and
  `max_nightly_price` > 0 and <= 100000 are optional). Returns
  `{ok:true,count,accommodations:[{id,name,destination,nightlyPrice,maxGuests,amenities}]}`,
  active records only, cheapest first, at most 20.
- `accommodation.get_search` accepts `{"params":{"search_id":11}}` and returns
  `{ok:true,search:{id,title,criteria,rankingMode,results:[{rank,accommodationId,name,nightlyPrice,reason}]}}`.
  Saved free-text preferences are omitted. A missing search returns `search_not_found`.

See the [Student 1 MCP HLD](../../student-1/docs/release-1-mcp-hld.md).

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
| `STUDENT2_DATABASE_API_URL` | `http://127.0.0.1:5302` | Fixed database API origin for itinerary reads and confirmed edits |
| `STUDENT1_DATABASE_API_URL` | `http://127.0.0.1:5301` | Fixed database API origin for accommodation reads |

Backends consume `MCP_SERVER_URL` / `MCP_ENABLED`. Itinerary database reads have
a 3-second socket timeout; the backend SDK session has a 5-second outer deadline.
The server limits requests to 8192 bytes and 64 sessions, with a 30-second idle
timeout. DNS-rebinding protection remains enabled for localhost, the configured
bind host, and `host.docker.internal`. These are development protections, not
authentication. Never expose the service publicly.

See [Student 2 deployment](../../student-2/docs/release-1-runbook.md) for native
setup and current validation limitations.
