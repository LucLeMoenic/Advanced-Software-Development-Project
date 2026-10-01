# Student 2 Release 1 Runbook

## Final Chunk Handoff - 1 October 2026

Database, MCP, editor integration and knowledge changes are merged through PRs
#92-#95. The final `LLM/Student_2_Release_Validation_And_Evidence` branch contains
launcher/CI improvements and shared-loop validation, preserving newer Student 3
checks. Fresh verification: 69 shared loop tests, isolated launcher regressions
and parsed workflow assertions pass. Full launcher startup, remote CI and fresh
live loop runs are not certified by these checks.

The sections below retain chronological implementation evidence, not current
service health. Native terminals were later closed; check/restart Ollama, MCP and
RAG before recording. Current UI: collapsible Edit/Advice assistant, explicit
preview/confirm/undo, plain numbered citations with full expandable sources and
weather only for weather-related questions. The corpus contains thirteen passages.

## Deployed Showcase Restoration - 1 October 2026

The updated frontend is now deployed at `http://localhost:5100/itinerary/`,
superseding the preview-only deployment status below. Rebuilt and replaced only
Student 2 frontend; retained healthy backend/database containers and saved data.
Restored native Ollama, MCP and RAG on the previously verified local private
interface `172.23.64.1` (ports 11434, 5400, 5500). No firewall policy changed.
These native services remain running in terminal sessions; closing them stops AI
availability. Use the shared launcher with the correct local `-NativeHost` to
restore them after a shutdown.

- All 16 application containers are healthy. All five integrated feature pages
	and all ten backend/database health endpoints return HTTP 200.
- Real gateway MCP add preview passed in 2.11 seconds, without confirmation.
	Real trip-aware RAG returned cited weather-planning advice in 13.32 seconds
	with low source relevance; this is not factual-certainty evidence.
- Deployed browser loaded the separate assistant, obtained a real Coffee break
	preview and cancelled it, then obtained real RAG advice and opened its cited
	source. Desktop layout had no horizontal overflow.
- Full JSON snapshots of all ten saved trips matched before and after testing.
- Installed the already configured Student 3 model `qwen2.5:3b` and verified it
	loads; left `llama3.2:3b` warm for the itinerary showcase. Other feature workflows
	and two-model development-loop runs were not re-certified by these checks.

## Showcase UI Separation - 1 October 2026

- Edit and Advice now share an independent Trip assistant region outside the
	saved stops. Desktop has three columns and persistent assistant navigation;
	tablet/phone layouts use separate stacked sections.
- MCP previews show change counts, numbered changes, Not saved, Current/Proposed
	states and highlighted proposed text. Phone comparisons stack at full width.
- Confirmed edits show action-specific feedback and eight-second highlights.
	Saved-trip selection and calendar dates beside days improve orientation.
- RAG uses Source relevance labels and plain numbered markers with expandable sources. Busy
	advice requests can be cancelled; late responses are ignored. Cancellation does
	not promise to stop work already running on the backend.
- Verification: 29 frontend tests pass, including keyboard tabs, date rollover,
	cancellation/retry races, text-safe citation navigation and confirmed-action
	feedback. Production build passes. Intercepted Playwright add/confirm/undo and
	citation flows pass; 320/768/1280px checks show no horizontal overflow.
- Browser responses were fixtures, not fresh live-model evidence. No saved trips
	were changed and no deployed containers were replaced. A separate Vite preview
	runs at `http://127.0.0.1:5174/`; the deployed gateway requires a frontend rebuild
	before these UI changes appear there. Native AI availability remains a separate
	pre-recording check.

## Startup and Validation Improvements - 1 October 2026

The shared [launcher](../../scripts/deploy/start-release1.ps1) now propagates
`-Model` to the backend and RAG model, synchronizes existing virtual environments,
and restarts MCP/RAG with current configuration. `-NativeHost` must be loopback or
a private IPv4 address assigned to this host. For VM-backed engines, choose an
address reachable from the VM; the script uses matching binds, container mapping
and readiness URLs. It does not change firewall policy. Private binds expose the
native APIs to that interface, so use a trusted network and administrator-managed
access rules. Ollama is also located at its standard Windows install path when
the current shell has not picked up its PATH entry.

Startup requires successful health responses and a Student 2 container probe of
enabled capabilities, RAG health, selected model loading and a real read-only MCP
summary. This does not certify RAG generation, interpreted edit intent or all five
features. MCP/RAG are restarted on every launch; saved trips are not edited.

