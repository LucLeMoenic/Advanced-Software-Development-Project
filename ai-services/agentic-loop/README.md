# Shared Two-Model Agentic Loop

This native .NET 8 command-line application extends the Release 0 loop. It uses two distinct models from the shared native Ollama runtime:

- implementer: Plan and Act;
- reviewer: Observe;
- human-controlled Adapt: apply/change/reject and post-test evidence.

It never writes source files, executes arbitrary shell commands, commits, or pushes. It reads explicitly named UTF-8 context files and writes auditable JSON records. Release 1 modes additionally perform bounded, read-only HTTP observations through a local feature backend.

## Setup

Install native Ollama and .NET 8, then run from the repository root. Shell processes do not automatically load Compose's `.env` file:

```powershell
ollama pull qwen2.5-coder:7b
ollama pull llama3.2:3b
$env:IMPLEMENTER_MODEL = 'qwen2.5-coder:7b'
$env:REVIEWER_MODEL = 'llama3.2:3b'
$env:OLLAMA_URL = 'http://127.0.0.1:11434'
```

The example configuration references two unique local models:

- `qwen2.5-coder:7b` for implementation;
- `llama3.2:3b` for review and the accommodation application's single model.

Models are not downloaded by Compose or CI. All application and loop consumers use this one native runtime. The CLI locates the repository root from the working directory's ancestors, including when `dotnet run --project` starts in the project folder. Outside the repository, pass an absolute `--workspace`; explicit prompt options remain supported.

## Run

Run the pre-test manually, then pass the real command and result:

```powershell
dotnet run --project ai-services/agentic-loop -- run `
  --task "Implement the selected bounded change" `
  --context "student-1/docs/context.md" `
  --context "path/to/relevant/source-file" `
  --pre-test-command "dotnet test path/to/tests" `
  --pre-test-result "All 12 tests passed before the change."
```

The command prints Plan, Act, Observe, and Adapt and writes a pending record under `docs/agentic-loop-records/`.

After the human applies or rejects the proposal and runs the post-test:

```powershell
dotnet run --project ai-services/agentic-loop -- finalise `
  --record "docs/agentic-loop-records/<record>.json" `
  --decision changed `
  --notes "Applied the reviewer correction; rejected unrelated suggestions." `
  --post-test-command "dotnet test path/to/tests" `
  --post-test-result "All 14 tests passed after the change."
```

Only finalised records are suitable for report evidence.

The `run` command records supplied test commands/results. The human runs tests and controls all source changes.

## Release 1 Validation Modes

Start native MCP/RAG and the feature containers first. These initial fixtures use Student 2's backend routes; other features must add their own contract fixtures to the same shared modes, not duplicate the loop.

```powershell
dotnet run --project ai-services/agentic-loop -- validate-mcp `
  --task 'Validate the itinerary tool boundary and captured summary against the design.' `
  --context ai-services/mcp-server/tools/itinerary.py `
  --backend-url http://127.0.0.1:5202 --trip-id 10

dotnet run --project ai-services/agentic-loop -- validate-rag `
  --task 'Validate the captured answer against its cited knowledge; report unsupported claims.' `
  --context ai-services/rag-server/knowledge/student-2/budget-basics.md `
  --question 'Is budget the total for the trip?'
```

These commands capture timestamped HTTP status, exact response and deterministic contract outcome as pre-test evidence before the normal Plan/Act/Observe/Adapt cycle. Only a loopback HTTP origin is accepted; paths and read-only POST bodies are fixed. Redirects are disabled, response size is bounded to 16000 bytes, and each observation has a 35-second deadline. Dependency failures and insufficient context must not be described as successful grounded answers. The models' verdicts do not override a failed contract check or prove entailment. Native Ollama is required to complete either loop mode.

Records include `validationMode` while retaining the existing finalisation schema. Finalise only after human verification and real post-test evidence. A backend observation does not replace protocol discovery, frontend screenshots, or manual source-support checks. Do not submit unit-test model doubles as live loop evidence.

## Tests

```powershell
dotnet test .\ai-services\agentic-loop\tests\AgenticLoop.Tests.csproj
```
