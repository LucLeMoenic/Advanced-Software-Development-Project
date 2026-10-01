# Student 2 Review Record

## 2026-10-01 - Final Chunk Integration Check

Resolved the shared loop merge by preserving Student 3 routes, request bodies and
validators while adding Student 2 preview/context checks. All 69 loop tests pass.
The five feature/shared suites add 431 passes; 39 opt-in live cases skip. Frontend
build, isolated launcher regressions, PowerShell parsing and CI wiring assertions
pass. Snapshot comparison accounts for all forty tracked and twelve new original
files; intentional differences retain current docs, Student 3 changes and the
previous chunk's edit-prompt Docker allowlist fix. Student 1 docs are untouched.

This verifies the local merge and offline gates, not fresh runtime health, full
launcher startup, Compose smoke execution, remote Actions or live loop records.
Historical runtime reviews below retain their original date and scope.

## 2026-10-01 - Pre-recording Runtime Check

Verdict: Student 2's itinerary UI segment is ready for recording. All sixteen
application containers are healthy. Through the integrated browser UI, "Swap
day 1 and day 2" returned a valid itinerary.preview_edit result (first request
about four seconds); the preview was cancelled without saving. After reloading
an initially stale tab, displayed current days matched the preview. A fresh
pacing question returned four supported claims, a low source-relevance category
and the full expandable daily-pacing passage in about thirteen seconds. No
saved-data writes or application edits were performed. Confirm/save and undo
were not repeated in this read-only check.

Reload before recording, keep native AI terminals running and allow for model
latency. This check certifies neither the other students' workflows nor the
complete group recording: Release 1 also requires local terminal validation and
both shared loop validation modes. Those demonstrations were not rerun here.

## 2026-10-01 - Expanded Travel Knowledge Validation

Six new topic passages are project-authored general guidance, not destination
research or current provider facts. Labels sit with the heading outside indexed
paragraphs; each indexed passage remains bounded and contains its own relevant
limitations. Total Student 2 passages increased from seven to thirteen.

All six new topics produced useful cited gateway answers. Inspection identified
an expense claim attributed to budget-basics instead of travel-budget-planning.
An added prompt sentence did not fix it and was removed; duplicated budget
calculation content was removed from the new planning source instead. The final
expense answer cited its supporting planning source correctly. The final fourteen
itinerary live cases pass, including live-train and named-venue-accessibility
abstention; these contract checks are not proof of arbitrary claim entailment.

A copied example source identifier caused an existing ownership case to fail.
Constraining the generation schema to retained source IDs resolved that case while
keeping strict server validation. The broad shared live run passed 26/28 cases;
Reykjavik season and Barcelona/Dubai nightlife still abstain. An old-versus-new
schema comparison reproduced both failures, so unrelated accommodation behaviour
was left unchanged. Offline suite: 77 passed, 28 live cases skipped.

## 2026-10-01 - RAG Grounding and Full-Passage Follow-up

Resolution of the two RAG findings only; other showcase-review items were excluded
by the user. Student 2 now receives complete retained passages, up to 2000 characters
each, through its existing citation field. Other features keep 280-character
excerpts. The shared prompt now says to report source disclaimers as limitations,
not new recommendations or requirements. No source facts were invented or expanded.

The first, longer prompt revision caused a supported budget question to abstain;
an original-versus-revised real-model comparison confirmed the regression. Replaced
it with a narrow single-sentence rule. Five focused live cases then passed: the
reported weather question, itinerary budget, off-topic budget abstention, attraction
ratings and Tokyo safety. These checks establish response/citation/abstention
contracts, not universal semantic correctness.

After backend deployment and native RAG restart, the original weather question
returned four source-supported claims in the browser: check forecasts near departure
and activities; keep outdoor plans flexible with indoor alternatives; match dates
and locations and do not confuse rain probability with amount/duration; missing
dates do not imply dry weather or establish suitability. The unsupported final
opening-hours/booking prescription was absent. The full 763-character source was
visible, with plain citation numbers and no horizontal overflow at 1280/320px.

Verification: 69 shared RAG tests pass (20 live cases skipped in the offline run),
five selected live cases pass, six focused backend validation cases pass, and all
30 frontend tests pass. The deployed sample was compared with its full cited source;
broader grounding reliability remains unproven. No saved-trip writes or git actions.

## 2026-10-01 - Remaining Showcase Readiness Review

Scope: current Release 1 brief/project specification, runbook/plan/known issues,
contribution log, workflow, shared loop guide and retained JSON records, current
git status, container/native health, and a real unsupported RAG request. No
application edits, saved-data writes, loop executions, commits or pushes.

### Prioritized Findings

1. High, mandatory shared evidence: none of the five retained JSON records in
	`docs/agentic-loop-records/` has `validationMode`. Run and capture both
	`validate-mcp` and `validate-rag`, inspect the actual outputs, then finalise
	with a human decision and real post-test evidence. The guide's default
	qwen2.5-coder:7b is absent; installed models are qwen2.5:3b and llama3.2:3b.
	Explicitly configure distinct models and the reachable Ollama address before
	rehearsal; do not mistake existing general development records for mode evidence.
2. High, submission traceability: recent implementation/workflow changes remain
	unstaged or untracked on LLM/student-2-trip-overview-clean. Remote CI cannot
	validate this uncommitted state. After review, use the repository's required
	BCP feature-branch process, retain all changes, and record commit/PR and successful
	workflow links. This review did not query remote Actions or alter git state.
3. Medium, RAG grounding/traceability: the earlier captured weather answer's final
	prescription was only partially supported; the shared renderer still returns
	280-character citation excerpts without full-source access. Resolve the recorded
	findings or explicitly disclose the limitation; verify the actual recorded answer
	against its full source, not merely a valid citation identifier or relevance score.
