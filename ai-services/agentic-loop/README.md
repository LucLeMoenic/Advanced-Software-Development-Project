# Shared Two-Model Agentic Loop

This .NET 8 container is part of the integrated Release 0 application. It uses two distinct models from the shared local Ollama runtime:

- implementer: Plan and Act;
- reviewer: Observe;
- human-controlled Adapt: apply/change/reject and post-test evidence.

It never writes source files, runs validation commands, commits, or pushes. It reads only explicitly named UTF-8 context files and writes auditable JSON records.

## Setup

Copy `.env.example` to `.env` and set the required model tags. Compose checks each tag and pulls it only when it is missing from the persistent Ollama volume:

```powershell
docker compose up -d agentic-loop
```

The example configuration references two unique local models:

- `qwen2.5-coder:7b` for implementation;
- `llama3.2:3b` for review and the accommodation application's single model.

If a configured model is missing, the shared `ollama-model-setup` job downloads it before AI consumers start. The job also preloads `APPLICATION_MODEL` so the accommodation backend does not spend its request timeout loading a cold model. The agentic loop and application microservices all use the single `ollama` runtime and persistent model store.

## Run

Run the pre-test manually, then pass the real command and result:

```powershell
docker compose exec agentic-loop dotnet /app/AgenticLoop.dll run `
  --task "Implement the selected bounded change" `
  --context "student-1/docs/context.md" `
  --context "path/to/relevant/source-file" `
  --pre-test-command "dotnet test path/to/tests" `
  --pre-test-result "All 12 tests passed before the change."
```

The command prints Plan, Act, Observe, and Adapt and writes a pending record under `docs/agentic-loop-records/`.

After the human applies or rejects the proposal and runs the post-test:

```powershell
docker compose exec agentic-loop dotnet /app/AgenticLoop.dll finalise `
  --record "/workspace/docs/agentic-loop-records/<record>.json" `
  --decision changed `
  --notes "Applied the reviewer correction; rejected unrelated suggestions." `
  --post-test-command "dotnet test path/to/tests" `
  --post-test-result "All 14 tests passed after the change."
```

Only finalised records are suitable for report evidence.

The service intentionally records supplied test commands/results rather than executing arbitrary shell commands. The human runs tests and controls all source changes.

## Tests

```powershell
dotnet test .\ai-services\agentic-loop\tests\AgenticLoop.Tests.csproj
docker build -t asd-agentic-loop .\ai-services\agentic-loop
```
