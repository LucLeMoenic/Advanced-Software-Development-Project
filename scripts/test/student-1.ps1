[CmdletBinding()]
param(
    [ValidateSet("Feature", "AgenticLoop", "All")]
    [string]$Area = "All"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
# On Windows, npm may resolve to an npm.ps1 shim that mis-parses splatted arguments.
$npm = if ($IsWindows) { "npm.cmd" } else { "npm" }
# CI uses the runner's python; locally, point STUDENT1_PYTHON at a virtual environment's interpreter.
$python = if ($env:STUDENT1_PYTHON) { $env:STUDENT1_PYTHON } else { "python" }

function Invoke-Checked {
    param([string]$FilePath, [string[]]$Arguments, [string]$FailureMessage)
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) { throw $FailureMessage }
}

if ($Area -in @("Feature", "All")) {
    Invoke-Checked $npm @("ci", "--prefix", "$repositoryRoot/student-1/frontend") "Student 1 frontend dependency installation failed."
    Invoke-Checked $npm @("test", "--prefix", "$repositoryRoot/student-1/frontend") "Student 1 frontend tests failed."
    Invoke-Checked $npm @("run", "build", "--prefix", "$repositoryRoot/student-1/frontend") "Student 1 frontend build failed."
    Invoke-Checked "dotnet" @("restore", "$repositoryRoot/student-1/backend/tests/Backend.Tests.csproj") "Student 1 backend restore failed."
    Invoke-Checked "dotnet" @("test", "$repositoryRoot/student-1/backend/tests/Backend.Tests.csproj", "--configuration", "Release", "--no-restore") "Student 1 backend tests failed."
    Invoke-Checked "dotnet" @("restore", "$repositoryRoot/student-1/database/tests/Database.Tests.csproj") "Student 1 database restore failed."
    Invoke-Checked "dotnet" @("test", "$repositoryRoot/student-1/database/tests/Database.Tests.csproj", "--configuration", "Release", "--no-restore") "Student 1 database tests failed."
    Invoke-Checked $python @("-m", "pip", "install", "--quiet", "-r", "$repositoryRoot/ai-services/mcp-server/requirements.txt", "-r", "$repositoryRoot/ai-services/rag-server/requirements.txt") "Shared MCP/RAG server dependency installation failed."
    Push-Location "$repositoryRoot/ai-services/mcp-server"
    try { Invoke-Checked $python @("-m", "pytest", "tests/test_accommodation_tools.py") "Student 1 MCP tool tests failed." } finally { Pop-Location }
    # Offline only: retrieval and dataset-candidate checks; live model evaluation is skipped unless RAG_LIVE_EVAL=1.
    Push-Location "$repositoryRoot/ai-services/rag-server"
    try { Invoke-Checked $python @("-m", "pytest", "tests/test_student1_retrieval.py", "tests/test_retrieval.py") "Student 1 RAG retrieval tests failed." } finally { Pop-Location }
}

if ($Area -in @("AgenticLoop", "All")) {
    Invoke-Checked "dotnet" @("restore", "$repositoryRoot/ai-services/agentic-loop/tests/AgenticLoop.Tests.csproj") "Agentic-loop restore failed."
    Invoke-Checked "dotnet" @("test", "$repositoryRoot/ai-services/agentic-loop/tests/AgenticLoop.Tests.csproj", "--configuration", "Release", "--no-restore") "Agentic-loop tests failed."
}