4. Medium, rehearsal/reliability: native terminals must remain running and cold
	model loading previously exceeded request deadlines. Rehearse startup with the
	verified private address, prewarm before recording, and avoid model switching
	while demonstrating requests. Full updated-launcher execution is still not
	certified. Healthy containers are not proof of every team's MCP/RAG workflows.
5. Medium, evidence/documentation: contribution and known-issues files contain old
	branch/status statements; the runbook's UI section still describes linked inline
	citations. Reconcile the current summary, add video/evidence links and timestamps,
	and rehearse all five features plus terminal validation and both loop modes
	within the ten-minute group limit. Retain source/response examples and CI results
	for the report; broad model evaluation remains a separate quality limitation.

### Verified Now

- All 16 Compose containers running and healthy; native 11434/5400/5500 listeners
  present on 172.23.64.1.
- Deployed gateway question "Who won the 2022 FIFA World Cup?" returned the fixed
  insufficient-context answer, no citations and confidence insufficient.
- Previous task's real browser weather-to-budget sequence and 181 backend passes
  (11 skipped), 30 frontend passes remain recent evidence, not rerun in this review.

Recommended order: resolve the bounded RAG issues, rehearse/finalise both shared
loop modes, capture current feature and team evidence, then commit/push with green
CI and assemble the report/video. No additional cosmetic redesign is recommended.

## 2026-10-01 - RAG Response and Release 1 Specification Check

Scope: the captured 7.35-second outdoor/weather advice response, its full cited
weather-planning source, shared grounding prompt/renderer, current UI, Release 1
brief and project specifications. No new model request or application change.

- Medium: the final claim says it is essential to consider opening hours and
	booking confirmations. The cited source identifies itself as not supplying
	those facts; that limitation does not fully support the generated prescription.
	The earlier weather guidance is substantially supported. Valid citation IDs
	alone do not prove claim support; generation.py validates IDs, not entailment.
- Medium: generation.py returns only the first 280 source characters and App.vue
	displays that snippet without a full-source link. A focused source check confirms
	the 763-character weather paragraph loses both missing-forecast and precipitation
	guidance in that excerpt, preventing full in-app inspection of those claims.
- The required confidence category is present as Source relevance: high; this is
	retrieval similarity, not factual confidence. The label matches current feature
	requirements; explaining its mapping to the rubric avoids presentation ambiguity.

Release 1 requires grounded answers, source citations, a confidence category,
insufficient-context handling, and frontend -> backend -> shared native RAG access.
It does not prescribe day-by-day recommendations, live weather, a vector database,
multiple distinct sources per answer, or itinerary modification. A successful
response alone does not establish insufficient-context, every-feature integration,
terminal/frontend evidence, or shared agentic-loop validation acceptance.

Recommended correction: keep the final sentence to the source's actual limitation
and expose complete retrieved passages for inspection. These are findings, not
implemented fixes. The whole group video is limited to ten minutes and must also
include local terminal validation and shared MCP/RAG agentic-loop execution.

## 2026-10-01 - Pre-Showcase UI/UX Recommendations

Scope: current Student 2 Vue template and request handlers, deployed initial
screen and saved Copenhagen trip. Read-only browser inspection; no edits confirmed
and no live model requests submitted. Recommendations, not implemented changes.

- Prioritise access to planning advice: it follows all itinerary days, while the
	editor is above them. A shared assistant area with Edit / Advice tabs would
	reduce scrolling and make both workflows equally discoverable.
- Replace the RAG result's generic Confidence label with Source relevance and
	make answer citation markers open the corresponding source excerpt. Current
	answer text and source disclosures are separate, with raw chunk IDs shown.
- After confirmation, briefly highlight affected itinerary entries and give an
	action-specific saved message. The current flow refreshes correctly but reports
	only Itinerary changes saved and returns focus to the preview button.
- Add a persistent selected-trip indication in the saved list and readable dates
	alongside day headings. Current list buttons have no selected-state binding,
	and itinerary headings display only Day N.
- Make advice loading visible in its submit button, with a progress indicator and
	cancel control for the bounded request. Current code disables Ask question and
	updates status text but leaves the button label unchanged. Do not invent stages
	or percentage progress without backend events.

Keep the existing visual language and explicit preview/confirmation workflow.
This review does not establish fresh live model, mobile or showcase acceptance.

## 2026-10-01 - Supporting MCP and RAG Implementation Review

Scope: shared native launcher, Student 2 backend/UI integration, proxy/image
packaging, assigned CI and shared loop validation. No application fixes requested
or applied; this is not an audit of every student feature.

### Findings

