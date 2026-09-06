[CmdletBinding()]
param(
    [ValidateSet("Feature", "AgenticLoop", "All")]
    [string]$Area = "All"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path

function Invoke-Checked {
    param([string]$FilePath, [string[]]$Arguments, [string]$FailureMessage)
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) { throw $FailureMessage }
}

if ($Area -in @("Feature", "All")) {
    Invoke-Checked "npm" @("ci", "--prefix", "$repositoryRoot/student-1/frontend") "Student 1 frontend dependency installation failed."
    Invoke-Checked "npm" @("test", "--prefix", "$repositoryRoot/student-1/frontend") "Student 1 frontend tests failed."
    Invoke-Checked "npm" @("run", "build", "--prefix", "$repositoryRoot/student-1/frontend") "Student 1 frontend build failed."
    Invoke-Checked "dotnet" @("restore", "$repositoryRoot/student-1/backend/tests/Backend.Tests.csproj") "Student 1 backend restore failed."
    Invoke-Checked "dotnet" @("test", "$repositoryRoot/student-1/backend/tests/Backend.Tests.csproj", "--configuration", "Release", "--no-restore") "Student 1 backend tests failed."
    Invoke-Checked "dotnet" @("restore", "$repositoryRoot/student-1/database/tests/Database.Tests.csproj") "Student 1 database restore failed."
    Invoke-Checked "dotnet" @("test", "$repositoryRoot/student-1/database/tests/Database.Tests.csproj", "--configuration", "Release", "--no-restore") "Student 1 database tests failed."
}

if ($Area -in @("AgenticLoop", "All")) {
    Invoke-Checked "dotnet" @("restore", "$repositoryRoot/ai-services/agentic-loop/tests/AgenticLoop.Tests.csproj") "Agentic-loop restore failed."
    Invoke-Checked "dotnet" @("test", "$repositoryRoot/ai-services/agentic-loop/tests/AgenticLoop.Tests.csproj", "--configuration", "Release", "--no-restore") "Agentic-loop tests failed."
}