Student 2 CI now reacts to the dedicated edit prompt and launcher changes, runs
the isolated launcher regressions, and runs the existing disabled-mode CRUD and
database-restart persistence smoke workflow. The shared loop's `validate-mcp`
captures an edit preview without confirmation and removes the token from evidence;
`validate-rag` includes the selected trip and has a 55-second contextual deadline.
Use an existing saved trip ID with both commands in the
[loop guide](../../ai-services/agentic-loop/README.md#release-1-validation-modes).

Verification for this improvement batch: launcher helper regressions pass; 65
shared loop tests pass; workflow YAML, both event filters and smoke mode flags
pass local assertions. Full launcher execution, the newly wired Compose smoke
job on CI, remote Actions results and new live loop records were not run. No
containers were redeployed, saved data changed, commits created or branches pushed.

## Natural-Language MCP Actions - 1 October 2026

This supersedes the manual reorder UI and three-action model limit below.
At `http://localhost:5100/itinerary/`, select a trip and use **Edit my itinerary**:

- "Add a Coffee break to day 2"
- "Remove Art gallery"
- "Change Harbour walk notes to Bring tickets"
- "Rename Art gallery to Modern art museum"
- "Shift my trip to start on 2027-06-01"
- "Undo my last itinerary change"

Use activity names from the selected trip. Inspect the current/proposed values,
then confirm or cancel. Moves/swaps remain supported. The manual reorder panel is
removed; **Undo last edit** remains as a model-free alternative. Every save,
including undo, requires confirmation. Only disposable data was changed in testing.

Limits: one action per request; title or notes separately; explicit numeric day
for additions; exact requested replacement text; dates in `YYYY-MM-DD` with the
same trip duration. No automatic activity invention, whole-trip/day deletion,
natural-language reordering, redo, or undo of manual CRUD/regeneration. Undo
restores the prior dates and full stops, including removed IDs/creation times,
and is invalidated by subsequent manual changes. Keep the model warm: deadlines
remain unchanged. Always refresh after an uncertain save instead of retrying.

Verification:

- 302 offline tests pass: database 39 (Linux container), backend 135, shared MCP
	101 and frontend 27. The backend's 11 opt-in model cases also pass separately:
	moves/swaps, all new actions, undo, prohibited deletion and vague-add clarification.
	Vite build and targeted editor diagnostics pass.
- Early universal-schema prompt revisions failed live cases through wrong fields,
	over-abstention and invented content. The final action-specific schema derives
	source days from saved IDs, permits one replacement field, and rejects ungrounded
	text/add days. The passing sample is not general model or injection certification.
- Real isolated backend -> model -> MCP -> database requests passed add, remove,
	notes, rename and date shift. Previews took 0.55-1.25 seconds and wrote nothing.
	Each was confirmed, then undone via natural language with original dates,
	IDs, days, ordering, text and creation timestamps restored exactly.
- Playwright used the deployed bundle routed to that isolated backend. All five
	preview/confirm/undo flows pass, including saved-list date refresh. No horizontal
	overflow at 320/768/1280px or page errors; manual reorder is absent. Screenshots
	are temporary browser artifacts, not committed report evidence.
- All three images built and deployed healthy; complete JSON for all ten existing
	saved trips was identical before/after. Native MCP was refreshed. The normal
	gateway produced a real-model add preview without changing saved data.
- RAG was unchanged and its prior evidence was not rerun. Remote CI, broader
	intent/injection evaluation, cold-start reliability, shared development-loop
	evidence and human release acceptance remain open.

No commit, push, network-policy change or additional model download was performed.
Keep normal Ollama/MCP/RAG terminals running. Earlier sections preserve history.

## Reorder and Undo Follow-up - 1 October 2026

Historical implementation; the manual controls described here are now removed.

Open `http://localhost:5100/itinerary/`, select a trip, and expand **Reorder stops**.
Select a stop, Before/After, and another stop on the same day. Preview displays
actual current/proposed positions, including sparse or tied stored ordering.
**Confirm changes** saves; **Cancel** leaves the trip unchanged.
**Undo last edit** also requires preview and confirmation. It reverses only the
last confirmed MCP edit, not manual edits or regeneration. An intervening manual
change makes undo unavailable. There is no redo; undo history survives database
restart, but outstanding preview tokens do not.

Reorder and undo use explicit controls with no model call. Initial live
`llama3.2:3b` trials selected wrong reorder actions or reversed stop IDs despite
prompt revisions; natural-language reorder/undo was therefore not retained.
The dedicated [edit prompt](../../ai-services/agentic-loop/prompts/itinerary-edit-v1.txt)
limits model selection to move day, swap days, and move stop. Existing read-only
review uses its separate prompt. These changes do not increase model deadlines.

Final verification:

- Database 17, backend 120, shared MCP 97 and frontend 23 offline tests pass
	(257 total). Four opt-in
	backend live-model cases pass: day swap, day move, named-stop move, and refusal
	of deletion. These are narrow intent checks, not general model certification.
- Real isolated HTTP/backend/MCP/database tests confirmed both reorder directions
	and exact undo restoration of IDs, days, ordering, notes and creation timestamps.
	Previews wrote nothing; a second undo was rejected. Explicit previews took
	0.09-0.26 seconds. Only disposable test data was changed.
- All three Student 2 images built and deployed healthy. All ten existing saved
	trips and complete stop data were identical before and after deployment.
- Playwright used the deployed UI routed to the isolated backend for real
	confirmation and undo. Both saved orders were correct, with no horizontal
	overflow at 320/768/1280px or page errors. Screenshots are browser artifacts
	under `.playwright-mcp/reorder-undo-*.png`, not committed report evidence.
- Test routing was removed. The normal gateway shows ten saved trips and both
	controls. A real-model day-swap preview passed in 1.17 seconds without changing
	saved data; explicit undo correctly reports unavailable with no prior edit.
- Targeted editor diagnostics pass. Shared RAG was unchanged in this follow-up;
	prior RAG results below were not rerun. Remote CI, broader intent/injection
	evaluation, cold-start reliability and human release evidence remain open.

No commit, push, firewall change or additional model download was performed.
Native MCP was refreshed; keep the normal service terminals running.
Earlier sections are chronological evidence, not the current limitation list.

## Ollama Installation Follow-up - 1 October 2026

After the user installed Ollama, restarted its localhost-only server with the
session setting `OLLAMA_HOST=0.0.0.0:11434`, downloaded `llama3.2:3b`, and restored
native MCP/RAG on `172.23.64.1`. No firewall rules or saved trips were changed.
The initial local model load/generation took 44.67 seconds; keep the model warm
before testing the application's shorter deadlines.

Genuine contextual RAG through the gateway succeeded in 10.6 seconds (HTTP 200)
for "How should I plan outdoor activities if the forecast shows rain?" on trip 20.
The model returned guidance citing `weather-planning#1`; weather was explicitly
outside the forecast window. This is one real generation success, not full
grounding/injection or human acceptance certification.

After the administrator firewall step was handed to the user and they requested
continuation, container access to Ollama passed in 0.01 seconds. The actual rule
change was not inspected; the previously observed connectivity blocker is resolved.
Through the shared gateway, "Swap days 1 and 2" on trip 20 returned HTTP 200 in
6.12 seconds using the real model and `itinerary.preview_edit`. Stop 41 moved from
day 1 to 2 in the preview and stop 42 from day 2 to 1. Complete saved-trip JSON
was identical before and after; no confirmation request was made.

A repeat real contextual RAG request passed in 9.51 seconds with a
`weather-planning#1` citation and explicit outside-window weather. These checks
verify the current live preview/advice paths, not all command types, live confirmed
writes, cold-start reliability or broader grounding/injection accuracy.
The manual Ollama bind setting applies only to the running terminal; it is not a
persistent configuration. Keep the native service terminals running for this session.

## Confirmed Editor and Contextual Advice - 1 October 2026

This supersedes the historical review UI and deployment status below.

- Open `http://localhost:5100/itinerary/` and select a saved trip.
- **Edit my itinerary**: request "Swap days 1 and 2", "Move day 1 to day 3"
	or a named-stop move. Inspect **Preview changes**, then **Confirm changes** or
	**Cancel**. Ambiguous requests require clarification. Confirmation calls no model.
- **Planning advice** includes the selected trip and optional weather. Retrieved
	guidance retains citations/confidence; forecasts have separate attribution and
	use the top geocoding result without a location picker.
- Preview tokens expire after ten minutes and are invalidated by database restart.
	Changed snapshots and replay are rejected. Refresh after an uncertain save;
	never automatically retry confirmation. Tokens are not authentication.

Verified implementation and deployment:

- Backend 98, database 10, MCP 94, RAG 65 and frontend 22 tests pass: **289 total**.
	The 19 opt-in live RAG cases were skipped. Cross-service tests use real registered
	tools and isolated SQLite with model doubles; no saved user data is modified.
- Vite production build, targeted editor diagnostics, database syntax and the
	extended disabled-mode PowerShell script parser pass. RAG retains an existing
	Starlette/httpx deprecation warning.
- Three Student 2 images built using explicit `podman build --format docker` and
	targeted Compose recreation completed healthy. All ten saved trips and their
	complete stop data were identical before and after deployment.
- Native MCP/RAG restarted on `172.23.64.1`. Real container -> native MCP ->
	database preview passed without changes. Real contextual RAG returned HTTP 200
	abstention for an unrelated question, no citations and `outside_window` weather.
	These tested transport paths now work; historical connectivity notes below do
	not describe their current state. No network-policy changes were made.
- With browser fixtures removed, the real gateway UI displayed the editor, ten
	saved trips, RAG abstention and the forecast-window notice, without overflow.
	Separate browser fixtures exercised preview/confirmation and weather separation
	at 320/768/1280px without overflow/page errors and with one confirmation request.
	Screenshots in browser output `.playwright-mcp/itinerary-editor-*.png` are not
	committed report artifacts.

Ollama is absent from PATH/default install location and has no listener on 11434.
Genuine command interpretation and generated weather-aware advice therefore remain
unverified. Live intent/grounding/injection checks, remote CI, shared two-model
development-loop evidence and human release acceptance remain open. No model was
downloaded, no saved edit confirmed, and no commit/push made. Native services and
Vite remain running; the development URL is `http://127.0.0.1:5174/`.

## Validation Follow-up - 1 October 2026

Fixed container prompt initialization: an explicit `ITINERARY_REVIEW_PROMPT` now
takes precedence without indexing beyond the shallow `/app` parent directories.
The new container-layout regression passes; the backend suite now passes 85 tests.

The available engine is Podman 5.8.5 behind Docker's CLI. The explicit build below
succeeded without changing running services or machine configuration:

```powershell
podman build --ignorefile student-2/backend/Dockerfile.dockerignore -f student-2/backend/Dockerfile -t localhost/student2-review-validation .
```

A disposable instance of that image, with networking disabled, passed application
startup, shared prompt loading, `/health` and disabled-review checks. Both updated
nginx configurations passed `nginx -t` in disposable containers, including shared
template substitution. The Podman validation build used OCI format, which ignores
the Dockerfile HEALTHCHECK; the health endpoint was checked directly. Use
`--format docker` to retain Dockerfile healthcheck metadata in standalone builds.

This resolves the image-packaging and nginx-syntax gaps recorded below, but does
not establish a successful Compose rebuild or integrated model/MCP review. Ollama
still has no listener on 11434. Native MCP/backend processes remain unchanged;
live-model source support, remote CI and development-loop evidence remain pending.
The development frontend remains at `http://127.0.0.1:5174/`, proxying to the
existing backend on 5202; restart/redeploy the backend and MCP before using reviews.

## Itinerary Review - 30 September 2026

The current UI replaces **Check overview** with **Review itinerary**. Open a saved
trip, ask a question, and submit. Both `AI_ENABLED=true` and `MCP_ENABLED=true` are
required. The model selects the saved-itinerary tool and optionally the weather
overview, then generates read-only findings with source evidence. Weather uses
the top destination match automatically; the confirmation control is removed.

Restart the native MCP process to register `itinerary.get_itinerary`. Rebuild
Student 2 backend/frontend and shared frontend before testing through port 5100.
The backend build context is now the repository root, with its Dockerfile-specific
ignore list restricting copied inputs. Compose handles this automatically. For a
standalone build from the root use `docker build -f student-2/backend/Dockerfile .`.
The shared review prompt is copied into the image; native execution resolves it
from the repository or `ITINERARY_REVIEW_PROMPT`.

Try "How could I spread these activities more evenly?", "Which days have nothing
planned?", and "Does the forecast affect my plans?". For weather success, use a
trip within the next 16 days and check the displayed matched place. An unsupported
question must identify missing evidence. Suggestions never change the trip.

Fresh offline checks: MCP 90, backend 84, frontend 18 tests pass; Vite production
build and Compose configuration pass. Playwright fixture checks at 320/768/1280px
show two findings, source evidence, first-match weather, no picker, no horizontal
overflow and no page exceptions. Screenshots were captured in the browser tool's
environment, not committed as integrated evidence.

Live limits: no Ollama listener was present on port 11434. The backend image build
stalled after Docker's missing-buildx warning and was stopped; image packaging and
nginx runtime validation remain unverified. Existing native/backend processes were
not replaced. No live generated review, integrated MCP review, remote CI or new
two-model development-loop evidence is claimed. Existing networking remains
deferred; no saved data or machine network settings were changed.

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
`itinerary.get_summary` tool remains available for existing clients and launcher checks; current loop validation uses edit previews.

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