1. **High, shared startup:** [start-release1.ps1](../../scripts/deploy/start-release1.ps1#L144)
	 cannot reproduce the verified private-interface setup from the runbook. MCP
	 readiness always probes loopback even when `MCP_HOST` binds a private address;
	 RAG startup hard-codes loopback. `LOCAL_AI_HOST` changes container DNS, not the
	 native bind. Default Ollama startup also leaves its bind to inherited settings.
	 The final check probes only RAG from Student 1, warns on failure and still
	 prints that Release 1 is running. Parameterize consistent bind/probe origins
	 and verify actual MCP and model access from Student 2 before declaring readiness.
2. **Medium, model configuration:** the launcher's `-Model` selects only the model
	 to pull/preload. Its only environment assignments are `MCP_ENABLED` and
	 `RAG_ENABLED`; it does not export `APPLICATION_MODEL` or `RAG_MODEL`.
	 [Compose](../../docker-compose.yml#L118) and
	 [RAG generation](../../ai-services/rag-server/generation.py#L86) consequently
	 retain their defaults or prior settings when a different model is requested.
	 Propagate the selected model before starting both native and container consumers.
3. **Medium, existing environments:**
	 [Get-VenvPython](../../scripts/deploy/start-release1.ps1#L80) installs requirements
	 only when the interpreter is absent. Updated requirements or a previously failed
	 pip install are never repaired on rerun. A function-only mocked-path probe
	 confirmed an existing interpreter returns without any Python/pip invocation.
	 Synchronize dependencies on changes and cover recovery from partial installation.
4. **Medium, validation coverage:**
	 [ServiceValidation](../../ai-services/agentic-loop/ServiceValidation.cs#L36)
	 still posts Student 2 MCP requests to the compatibility `mcp-summary` route
	 with an empty body and sends RAG only `{question}`. It cannot exercise current
	 model-selected edit previews or selected-trip/weather advice, even when a
	 question or trip ID is supplied. Keep the legacy smoke fixture if useful, but
	 add current preview/context fixtures and explicit disposable-data coverage for
	 confirmation/undo. Do not turn validation into unconfirmed user-data writes.
	 The 35-second fixture deadline also needs review if contextual RAG is added.
5. **Medium, CI coverage:**
	 [student-2.yml](../../.github/workflows/student-2.yml#L5) omits the edit runtime
	 prompt from both trigger lists. Its integration step checks health, trip listing
	 and flags only; it never invokes the existing
	 [disabled-mode smoke runner](../../scripts/test/student-2.ps1#L15) covering
	 disabled endpoints, fallback, CRUD, regeneration and restart persistence.
	 Add the prompt trigger and run that fixture against disposable CI services.
6. **Low, design drift:** the current section of
	 [release-1-design.md](release-1-design.md#L22) still describes only moves/swaps,
	 points selection at the review prompt and says tokens contain no stop text.
	 Selection actually uses the separate edit prompt; add/update operations carry
	 user text inside the signed operation token. Update the diagram and token/prompt
	 descriptions before reusing them in report evidence. Signing is not encryption.

### Validation and Boundaries

- Fresh tests: backend 135, frontend 27, shared MCP 101, shared RAG 65 and loop 43
	pass (371 total); 11 backend and 19 RAG live cases skipped. RAG emits the existing
	Starlette/httpx deprecation warning. No database-suite rerun in this review.
- Initial loop `--no-restore` failed on missing targeting packs; normal restore
	succeeded and all 43 tests passed. These are model doubles, not live loop outputs.
- PowerShell parser/model-assignment and existing-venv probes support findings
	2 and 3 without launching services. Source/caller checks support other findings.
- No listeners were found on 5400, 5500 or 11434 during the read-only runtime check;
	loopback/private MCP and RAG URLs were unreachable. Services were not restarted.
	Earlier successful live evidence remains historical, not current readiness.
- Suspected prompt exclusion was not reproduced: the Podman image build with the
	explicit Docker-specific ignore file succeeded using cached layers. No packaging
	defect is claimed and a clean Docker/remote-CI run remains separate evidence.
- No new backend/UI defect was established in the inspected paths. Existing
	timeouts, server-side validation, text rendering and stale-response tests pass;
	this does not certify general intent accuracy or claim entailment.
- Shared loop outputs, current remote Actions evidence, all-feature integration,
	contribution commits and report/video artifacts still need completion. Only this
	review record changed; no saved trips, deployed services, commits or pushes changed.

## 2026-10-01 - MCP and RAG Criteria Assessment

Compared current Student 2 paths and recorded validation with Release 1 criteria
3 and 4, plus related architecture, CI, integration and evidence requirements.
This is a scoped source/evidence assessment, not a fresh runtime or group-wide audit.

- Student 2 substantially satisfies the functional MCP contract: native shared
	registered tools, frontend/backend access, bounded structured results and
	confirmed edits. The runbook records real-model HTTP and browser validation.
- RAG retrieves project Markdown context, generates with the local model, displays
	source citations/confidence and handles insufficient context. TF-IDF is not
	disallowed; the brief does not mandate embeddings, a vector database or a
	minimum tool count. Source validity alone does not prove claim support.
- Full marks are not established: both criteria allocate a report-evidence point
	and require every feature's integration. Retain genuine cited-answer and
	insufficient-context UI/terminal examples and human source-support checks.
- The shared registry currently contains accommodation, attractions and itinerary
	modules only. This review does not establish successful MCP/RAG interactions
	for every student feature. Do not infer group completeness from Student 2 tests.
- Both loop validation commands exist, but successful captured MCP/RAG loop
	outputs remain open in the current runbook. Current-release remote CI evidence,
	contribution commits, diagrams/report/video and Q&A are separate completion gates.
- Small CI coverage gap: both path-filter lists in `student-2.yml` include the
	review prompt but omit `ai-services/agentic-loop/prompts/itinerary-edit-v1.txt`;
	an edit-prompt-only change will not trigger that workflow. Modes are correctly
	disabled in its integration startup and checked by the capability smoke test.

No runtime changes, live calls, new test runs, commits or pushes in this assessment.
Prior runbook results are evidence of earlier runs, not fresh availability checks.

## 2026-10-01 - Editor and Advice Implementation Checks

Inspected the database save path: bulk replacement changes IDs and cannot safely
confirm a stale preview. Added database-owned signed previews, full-state revision
checks and atomic move/swap updates. Fixed empty-source-day swaps during focused
validation. Confirmation accepts only a token and never calls the model.

Weather now supports separate RAG guidance, with bounded context excluding
traveller identity and a general weather-planning source. Retrieval, citations
and abstention retain their existing contracts; forecasts are attributed
separately. This is implementation review, not independent security/model review.

Verified 289 offline tests (98 backend, 10 database, 94 MCP, 65 RAG, 22 frontend);
19 live RAG cases skipped. Cross-service tests use real tools/SQLite with model
doubles. Images build and targeted deployment is healthy with saved state
unchanged. Real container MCP preview, contextual RAG abstention/weather and the
actual gateway UI pass. Responsive browser fixtures pass without overflow or
page errors. The [runbook](release-1-runbook.md) records verification boundaries.

Open: live model selection/generation (Ollama unavailable), semantic intent and
source-support checks, authentication (outside local-demo scope), remote CI,
shared development-loop evidence and human acceptance. No commit or push made.

## 2026-10-01 - Container Startup Follow-up

Found and fixed an initialization defect: `parents[2]` was evaluated even when
the prompt environment override was present, raising IndexError for the container's
`/app/itinerary_review.py`. The override is now used first; chained parent access
keeps the default path safe. A shallow-layout regression and an actual Linux image
startup check verify the correction. Removed an empty duplicate checklist heading.

Backend 85 tests pass. Explicit Podman image build and network-disabled prompt,
health and disabled-review checks pass. Feature/shared nginx syntax checks pass.
Live model and integrated review execution remain blocked by missing Ollama and
the previously deferred host-connectivity gate. No running services were replaced.

## 2026-09-30 - Itinerary Review Implementation Checks

Inspected the actual UI/backend/tool path while implementing the requested review.
Corrected the existing first-match rejection and removed the location picker and
duplicate summary metrics. Added server-owned trip IDs, bounded tool selection,
strict response validation, real source evidence, disabled-mode and stale-result
guards. Preserved legacy overview/summary contracts and separate RAG behavior.

Verified MCP 90, backend 84 and frontend 18 tests; production build and Compose
configuration pass. Browser fixtures cover 320/768/1280px without overflow or
page errors. These are implementation checks, not independent or live model review.

Remaining risks: generated prose can misuse valid evidence; automatic geocoding
can select the wrong place; two reads are not an atomic snapshot. No Ollama
listener was available. The Docker build stalled after its buildx warning and was
stopped. Live grounding/injection evaluation, actual image/nginx runtime, integrated
MCP review, remote CI and genuine development-loop evidence remain open. No
network policy or saved trips were changed. Human review is pending.

## 2026-09-29 - Pending Change Review and Corrections

Reviewed the local pending changes, not a published PR or its remote CI results.
Scope included the overview producer/backend/UI contract, regression tests,
dependency lockfile, database test portability, optional smoke runner and docs.

### Findings Addressed

- Malformed forecast dates could fail the whole overview: `9999-12-31` followed
	by another date raised `OverflowError` during consecutive-date construction,
	escaping the weather-unavailable fallback. Reproduced with an in-memory
	provider response. Moved the stale-date rejection before date arithmetic;
	three tool-level regressions verify the summary survives upper-bound,
	lower-bound and invalid date responses.
- Removed this session's two Student 2 entries from the Student 1 prompt log,
	following the user's scope clarification. Verified that file now exactly
	matches HEAD; existing Student 1 entries were preserved.

### Verification and Limits

Fresh results: MCP 89, backend 49, database 5, frontend 16 and RAG 62 tests pass
(221 total); 19 live-model tests skip. Production Vite build, Compose config and
editor diagnostics pass. In-memory reproduction of the smoke runner's current
JSON collection filtering selected only its fixture, not the seed record.

No further defect was identified in the inspected paths, but this is not a
guarantee of a defect-free release. The container-to-native networking blocker
remains explicitly deferred. Remote CI, real model results and the data-mutating
smoke/restart path were not verified. The new weather module and supplied Release 1
brief remain untracked and must not be omitted when preparing the change set.
No saved trips, firewall settings or VM networking were changed; no commit,
push or merge was performed.

## 2026-09-29 - Limited Pre-Push Check

Scope: pending Student 2 overview work, test-runner safety/readiness, generated
artifacts and handoff documentation. This is not a full release or security review.

- Integration blocker remains: container-to-native MCP calls time out. The user
	explicitly deferred it; no firewall or VM networking changes were made.
- Generated Vite output and local Playwright artifacts are now ignored, not deleted.
- Database tests use temporary directories and pass on Windows; the runbook's
	obsolete temporary-file failure warning was corrected.
- MCP 86, backend 49, database 5 and frontend 16 tests passed; production build
	and PowerShell syntax checks passed. These do not establish live integration.
- The smoke runner was inspected but not executed against saved trips. CI currently
	uses its default unit-test path and separate basic container smoke commands;
	the expanded `-Smoke` CRUD/restart path still lacks fresh end-to-end evidence.

Human review, remote CI and integrated acceptance remain outstanding. No commit,
push or merge was performed. Networking follow-up is intentionally out of scope.

## 2026-09-27 - Release 1 Defect-Fix Follow-Up

The original six findings below are retained. Their current status:

| Finding | Resolution and evidence |
|---|---|
| 1: Integrated native-service success | Blocked at the VM-to-Windows boundary. Podman's default route matches the private Windows listener, but a direct VM RAG health request times out. Native calls succeed. No Ollama executable on PATH or model listener was found. Requires administrator network investigation and native model setup; no privileged changes attempted. |
| 2: Loop command/context | Fixed. Repository-root discovery handles dotnet run --project; README uses bounded itinerary source. Two new tests preserve context caps. Both actual CLI modes now reach the unavailable Ollama connection after loading context/prompts. No live-model record claimed. |
| 3: Extra MCP arguments | Fixed for the itinerary tool's generated argument model and discovery schema. Regression asserts no database call; native protocol discovery rejects the extra key and still accepts a valid persisted-trip request. Configuration uses pinned MCP 2.2.0 registration internals: retain schema/execution regressions on SDK upgrades. |
| 4: Buffered limits | Fixed in both Python RAG clients with incremental reads. Each oversized-stream regression consumes 16384 bytes of a 102400-byte response, rejects it and closes the stream; the 16000-byte body limit and outer deadlines remain. |
| 5: Grounding evaluation | Partially addressed. Nine real Student 2/3 supported/adversarial cases verify retrieval candidates; opt-in live tests emit answer/source/rubric evidence and require abstention on unsupported questions. Live generation, human entailment checks and independent held-out evaluation remain open. High-scoring unanswerable budget questions demonstrate why thresholds remain provisional. |
| 6: Malformed database JSON | Fixed. The actual requests JSONDecodeError now maps to invalid_dependency_response, covered by regression. |

Fresh suites: backend 35, MCP 26, RAG 31, loop 38: **130 passed**, with nine live
RAG cases explicitly skipped. Updated native services were restarted; the backend
image rebuilt and became healthy. Native MCP protocol and no-context RAG checks
pass. No saved data was mutated, no model output was fabricated, and no commit/push
was made. See the [runbook](release-1-runbook.md) for remaining machine setup and
genuine acceptance gates. Release 1 is still not acceptance-ready.

## 2026-09-27 - Release 1 Implementation Against Documentation

**Verdict:** Substantial implementation alignment, but not Release 1 acceptance-ready. This review compares current code with the [implementation design](release-1-design.md), [runbook](release-1-runbook.md), [feature requirements](requirements.md), and [Release 1 brief](../../docs/Project_Specifications/Release_1_brief.md). It does not assign marks or certify other students' features. No runtime code was changed.

### Verified Findings

1. **Blocking acceptance: neither new interaction succeeds through the integrated backend.** Fresh read-only POSTs to `http://localhost:5100/itinerary-api/trips/10/mcp-summary` and `/itinerary-advice` both returned HTTP 504 with `dependency_timeout`. The latter used the documented budget question. The brief requires successful frontend/backend MCP and generated, cited RAG demonstrations; native-only SDK success and an insufficient-context response do not satisfy those gates. The runbook acknowledges the connectivity/model setup problem accurately. Resolve private host routing and native model setup, then capture both success paths and live loop evidence.

2. **High: documented loop execution cannot reach validation.** The [MCP example](../../ai-services/agentic-loop/README.md#L65), run from the repository root with explicit distinct model tags, failed with `Context file does not exist: student-2/docs/release-1-design.md`. [Workspace resolution](../../ai-services/agentic-loop/AgenticLoopApplication.cs#L156) relies on the process working directory, which does not resolve that path in this `dotnet run --project` invocation. Repeating with `--workspace` set to the repository root failed with `Context file exceeds 16000 bytes`. The [per-file cap](../../ai-services/agentic-loop/AgenticLoopApplication.cs#L364) therefore also rejects the example's chosen document. Use an explicit supported workspace and bounded context fixtures; test the documented CLI commands, not only loop internals. Do not remove the safety cap simply to fit this document.

3. **Medium: the MCP top-level input boundary is not strict.** The [registered tool](../../ai-services/mcp-server/tools/itinerary.py#L56) forbids extra keys inside `params`, but not at the SDK argument-envelope level. An in-process call through the installed official MCP server with `{"params":{"trip_id":12},"url":"http://unexpected"}` succeeded and made one mocked database read. The design specifically requires this SDK-dependent case to be checked; [current tests](../../ai-services/mcp-server/tests/test_itinerary_tools.py#L47) cover only nested extras. Reject unknown top-level keys before the tool executes and add protocol coverage. The extra URL was ignored, not followed: this is not evidence of URL injection, and the browser backend currently sends only fixed arguments.

4. **Medium: response-size checks are post-buffer checks, not memory bounds.** [RAG generation](../../ai-services/rag-server/generation.py#L81) awaits a fully buffered HTTP response before checking 16000 bytes; the [backend RAG adapter](../backend/ai_clients.py#L142) uses the same pattern. A synthetic HTTP stream supplied 102400 bytes and all were consumed before generation raised its controlled 502. This does not meet the design's bounded-upstream-output intent, although the runbook/shared README disclose the limitation. Enforce the byte limit while reading and test early stream closure; retain the outer time deadlines.

5. **Medium acceptance gap: calibration and grounding validation are incomplete.** The design requires labelled evaluation across available feature corpora, irrelevant keyword overlap, adversarial questions, and held-out claim-to-source checks. The [retrieval fixture test](../../ai-services/rag-server/tests/test_retrieval.py#L79) evaluates only Student 2's twelve questions; the four irrelevant examples do not exercise misleading itinerary-keyword overlap. Existing Student 3 fixture tests are not a calibration of the real shared corpus. [Generation tests](../../ai-services/rag-server/tests/test_query.py#L21) use test doubles and validate structure/references, not actual model entailment. Treat confidence thresholds as provisional and do not equate valid citation IDs with supported claims.

6. **Low: malformed database JSON receives the wrong public error category.** A mocked database HTTP 200 whose JSON parser raised `requests.exceptions.JSONDecodeError` produced `dependency_unavailable` from the itinerary tool. That exception is caught by [RequestException](../../ai-services/mcp-server/tools/itinerary.py#L67) before the invalid-data branch. The backend consequently maps it to 503 rather than the design's `invalid_dependency_response`/502. Separate JSON decoding errors from network failures and add a regression for an actual requests JSON-decoding exception.

### Design Coverage

| Slice | Assessment |
|---|---|
| Configuration and adapters | Largely aligned: strict flags, capabilities without probes, disabled zero-call tests, fixed tool/feature routes, response validation and controlled dependency errors. Size limiting and one error mapping need correction. |
| MCP vertical slice | Read-only database ownership, privacy filtering, inclusive day coverage and decimal allocation implemented. Live container path, top-level argument rejection, discovery/handshake/cleanup coverage remain open. |
| RAG foundation and advice | Six feature documents, feature isolation, filtered retrieval, constrained generation, citation assembly and abstention implemented. Live generation, cross-feature calibration and adversarial/semantic grounding checks remain open. |
| Frontend | Summary/advice controls, safe text rendering, disabled/busy/error states and deletion-race coverage implemented. Prior viewport results are documented; keyboard/focus and broader navigation races were not independently browser-tested in this review. |
| Host deployment and CI | Native-only AI topology and Student 2 CI disable flags are present; gateway integration was previously verified. Current live AI requests fail. A successful remote workflow for the final commit is not evidenced here. |
| Assessment validation | Separate native loop modes exist but documented invocation fails. Genuine model outputs, human finalisation, full group behavior, contribution commits and report/showcase evidence remain pending. |

### Verification and Scope

Fresh suites: backend 34/34, MCP 24/24, RAG 21/21, frontend 9/9, shared loop 36/36: **124 passed**. The five database tests were not rerun; their prior Linux pass and Windows temporary-file limitation remain historical evidence. Python probes used the explicit portable Python 3.11.9 runtime, not a claimed editor-selected interpreter.

Additional checks: two real gateway HTTP outcomes; two expected CLI failure reproductions; installed-SDK extra-argument and malformed-JSON probes; a synthetic oversized HTTP stream. These probes did not mutate saved trips or invoke a model. Remote GitHub Actions, live model quality, all other features and firewall configuration were not independently validated. Review entries are the only repository edits for this request.

## 2026-09-01 - Release 0 Readiness Review

**Scope:** Student 2 frontend, backend, database API, SQLite seed data, shared navigation, root Docker configuration, Student 2 CI, development-agent workflow evidence, planning artefacts, and Release 0 report/showcase requirements.

### Findings

| Severity | Finding | Status |
|---|---|---|
| Blocking | Student 2 initially had no individual requirements/backlog contribution, feature plan, risk plan, conceptual/ERD/logical/physical data designs, architecture diagrams, contribution log, screenshots, known-issues record, attendance evidence, or showcase-video evidence. | Planning/design documents, contribution-log structure, browser checklist, and known issues are now present. Shared-backlog linkage, screenshots, attendance, and showcase evidence remain open. |
| Blocking | No finalised shared agentic-loop execution record exists. The `agentTrace` returned by itinerary creation is application narration and is not evidence of the required two-model development Plan/Act/Observe/Adapt workflow. | Open |
| Blocking | The Student 2 workflow exists, but no successful GitHub Actions run or captured Compose execution evidence is stored. | Selective local commits now exist on `LLM/release-0-itinerary-planner`; push, PR, Actions, and clean Compose evidence remain open. |
| Required | Trip creation persisted the trip before all generated stops, and whole-itinerary regeneration deleted existing stops before replacement persistence succeeded. | Resolved with database-owned atomic create/replace operations and regression tests. |
| Required | AI validation accepted an incomplete stop array without enforcing two stops per day or complete day coverage. | Resolved with exact full-itinerary and single-stop regeneration contracts plus focused tests. |
| Required | Backend stop CRUD forwarded payloads without public-boundary validation, and frontend behavior had no automated tests. | Resolved for primary behavior with backend validation and two jsdom frontend tests; broader edge coverage remains useful. |
| Required | The frontend loaded HTMX from an external CDN despite having a local JavaScript implementation. | Resolved by removing HTMX and loading the local ES module directly. |
| Required | The backend and database accept a stop day from 1-31 without checking it against the parent trip. A two-day trip can therefore persist a day-31 stop through the normal add/edit endpoints. | Open |
| Required | Updating a trip can shorten its date range without checking existing stops, leaving persisted stops outside the revised trip duration. | Open |
| Required | The backend and database expose trip update endpoints, but the frontend has no trip-edit control or request path. The Release 0 checklist's claim that trip CRUD is implemented through the frontend is therefore inaccurate. | Open |
| Required | Updating a stop to reference a missing trip can raise an uncaught SQLite foreign-key exception and return HTTP 500 instead of a controlled validation/not-found response. | Open |
| Required | Automated coverage is too narrow to support the checklist's broad completion claim. The two frontend tests cover only list/create; focused tests do not cover frontend update/delete/regeneration, trip shortening, parent-relative stop days, stop-update foreign keys, or explicit cascade-delete assertions. | Open |
| Complete | Frontend, backend, and database services, health endpoints, Dockerfiles, root service wiring, shared `/itinerary/` route, shared theme alignment, SQLite ownership boundary, Ollama generation/fallback, and the versioned application prompt exist. Fresh-database tests assert 10 trips and 20 stops. Stop CRUD and backend/database trip CRUD exist, but frontend trip update remains incomplete. | Implemented with open defects and broader evidence still required |

### Source-Only Follow-Up Review

At the user's request, this follow-up reviewed documentation and source code only. No commands, tests, builds, containers, or live services were run. The findings above are grounded in the checked-in handlers, frontend event wiring, and test cases; runtime claims from earlier records were not independently revalidated.

The release checklist and known-issues record also conflict: the checklist says push and successful Actions evidence are pending, while known issues says the branch is pushed and the latest Student 2 Actions run failed during backend test collection. Reconcile both documents against the actual remote run before using either as report evidence.

### Current Evidence

All seven manually started shared/Student 1/Student 2 containers are running locally, and port `5100` is bound to the shared frontend. This confirms current process state only; it is not a recorded clean Compose deployment because the local Docker installation lacks the Compose plugin. No new functional tests were run during this review at the user's request.

**Verdict:** Student 2 is not Release 0 submission-ready. In addition to the existing CI, Compose, agentic-loop, browser, and report evidence gaps, frontend trip update and parent-relative stop/date integrity must be fixed and covered by focused tests before the implementation can accurately claim complete CRUD.

## 2026-09-02 - Release 0 Criteria Reassessment

**Scope:** Current Student 2 implementation and checked-in evidence assessed against all ten Release 0 marking criteria.

### Findings

| Severity | Criterion | Finding |
|---|---|---|
| Blocking | 4, 5 | No finalised Student 2 Plan/Act/Observe/Adapt runner record exists. The itinerary response's `agentTrace` is application narration and does not demonstrate the assessed two-model development workflow or human decision. |
| Blocking | 6, 9 | No successful `student-2.yml` run URL or screenshot is recorded. The checklist says push/PR are pending while `known-issues.md` says the branch was pushed and CI failed, so the evidence records must be reconciled against GitHub. |
| Blocking | 7, 9 | No clean shared `docker compose up --build` execution, service-health capture, routing capture, or persistence-after-restart evidence is recorded. Manually started containers do not prove the required Compose workflow. |
| Blocking | 9, 10 | Integrated screenshots, attendance checkpoint, published showcase URL, and Student 2 demonstration timestamp are absent. These cannot receive implementation credit without durable report/showcase evidence. |
| Required | 8 | Full trip CRUD is not available through the frontend: trips can be created, opened, and deleted, but there is no trip-edit control or `PUT /trips/{id}` browser path. |
| Required | 8 | Normal stop create/update validates day only against 1-31, not the parent trip duration. A short trip can therefore contain an out-of-range stop. |
| Required | 8 | Updating a trip can shorten its date range without rejecting or reconciling existing stops that then fall outside the trip. |
| Required | 8 | Updating a stop to a nonexistent `tripId` can raise an uncaught SQLite foreign-key error and return HTTP 500 rather than a controlled 400/404 response. |
| Required | 2, 8 | Automated coverage does not exercise frontend trip update, stop update/delete/regeneration, whole-trip regeneration, parent-relative stop dates, trip shortening, failed foreign-key updates, or an explicit cascade-delete assertion. |
| Evidence gap | 3 | Ollama integration, strict model-output validation, and deterministic fallback exist in source, but no genuine frontend-triggered AI success or forced-fallback capture identifies the exact approved model tag in use. |
| Evidence gap | 1, 9 | Requirements are documented locally but are not yet linked from the shared sprint backlog/report plan. GitHub commit/PR evidence and the report-facing repository/integration evidence remain incomplete. |

### Criterion Assessment

| No. | Criterion | Current assessment |
|---:|---|---|
| 1 | Project setup | Partially evidenced: structure, routing, seed data, Dockerfiles, workflow, and shared Ollama wiring exist; remote and integrated execution evidence is incomplete. |
| 2 | Service implementation | Implemented in source with health endpoints and HTTP service boundaries; operational integrated execution is not yet evidenced. |
| 3 | AI-Mode integration | Implemented in source with an approved default model and fallback; live integrated proof is pending. |
| 4 | Agentic AI workflow | Not evidenced for Student 2. |
| 5 | Prompt engineering and context | Application prompt and AI activity records exist; the genuine loop record, model roles, selected context, validation, and human decision evidence are incomplete. |
| 6 | DevOps and GitHub Actions | Workflow is implemented; successful remote execution evidence is missing. |
| 7 | Docker Compose integration | Student 2 services are wired into the shared file; successful clean Compose execution evidence is missing. |
| 8 | Working software | Partial: create/read/delete trips and stop CRUD/regeneration exist, but frontend trip update and data-integrity handling are incomplete. |
| 9 | Technical report | In progress; substantial execution, screenshot, commit/PR, attendance, and showcase evidence remains. |
| 10 | Project demonstration | Not evidenced. |

**Verdict:** Not Release 0 submission-ready. Fix the four Criterion 8 implementation defects first, then capture the agentic-loop, CI, Compose, browser, report, attendance, and showcase evidence needed to turn source-level claims into assessable proof.

### Validation Note

Independent execution on 2026-09-02 was blocked by the available shell environment: Python was not on `PATH`, frontend test dependencies were not installed (`vitest` unavailable), and the installed Docker Compose command rejected `config --quiet`. The source-level defects and missing evidence above were therefore not reclassified as runtime-tested findings. VS Code reported no diagnostics in the Student 2 workflow or root Compose file.

### Feature-Fix Resolution

The four Criterion 8 implementation defects from this reassessment were resolved on 2026-09-02:

- The frontend now edits persisted trip details through `PUT /api/trips/{id}` and reloads the complete saved itinerary.
- Backend and database APIs reject stop days outside the parent trip duration; the stop dialog mirrors the current duration.
- Trip updates reject date ranges that would exclude existing stops, preserving the prior trip and stops.
- Stop updates targeting a missing trip return a controlled `404` without modifying the existing stop.
- Focused coverage now includes frontend trip update, stop edit/regeneration/removal, whole-itinerary regeneration, parent-relative stop days, trip shortening, missing-parent updates, and cascade deletion.

Validation used disposable language-runtime containers because the host shell lacked Python/Vitest: database 5/5, backend 8/8, and frontend 4/4 tests pass. Criteria 4-7 and 9-10 evidence gaps remain open and are not resolved by these feature changes.

## 2026-09-02 - Post-Implementation Release 0 Review

**Scope:** Fresh review of Student 2 source, automated tests, current Compose runtime, shared integration, CI, and checked-in assessment evidence against the ten Release 0 criteria. This section supersedes earlier current-status claims but preserves them as historical review context.

### Verified Findings

| Severity | Criterion | Finding |
|---|---|---|
| Blocking evidence | 4, 5 | No finalised Student 2 two-model Plan/Act/Observe/Adapt record exists under `docs/agentic-loop-records/`. The application `agentTrace` is not development-loop evidence. |
| Blocking evidence | 6, 9, 10 | No successful Student 2 Actions URL, technical report artifact, integrated screenshot set, attendance checkpoint, published showcase URL, or Student 2 video timestamp is checked in. |
| High integration risk | 1, 7 | Student 2 is integrated and healthy, but the group Compose application still lacks complete backend/database sets for Students 4 and 5. The required integrated five-feature application is therefore not evidenced as complete. |
| High compliance risk | 1 | The Release 0 brief explicitly requests a shared HTMX index, while the shared entry point is Vue. Student 2's README also still describes its frontend as HTMX although its implementation is plain HTML/CSS/JavaScript. Confirm tutor acceptance or align implementation and documentation. |
| Required fix | 8 | Stop update accepts a client-supplied `tripId` and the database updates `trip_id`, allowing an existing stop to be moved to another valid trip. The requirement describes stop updates as day/activity/notes changes, so ownership should be derived from the stored stop and remain immutable. |
| Required fix | 8 | The stop form submits `sortOrder: 99` for both create and edit. Editing an existing stop therefore silently moves it to the end instead of preserving its stored order. |
| Required fix | 2, 8 | API failures open the custom error dialog but do not replace stale live-region text such as “Planning your itinerary...” or “Regenerating the itinerary...”, producing contradictory status feedback. |
| Test gap | 2, 3, 7 | CI validates isolated mocked suites, Compose syntax, and image builds, but does not start the stack or smoke-test shared proxy, backend/database HTTP boundaries, persistence, or controlled Ollama success/fallback behavior. |
| Documentation risk | 6, 7, 9 | `release-0-checklist.md`, `known-issues.md`, `contribution-log.md`, and earlier review sections contain stale or conflicting branch, Compose, test-count, push, and CI claims. Reconcile them before report use. |

### Criterion Assessment

| No. | Criterion | Repository and runtime support |
|---:|---|---|
| 1 | Project setup | Partial: Student 2 structure, seeded data, workflow, shared route, and model configuration exist; shared HTMX compliance and complete five-feature integration remain unresolved. |
| 2 | Service implementation | Supported for Student 2 locally: frontend, backend, and database services are healthy and integrated; error-state consistency and CI integration coverage remain open. |
| 3 | AI-Mode integration | Partial: approved-model Ollama invocation, strict output validation, and fallback exist in source; genuine frontend-triggered AI success evidence is absent. |
| 4 | Agentic AI workflow | Unsupported by evidence: shared runner assets exist but no finalised Student 2 execution record exists. |
| 5 | Prompt engineering and context | Partial: versioned application prompt and AI logs exist; assessed two-model context, review, adaptation, and human-decision record is absent. |
| 6 | DevOps and GitHub Actions | Partial: the workflow runs all isolated suites, validates Compose, and builds images; no successful remote run is recorded and no runtime smoke test exists. |
| 7 | Docker Compose integration | Partial: the live Student 2 path is healthy through shared Compose routing, but complete group integration and durable evidence are incomplete. |
| 8 | Working software | Substantially implemented: browser/backend/database CRUD and generation workflows run, with stop ownership, ordering, and stale-error-state defects still requiring correction. |
| 9 | Technical report | Partial: extensive feature documentation exists, but the report and required CI, AI, browser, attendance, and execution evidence are incomplete. |
| 10 | Project demonstration | Unsupported by evidence: no published video, attendance record, or Student 2 timestamp is present. |

### Validation Evidence

- Frontend Vitest: 6/6 passed in Node 22.
- Backend pytest: 8/8 passed in Python 3.11.
- Database pytest: 5/5 passed in Python 3.11.
- `docker compose config --quiet`: passed.
- `shared-frontend`, `student2-frontend`, `student2-backend`, `student2-database`, and `ollama`: running and healthy.
- Shared home, `/itinerary/`, and `/itinerary-api/trips`: HTTP 200.
- Current persisted development data: 11 trips and 11 stops; fresh initialization source creates 10 trips and 20 stops.

**Verdict:** Student 2 is functionally substantial and locally integrated, but not yet Release 0 submission-ready. Fix the three implementation defects, add an integrated CI smoke test, reconcile stale documentation, and capture the missing AI, agentic-loop, Actions, report, attendance, and showcase evidence.

## 2026-09-02 - Required Fix Resolution

**Scope:** Resolution of the implementation, CI, and documentation findings from the post-implementation review.

| Previous finding | Resolution | Evidence |
|---|---|---|
| Client-controlled stop ownership | Resolved. Backend and database update handlers derive `tripId` from the stored stop and never update `trip_id`. | Backend ownership regression passes; database forged-`tripId` regression passes. |
| Stop edits overwrite ordering | Resolved. The frontend preserves stored `sortOrder`, and both APIs derive it from the stored stop rather than trusting an update payload; new stops receive the next order within their selected day. | Frontend request-payload and API forged-order regressions pass. |
| API errors leave stale progress text | Resolved. Opening an error dialog clears the live status region first. | Frontend failed-planning regression passes. |
| CI has no runtime integration check | Resolved in workflow. CI starts the three Student 2 services without Ollama dependencies, waits for health, and verifies backend-to-database retrieval of at least 10 trips. | Exact Compose startup and smoke commands pass locally with 11 trips. Remote Actions evidence remains pending. |
| Current documents conflict | Resolved for current-status documents. Historical review entries remain unchanged as dated evidence. | README, checklist, feature/risk plans, known issues, contribution log, and prompt log use the current branch and validation state. |

Validation after the fixes: frontend 6/6, backend 10/10, database 5/5; Compose configuration valid; Student 2 frontend, backend, and database healthy; backend trip retrieval returned 11 records. A genuine shared-route request produced trip 14 in `ai` mode with two stops on each day; the preceding invalid model shape produced trip 13 in deterministic `fallback` mode with complete coverage.

**Current verdict:** The identified Student 2 implementation defects and local AI execution requirement are resolved. Remaining blockers are evidence or team-owned work: a finalised human-controlled two-model loop record, a successful remote Actions run, clean-checkout/browser/report evidence, complete Student 4/5 service integration, and retained tutor acceptance of the shared Vue frontend.